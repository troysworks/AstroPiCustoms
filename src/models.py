import json
from datetime import datetime
from enum import Enum
from typing import Optional

import astropy.units as u
from astropy.coordinates import SkyCoord, EarthLocation, AltAz, Angle
from astropy.time import Time
from pydantic import BaseModel


class PythonToDriveData(BaseModel):
    az_ra_steps_sp: Optional[float]
    alt_dec_steps_sp: Optional[float]
    control_mode: Optional[int]


class DriveToPythonData(BaseModel):
    alt_steps: Optional[float]
    alt_steps_adder: Optional[float]
    alt_diff: Optional[float]
    az_steps: Optional[float]
    az_steps_adder: Optional[float]
    az_diff: Optional[float]
    drive_status: Optional[str]


class PythonToJavascriptData(PythonToDriveData, DriveToPythonData):
    latitude: Optional[float]
    longitude: Optional[float]
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
    local_sidereal_start: Optional[float]
    mount_select: Optional[int]
    ra_hour_decimal: Optional[float]
    dec_deg_decimal: Optional[float]
    object_info: Optional[str]
    calculating: Optional[str]
    soft_ra_adder: Optional[float]
    soft_dec_adder: Optional[float]

    running: Optional[bool]
    meridian: Optional[str]

    def calculate(self, sky_coord: SkyCoord, earth_location: EarthLocation):
        self.calculate_alt_az(sky_coord, earth_location)  # 1st
        self.calculate_drive_counts(sky_coord, earth_location)  # 2nd

    def calculate_alt_az(self, sky_coord: SkyCoord, earth_location: EarthLocation):
        transform = sky_coord.transform_to(AltAz(obstime=Time(datetime.utcnow(), scale='utc'), location=earth_location))
        # ra_dec = sky_coord.transform_to(RADEC(obstime=Time(datetime.utcnow(), scale='utc'), location=earth_location))
        alt_dms = transform.alt.dms
        az_dms = transform.az.dms

        self.altitude_deg_decimal = float("{:.3f}".format(transform.alt.deg))
        self.azimuth_deg_decimal = float("{:.3f}".format(transform.az.deg))

        self.altitude_deg = alt_dms.d
        self.altitude_min = alt_dms.m
        self.altitude_sec = alt_dms.s

        self.azimuth_deg = az_dms.d
        self.azimuth_min = az_dms.m
        self.azimuth_sec = az_dms.s

        sidereal = Time(datetime.utcnow(), scale='utc', location=earth_location).sidereal_time('mean')
        self.local_sidereal = float(format("%.3f" % Angle(sidereal).hourangle))
        self.ra_hour_decimal = Angle(sky_coord.ra).hour
        self.dec_deg_decimal = Angle(sky_coord.dec).degree

        if self.ra_hour_decimal > self.local_sidereal > self.ra_hour_decimal - .1:
            self.meridian = "Meridian Flip Soon"
        else:
            self.meridian = ""

    def calculate_drive_counts(self, sky_coord: SkyCoord, earth_location: EarthLocation):
        altitude_deg = self.altitude_deg_decimal
        azimuth_deg = self.azimuth_deg_decimal
        dec_decimal_deg = self.dec_deg_decimal  # Angle(self.dec_deg_decimal).degree
        ra_count = 0
        dec_count = 0
        if self.soft_ra_adder is None:
            self.soft_ra_adder = 0
            self.soft_dec_adder = 0

        # Convert current sidereal and sky_coord to an Angle
        sidereal_angle = Time(datetime.utcnow(), scale='utc', location=earth_location).sidereal_time('mean')
        sky_coord_angle = Angle(sky_coord.ra)

        # Calc diff
        diff_angle: Angle = sky_coord_angle - sidereal_angle

        # Roll over the angle to a negative diff after 180d or 12h
        diff_angle_180 = diff_angle.wrap_at(180 * u.deg)
        diff_small_angle = diff_angle.wrap_at(90 * u.deg)
        # diff_deg_tuple = diff_angle.dms
        # diff_deg = diff_angle.dms.d
        diff_deg = diff_angle_180.value

        if diff_deg < 0:
            offset = (90 - abs(diff_deg)) * -1
        else:
            offset = 90 - diff_deg

        if self.mount_select == 0:  # EQ
            ra_count = offset / self.ra_or_az_pulse_per_deg
            if offset < 0:  # east
                dec_count = (90 - dec_decimal_deg) * -1 / float(self.dec_or_alt_pulse_per_deg)
            else:  # west
                dec_count = (90 - dec_decimal_deg) / float(self.dec_or_alt_pulse_per_deg)

        if self.mount_select == 1:  # Fork Mount
            if diff_deg >= 0:
                ra_count = (180 - diff_deg) / self.ra_or_az_pulse_per_deg
            else:
                ra_count = abs(-180 + diff_deg) / self.ra_or_az_pulse_per_deg
            dec_count = (90 - dec_decimal_deg) * -1 / float(self.dec_or_alt_pulse_per_deg)

        #  use alt az set points
        if self.mount_select == 2:
            ra_count = azimuth_deg.deg / self.ra_or_az_pulse_per_deg
            dec_count = altitude_deg.deg / self.dec_or_alt_pulse_per_deg

        self.az_ra_steps_sp = float("{:.3f}".format(ra_count + self.soft_ra_adder))
        self.alt_dec_steps_sp = float("{:.3f}".format(dec_count + self.soft_dec_adder))
        # print("self.soft_ra_adder ", self.soft_ra_adder, " self.soft_dec_adder ", self.soft_dec_adder)


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
