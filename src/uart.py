import logging
import time
from typing import Optional

from serial import Serial

from src.models import PythonToDriveData, DriveToPythonData, TrackerData

SERIAL_PORT = '/dev/ttyS0'
SERIAL_BAUD = 9600


class UARTServer:
    def __init__(self, tracker_data: TrackerData, port: str = None, baud: int = None):
        self.serial = Serial(port or SERIAL_PORT, baudrate=baud or SERIAL_BAUD)
        self.last_send: float = time.time()
        self.tracker_data = tracker_data

    def __del__(self):
        self.serial.close()

    def send(self, az_steps_sp: float, alt_steps_sp: float, control_mode: int, ra_az_osc_calc: int,
             dec_alt_osc_calc: int, manual_move: str):
        encode = f'{alt_steps_sp},{az_steps_sp},{control_mode},{ra_az_osc_calc},{dec_alt_osc_calc},{manual_move}\n'.encode()
        self.serial.write(encode)
        self.last_send = time.time()
        # print('sent ', encode)

    def read(self) -> Optional[PythonToDriveData]:
        model = None

        if self.serial.inWaiting() > 1:
            results = self.serial.readline().decode('utf-8')
            # ONLY USE THE LAST LINE IN THE BUFFER
            lines = [
                line
                for line in results.split('\n')
                if line
            ]
            line = lines[-1]
            if line:
                # logging.debug(f'UART Server read raw: {line}')
                columns = line.split(',')

                model = DriveToPythonData(**dict(
                    alt_steps=columns[0],
                    alt_steps_adder=columns[1],
                    alt_diff=columns[2],
                    az_steps=columns[3],
                    az_steps_adder=columns[4],
                    az_diff=columns[5],
                    drive_status=columns[6],
                    az_osc_drive=columns[7],
                    alt_osc_drive=columns[8]
                ))

                # logging.debug(f'UART Model: {model}')

        self.serial.flush()

        # return last model received
        return model

    def background_task(self):
        logging.debug('Starting UART Server')
        self.tracker_data.base.running = True

        while self.tracker_data.base.running:
            data = self.read()
            if data:
                # Update tracker_data from data [DriveToPythonData]
                for k, v in data.dict().items():
                    if hasattr(self.tracker_data.base, k):
                        setattr(self.tracker_data.base, k, v)

            if self.tracker_data.sky_coord:
                self.tracker_data.base.calculate(self.tracker_data.sky_coord, self.tracker_data.earth_location)

                self.send(
                    self.tracker_data.base.az_ra_steps_sp,
                    self.tracker_data.base.alt_dec_steps_sp,
                    self.tracker_data.base.control_mode,
                    self.tracker_data.base.ra_az_osc_calc,
                    self.tracker_data.base.dec_alt_osc_calc,
                    self.tracker_data.base.manual_move
                )

            # TODO - Try to match all sleep timers across all devises
            time.sleep(0.1)

        logging.debug('Exited UART Server')
