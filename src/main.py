import logging

from uvicorn import Config as UvicornConfig
from uvicorn import Server


def main():
    # TODO - pass cmd args here...

    logging.basicConfig(level=logging.DEBUG)

    uvicorn_config = UvicornConfig(
        'src.app:app',
        host='0.0.0.0',
        log_level='debug',
    )

    server = Server(uvicorn_config)

    server.run()

    # from src.models import TrackerData
    # from src.uart import UARTServer
    #
    # tracker_data = TrackerData()
    # uart_server = UARTServer(tracker_data)
    # uart_server.background_task()


if __name__ == '__main__':
    main()