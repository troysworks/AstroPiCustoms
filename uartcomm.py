"""
UART communication on Raspberry Pi using Python
http://www.electronicwings.com
receved from astroberry lx200 to get first calls
"""
import serial
from time import sleep

ser = serial.Serial('COM9', 9600)  # Open port with baud rate /dev/ttyS0
while True:
    received_data = ser.read()  # read serial port
    sleep(0.1)
    data_left = ser.inWaiting()  # check for remaining byte
    received_data += ser.read(data_left)
    print(received_data)  # print received data
    received_data += received_data
    ser.write(received_data)  # transmit data serially
