import datetime

from serial import Serial
import time

SERIAL_PORT = '/dev/ttyS0'  # '/dev/ttyS0' ttyAMA0 COM7
SERIAL_BAUD = 9600
AltSp = 7200.00
AltAdder = .15
AzSp = 3600.00
AzAdder = .15
Mode = 1


class UARTClient:
    def __init__(self, port: str = None, baud: int = None):
        self.serial = Serial(port or SERIAL_PORT, baudrate=baud or SERIAL_BAUD)

    def __del__(self):
        self.serial.close()

    def send(self, data: bytes):
        self.serial.write(data)

    def read(self):
        results = self.serial.readline()  # .decode('utf-8')  # .split(',')
        print(results)
        print('checking')


if __name__ == '__main__':
    client = UARTClient()
    # client.send(str(AltSp) + "," + str(AzSp) + "," + str(Mode)
    client.send('Hello'.encode())
    print('send')
    time.sleep(.1)
    while True:
        #  TODO - Add Logic here for receiving data from client
        client.send(f'{AltSp},{AzSp},{Mode}\n'.encode())
        client.read()
        time.sleep(.1)
        print('looping')
        #  TODO - Add Logic here to send some response back to the client
        # client.send(str(AltSp) + "," + str(AzSp) + "," + str(Mode)


        AltSp += AltAdder
        AzSp += AzAdder
        Mode = 2
