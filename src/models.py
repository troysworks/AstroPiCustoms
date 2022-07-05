import json
from datetime import datetime, timezone
from enum import Enum
from time import time
from typing import Optional

import astropy.units as u

from astropy.coordinates import SkyCoord, EarthLocation, AltAz, Angle
from astropy.time import Time
from pydantic import BaseModel


avg_counter = 0
last_time_start = 0
last_az_deg = 0
last_alt_deg = 0


def calculate_utc_offset(self):
    tz = datetime.now(timezone.utc).astimezone().tzinfo
    # tz = pytz.timezone('Asia/Calcutta')
    dt = datetime.utcnow()

    offset_seconds = tz.utcoffset(dt).seconds
    offset_hr = 24 - int(offset_seconds / 3600.0)
    if self.longitude < 0:
        offset_hr *= -1
    return offset_hr


class PythonToDriveData(BaseModel):
    az_ra_steps_sp: Optional[float]
    alt_dec_steps_sp: Optional[float]
    control_mode: Optional[int]


class DriveToPythonData(BaseModel):
    alt_steps: Optional[float]
    alt_steps_adder: Optional[float]
    alt_diff: Optional[float]
    alt_osc_drive: Optional[int]

    az_steps: Optional[float]
    az_steps_adder: Optional[float]
    az_diff: Optional[float]
    az_osc_drive: Optional[int]

    drive_status: Optional[str]


class PythonToJavascriptData(PythonToDriveData, DriveToPythonData):
    latitude: Optional[float]
    latitude_dm: Optional[str]
    longitude: Optional[float]
    longitude_dms: Optional[str]
    sea_level: Optional[float]

    ra_or_az_pulse_per_deg: Optional[float]
    dec_or_alt_pulse_per_deg: Optional[float]

    altitude_deg: Optional[int]
    altitude_min: Optional[int]
    altitude_sec: Optional[float]
    azimuth_deg: Optional[int]
    azimuth_min: Optional[int]
    azimuth_sec: Optional[float]
    altitude_deg_decimal: Optional[float]
    azimuth_deg_decimal: Optional[float]

    custom_ra_hour: Optional[int]
    custom_ra_min: Optional[int]
    custom_ra_sec: Optional[float]
    custom_dec_deg: Optional[int]
    custom_dec_min: Optional[int]
    custom_dec_sec: Optional[float]

    local_sidereal: Optional[float]
    local_sidereal_hms: Optional[str]
    new_start: Optional[bool]
    mount_select: Optional[int]
    ra_hour_decimal: Optional[float]
    ra_hour_hms: Optional[str]
    dec_deg_decimal: Optional[float]
    dec_deg_dms: Optional[str]
    object_info: Optional[str]
    calculating: Optional[str]
    soft_ra_adder: Optional[float]
    soft_dec_adder: Optional[float]
    north_south_select: Optional[int]
    dec_alt_osc_calc: Optional[int]
    ra_az_osc_calc: Optional[int]
    running: Optional[bool]
    meridian: Optional[str]
    utcoffset: Optional[int]
    local_time: Optional[str]
    local_date: Optional[str]
    custom_goto: Optional[bool]
    diff_deg: Optional[float]
    offset_deg: Optional[float]
    az_to_ra: Optional[str]
    alt_to_dec: Optional[str]
    drive_deg_ra: Optional[float]
    drive_deg_dec: Optional[float]
    drive_deg_alt: Optional[float]
    drive_deg_az: Optional[float]

    def calculate(self, sky_coord: SkyCoord, earth_location: EarthLocation):
        self.calculate_alt_az(sky_coord, earth_location)  # 1st
        self.calculate_drive_counts()  # 2nd

    def calculate_alt_az(self, sky_coord: SkyCoord, earth_location: EarthLocation):
        tz = datetime.now(timezone.utc).astimezone().tzinfo
        dt = datetime.utcnow()
        offset_hr = 24 - (tz.utcoffset(dt).seconds / 3600)

        if self.longitude < 0:
            offset_hr *= -1
        self.utcoffset = int(offset_hr)

        transform = sky_coord.transform_to(AltAz(obstime=Time(datetime.utcnow(), scale='utc'), location=earth_location))
        alt_dms = transform.alt.dms
        az_dms = transform.az.dms

        self.altitude_deg_decimal = float("{:.3f}".format(transform.alt.deg))
        self.azimuth_deg_decimal = float("{:.3f}".format(transform.az.deg))

        self.altitude_deg = alt_dms.d
        self.altitude_min = alt_dms.m
        self.altitude_sec = float("{:.2f}".format(alt_dms.s))

        self.azimuth_deg = az_dms.d
        self.azimuth_min = az_dms.m
        self.azimuth_sec = float("{:.2f}".format(az_dms.s))

        sidereal = Time(datetime.utcnow(), scale='utc', location=earth_location).sidereal_time('mean')
        self.local_sidereal = float(Angle(sidereal).hourangle)
        self.local_sidereal_hms = self.dms(Angle(sidereal).hourangle)

        if self.new_start:
            self.ra_hour_decimal = self.local_sidereal
            self.drive_deg_ra = 0
        else:
            self.ra_hour_decimal = Angle(sky_coord.ra).hour

        # Convert current sidereal and sky_coord to an Angle
        sky_coord_angle = Angle(sky_coord.ra)

        # Calc diff
        diff_angle: Angle = sky_coord_angle - sidereal

        # Roll over the angle to a negative diff after 180d or 12h
        diff_angle_180 = diff_angle.wrap_at(180 * u.deg)
        self.diff_deg = diff_angle_180.value

        if self.diff_deg < 0:
            self.offset_deg = (90 - abs(self.diff_deg)) * -1
        else:
            self.offset_deg = 90 - self.diff_deg

        new_altaz = SkyCoord(
            AltAz(obstime=Time(datetime.utcnow(), scale='utc'), az=self.drive_deg_az * u.degree, alt=self.drive_deg_alt * u.degree,
                  location=earth_location))
        new_radec = new_altaz.transform_to('icrs')
        self.az_to_ra = Angle(new_radec.ra).hourangle
        self.alt_to_dec = Angle(new_radec.dec).value

        if self.mount_select < 2:
            if self.new_start or self.drive_status == 'Home Pos':
                self.ra_hour_hms = self.dms(self.local_sidereal)
                self.dec_deg_dms = self.dec(self.drive_deg_dec)
            else:
                self.ra_hour_hms = self.dms(self.local_sidereal + (self.drive_deg_ra / 15))
                self.dec_deg_dms = self.dec(self.drive_deg_dec)
        else:
            if self.new_start:
                self.ra_hour_hms = self.dms(self.local_sidereal)
                self.dec_deg_dms = self.dec(90 - self.latitude)
            else:
                self.ra_hour_hms = self.dms(self.az_to_ra)
                self.dec_deg_dms = self.dec(self.alt_to_dec)

        self.dec_deg_decimal = Angle(sky_coord.dec).degree
        self.local_time = datetime.now().time().strftime("%H:%M:%S")
        self.local_date = datetime.now().date().strftime("%m/%d/%y")

        self.latitude_dm = self.dm(self.latitude)  # sDD*MM#
        self.longitude_dms = self.ldeg(self.latitude)  # sDDD*MM:SS#

        if self.ra_hour_decimal > self.local_sidereal > self.ra_hour_decimal - .1 and self.mount_select < 2:
            self.meridian = "Meridian Flip Soon"
        else:
            self.meridian = ""

    @staticmethod
    def dms(decimal):
        h = int(decimal)
        m = int((decimal * 60) % 60)
        s = int((decimal * 3600) % 60)
        return "%02d:%02d:%02d" % (h, m, s)

    @staticmethod
    def dec(decimal):
        h = int(decimal)
        m = int((decimal * 60) % 60)
        s = int((decimal * 3600) % 60)
        x = "%02d*%02d’%02d" % (h, m, s)
        return x
        #  sDD*MM’SS

    @staticmethod
    def ldeg(decimal):
        h = int(decimal)
        m = int((decimal * 60) % 60)
        s = int((decimal * 3600) % 60)
        x = "%02d*%02d:%02d" % (h, m, s)
        return x

    @staticmethod
    def dm(decimal):
        h = int(decimal)
        m = int((decimal * 60) % 60)
        return "%02d*%02d" % (h, m)

    def calculate_drive_counts(self):
        global avg_counter, last_time_start, last_az_deg, last_alt_deg

        if self.custom_goto:
            self.control_mode = 2
            self.custom_goto = False
            from src.app import move_custom
            move_custom()

        ra_count = 0
        dec_count = 0

        if self.north_south_select == 0:  # north

            if self.mount_select == 0:  # EQ north
                ra_count = self.diff_deg / self.ra_or_az_pulse_per_deg
                self.drive_deg_ra = self.az_steps * self.ra_or_az_pulse_per_deg
                if self.diff_deg < 0:  # east
                    dec_count = (90 - self.dec_deg_decimal) * -1 / self.dec_or_alt_pulse_per_deg
                    self.drive_deg_dec = 90 + (self.dec_or_alt_pulse_per_deg * self.alt_steps)
                else:  # west
                    dec_count = (90 - self.dec_deg_decimal) / self.dec_or_alt_pulse_per_deg
                    self.drive_deg_dec = 90 - (self.dec_or_alt_pulse_per_deg * self.alt_steps)

            if self.mount_select == 1:  # Fork Mount north
                if self.diff_deg >= 0:  # west
                    ra_count = (180 - self.diff_deg) / self.ra_or_az_pulse_per_deg
                    self.drive_deg_ra = 180 - (self.ra_or_az_pulse_per_deg * self.az_steps)
                else:
                    ra_count = (180 - self.diff_deg) * -1 / self.ra_or_az_pulse_per_deg
                    self.drive_deg_ra = 180 + (self.ra_or_az_pulse_per_deg * self.az_steps)
                dec_count = (90 - self.dec_deg_decimal) * -1 / self.dec_or_alt_pulse_per_deg
                self.drive_deg_dec = 90 + (self.dec_or_alt_pulse_per_deg * self.alt_steps)

            #  use alt az set points north
            if self.mount_select == 2:
                ra_count = self.azimuth_deg_decimal / self.ra_or_az_pulse_per_deg
                dec_count = self.altitude_deg_decimal / self.dec_or_alt_pulse_per_deg
                self.drive_deg_az = self.az_steps * self.ra_or_az_pulse_per_deg
                self.drive_deg_alt = self.alt_steps * self.dec_or_alt_pulse_per_deg

        else:  # south

            if self.mount_select == 0:  # EQ south
                ra_count = self.diff_deg / self.ra_or_az_pulse_per_deg * -1
                self.drive_deg_ra = self.az_steps * self.ra_or_az_pulse_per_deg * -1
                if self.diff_deg < 0:  # east
                    dec_count = (-90 - self.dec_deg_decimal) / self.dec_or_alt_pulse_per_deg
                    self.drive_deg_dec = (90 + (self.dec_or_alt_pulse_per_deg * self.alt_steps)) * -1
                else:  # west
                    dec_count = (-90 - self.dec_deg_decimal) * -1 / self.dec_or_alt_pulse_per_deg
                    self.drive_deg_dec = -90 + (self.dec_or_alt_pulse_per_deg * self.alt_steps)

            if self.mount_select == 1:  # Fork Mount south
                if self.diff_deg >= 0:
                    ra_count = (180 - self.diff_deg) / self.ra_or_az_pulse_per_deg * -1
                    self.drive_deg_ra = 180 + (self.ra_or_az_pulse_per_deg * self.az_steps)
                else:
                    ra_count = (-180 + self.diff_deg) / self.ra_or_az_pulse_per_deg * -1
                    self.drive_deg_ra = (-180 + (self.ra_or_az_pulse_per_deg * self.az_steps)) * -1
                dec_count = (-90 - self.dec_deg_decimal) / self.dec_or_alt_pulse_per_deg
                self.drive_deg_dec = (90 + (self.dec_or_alt_pulse_per_deg * self.alt_steps)) * -1

            #  use alt az set points south
            if self.mount_select == 2:
                ra_count = (180 - self.azimuth_deg_decimal) / self.ra_or_az_pulse_per_deg * -1
                dec_count = self.altitude_deg_decimal / self.dec_or_alt_pulse_per_deg
                self.drive_deg_az = (180 + self.az_steps * self.ra_or_az_pulse_per_deg)
                self.drive_deg_alt = self.alt_steps * self.dec_or_alt_pulse_per_deg

        if self.mount_select < 2:  # Eq and Fork
            self.dec_alt_osc_calc = 0
            self.ra_az_osc_calc = int(((360 / self.ra_or_az_pulse_per_deg) * 16) / 24 / 60 / 60)

        if self.mount_select == 2:  # Alt Az

            if avg_counter == 0:
                last_time_start = time() * 1000
                last_az_deg = self.azimuth_deg_decimal
                last_alt_deg = self.altitude_deg_decimal

            avg_counter += 1
            if avg_counter >= 20:
                avg_counter = 0
                time_diff = (time() * 1000) - last_time_start

                az_diff = abs(self.azimuth_deg_decimal - last_az_deg)
                alt_diff = abs(self.altitude_deg_decimal - last_alt_deg)
                dec_alt = int((alt_diff / (time_diff / 1000) / self.dec_or_alt_pulse_per_deg) * 16)
                self.dec_alt_osc_calc = int(dec_alt - (dec_alt * .05))
                ra_az = int((az_diff / (time_diff / 1000) / self.ra_or_az_pulse_per_deg) * 16)
                self.ra_az_osc_calc = int(ra_az - (ra_az * .05))

        self.az_ra_steps_sp = float("{:.3f}".format(ra_count + self.soft_ra_adder))
        self.alt_dec_steps_sp = float("{:.3f}".format(dec_count + self.soft_dec_adder))


class TrackerData:
    base: PythonToJavascriptData
    sky_coord: Optional[SkyCoord]
    earth_location: Optional[EarthLocation]

    def __init__(self):
        with open('config.json', 'r') as f:
            config = json.load(f)

        self.base = PythonToJavascriptData(**config)

        self.sky_coord = None
        self.earth_location = Builder.earth_location(self.base.latitude, self.base.longitude, self.base.sea_level)


class CelestialObjectGroup(str, Enum):
    solar_system = 'solar_system'
    ngc = 'ngc'
    messer = 'messer'
    star = 'star'
    custom = 'custom'


class Builder:
    @staticmethod
    def sky_coord(right_ascension: str, declination: str) -> SkyCoord:
        return SkyCoord(right_ascension, declination, frame='icrs')

    @staticmethod
    def earth_location(latitude: float, longitude: float, height: float) -> EarthLocation:
        return EarthLocation(lat=latitude * u.deg, lon=longitude * u.deg, height=height * u.m)
