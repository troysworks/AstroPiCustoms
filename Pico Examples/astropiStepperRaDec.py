import time
from machine import Pin, UART, PWM, ADC

# Astropi Customs 1-25-22
# Meade 8 Ra Dec st-4 guide-able
# stepper motors and 1/16 microstep for tracking
# for raspberry pi Pico Examples
# Ra drive uses 0.00333 deg/count
# Dec drive uses 0.01875 deg/count
# uart communication to/from raspberry pi for counts setpoint and modes
# save as main.py on Pico Examples to auto run

COMMAND_PARSE = b'\n'


class AltAzProcess:
    uart = None  # type: UARTProcess

    def __init__(self):
        self.max_speed = 200
        self.loop_count = 0
        self.dec_hz = 0
        self.ra_hz = 0
        self.dec_dir = 0
        self.ra_dir = 0
        self.duty50 = 32767
        self.step = 0.002083  # deg/step
        self.dec_diff = 0
        self.dec_manual = False
        self.dec_steps = 0
        self.dec_steps_adder = 0
        self.dec_steps_sp = 0
        self.dec_guide_adder = 0
        self.dec_guide_change_value = 10
        self.dec_guide_pos_flag = False
        self.dec_guide_neg_flag = False
        self.ra_diff = 0
        self.ra_manual = False
        self.ra_steps = 0
        self.ra_steps_adder = 0
        self.ra_steps_sp = 0
        self.ra_guide_adder = 0
        self.ra_guide_change_value = 10
        self.ra_guide_pos_flag = False
        self.ra_guide_neg_flag = False
        self.drive_data = ""
        self.drive_status = ""
        self.dec_control_dir = 0
        self.ra_control_dir = 0
        self.dec_control_sp_last = 0
        self.ra_control_sp_last = 0
        self.dec_control_sp = 0
        self.ra_control_sp = 0
        self.man_speed_value = 0

        self.dec_pwm = PWM(Pin(6))  # create PWM object from a pin
        self.dec_pwm.freq(30)  # set frequency
        self.dec_pwm.duty_u16(0)  # set duty cycle, range 0-65535
        self.dec_counter = Pin(9, Pin.IN, Pin.PULL_DOWN)
        self.dec_counter.irq(trigger=Pin.IRQ_RISING, handler=self.dec_counter_callback)
        self.dec_dir_pin = Pin(8, Pin.OUT)
        self.dec_dir_pin.value(0)
        self.dec_step_pin = Pin(7, Pin.OUT)
        self.dec_step_pin.value(0)
        self.dec_speed_pin = Pin(5, Pin.OUT)  # 1/16 Step when 1
        self.dec_speed_pin.value(0)
        self.dec_guide_neg = Pin(18, Pin.IN, Pin.PULL_DOWN)
        self.dec_guide_neg.irq(trigger=Pin.IRQ_RISING, handler=self.dec_guide_neg_callback)
        self.dec_guide_pos = Pin(17, Pin.IN, Pin.PULL_DOWN)
        self.dec_guide_pos.irq(trigger=Pin.IRQ_RISING, handler=self.dec_guide_pos_callback)

        self.ra_osc_sp = 19
        self.ra_osc = 19
        self.ra_pwm = PWM(Pin(10))  # create PWM object from a pin
        self.ra_pwm.freq(30)  # set frequency
        self.ra_pwm.duty_u16(0)  # set duty cycle, range 0-65535
        self.ra_counter = Pin(13, Pin.IN, Pin.PULL_DOWN)
        self.ra_counter.irq(trigger=Pin.IRQ_RISING, handler=self.ra_counter_callback)
        self.ra_dir_pin = Pin(12, Pin.OUT)
        self.ra_dir_pin.value(0)
        self.ra_step_pin = Pin(11, Pin.OUT)
        self.ra_step_pin.value(0)
        self.ra_speed_pin = Pin(14, Pin.OUT)  # 1/16 Step when 1
        self.ra_speed_pin.value(0)
        self.ra_guide_neg = Pin(19, Pin.IN, Pin.PULL_DOWN)
        self.ra_guide_neg.irq(trigger=Pin.IRQ_RISING, handler=self.ra_guide_neg_callback)
        self.ra_guide_pos = Pin(16, Pin.IN, Pin.PULL_DOWN)
        self.ra_guide_pos.irq(trigger=Pin.IRQ_RISING, handler=self.ra_guide_pos_callback)

        self.dec_up_sw = Pin(28, Pin.IN, Pin.PULL_DOWN)
        self.dec_down_sw = Pin(27, Pin.IN, Pin.PULL_DOWN)
        self.ra_left_sw = Pin(26, Pin.IN, Pin.PULL_DOWN)
        self.ra_right_sw = Pin(22, Pin.IN, Pin.PULL_DOWN)
        self.speed8_sw = Pin(21, Pin.IN, Pin.PULL_DOWN)
        self.speed16_sw = Pin(20, Pin.IN, Pin.PULL_DOWN)

    def dec_drive(self, hz, direction, duty):
        if hz < 15:
            hz = 15
        self.dec_pwm.duty_u16(duty)  # 0=off
        self.dec_dir_pin.value(direction)
        self.dec_pwm.freq(hz)  # set frequency

    def dec_step(self, steps, direction):
        self.dec_dir_pin.value(direction)
        self.dec_pwm.duty_u16(0)  # 0=off
        if steps > 0:
            for x in range(steps):
                self.dec_step_pin.value(1)
                time.sleep(.0025)
                self.dec_step_pin.value(0)
                time.sleep(.0025)

    def dec_counter_callback(self, pin):

        if self.dec_manual:
            if self.dec_dir == 1:
                if self.dec_speed_pin.value():
                    self.dec_steps_adder += (1 / 16)
                else:
                    self.dec_steps_adder += 1

            else:
                if self.dec_speed_pin.value():
                    self.dec_steps_adder -= (1 / 16)
                else:
                    self.dec_steps_adder -= 1
        else:

            if self.dec_dir == 1:
                if self.dec_speed_pin.value():
                    self.dec_steps += (1 / 16)
                else:
                    self.dec_steps += 1

            else:
                if self.dec_speed_pin.value():
                    self.dec_steps -= (1 / 16)
                else:
                    self.dec_steps -= 1

    def dec_guide_neg_callback(self, pin):
        self.dec_guide_neg_flag = True
        
    def dec_guide_pos_callback(self, pin):
        self.dec_guide_pos_flag = True
        
    def ra_drive(self, hz, direction, duty):
        if hz < 15:
            hz = 15
        self.ra_pwm.duty_u16(duty)  # 0=off
        self.ra_dir_pin.value(direction)
        self.ra_pwm.freq(hz)  # set frequency

    def ra_step(self, steps, direction):
        self.ra_dir_pin.value(direction)
        self.ra_pwm.duty_u16(0)  # 0=off
        if steps > 0:
            for x in range(steps):
                self.ra_step_pin.value(1)
                time.sleep(.0025)
                self.ra_step_pin.value(0)
                time.sleep(.0025)

    def ra_counter_callback(self, pin):

        if self.ra_manual:
            if self.ra_dir == 1:
                if self.ra_speed_pin.value():
                    self.ra_steps_adder += (1 / 16)
                else:
                    self.ra_steps_adder += 1

            else:
                if self.ra_speed_pin.value():
                    self.ra_steps_adder -= (1 / 16)
                else:
                    self.ra_steps_adder -= 1
        else:

            if self.ra_dir == 1:
                if self.ra_speed_pin.value():
                    self.ra_steps += (1 / 16)
                else:
                    self.ra_steps += 1

            else:
                if self.ra_speed_pin.value():
                    self.ra_steps -= (1 / 16)
                else:
                    self.ra_steps -= 1
                    
    def ra_guide_neg_callback(self, pin):
        self.ra_guide_neg_flag = True

    def ra_guide_pos_callback(self, pin):
        self.ra_guide_pos_flag = True

    def tick(self):

        self.loop_count += 1
        if self.loop_count >= 5:
            self.loop_count = 0

            prev_drive_data = self.drive_data
            status = 'unknown'
            if self.dec_diff > 25 or self.ra_diff > 25 and self.uart.control_mode == 2:
                status = "Slewing"
            if self.dec_diff < 25 and self.ra_diff < 25 and self.uart.control_mode == 2:
                status = "Tracking"
            if self.uart.dec_steps_sp == 0 and self.uart.dec_steps_sp == 0 and self.uart.control_mode == 2:
                status = "Slewing Home"
            if self.dec_diff < 5 and self.ra_diff < 5 and self.uart.dec_steps_sp == 0 and self.uart.dec_steps_sp == 0:
                status = "Home Pos"
            if self.uart.control_mode < 2:
                status = "Stopped"
            diff_alt = "{:.1f}".format(self.dec_diff)
            diff_az = "{:.1f}".format(self.ra_diff)
            steps_alt = "{:.1f}".format(self.dec_steps)
            steps_az = "{:.1f}".format(self.ra_steps)
            dec_adder = "{:.1f}".format(self.dec_steps_adder + self.dec_guide_adder)
            ra_adder = "{:.1f}".format(self.ra_steps_adder + self.ra_guide_adder)
            self.drive_data = '{0},{1},{2},{3},{4},{5},{6}'.format(
                steps_alt,
                dec_adder,
                diff_alt,
                steps_az,
                ra_adder,
                diff_az,
                status
            )

            if prev_drive_data != self.drive_data:
                print('AltAzProcess', 'tick()', self.drive_data, " Ra osc ", self.ra_osc)
                self.uart.send()

        #  manual buttons
        self.man_speed_value = 60 + (self.speed8_sw.value() * 60) + (
                self.speed16_sw.value() * 140)
        if self.dec_up_sw.value():
            self.dec_manual = True
            self.dec_dir = 1
            self.dec_speed_pin.value(0)
            self.dec_drive(self.man_speed_value, self.dec_dir, self.duty50)

        if self.dec_down_sw.value():
            self.dec_manual = True
            self.dec_dir = 0
            self.dec_speed_pin.value(0)
            self.dec_drive(self.man_speed_value, self.dec_dir, self.duty50)

        if self.dec_manual and not self.dec_up_sw.value() and not self.dec_down_sw.value():
            self.dec_drive(self.man_speed_value, self.dec_dir, 0)  # off
            self.dec_manual = False

        if self.ra_left_sw.value():
            self.ra_manual = True
            self.ra_dir = 1
            self.ra_speed_pin.value(0)
            self.ra_drive(self.man_speed_value, self.ra_dir, self.duty50)

        if self.ra_right_sw.value():
            self.ra_manual = True
            self.ra_dir = 0
            self.ra_speed_pin.value(0)
            self.ra_drive(self.man_speed_value, self.ra_dir, self.duty50)

        if self.ra_manual and not self.ra_left_sw.value() and not self.ra_right_sw.value():
            self.ra_drive(self.man_speed_value, self.ra_dir, 0)  # off
            self.ra_manual = False

        if self.uart.control_mode < 2 and not self.dec_manual and not self.ra_manual:
            self.dec_drive(20, self.dec_dir, 0)  # off
            self.ra_drive(20, self.ra_dir, 0)  # off

        # guiding
        if self.dec_guide_neg_flag:
            if self.dec_guide_neg.value():
                self.dec_guide_adder -= self.dec_guide_change_value
            else:
                self.dec_guide_adder -= self.dec_guide_change_value
                self.dec_guide_neg_flag = False
                
        if self.dec_guide_pos_flag:           
            if self.dec_guide_pos.value():
                self.dec_guide_adder += self.dec_guide_change_value
            else:
                self.dec_guide_adder += self.dec_guide_change_value
                self.dec_guide_pos_flag = False

        if self.ra_guide_neg_flag:
            if self.ra_guide_neg.value():
                self.ra_guide_adder -= self.ra_guide_change_value
            else:
                self.ra_guide_adder -= self.ra_guide_change_value
                self.ra_guide_neg_flag = False

        if self.ra_guide_pos_flag:
            if self.ra_guide_pos.value():
                self.ra_guide_adder += self.ra_guide_change_value
            else:
                self.ra_guide_adder += self.ra_guide_change_value
                self.ra_guide_pos_flag = False

        self.dec_control_sp = self.uart.dec_steps_sp + self.dec_guide_adder
        self.ra_control_sp = self.uart.ra_steps_sp + self.ra_guide_adder

        if self.dec_control_sp >= self.dec_steps:  # Up
            self.dec_diff = self.dec_control_sp - self.dec_steps
        else:  # Down
            self.dec_diff = self.dec_steps - self.dec_control_sp

        if self.ra_control_sp >= self.ra_steps:  # Right
            self.ra_diff = self.ra_control_sp - self.ra_steps
        else:  # Left
            self.ra_diff = self.ra_steps - self.ra_control_sp

        # Track mode
        if self.uart.control_mode == 2 and not self.dec_manual and not self.ra_manual:  # track mode
            if self.dec_control_sp >= self.dec_steps:  # Up
                self.dec_dir = 1  # Up
            else:  # Down
                self.dec_dir = 0  # Down

            if self.ra_control_sp >= self.ra_steps:  # Right
                self.ra_dir = 1  # Right
            else:  # Left
                self.ra_dir = 0  # Left

            # dec control direction
            if self.dec_control_sp >= self.dec_control_sp_last and self.dec_control_sp != self.dec_control_sp_last:
                self.dec_control_dir = 1  # Up
            elif self.dec_control_sp < self.dec_control_sp_last and self.dec_control_sp != self.dec_control_sp_last:
                self.dec_control_dir = 0  # Down
            self.dec_control_sp_last = self.dec_control_sp

            # ra control direction
            if self.ra_control_sp >= self.ra_control_sp_last and self.ra_control_sp != self.ra_control_sp_last:
                self.ra_control_dir = 1  # Right
            elif self.ra_control_sp < self.ra_control_sp_last and self.ra_control_sp != self.ra_control_sp_last:
                self.ra_control_dir = 0  # Left
            self.ra_control_sp_last = self.ra_control_sp

            if self.uart.dec_steps_sp == 0:
                self.dec_control_dir = self.dec_dir

            if self.uart.ra_steps_sp == 0:
                self.ra_control_dir = self.ra_dir

            dec_diff_micro = self.dec_diff * 16
            if dec_diff_micro <= 5 or (self.dec_diff < 2 and self.dec_control_dir != self.dec_dir):
                self.dec_drive(self.dec_hz, self.dec_control_dir, 0)  # off
            elif self.dec_diff > 5:
                self.dec_speed_pin.value(0)  # fast
                self.dec_hz = int(self.dec_diff * 4)
                if self.dec_hz > self.max_speed:
                    self.dec_hz = self.max_speed
                self.dec_drive(self.dec_hz, self.dec_dir, self.duty50)
            elif dec_diff_micro > 1 and self.ra_diff < 5:
                self.dec_speed_pin.value(1)  # slow
                self.dec_step(dec_diff_micro, self.dec_control_dir)

            ra_diff_micro = self.ra_diff * 16
            if ra_diff_micro <= 3 or (self.ra_diff < 2 and self.ra_control_dir != self.ra_dir):
                if self.uart.ra_steps_sp == 0:
                    self.ra_drive(self.ra_osc_sp, self.ra_control_dir, 0)  # off
                else:
                    self.ra_drive(self.ra_osc_sp, self.ra_control_dir, self.duty50)  # slower
            elif self.ra_diff > 10:
                self.ra_speed_pin.value(0)  # fast
                self.ra_hz = int(self.ra_diff * 2)
                if self.ra_hz > self.max_speed:
                    self.ra_hz = self.max_speed
                self.ra_drive(self.ra_hz, self.ra_dir, self.duty50)
            elif ra_diff_micro > 3 and self.dec_diff < 5:
                self.ra_speed_pin.value(1)  # slow
                if self.ra_control_dir:
                    self.ra_osc = int(self.ra_osc_sp + (ra_diff_micro / 10))
                    self.ra_drive(self.ra_osc, self.ra_control_dir, self.duty50)
                else:
                    self.ra_osc = int(self.ra_osc_sp - (ra_diff_micro / 10))
                    self.ra_drive(self.ra_osc, self.ra_control_dir, self.duty50)


class UARTProcess:
    buffer: bytes

    ra_dec: AltAzProcess

    def __init__(self):
        self.uart0 = UART(0, baudrate=9600, tx=Pin(0), rx=Pin(1))
        self.dec_steps_sp = 0
        self.ra_steps_sp = 0
        self.control_mode = 0

        self.reset()

    def tick(self):
        if self.uart0.any():
            last_bytes: bytes = self.uart0.read()

            while COMMAND_PARSE in last_bytes:
                index = last_bytes.index(COMMAND_PARSE)
                self.buffer += last_bytes[:index]
                last_bytes = last_bytes[index + 1:]

            self.buffer += last_bytes
            self.decode_buffer()
            self.reset()

    def send(self):
        response = '{0}\n'.format(self.ra_dec.drive_data)
        self.uart0.write(response)

    def decode_buffer(self, decode: str = 'utf-8', split: str = ','):
        try:
            self.dec_steps_sp, self.ra_steps_sp, self.control_mode = self.buffer.decode('utf-8').split(',')
            self.dec_steps_sp = float(self.dec_steps_sp)
            self.ra_steps_sp = float(self.ra_steps_sp)
            self.control_mode = int(self.control_mode)
            print('Received', 'AltSP ', self.dec_steps_sp, ' AzSP ', self.ra_steps_sp, ' Control Mode ', self.control_mode)
            if self.control_mode == 3:
                self.dec_steps_sp = 0
                self.ra_steps_sp = 0
                self.control_mode = 2
                self.ra_dec.dec_steps_adder = 0
                self.ra_dec.ra_steps_adder = 0
                self.ra_dec.dec_guide_adder = 0
                self.ra_dec.ra_guide_adder = 0

        except:
            print('Error trying to decode: {0}'.format(self.buffer))
            
    def reset(self):
        self.buffer = b''


def main():
    uart = UARTProcess()
    ra_dec = AltAzProcess()

    # Pass the XXXProcess to each other Process
    uart.ra_dec = ra_dec
    ra_dec.uart = uart

    while True:
        uart.tick()
        ra_dec.tick()
        time.sleep(0.1)  # TODO - Can this be changed???


if __name__ == '__main__':
    main()
