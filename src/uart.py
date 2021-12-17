import logging
from typing import Optional

from serial import Serial
import time

from src.models import PythonToDriveData, DriveToPythonData, TrackerData

SERIAL_PORT = '/dev/ttyS0'  # ttyS0 for rpi 4, ttyAMA0 for rpi3b+
SERIAL_BAUD = 9600
SEND_INTERVAL = 1  # seconds


class UARTServer:
    def __init__(self, tracker_data: TrackerData, port: str = None, baud: int = None, send_interval: int = None):
        self.serial = Serial(port or SERIAL_PORT, baudrate=baud or SERIAL_BAUD)
        self.is_running = False
        self.send_interval = send_interval or SEND_INTERVAL
        self.last_send: float = time.time()
        self.tracker_data = tracker_data

    def __del__(self):
        self.serial.close()

    def send(self, az_steps_sp: float, alt_steps_sp: float, control_mode: int):
        encode = f'{alt_steps_sp},{az_steps_sp},{control_mode}\n'.encode()
        self.serial.write(encode)
        self.last_send = time.time()

    def read(self) -> Optional[PythonToDriveData]:
        model = None

        if self.serial.inWaiting() > 1:
            # Blocking connection
            # logging.debug('ENTERING BLOCKING READ!!!')
            results = self.serial.readline().decode('utf-8')
            # logging.debug('EXITING BLOCKING READ!!!')

            # loop over '\n' when receiving multiple lines/results from uart
            for line in results.split('\n'):
                if line:
                    logging.debug(f'UART Server read raw: {line}')
                    columns = line.split(',')
                    # for c in columns:
                    #     logging.debug(f'UART Column: {c}')

                    model = DriveToPythonData(**dict(
                        alt_steps=columns[0],
                        alt_steps_adder=columns[1],
                        az_steps=columns[2],
                        az_steps_adder=columns[3],
                        drive_status=columns[4]
                    ))

                    logging.debug(f'UART Model: {model}')

        # return last model received
        return model

    def background_task(self):
        logging.debug('Starting UART Server')
        self.is_running = True

        while self.is_running:
            data = self.read()
            if data:
                # Update tracker_data from data [DriveToPythonData]
                for k, v in data.dict().items():
                    if hasattr(self.tracker_data.base, k):
                        setattr(self.tracker_data.base, k, v)

            time.sleep(0.01)

        logging.debug('Exited UART Server')
