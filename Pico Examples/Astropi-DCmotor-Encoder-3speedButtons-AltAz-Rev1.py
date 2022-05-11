import time
from machine import Pin, UART, PWM, ADC

COMMAND_PARSE = b'\n'


# Orion 8-10in alt az replacement for bad control board
# DC motors and shaft IR encoders
# for raspberry pi pico to control factory drives and encoders
# az drive uses 0.000624 deg/count at shaft encoder
# alt drive uses 0.00073 deg/count at shaft encoder
# uart communication to/from raspberry pi for counts setpoint and modes
# save as main.py on pico to auto run

class AltAzProcess:
    uart = None  # type: UARTProcess

    def __init__(self):
        self.loop_count = 0

        self.alt_steps = 0
        self.alt_manual = False
        self.alt_steps_adder = 0
        self.alt_steps_sp = 0
        self.alt_diff = 0
        self.az_steps = 0
        self.az_manual = False
        self.az_steps_adder = 0
        self.az_steps_sp = 0
        self.az_diff = 0
        self.drive_data = ""

        self.speed_adj_alt = [1,1,1.06,1.085,1.11,1.135,1.16,1.185,1.21,1.235,1.26]
        self.speed_adj_az = [1,1,1.22,1.245,1.27,1.295,1.32,1.345,1.37,1.395,1.42]
        self.speed_scale = 0.000408  # 1/2450 for 11 lookups

        self.alt_dir = 0
        self.az_dir = 0
        self.alt_dir_count = 0
        self.az_dir_count = 0
        self.alt_control_dir = 0
        self.az_control_dir = 0
        self.alt_control_SP_last = 0
        self.az_control_SP_last = 0
        self.alt_duty = 0  # 0-65535 use 38% or 25000 max
        self.az_duty = 0  # 0-65535 use 38% or 25000 max
        self.max_duty = 25000
        self.duty75 = 22500
        self.duty30 = 7500
        self.duty15 = 2500  # 3000 minimum
        self.man_speed_value = 0
        self.freq = 10

        self.alt_up_sw = Pin(28, Pin.IN, Pin.PULL_DOWN)
        self.alt_down_sw = Pin(27, Pin.IN, Pin.PULL_DOWN)
        self.az_left_sw = Pin(26, Pin.IN, Pin.PULL_DOWN)
        self.az_right_sw = Pin(22, Pin.IN, Pin.PULL_DOWN)
        self.speed8_sw = Pin(21, Pin.IN, Pin.PULL_DOWN)
        self.speed16_sw = Pin(20, Pin.IN, Pin.PULL_DOWN)

        self.alt_shaft_counter_clock = Pin(10, Pin.IN, Pin.PULL_DOWN)
        self.alt_shaft_counter_clock.irq(trigger=Pin.IRQ_RISING, handler=self.alt_shaft_counter_callback)

        self.az_shaft_counter_clock = Pin(19, Pin.IN, Pin.PULL_DOWN)
        self.az_shaft_counter_clock.irq(trigger=Pin.IRQ_RISING, handler=self.az_shaft_counter_callback)

        self.alt_pwm_cw = PWM(Pin(8))  # create PWM object from a pin
        self.alt_pwm_cw.freq(self.freq)  # set frequency
        self.alt_pwm_cw.duty_u16(0)  # set duty cycle, range 0-65535
        self.alt_pwm_ccw = PWM(Pin(9))  # create PWM object from a pin
        self.alt_pwm_ccw.freq(self.freq)  # set frequency
        self.alt_pwm_ccw.duty_u16(0)  # set duty cycle, range 0-65535

        self.az_pwm_cw = PWM(Pin(15))  # create PWM object from a pin
        self.az_pwm_cw.freq(self.freq)  # set frequency
        self.az_pwm_cw.duty_u16(0)  # set duty cycle, range 0-65535
        self.az_pwm_ccw = PWM(Pin(14))  # create PWM object from a pin
        self.az_pwm_ccw.freq(self.freq)  # set frequency
        self.az_pwm_ccw.duty_u16(0)  # set duty cycle, range 0-65535

    def alt_shaft_counter_callback(self, pin):

        if self.alt_dir_count:
            if self.alt_manual:
                self.alt_steps_adder += self.speed_adj_alt[int(self.man_speed_value * self.speed_scale)]
            else:
                self.alt_steps += self.speed_adj_alt[int(self.alt_duty * self.speed_scale)]
        else:
            if self.alt_manual:
                self.alt_steps_adder -= self.speed_adj_alt[int(self.man_speed_value * self.speed_scale)]
            else:
                self.alt_steps -= self.speed_adj_alt[int(self.alt_duty * self.speed_scale)]

    def az_shaft_counter_callback(self, pin):

        if self.az_dir_count:
            if self.az_manual:
                self.az_steps_adder += self.speed_adj_az[int(self.man_speed_value * self.speed_scale)]
            else:
                self.az_steps += self.speed_adj_az[int(self.az_duty * self.speed_scale)]
        else:
            if self.az_manual:
                self.az_steps_adder -= self.speed_adj_az[int(self.man_speed_value * self.speed_scale)]
            else:
                self.az_steps -= self.speed_adj_az[int(self.az_duty * self.speed_scale)]

    def altdrive(self, Hz, Dir, Duty):
        self.alt_dir_count = Dir
        if Dir:
            self.alt_pwm_ccw.duty_u16(0)  # 0=off
            self.alt_pwm_cw.duty_u16(Duty)
            self.alt_pwm_cw.freq(Hz)  # set frequency
        else:
            self.alt_pwm_cw.duty_u16(0)  # 0=off
            self.alt_pwm_ccw.duty_u16(Duty)
            self.alt_pwm_ccw.freq(Hz)  # set frequency

    def azdrive(self, Hz, Dir, Duty):
        self.az_dir_count = Dir
        if Dir:
            self.az_pwm_ccw.duty_u16(0)  # 0=off
            self.az_pwm_cw.duty_u16(Duty)
            self.az_pwm_cw.freq(Hz)  # set frequency
        else:
            self.az_pwm_cw.duty_u16(0)  # 0=off
            self.az_pwm_ccw.duty_u16(Duty)
            self.az_pwm_ccw.freq(Hz)  # set frequency

    def tick(self):

        self.loop_count += 1
        if self.loop_count >= 5:
            self.loop_count = 0

            prev_drive_data = self.drive_data
            status = 'unknown'
            if self.alt_diff > 15 or self.az_diff > 15 and self.uart.control_mode == 2:
                status = "Slewing"
            if self.alt_diff < 15 or self.az_diff < 15 and self.uart.control_mode == 2:
                status = "Tracking"
            if self.uart.alt_steps_sp == 0 and self.uart.alt_steps_sp == 0 and self.uart.control_mode == 2:
                status = "Slewing Home"
            if self.alt_diff < 5 and self.az_diff < 5 and self.uart.alt_steps_sp == 0 and self.uart.alt_steps_sp == 0:
                status = "Home Pos"
            if self.uart.control_mode < 2:
                status = "Stopped"
            alt_diff = "{:.1f}".format(self.alt_diff)
            az_diff = "{:.1f}".format(self.az_diff)
            alt_steps = "{:.1f}".format(self.alt_steps)
            az_steps = "{:.1f}".format(self.az_steps)
            alt_steps_adder = "{:.1f}".format(self.alt_steps_adder)
            az_steps_adder = "{:.1f}".format(self.az_steps_adder)
            az_duty = int(self.az_duty * .004)
            alt_duty = int(self.az_duty * .004)
            self.drive_data = '{0},{1},{2},{3},{4},{5},{6},{7},{8}'.format(
                alt_steps,
                alt_steps_adder,
                alt_diff,
                az_steps,
                az_steps_adder,
                az_diff,
                status,
                az_duty,
                alt_duty
            )

            if prev_drive_data != self.drive_data:
                print('ControlProcess', self.drive_data)
                self.uart.send()

        #  manual buttons
        self.man_speed_value = self.duty15 + (self.speed8_sw.value() * self.duty30) + (
                self.speed16_sw.value() * self.duty75)
        if self.alt_up_sw.value():
            self.alt_manual = True
            self.alt_dir = 1
            self.altdrive(self.freq, self.alt_dir, self.man_speed_value)

        if self.alt_down_sw.value():
            self.alt_manual = True
            self.alt_dir = 0
            self.altdrive(self.freq, self.alt_dir, self.man_speed_value)

        if self.alt_manual and not self.alt_up_sw.value() and not self.alt_down_sw.value():
            self.altdrive(self.freq, self.alt_dir, 0)  # off
            self.alt_manual = False

        if self.az_left_sw.value():
            self.az_manual = True
            self.az_dir = 1
            self.azdrive(self.freq, self.az_dir, self.man_speed_value)

        if self.az_right_sw.value():
            self.az_manual = True
            self.az_dir = 0
            self.azdrive(self.freq, self.az_dir, self.man_speed_value)

        if self.az_manual and not self.az_left_sw.value() and not self.az_right_sw.value():
            self.azdrive(self.freq, self.az_dir, 0)  # off
            self.az_manual = False

        if self.uart.control_mode < 2 and not self.alt_manual and not self.az_manual:
            self.alt_duty = 0
            self.az_duty = 0
            self.altdrive(self.freq, self.alt_dir, self.alt_duty)  # off
            self.azdrive(self.freq, self.az_dir, self.az_duty)  # off

        # Alt direction and error diff
        if self.uart.alt_steps_sp >= self.alt_steps:  # Up
            self.alt_diff = int(self.uart.alt_steps_sp - self.alt_steps)
            self.alt_dir = 1  # Up
        else:  # Down
            self.alt_diff = int(self.alt_steps - self.uart.alt_steps_sp)
            self.alt_dir = 0  # Down

        # Alt control direction
        if self.uart.alt_steps_sp >= self.alt_control_SP_last:
            self.alt_control_dir = 1  # Up
        else:
            self.alt_control_dir = 0  # Down
        self.alt_control_SP_last = self.uart.alt_steps_sp

        # Az direction and error diff
        if self.uart.az_steps_sp > self.az_steps:  # Right
            self.az_diff = int(self.uart.az_steps_sp - self.az_steps)
            self.az_dir = 1  # Right
        else:  # Left
            self.az_diff = int(self.az_steps - self.uart.az_steps_sp)
            self.az_dir = 0  # Left

        # Az control direction
        if self.uart.az_steps_sp >= self.az_control_SP_last and self.uart.az_steps_sp != self.az_control_SP_last:
            self.az_control_dir = 1  # Right
        elif self.uart.az_steps_sp < self.az_control_SP_last and self.uart.az_steps_sp != self.az_control_SP_last:
            self.az_control_dir = 0  # Left
        self.az_control_SP_last = self.uart.az_steps_sp

        # track mode
        if self.uart.control_mode == 2 and not self.alt_manual and not self.az_manual:

            if self.uart.alt_steps_sp == 0:
                self.alt_control_dir = self.alt_dir

            if self.uart.az_steps_sp == 0:
                self.az_control_dir = self.az_dir

            # Alt tracking/Slewing
            if self.alt_diff <= 2 or (self.alt_diff < 20 and self.alt_control_dir != self.alt_dir):
                self.alt_duty = 0
                self.altdrive(self.freq, self.alt_control_dir, self.alt_duty)
            elif self.alt_diff >= 1500:
                self.alt_duty = self.max_duty
                self.altdrive(self.freq, self.alt_dir, self.alt_duty)
            elif self.alt_diff < 1500 and self.alt_diff >= 500:
                self.alt_duty = self.duty30
                self.altdrive(self.freq, self.alt_dir, self.alt_duty)
            elif self.alt_diff < 500 and self.alt_diff >= 100:
                self.alt_duty = int(self.duty30 / 2) + self.alt_diff
                self.altdrive(self.freq, self.alt_dir, self.alt_duty)
            elif self.alt_diff < 100 and self.alt_diff >= 50:
                self.alt_duty = self.duty15 + self.alt_diff
                self.altdrive(self.freq, self.alt_dir, self.alt_duty)
            elif self.alt_diff < 50 and self.alt_diff > 2:
                if self.alt_control_dir:
                    self.alt_duty = self.duty15
                    while self.uart.alt_steps_sp > self.alt_steps + 1:
                        self.altdrive(self.freq, self.alt_control_dir, self.alt_duty)
                    self.altdrive(self.freq, self.alt_control_dir, 0)
                else:
                    self.alt_duty = self.duty15
                    while self.uart.alt_steps_sp < self.alt_steps - 1:
                        self.altdrive(self.freq, self.alt_control_dir, self.alt_duty)
                    self.altdrive(self.freq, self.alt_control_dir, 0)

            # Az tracking/Slewing
            if self.az_diff <= 2 or (self.az_diff < 20 and self.az_control_dir != self.az_dir):
                self.az_duty = 0
                self.azdrive(self.freq, self.az_control_dir, self.az_duty)
            elif self.az_diff >= 1500:
                self.az_duty = self.max_duty
                self.azdrive(self.freq, self.az_dir, self.az_duty)
            elif self.az_diff < 1500 and self.az_diff >= 500:
                self.az_duty = self.duty30
                self.azdrive(self.freq, self.az_dir, self.az_duty)
            elif self.az_diff < 500 and self.az_diff >= 100:
                self.az_duty = int(self.duty30 / 2) + self.az_diff
                self.azdrive(self.freq, self.az_dir, self.az_duty)
            elif self.az_diff < 100 and self.az_diff >= 50:
                self.az_duty = self.duty15 + self.az_diff
                self.azdrive(self.freq, self.az_dir, self.az_duty)
            elif self.az_diff < 50 and self.az_diff > 2:
                if self.az_control_dir:
                    self.az_duty = self.duty15 + 500
                    while self.uart.az_steps_sp > self.az_steps + 1:
                        self.azdrive(self.freq, self.az_control_dir, self.az_duty)
                    self.azdrive(self.freq, self.az_control_dir, 0)
                else:
                    self.az_duty = self.duty15 + 500
                    while self.uart.az_steps_sp < self.az_steps - 1:
                        self.azdrive(self.freq, self.az_control_dir, self.az_duty)
                    self.azdrive(self.freq, self.az_control_dir, 0)


class UARTProcess:
    buffer: bytes

    alt_az: AltAzProcess

    def __init__(self):
        self.uart0 = UART(0, baudrate=9600, tx=Pin(0), rx=Pin(1))
        self.alt_steps_sp = 0
        self.az_steps_sp = 0
        self.control_mode = 0
        self.ra_osc = 0
        self.dec_osc = 0


        self.reset()

    def tick(self):
        if self.uart0.any():
            last_bytes: bytes = self.uart0.read()

            # print('UARTProcess', 'tick()')

            # TODO - does this cause blocking???
            while COMMAND_PARSE in last_bytes:
                index = last_bytes.index(COMMAND_PARSE)
                self.buffer += last_bytes[:index]
                last_bytes = last_bytes[index + 1:]

            self.buffer += last_bytes
            self.decode_buffer()
            self.reset()

    def send(self):
        #  TODO - Add Logic here to send some response back to the client
        response = '{0}\n'.format(self.alt_az.drive_data)
        self.uart0.write(response)

    def decode_buffer(self, decode: str = 'utf-8', split: str = ','):
        try:
            self.alt_steps_sp, self.az_steps_sp, self.control_mode, self.ra_osc, self.dec_osc = self.buffer.decode('utf-8').split(',')
            self.alt_steps_sp = float(self.alt_steps_sp)
            self.az_steps_sp = float(self.az_steps_sp)
            self.control_mode = int(self.control_mode)
            self.ra_osc = int(self.ra_osc)
            self.dec_osc = int(self.dec_osc)

            print('Received', 'AltSP ', self.alt_steps_sp, ' AzSP ', self.az_steps_sp, ' Control Mode ',
                  self.control_mode)
            if self.control_mode == 3:
                self.alt_steps_sp = 0
                self.az_steps_sp = 0
                self.control_mode = 2
                self.alt_az.alt_steps_adder = 0
                self.alt_az.az_steps_adder = 0
        except:
            print('Error trying to decode: {0}'.format(self.buffer))

    def reset(self):
        self.buffer = b''


def main():
    uart = UARTProcess()
    alt_az = AltAzProcess()

    # Pass the XXXProcess to each other Process
    uart.alt_az = alt_az
    alt_az.uart = uart

    while True:
        uart.tick()
        alt_az.tick()
        time.sleep(0.1)


if __name__ == '__main__':
    main()