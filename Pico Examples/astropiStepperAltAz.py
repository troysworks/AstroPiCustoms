import time
from machine import Pin, UART, PWM, ADC

# Astropi Customs 2-9-22
# Meade 8 alt az
# stepper motors and 1/16 microstep for tracking
# for raspberry pi Pico Examples
# az drive uses 0.00333 deg/count
# alt drive uses 0.01875 deg/count
# uart communication to/from raspberry pi for counts setpoint and modes
# save as main.py on Pico Examples to auto run

COMMAND_PARSE = b'\n'


class AltAzProcess:
    uart = None  # type: UARTProcess

    def __init__(self):
        self.max_speed = 200
        self.loop_count = 0
        self.alt_hz = 0
        self.az_hz = 0
        self.alt_dir = 0
        self.az_dir = 0
        self.duty50 = 32767
        self.step = 0.002083  # deg/step
        self.alt_diff = 0
        self.alt_manual = False
        self.alt_steps = 0
        self.alt_steps_adder = 0
        self.alt_steps_sp = 0
        self.az_diff = 0
        self.az_manual = False
        self.az_steps = 0
        self.az_steps_adder = 0
        self.az_steps_sp = 0
        self.drive_data = ""
        self.drive_status = ""
        self.alt_control_dir = 0
        self.az_control_dir = 0
        self.alt_control_SP_last = 0
        self.az_control_SP_last = 0
        self.man_speed_value = 0

        self.alt_pwm = PWM(Pin(6))  # create PWM object from a pin
        self.alt_pwm.freq(30)  # set frequency
        self.alt_pwm.duty_u16(0)  # set duty cycle, range 0-65535
        self.alt_counter = Pin(9, Pin.IN, Pin.PULL_DOWN)
        self.alt_counter.irq(trigger=Pin.IRQ_RISING, handler=self.alt_counter_callback)
        self.alt_dir_pin = Pin(8, Pin.OUT)
        self.alt_dir_pin.value(0)
        self.alt_step_pin = Pin(7, Pin.OUT)
        self.alt_step_pin.value(0)
        self.alt_speed_pin = Pin(5, Pin.OUT)  # 1/16 Step when 1
        self.alt_speed_pin.value(0)

        self.az_pwm = PWM(Pin(10))  # create PWM object from a pin
        self.az_pwm.freq(30)  # set frequency
        self.az_pwm.duty_u16(0)  # set duty cycle, range 0-65535
        self.az_counter = Pin(13, Pin.IN, Pin.PULL_DOWN)
        self.az_counter.irq(trigger=Pin.IRQ_RISING, handler=self.az_counter_callback)
        self.az_dir_pin = Pin(12, Pin.OUT)
        self.az_dir_pin.value(0)
        self.az_step_pin = Pin(11, Pin.OUT)
        self.az_step_pin.value(0)
        self.az_speed_pin = Pin(14, Pin.OUT)  # 1/16 Step when 1
        self.az_speed_pin.value(0)

        self.alt_up_sw = Pin(28, Pin.IN, Pin.PULL_DOWN)
        self.alt_down_sw = Pin(27, Pin.IN, Pin.PULL_DOWN)
        self.az_left_sw = Pin(26, Pin.IN, Pin.PULL_DOWN)
        self.az_right_sw = Pin(22, Pin.IN, Pin.PULL_DOWN)
        self.speed8_sw = Pin(21, Pin.IN, Pin.PULL_DOWN)
        self.speed16_sw = Pin(20, Pin.IN, Pin.PULL_DOWN)

    def alt_drive(self, hz, direction, duty):
        if hz >= 10:
            self.alt_pwm.duty_u16(duty)  # 0=off
            self.alt_dir_pin.value(direction)
            self.alt_pwm.freq(hz)  # set frequency

    def alt_step(self, steps, direction):
        self.alt_dir_pin.value(direction)
        self.alt_pwm.duty_u16(0)  # 0=off
        if steps > 0:
            for x in range(steps):
                self.alt_step_pin.value(1)
                time.sleep(.0025)
                self.alt_step_pin.value(0)
                time.sleep(.0025)

    def alt_counter_callback(self, pin):

        if self.alt_manual:
            if self.alt_dir == 1:
                if self.alt_speed_pin.value():
                    self.alt_steps_adder += (1 / 16)
                else:
                    self.alt_steps_adder += 1

            else:
                if self.alt_speed_pin.value():
                    self.alt_steps_adder -= (1 / 16)
                else:
                    self.alt_steps_adder -= 1
        else:

            if self.alt_dir == 1:
                if self.alt_speed_pin.value():
                    self.alt_steps += (1 / 16)
                else:
                    self.alt_steps += 1

            else:
                if self.alt_speed_pin.value():
                    self.alt_steps -= (1 / 16)
                else:
                    self.alt_steps -= 1

    def az_drive(self, hz, direction, duty):
        if hz >= 10:
            self.az_pwm.duty_u16(duty)  # 0=off
            self.az_dir_pin.value(direction)
            self.az_pwm.freq(hz)  # set frequency

    def az_step(self, steps, direction):
        self.az_dir_pin.value(direction)
        self.az_pwm.duty_u16(0)  # 0=off
        if steps > 0:
            for x in range(steps):
                self.az_step_pin.value(1)
                time.sleep(.0025)  # TODO - Find non blocking alternative
                self.az_step_pin.value(0)
                time.sleep(.0025)  # TODO - Find non blocking alternative

    def az_counter_callback(self, pin):

        if self.az_manual:
            if self.az_dir == 1:
                if self.az_speed_pin.value():
                    self.az_steps_adder += (1 / 16)
                else:
                    self.az_steps_adder += 1

            else:
                if self.az_speed_pin.value():
                    self.az_steps_adder -= (1 / 16)
                else:
                    self.az_steps_adder -= 1
        else:

            if self.az_dir == 1:
                if self.az_speed_pin.value():
                    self.az_steps += (1 / 16)
                else:
                    self.az_steps += 1

            else:
                if self.az_speed_pin.value():
                    self.az_steps -= (1 / 16)
                else:
                    self.az_steps -= 1

    def tick(self):

        self.loop_count += 1
        if self.loop_count >= 5:
            self.loop_count = 0

            prev_drive_data = self.drive_data
            status = 'unknown'
            if self.alt_diff > 25 or self.az_diff > 25 and self.uart.control_mode == 2:
                status = "Slewing"
            if self.alt_diff < 25 and self.az_diff < 25 and self.uart.control_mode == 2:
                status = "Tracking"
            if self.uart.alt_steps_sp == 0 and self.uart.alt_steps_sp == 0 and self.uart.control_mode == 2:
                status = "Slewing Home"
            if self.alt_diff < 5 and self.az_diff < 5 and self.uart.alt_steps_sp == 0 and self.uart.alt_steps_sp == 0:
                status = "Home Pos"
            if self.uart.control_mode < 2:
                status = "Stopped"
            diff_alt = "{:.1f}".format(self.alt_diff)
            diff_az = "{:.1f}".format(self.az_diff)
            steps_alt = "{:.1f}".format(self.alt_steps)
            steps_az = "{:.1f}".format(self.az_steps)
            self.drive_data = '{0},{1},{2},{3},{4},{5},{6}'.format(
                steps_alt,
                self.alt_steps_adder,
                diff_alt,
                steps_az,
                self.az_steps_adder,
                diff_az,
                status
            )

            if prev_drive_data != self.drive_data:
                print('AltAzProcess', 'tick()', self.drive_data)
                self.uart.send()

        #  manual buttons
        self.man_speed_value = 60 + (self.speed8_sw.value() * 60) + (
                self.speed16_sw.value() * 140)
        if self.alt_up_sw.value():
            self.alt_manual = True
            self.alt_dir = 1
            self.alt_speed_pin.value(0)
            self.alt_drive(self.man_speed_value, self.alt_dir, self.duty50)
            # print('man_speed_value', self.man_speed_value, " up")

        if self.alt_down_sw.value():
            self.alt_manual = True
            self.alt_dir = 0
            self.alt_speed_pin.value(0)
            self.alt_drive(self.man_speed_value, self.alt_dir, self.duty50)
            # print('man_speed_value', self.man_speed_value, " down")

        if self.alt_manual and not self.alt_up_sw.value() and not self.alt_down_sw.value():
            self.alt_drive(self.man_speed_value, self.alt_dir, 0)  # off
            self.alt_manual = False
            # print('man_speed_value', self.man_speed_value, " off_alt")

        if self.az_left_sw.value():
            self.az_manual = True
            self.az_dir = 1
            self.az_speed_pin.value(0)
            self.az_drive(self.man_speed_value, self.az_dir, self.duty50)
            # print('man_speed_value', self.man_speed_value, " left")

        if self.az_right_sw.value():
            self.az_manual = True
            self.az_dir = 0
            self.az_speed_pin.value(0)
            self.az_drive(self.man_speed_value, self.az_dir, self.duty50)
            # print('man_speed_value', self.man_speed_value, " right")

        if self.az_manual and not self.az_left_sw.value() and not self.az_right_sw.value():
            self.az_drive(self.man_speed_value, self.az_dir, 0)  # off
            self.az_manual = False
            # print('man_speed_value', self.man_speed_value, " off_az")

        if self.uart.alt_steps_sp >= self.alt_steps:  # Up
            self.alt_diff = self.uart.alt_steps_sp - self.alt_steps
            self.alt_dir = 1  # Up
        else:  # Down
            self.alt_diff = self.alt_steps - self.uart.alt_steps_sp
            self.alt_dir = 0  # Down

        if self.uart.az_steps_sp > self.az_steps:  # Right
            self.az_diff = self.uart.az_steps_sp - self.az_steps
            self.az_dir = 1  # Right
        else:  # Left
            self.az_diff = self.az_steps - self.uart.az_steps_sp
            self.az_dir = 0  # Left

        # Track mode
        if self.uart.control_mode == 2 and not self.alt_manual and not self.az_manual:  # track mode

            # Alt control direction
            if self.uart.alt_steps_sp >= self.alt_control_SP_last and self.uart.alt_steps_sp != self.alt_control_SP_last:
                self.alt_control_dir = 1  # Up
            elif self.uart.alt_steps_sp < self.alt_control_SP_last and self.uart.alt_steps_sp != self.alt_control_SP_last:
                self.alt_control_dir = 0  # Down
            self.alt_control_SP_last = self.uart.alt_steps_sp

            # Az control direction
            if self.uart.az_steps_sp >= self.az_control_SP_last and self.uart.az_steps_sp != self.az_control_SP_last:
                self.az_control_dir = 1  # Right
            elif self.uart.az_steps_sp < self.az_control_SP_last and self.uart.az_steps_sp != self.az_control_SP_last:
                self.az_control_dir = 0  # Left
            self.az_control_SP_last = self.uart.az_steps_sp

            if self.uart.alt_steps_sp == 0:
                self.alt_control_dir = self.alt_dir

            if self.uart.az_steps_sp == 0:
                self.az_control_dir = self.az_dir

            alt_diff_micro = self.alt_diff * 16
            if alt_diff_micro <= 2 or (self.alt_diff < 1 and self.alt_control_dir != self.alt_dir):
                self.alt_drive(self.alt_hz, self.alt_control_dir, 0)  # off
                # print("alt_off ")
            elif self.alt_diff >= 5:
                self.alt_speed_pin.value(0)  # fast
                self.alt_hz = int(self.alt_diff * 4)
                if self.alt_hz > self.max_speed:
                    self.alt_hz = self.max_speed
                if self.alt_hz < 10:
                    self.alt_hz = 10
                self.alt_drive(self.alt_hz, self.alt_dir, self.duty50)
                # print("alt_mid ")
            elif alt_diff_micro > 1 and self.az_diff < 5:
                self.alt_speed_pin.value(1)  # slow
                self.alt_step(alt_diff_micro, self.alt_control_dir)
                # print("alt_slow ", "alt_diff_micro ", alt_diff_micro)

            az_diff_micro = self.az_diff * 16
            if az_diff_micro < 2 or (self.az_diff < 1 and self.az_control_dir != self.az_dir):
                self.az_drive(self.az_hz, self.az_control_dir, 0)  # off
                # print("az_off ")
            elif self.az_diff >= 5:
                self.az_speed_pin.value(0)  # fast
                self.az_hz = int(self.az_diff * 4)
                if self.az_hz > self.max_speed:
                    self.az_hz = self.max_speed
                if self.az_hz < 10:
                    self.az_hz = 10
                self.az_drive(self.az_hz, self.az_dir, self.duty50)
                # print("az_mid ")
            elif az_diff_micro > 0 and self.alt_diff < 5:
                self.az_speed_pin.value(1)  # slow
                self.az_step(az_diff_micro, self.az_control_dir)
                # print("az_slow ", "az_diff_micro ", az_diff_micro)

            # print('alt_diff ', self.alt_diff, ' alt_control_dir ', self.alt_control_dir, ' alt_dir ', self.alt_dir)
            # print('az_diff ', self.az_diff, ' az_control_dir ', self.az_control_dir, ' az_dir ', self.az_dir)


class UARTProcess:
    buffer: bytes

    alt_az: AltAzProcess

    def __init__(self):
        self.uart0 = UART(0, baudrate=9600, tx=Pin(0), rx=Pin(1))
        self.alt_steps_sp = 0
        self.az_steps_sp = 0
        self.control_mode = 0

        self.reset()

    def tick(self):
        if self.uart0.any():
            last_bytes: bytes = self.uart0.read()

            # print('UARTProcess', 'tick()')

            while COMMAND_PARSE in last_bytes:
                index = last_bytes.index(COMMAND_PARSE)
                self.buffer += last_bytes[:index]
                last_bytes = last_bytes[index + 1:]

            self.buffer += last_bytes
            self.decode_buffer()
            self.reset()

    def send(self):
        response = '{0}\n'.format(self.alt_az.drive_data)
        self.uart0.write(response)

    def decode_buffer(self, decode: str = 'utf-8', split: str = ','):
        try:
            self.alt_steps_sp, self.az_steps_sp, self.control_mode = self.buffer.decode('utf-8').split(',')
            self.alt_steps_sp = float(self.alt_steps_sp)
            self.az_steps_sp = float(self.az_steps_sp)
            self.control_mode = int(self.control_mode)
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
            # time.sleep(0.1)
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
        time.sleep(0.1)  # TODO - Can this be changed???


if __name__ == '__main__':
    main()
