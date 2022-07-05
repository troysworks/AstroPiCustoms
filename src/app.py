import logging
import threading
from datetime import datetime
from astropy import units as u
from astropy.coordinates import solar_system_ephemeris, SkyCoord, get_body, Angle
from astropy.time import Time
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from starlette import status
from src.data import DataFile
from src.models import PythonToJavascriptData, CelestialObjectGroup, TrackerData, Builder
from src.uart import UARTServer
from src.tcp import SocketServer

logging.debug('Starting Application')

app = FastAPI()
templates = Jinja2Templates(directory='src/templates')

# TODO - Rethink these variables
tracker_data = TrackerData()
uart_server = UARTServer(tracker_data)
tcp_socket = SocketServer(tracker_data, port=10760)


def update_tracker_data(update_data: PythonToJavascriptData):
    for key, val in update_data.dict().items():
        if val is not None:
            setattr(tracker_data.base, key, val)


@app.get('/', response_class=HTMLResponse)
def astro_form(request: Request):
    return templates.TemplateResponse('AstroForm.html', {
        'request': request,
        'solar_system': {
            b: b
            for b in DataFile.solar_system()
        },
        'ngc': DataFile.build_select_ngc(),
        'messer': DataFile.build_select_messer(),
        'star': DataFile.build_select_star()
    })


@app.get('/soft_adder/{button}/{scale}')
def soft_adder(button: str, scale: str):
    button = int(button)
    scale = float(scale)
    if not tracker_data.base.soft_ra_adder:
        tracker_data.base.soft_ra_adder = 0
    if not tracker_data.base.soft_dec_adder:
        tracker_data.base.soft_dec_adder = 0

    if button == 0:
        tracker_data.base.soft_ra_adder += scale / tracker_data.base.ra_or_az_pulse_per_deg
    elif button == 1:
        tracker_data.base.soft_ra_adder -= scale / tracker_data.base.ra_or_az_pulse_per_deg
    elif button == 2:
        tracker_data.base.soft_dec_adder += scale / tracker_data.base.dec_or_alt_pulse_per_deg
    elif button == 3:
        tracker_data.base.soft_dec_adder -= scale / tracker_data.base.dec_or_alt_pulse_per_deg

    return tracker_data.base


@app.get('/convert/{celestial}/{key}')
def put_convert(celestial: CelestialObjectGroup, key: str = None):
    sky_coord = None
    data = None
    tracker_data.base.object_info = ""

    if celestial == CelestialObjectGroup.solar_system:
        solar_system_ephemeris.set('builtin')
        sky_coord = get_body(key, Time(datetime.utcnow(), scale='utc'), tracker_data.earth_location)

        tracker_data.base.ra_hour_decimal = Angle(sky_coord.ra).hourangle
        tracker_data.base.dec_deg_decimal = float(sky_coord.dec.value)
        tracker_data.base.object_info = "Solar System " + key + " "

    elif celestial == CelestialObjectGroup.ngc:
        data = DataFile.get_ngc(key)

        tracker_data.base.object_info = "NGC " + key + " "

    elif celestial == CelestialObjectGroup.messer:
        data = DataFile.get_messer(key)

        tracker_data.base.object_info = "Messer " + key + " "

    elif celestial == CelestialObjectGroup.star:
        data = DataFile.get_star(key)

        tracker_data.base.object_info = "Star " + key + " "

    elif celestial == CelestialObjectGroup.custom:
        data = ""

        if tracker_data.base.custom_ra_hour:
            tracker_data.base.ra_hour_decimal = tracker_data.base.custom_ra_hour + \
                                                (tracker_data.base.custom_ra_min * 0.01666) + (
                                                        tracker_data.base.custom_ra_sec * 0.0002778)
            tracker_data.base.dec_deg_decimal = tracker_data.base.custom_dec_deg + (tracker_data.base.custom_dec_min * 0.01666) + (tracker_data.base.custom_dec_sec * 0.0002778)

        sky_coord = SkyCoord(ra=tracker_data.base.ra_hour_decimal * u.hour,
                             dec=tracker_data.base.dec_deg_decimal * u.degree, frame='icrs')

        tracker_data.base.object_info = "Custom "

    if data:
        tracker_data.base.ra_hour_decimal = float(data['ra_hour_decimal'])
        tracker_data.base.dec_deg_decimal = float(data['dec_deg_decimal'])
        sky_coord = SkyCoord(ra=tracker_data.base.ra_hour_decimal * u.hour,
                             dec=tracker_data.base.dec_deg_decimal * u.degree, frame='icrs')

    if sky_coord:
        tracker_data.sky_coord = sky_coord
        tracker_data.base.object_info += sky_coord.to_string('hmsdms')

        tracker_data.base.calculating = ""
        tracker_data.base.new_start = False

        if tracker_data.sky_coord:
            tracker_data.base.calculate(tracker_data.sky_coord, tracker_data.earth_location)
        return tracker_data.base

    raise status.HTTP_404_NOT_FOUND


def move_custom():
    print('hello')
    put_convert(CelestialObjectGroup.custom)


@app.get('/update_tracker', response_model=PythonToJavascriptData)
def get_update_tracker():
    return tracker_data.base


@app.post('/update_tracker', response_model=PythonToJavascriptData)
def post_update_tracker(results: PythonToJavascriptData = None):
    update_tracker_data(results)
    if tracker_data.sky_coord:
        tracker_data.base.calculate(tracker_data.sky_coord, tracker_data.earth_location)
    return tracker_data.base


@app.on_event('startup')
def startup():
    tracker_data.base.az_steps = 0
    tracker_data.base.alt_steps = 0
    tracker_data.base.drive_deg_ra = 0
    tracker_data.base.drive_deg_dec = 0
    tracker_data.base.soft_ra_adder = 0
    tracker_data.base.soft_dec_adder = 0
    tracker_data.base.dec_alt_osc_calc = 5
    tracker_data.base.ra_az_osc_calc = 5
    tracker_data.base.drive_deg_alt = 0
    tracker_data.base.drive_deg_az = 0

    # Add initial tracker_data info before starting uart thread
    tracker_data.base.control_mode = 1
    earth_location = Builder.earth_location(tracker_data.base.latitude, tracker_data.base.longitude, tracker_data.base.sea_level)
    sidereal = Time(datetime.utcnow(), scale='utc', location=earth_location).sidereal_time('mean')
    tracker_data.base.local_sidereal = float(Angle(sidereal).hourangle)

    if tracker_data.base.mount_select < 2:  # EQ - fork
        if tracker_data.base.north_south_select == 0:  # north aline
            tracker_data.base.dec_deg_decimal = 90
            tracker_data.base.ra_hour_decimal = tracker_data.base.local_sidereal
        else: # south aline
            tracker_data.base.dec_deg_decimal = -90
            tracker_data.base.ra_hour_decimal = tracker_data.base.local_sidereal

    if tracker_data.base.mount_select == 2:  # alt az
        if tracker_data.base.north_south_select == 0:  # north aline
            tracker_data.base.dec_deg_decimal = 90 - tracker_data.base.latitude
            tracker_data.base.ra_hour_decimal = tracker_data.base.local_sidereal
        else:  # south aline
            tracker_data.base.dec_deg_decimal = -90 - tracker_data.base.latitude
            tracker_data.base.ra_hour_decimal = tracker_data.base.local_sidereal

    put_convert(CelestialObjectGroup.custom)
    tracker_data.base.new_start = True

    uart_thread = threading.Thread(target=uart_server.background_task)
    uart_thread.start()

    socket_thread = threading.Thread(target=tcp_socket.background_task)
    socket_thread.start()
