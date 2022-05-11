import time

from machine import Pin, UART, PWM, ADC

# Astropi Customs 5-7-22
# GSO 10 inch Alt Az
# stepper motors and 1/16 microstep for tracking
# for raspberry pi pico
# Ra drive uses 0.002083 deg/count
# Dec drive uses 0.002083 deg/count
# uart communication to/from raspberry pi for counts setpoint and modes
# save as main.py on pico to auto run

COMMAND_PARSE = b'\n'


class ControlProcess:
    uart = None  # type: UARTProcess

    def __init__(self):
        self.max_speed = 800
        self.oneto8_speed = self.max_speed / 8
        self.deadband = 5500
        self.ra_speed = 0
        self.dec_speed = 0
        self.ra_hz_manual = 0
        self.dec_hz_manual = 0
        self.ra_manual = False
        self.dec_manual = False
        self.loop_count = 0
        self.dec_osc = 0
        self.ra_osc = 0
        self.dec_dir = 0
        self.ra_dir = 0
        self.duty50 = 32767
        self.dec_diff = 0
        self.dec_manual = False
        self.dec_steps = 0
        self.dec_steps_adder = 0
        self.dec_guide_adder = 0
        self.dec_guide_change_value = 2
        self.dec_guide_pos_flag = False
        self.dec_guide_neg_flag = False
        self.ra_diff = 0
        self.ra_manual = False
        self.ra_steps = 0
        self.ra_steps_adder = 0
        self.ra_guide_adder = 0
        self.ra_guide_change_value = 6
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

        self.adc_dec = ADC(Pin(26))
        self.adc_ra = ADC(Pin(27))
        self.speed_btn = Pin(22, Pin.IN, Pin.PULL_DOWN)

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
            diff_dec = "{:.1f}".format(self.dec_diff)
            diff_ra = "{:.1f}".format(self.ra_diff)
            steps_dec = "{:.1f}".format(self.dec_steps)
            steps_ra = "{:.1f}".format(self.ra_steps)
            dec_adder = "{:.1f}".format(self.dec_steps_adder + self.dec_guide_adder)
            ra_adder = "{:.1f}".format(self.ra_steps_adder + self.ra_guide_adder)
            self.drive_data = '{0},{1},{2},{3},{4},{5},{6},{7},{8}'.format(
                steps_dec,
                dec_adder,
                diff_dec,
                steps_ra,
                ra_adder,
                diff_ra,
                status,
                self.ra_osc,
                self.dec_osc
            )

            if prev_drive_data != self.drive_data:
                print('ControlProcess', self.drive_data)
                self.uart.send()

        dec = self.adc_dec.read_u16()
        ra = self.adc_ra.read_u16()

        # manual moves joystick
        if 32767 - self.deadband <= dec <= 32767 + self.deadband:
            self.dec_speed = 0
            self.dec_dir = self.dec_dir
            self.dec_hz_manual = 0

        elif dec <= 32767 - self.deadband:
            self.dec_speed = int((32767 - dec) / 4095)
            self.dec_dir = 0  # Down
            self.dec_hz_manual = int(
                (self.oneto8_speed * self.dec_speed) + (self.oneto8_speed * self.dec_speed * self.speed_btn.value()))

        elif dec >= 32767 + self.deadband:
            self.dec_speed = int((dec - 32767) / 4095)
            self.dec_dir = 1  # Up
            self.dec_hz_manual = int(
                (self.oneto8_speed * self.dec_speed) + (self.oneto8_speed * self.dec_speed * self.speed_btn.value()))

        if 32767 - self.deadband <= ra <= 32767 + self.deadband:
            self.ra_speed = 0
            self.ra_dir = self.ra_dir
            self.ra_hz_manual = 0

        elif ra <= 32767 - self.deadband:
            self.ra_speed = int((32767 - ra) / 4095)
            self.ra_dir = 1  # Right
            self.ra_hz_manual = int(
                (self.oneto8_speed * self.ra_speed) + (self.oneto8_speed * self.ra_speed * self.speed_btn.value()))

        elif ra >= 32767 + self.deadband:
            self.ra_speed = int((ra - 32767) / 4095)
            self.ra_dir = 0  # Left
            self.ra_hz_manual = int(
                (self.oneto8_speed * self.ra_speed) + (self.oneto8_speed * self.ra_speed * self.speed_btn.value()))

        if self.dec_hz_manual == 0 and self.dec_manual:
            # self.dec_speed_pin.value(1)
            self.dec_manual = False
            self.dec_drive(15, self.dec_dir, 0)  # off

        elif self.dec_hz_manual > 0:
            self.dec_speed_pin.value(0)
            self.dec_manual = True
            self.dec_drive(self.dec_hz_manual, self.dec_dir, self.duty50)
            print("dec_hz_manual ", str(self.dec_hz_manual))

        if self.ra_hz_manual == 0 and self.ra_manual:
            # self.ra_speed_pin.value(1)
            self.ra_manual = False
            self.ra_drive(15, self.ra_dir, 0)  # off

        elif self.ra_hz_manual > 0:
            self.ra_speed_pin.value(0)
            self.ra_manual = True
            self.ra_drive(self.ra_hz_manual, self.ra_dir, self.duty50)
            print("ra_hz_manual ", str(self.ra_hz_manual))

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
            self.dec_dir = 1
        else:  # Down
            self.dec_diff = self.dec_steps - self.dec_control_sp
            self.dec_dir = 0

        if self.ra_control_sp >= self.ra_steps:  # Right
            self.ra_diff = self.ra_control_sp - self.ra_steps
            self.ra_dir = 1
        else:  # Left
            self.ra_diff = self.ra_steps - self.ra_control_sp
            self.ra_dir = 0

        ra_step_mode = ''
        dec_step_mode = ''
        # Track mode
        if self.uart.control_mode == 2 and not self.dec_manual and not self.ra_manual:  # track mode

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
            #  Dec Tracking
            if self.uart.dec_steps_sp == 0 and self.dec_diff < 2:
                self.dec_osc = 0
                self.dec_drive(self.dec_osc, self.dec_control_dir, 0)
                dec_step_mode = 'home'

            elif dec_diff_micro <= 2 or (self.dec_diff < 2 and self.dec_control_dir != self.dec_dir):
                self.dec_speed_pin.value(1)  # slow
                self.dec_osc = int(self.uart.dec_osc - (self.uart.dec_osc * .1))
                self.dec_drive(self.dec_osc, self.dec_control_dir, self.duty50)
                dec_step_mode = 'Slow'

            elif self.dec_diff > 10:
                self.dec_speed_pin.value(0)  # fast
                if self.dec_osc + 25 < int(self.dec_diff * 3):
                    self.dec_osc += 25
                else:
                    self.dec_osc = int(self.dec_diff * 3)
                if self.dec_osc > self.max_speed:
                    self.dec_osc = self.max_speed
                self.dec_drive(self.dec_osc, self.dec_dir, self.duty50)
                dec_step_mode = 'Slewing'

            elif dec_diff_micro > 1 and self.ra_diff < 5:
                self.dec_speed_pin.value(1)  # slow
                if self.dec_control_dir:
                    if self.dec_control_sp >= self.dec_steps:  # Right
                        self.dec_osc = int(self.uart.dec_osc + (dec_diff_micro * .1))
                    else:  # left
                        self.dec_osc = int(self.uart.dec_osc - (dec_diff_micro * .1))

                    if self.dec_osc < 15:
                        self.dec_step(dec_diff_micro, self.dec_control_dir)  # single step
                        dec_step_mode = 'Single step up'
                    else:
                        self.dec_drive(self.dec_osc, self.dec_control_dir, self.duty50)  # PWM
                        dec_step_mode = 'PWM up'
                else:
                    if self.dec_control_sp < self.dec_steps:  # left
                        self.dec_osc = int(self.uart.dec_osc + (dec_diff_micro * .1))
                    else:  # Right
                        self.dec_osc = int(self.uart.dec_osc - (dec_diff_micro * .1))
                    if self.dec_osc < 15:
                        self.dec_step(dec_diff_micro, self.dec_control_dir)  # single step
                        dec_step_mode = 'Single step down'
                    else:
                        self.dec_drive(self.dec_osc, self.dec_control_dir, self.duty50)  # PWM
                        dec_step_mode = 'PWM down'

            #  Ra Tracking
            ra_diff_micro = self.ra_diff * 16
            if self.uart.ra_steps_sp == 0 and self.ra_diff < 2:
                self.ra_osc = 0
                self.ra_drive(self.ra_osc, self.ra_control_dir, 0)
                ra_step_mode = 'home'

            elif ra_diff_micro <= 2 or (self.ra_diff < 2 and self.ra_control_dir != self.ra_dir):
                self.ra_speed_pin.value(1)  # slow
                self.ra_osc = int(self.uart.ra_osc - (self.uart.ra_osc * .1))
                self.ra_drive(self.ra_osc, self.ra_control_dir, self.duty50)
                ra_step_mode = 'Slow'

            elif self.ra_diff > 10:  # slew
                self.ra_speed_pin.value(0)  # fast
                if self.ra_osc + 25 < int(self.ra_diff * 3):
                    self.ra_osc += 25
                else:
                    self.ra_osc = int(self.ra_diff * 3)
                if self.ra_osc > self.max_speed:
                    self.ra_osc = self.max_speed
                self.ra_drive(self.ra_osc, self.ra_dir, self.duty50)
                ra_step_mode = 'Slewing'

            elif ra_diff_micro > 1 and self.dec_diff < 10:
                self.ra_speed_pin.value(1)  # slow
                if self.ra_control_dir:
                    if self.ra_control_sp >= self.ra_steps:  # Right
                        self.ra_osc = int(self.uart.ra_osc + (ra_diff_micro * .1))
                    else:  # left
                        self.ra_osc = int(self.uart.ra_osc - (ra_diff_micro * .1))
                        
                    if self.ra_osc < 15:
                        self.ra_step(ra_diff_micro, self.ra_control_dir)  # single step
                        ra_step_mode = 'Single step right'
                    else:
                        self.ra_drive(self.ra_osc, self.ra_control_dir, self.duty50)  # PWM
                        ra_step_mode = 'PWM right'
                else:
                    if self.ra_control_sp < self.ra_steps:  # left
                        self.ra_osc = int(self.uart.ra_osc + (ra_diff_micro * .1))
                    else:  # Right
                        self.ra_osc = int(self.uart.ra_osc - (ra_diff_micro * .1))
                    if self.ra_osc < 15:
                        self.ra_step(ra_diff_micro, self.ra_control_dir)  # single step
                        ra_step_mode = 'Single step left'
                    else:
                        self.ra_drive(self.ra_osc, self.ra_control_dir, self.duty50)  # PWM
                        ra_step_mode = 'PWM left'
                        
            print(' ra_osc ', self.ra_osc, 'ra_step_mode ', ra_step_mode, ' dec_osc ', self.dec_osc, 'dec_step_mode ', dec_step_mode)
            #  print(' dec_control_dir ', self.dec_control_dir, ' dec_dir ', self.dec_dir, ' dec_diff ', self.dec_diff, ' dec_osc ', self.dec_osc)


class UARTProcess:
    buffer: bytes

    ra_dec: ControlProcess

    def __init__(self):
        self.uart0 = UART(0, baudrate=9600, tx=Pin(0), rx=Pin(1))
        self.dec_steps_sp = 0
        self.ra_steps_sp = 0
        self.control_mode = 0
        self.ra_osc = 0
        self.dec_osc = 0

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
            self.dec_steps_sp, self.ra_steps_sp, self.control_mode, self.ra_osc, self.dec_osc = self.buffer.decode('utf-8').split(',')
            self.dec_steps_sp = float(self.dec_steps_sp)
            self.ra_steps_sp = float(self.ra_steps_sp)
            self.control_mode = int(self.control_mode)
            self.ra_osc = int(self.ra_osc)
            self.dec_osc = int(self.dec_osc)

            print('Received', 'DecSP ', self.dec_steps_sp, ' RaSP ', self.ra_steps_sp, ' Control Mode ',
                  self.control_mode)
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
    ra_dec = ControlProcess()

    # Pass the XXXProcess to each other Process
    uart.ra_dec = ra_dec
    ra_dec.uart = uart

    while True:
        uart.tick()
        ra_dec.tick()
        time.sleep(0.1)  # TODO - Can this be changed???


if __name__ == '__main__':
    main()
