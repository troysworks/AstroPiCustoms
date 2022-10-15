import datetime
import logging
import socket
import time

from tcp import SocketServer


class SocketClient(SocketServer):
    def sock(self, sock: socket.socket):
        sock.connect(self.server_address)

        for _ in range(100):
            #     self.send(sock, f'Hello, world, {datetime.datetime.now()}')
            #     time.sleep(0.5)
            self.send(sock, '\x06')
            time.sleep(5)
            self.send(sock, '')
            time.sleep(5)
            # self.send(sock, ':Gc#')
            # time.sleep(5)
            # self.send(sock, ':GM#')
            # time.sleep(5)
            # self.send(sock, ':GT#')
            # time.sleep(5)
            # self.send(sock, ':Gt#')
            # time.sleep(5)
            # self.send(sock, ':GG#')
            # time.sleep(5)
            # self.send(sock, ':GL#')
            # time.sleep(5)
            # self.send(sock, ':GC#')
            # time.sleep(5)
            # self.send(sock, ':GD#')
            # time.sleep(5)
            # self.send(sock, ':GR#')
            # time.sleep(5)
            self.send(sock, ':Sd+45*30:04#')
            time.sleep(5)
            self.send(sock, ':Sr06:30:15#')
            time.sleep(5)
            self.send(sock, ':MA#')
            time.sleep(5)


if __name__ == '__main__':
    logging.basicConfig(level=logging.DEBUG)

    test_socket = SocketClient(None, port=10760)
    test_socket.background_task()
