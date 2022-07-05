import logging
import socket
import re
import time

from src.models import TrackerData


class SocketServer:
    def __init__(self, tracker_data: TrackerData, *, port: int):
        self.hostname = socket.gethostname()
        self.host = socket.gethostbyname(self.hostname)
        self.port = port
        self.server_address = (self.host, port)
        self.tracker_data = tracker_data
        logging.debug(f'{self.__class__.__name__}: {self.server_address}')

    def __del__(self):
        ...

    @staticmethod
    def command_builder(cmd, *args):
        arg = ''.join([str() for s in args])
        return ('#:%s%s#' % (cmd, str(arg))).encode()

    @staticmethod
    def send(sock: socket.socket, string: str):
        _bytes = string.encode()
        sock.send(_bytes)
        logging.debug(f'Sent: {string}')

    @staticmethod
    def read(sock: socket.socket, decode: bool = False):
        data = sock.recv(1024)
        if data:
            if decode:
                data = data.decode()
            logging.debug(f'Read: {data}')
            return data
        else:
            # logging.debug(f'Failed to read anything')
            return None

    def background_task(self):
        while True:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
                logging.debug(f'Entering sock()')
                self.sock(sock)

    def sock(self, sock: socket.socket):
        sock.bind(self.server_address)
        sock.listen()
        remote_sock, remote_address = sock.accept()
        with remote_sock:
            logging.debug(f'Connected from {remote_address}')

            while True:
                read = self.read(remote_sock)
                if read is not None:
                    commands = re.findall(b'(?<=:)[^#]+(?#)|\x06', read)
                    for command in commands:
                        self.process_command(remote_sock, command.decode())
                else:
                    print('sleep ')
                    time.sleep(0.5)

    def get_mount_mode(self):
        if self.tracker_data.base.mount_select < 2:
            return 'P'  # 0 = EQ 1 = Fork
        else:
            return 'A'  # 2 = Alt Az

    def is_slewing(self):
        if self.tracker_data.base.drive_status == 'Slewing' or self.tracker_data.base.drive_status == 'Slewing Home':
            return chr(127) + chr(127) + chr(127) + chr(127) + chr(127) + chr(127) + '#'  # slewing
        else:
            return '#'  # not slewing

    @staticmethod
    def CM_sync():
        return 'OBJ#'

    def MS_move_to_target(self):
        self.tracker_data.base.custom_goto = True
        self.tracker_data.base.soft_ra_adder = 0
        self.tracker_data.base.soft_dec_adder = 0
        return "0"

    def Sd_set_dec_deg(self, dms):
        # dms = ':Sd+45*30:04#'
        s = dms[2:-8]  # sign + -
        self.tracker_data.base.custom_dec_deg = int(float(dms[3:-6]))  # DD
        self.tracker_data.base.custom_dec_min = int(float(dms[6:-3]))  # MM
        self.tracker_data.base.custom_dec_sec = float(dms[-2:])  # SS
        if s == "-":
            self.tracker_data.base.custom_dec_deg = self.tracker_data.base.custom_dec_deg * -1
        return "1"

    def Sr_set_ra_hr(self, hms):
        # SrHH:MM:SS
        temp = hms.split(':')
        self.tracker_data.base.custom_ra_hour = int(float(temp[0][-2:]))
        self.tracker_data.base.custom_ra_min = int(float(temp[1]))
        self.tracker_data.base.custom_ra_sec = float(temp[2])
        return "1"

    def move_mount(self, button, scale):
        if not self.tracker_data.base.soft_ra_adder:
            self.tracker_data.base.soft_ra_adder = 0
        if not self.tracker_data.base.soft_dec_adder:
            self.tracker_data.base.soft_dec_adder = 0

        if button == 0:
            self.tracker_data.base.soft_ra_adder += scale / self.tracker_data.base.ra_or_az_pulse_per_deg
        elif button == 1:
            self.tracker_data.base.soft_ra_adder -= scale / self.tracker_data.base.ra_or_az_pulse_per_deg
        elif button == 2:
            self.tracker_data.base.soft_dec_adder += scale / self.tracker_data.base.dec_or_alt_pulse_per_deg
        elif button == 3:
            self.tracker_data.base.soft_dec_adder -= scale / self.tracker_data.base.dec_or_alt_pulse_per_deg

    def guide_mount(self, button, msec):
        scale = msec / 150000
        self.move_mount(button, scale)

    def process_command(self, sock: socket.socket, command):
        if command:  # and command in command_map:
            results = None

            if command in (b'\x06', ''):
                results = self.get_mount_mode()

            elif command == 'D':
                results = self.is_slewing()

            elif command == 'Gc':
                results = '24#'

            elif command == 'GM':
                results = 'Site1#'

            elif command == 'GT':
                results = f'{round(self.tracker_data.base.ra_az_osc_calc, 1)}#'

            elif command == 'Gg':
                results = self.tracker_data.base.longitude_dms + '#'

            elif command == 'Gt':
                results = self.tracker_data.base.latitude_dm + '#'

            elif command == 'GG':
                results = str(self.tracker_data.base.utcoffset) + '#'

            elif command == 'GL':
                results = self.tracker_data.base.local_time + '#'

            elif command == 'GC':
                results = self.tracker_data.base.local_date + '#'

            elif command == 'GVD':
                results = "12 12 2022#"

            elif command == 'GVT':
                results = "01:01:01#"

            elif command == 'GVN':
                results = "41.0#"

            elif command == 'GVP':
                results = "AutostarMimic#"

            elif command == 'CM':
                results = self.CM_sync()

            elif command == 'GD':
                results = self.tracker_data.base.dec_deg_dms + '#'

            elif command == 'GR':
                results = self.tracker_data.base.ra_hour_hms + '#'

            elif command == 'MS' or command == 'MA':
                results = self.MS_move_to_target()

            elif command.startswith('Sd'):
                results = self.Sd_set_dec_deg(command)

            elif command.startswith('Sr'):
                results = self.Sr_set_ra_hr(command)

            elif command == 'hP':
                self.tracker_data.base.control_mode = 3
                results = '0'

            elif command.startswith('St'):
                results = '1'

            elif command.startswith('Sg'):
                results = '1'

            elif command.startswith('Sw'):
                results = '1'

            elif command.startswith('SG'):
                results = '1'

            elif command.startswith('SL'):
                results = '1'

            elif command.startswith('SC'):
                results = '1'

            elif command == 'Me':
                self.move_mount(1, .05)

            elif command == 'Mn':
                self.move_mount(2, .05)

            elif command == 'Ms':
                self.move_mount(3, .05)

            elif command == 'Mw':
                self.move_mount(0, .05)

            elif command.startswith('Mge'):  # :MgeXXXX#
                self.guide_mount(1, int(command[3:]))

            elif command.startswith('Mgn'):
                self.guide_mount(2, int(command[3:]))

            elif command.startswith('Mgs'):
                self.guide_mount(3, int(command[3:]))

            elif command.startswith('Mgw'):
                self.guide_mount(0, int(command[3:]))

            else:
                logging.debug(f'Unhandled command: {command}')

            if results:
                logging.debug(f'Process command: {command} results: {results}')
                self.send(sock, results)
            else:
                logging.debug(f'No command results to send: {command}')

        elif command:
            logging.debug(f'Unhandled command: {command}')
