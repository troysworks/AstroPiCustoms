from typing import Optional
from unittest import TestCase

import serial


# used to control meade telescope to test calls from astroberry lx200 driver
def command_builder(cmd, *args):
    arg = ''.join([str() for s in args])
    return ('#:%s%s#' % (cmd, str(arg))).encode()


class TestThings(TestCase):

    def test_new(self):

        def decode_bytes(byte: bytes) -> Optional[str]:
            if byte == b'\xdf':
                return 'D'
            try:
                return byte.decode()
            except Exception as e:
                return None

        def read_from_com(com_port: serial.Serial) -> Optional[str]:
            results = decode_bytes(com_port.read())

            while results:
                single = decode_bytes(com_port.read())
                if single and single != '#':
                    results += single
                else:
                    break

            return results

        def com_write_and_read(com_port: serial.Serial, command: str) -> Optional[str]:
            com_port.write(command_builder(command))
            return read_from_com(com)

        com = serial.Serial(
            port='COM7',
            # '/dev/ttyS0' '/dev/ttyUSB0' 'COM7' number of device, numbering starts at '/dev/serial1' '/dev/ttyAMA0'
            # zero. If everything fails, the user
            # can specify a device string, note
            # that this isn't portable anymore
            # if no port is specified an unconfigured
            # and closed serial port object is created
            baudrate=9600,  # baudrate
            bytesize=serial.EIGHTBITS,  # number of databits
            parity=serial.PARITY_NONE,  # enable parity checking
            stopbits=serial.STOPBITS_ONE,  # number of stopbits
            timeout=3,  # 10       #set a timeout value, None for waiting forever
            xonxoff=0,  # no software flow control
            rtscts=0,  # no RTS/CTS flow control
            writeTimeout=3,  # set a timeout for writes
            dsrdtr=None,  # None: use rtscts setting, dsrdtr override if true or false
        )

        # Check mode type

        # com.write(chr(0x06).encode())
        # mode = decode_bytes(com.read())
        # print(f'Mode: {mode}')
        mode = com_write_and_read(com, '\x06')  # A or P
        print('mode ', mode)
        #
        # Format = com_write_and_read(com, 'Gc')  # Calendar Format (24)
        # print('Format ', Format)
        #
        # Site = com_write_and_read(com, 'GM')  # Get Site 80550
        # print('Site ', Site)

        # rate = com_write_and_read(com, 'GT')  # Get tracking rate +60.1
        # print('rate ', rate)

        # SiteLa = com_write_and_read(com, 'Gt')  # Site Latitude +39D44:00
        # print('SiteLa ', SiteLa)

        # SiteLo = com_write_and_read(com, 'Gg')  # site Longitude 104D59:00
        # print('SiteLo ', SiteLo)

        # cdate = com_write_and_read(com, 'GC')  # current date 05/25/22
        # print('cdate ', cdate)

        # Fwdate = com_write_and_read(com, 'GVD')  # Firmware Date Jan 11 2006
        # print('Fwdate ', Fwdate)

        # Fwtime = com_write_and_read(com, 'GVT')  # Firmware Time 13:00:20
        # print('Fwtime ', Fwtime)

        # Fwn = com_write_and_read(com, 'GVN')  # Firmware  Number 41Ec
        # print('Fwn ', Fwn)

        # Pn = com_write_and_read(com, 'GVP')  # Product Name Autostar
        # print('Pn ', Pn)

        # Setutcoffset = com_write_and_read(com, 'SG-06.0')  # local time to yield UTC 1
        # print('Setutcoffset ', Setutcoffset)

        # utcoffset = com_write_and_read(com, 'GG')  # Get UTC offset time -07 with dst yes
        # print('utcoffset ', utcoffset)

        # altitude = com_write_and_read(com, 'GA')
        # az = com_write_and_read(com, 'GZ')
        # sr = com_write_and_read(com, 'GS')  # sidereal of mount
        # print('altitude ', altitude, ' az ', az, ' sr ', sr)
        #
        # srset = com_write_and_read(com, 'SS04:35:00')
        # mvdec = com_write_and_read(com, 'Sds11*51:30')  # set dec values
        # mvra = com_write_and_read(com, 'Sr10:09:30')  # set Ra values
        # MS = com_write_and_read(com, 'MS')  # slew to target
        #
        # print('mvdec ', mvdec, ' mvra ', mvra, 'MS', MS)


# S – Telescope Set Commands
# :SdsDD*MM# 'Sds05*05:30'
# Set target object declination to sDD*MM or sDD*MM:SS depending on the current precision setting
# Returns:
# 1 - Dec Accepted
# 0 – Dec invalid


# :SrHH:MM.T#
# :SrHH:MM:SS#  'Sr07:18:30'
# Set target object RA to HH:MM.T or HH:MM:SS depending on the current precision setting.
# Returns:
# 0 – Invalid
# 1 - Valid

# :SSHH:MM:SS#
# Sets the local sideral time to HH:MM:SS
# Returns:
# 0 – Invalid
# 1 - Valid

if __name__ == "__main__":
    t = TestThings()
    t.test_new()
