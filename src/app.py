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
from src.models import PythonToJavascriptData, CelestialObjectGroup, TrackerData
from src.uart import UARTServer

logging.debug('Starting Application')

app = FastAPI()
templates = Jinja2Templates(directory='src/templates')

tracker_data = TrackerData()
uart_server = UARTServer(tracker_data)


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
        'star': DataFile.build_select_star()
    })


@app.get('/convert/{celestial}/{key}')
async def put_convert(celestial: CelestialObjectGroup, key: str):
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

    elif celestial == CelestialObjectGroup.star:
        data = DataFile.get_star(key)

        tracker_data.base.object_info = "Star " + key + " "

    elif celestial == CelestialObjectGroup.custom:
        data = ""
        tracker_data.base.ra_hour_decimal = tracker_data.base.custom_ra_hour + \
                                            (tracker_data.base.custom_ra_min * 0.01666) + (
                                                    tracker_data.base.custom_ra_sec * 0.0002778)
        tracker_data.base.dec_deg_decimal = tracker_data.base.custom_dec_deg + \
                                            (tracker_data.base.custom_dec_min * 0.01666) + (
                                                    tracker_data.base.custom_dec_sec * 0.0002778)
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
        tracker_data.base.custom_ra_hour = int(tracker_data.base.ra_hour_decimal)
        tracker_data.base.custom_ra_min = int((tracker_data.base.ra_hour_decimal * 60) % 60)
        tracker_data.base.custom_ra_sec = (tracker_data.base.ra_hour_decimal * 3600) % 60

        dd = tracker_data.base.dec_deg_decimal
        is_positive = dd >= 0
        dd = abs(dd)
        minutes, seconds = divmod(dd * 3600, 60)
        degrees, minutes = divmod(minutes, 60)
        degrees = degrees if is_positive else -degrees

        tracker_data.base.custom_dec_deg = degrees
        tracker_data.base.custom_dec_min = minutes
        tracker_data.base.custom_dec_sec = seconds
        tracker_data.base.calculating = ""

        if not tracker_data.base.control_mode:
            tracker_data.base.control_mode = 0
        if tracker_data.sky_coord:
            tracker_data.base.calculate(tracker_data.sky_coord, tracker_data.earth_location)
        return tracker_data.base

    raise status.HTTP_404_NOT_FOUND


@app.get('/update_tracker', response_model=PythonToJavascriptData)
async def get_update_tracker():
    return tracker_data.base


@app.post('/update_tracker', response_model=PythonToJavascriptData)
async def post_update_tracker(results: PythonToJavascriptData = None):
    update_tracker_data(results)
    if tracker_data.sky_coord:
        tracker_data.base.calculate(tracker_data.sky_coord, tracker_data.earth_location)
    return tracker_data.base


@app.on_event('startup')
def startup():
    thread = threading.Thread(target=uart_server.background_task)
    thread.start()
