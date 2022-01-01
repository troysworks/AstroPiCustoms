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

    custom_ra_hour: Optional[int]
    custom_ra_min: Optional[int]
    custom_ra_sec: Optional[float]
    custom_dec_deg: Optional[int]
    custom_dec_min: Optional[int]
    custom_dec_sec: Optional[float]

    local_sidereal: Optional[float]
    mount_select: Optional[int]
    ra_hour_decimal: Optional[float]
    dec_deg_decimal: Optional[float]
    object_info: Optional[str]
    calculating: Optional[str]

    running: Optional[bool]

    def calculate(self, sky_coord: SkyCoord, earth_location: EarthLocation):
        self.calculate_alt_az(sky_coord, earth_location)  # 1st
        self.calculate_drive_counts(sky_coord, earth_location)  # 2nd

    def calculate_alt_az(self, sky_coord: SkyCoord, earth_location: EarthLocation):
        transform = sky_coord.transform_to(AltAz(obstime=Time(datetime.utcnow(), scale='utc'), location=earth_location))
        # ra_dec = sky_coord.transform_to(RADEC(obstime=Time(datetime.utcnow(), scale='utc'), location=earth_location))
        alt_dms = transform.alt.dms
        az_dms = transform.az.dms

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

    def calculate_drive_counts(self, sky_coord: SkyCoord, earth_location: EarthLocation):
        transform = sky_coord.transform_to(AltAz(obstime=Time(datetime.utcnow(), scale='utc'), location=earth_location))
        altitude_deg = transform.alt
        azimuth_deg = transform.az
        ra_decimal_hrs = self.ra_hour_decimal  # Angle(self.ra_hour_decimal).value
        dec_decimal_deg = self.dec_deg_decimal  # Angle(self.dec_deg_decimal).degree

        quads = [0, 0, 0, 0]
        q24 = 0

        # define  Quads
        if self.local_sidereal <= 12:
            quads[1] = self.local_sidereal
            quads[0] = self.local_sidereal + 6
            quads[3] = self.local_sidereal + 12
            if self.local_sidereal >= 6:
                quads[2] = self.local_sidereal - 6
            else:
                quads[2] = self.local_sidereal + 18
        else:
            quads[1] = self.local_sidereal
            quads[2] = self.local_sidereal - 6
            quads[3] = self.local_sidereal - 12
            if self.local_sidereal + 6 >= 24:
                quads[0] = self.local_sidereal - 18
            else:
                quads[0] = self.local_sidereal + 6

        # get  24 hr quad
        q = quads.index(max(quads))
        if q == 0:  # NE
            q24 = 3
        if q == 1:  # NW
            q24 = 0
        if q == 2:  # SW
            q24 = 1
        if q == 3:  # SE
            q24 = 2

        if self.mount_select == 1:  # Fork Mount
            if self.local_sidereal <= ra_decimal_hrs:
                hrs_ra = ra_decimal_hrs - self.local_sidereal
                ra_count = hrs_ra * 15 / self.ra_or_az_pulse_per_deg
            else:
                hrs_ra = (24 - self.local_sidereal) + ra_decimal_hrs
                ra_count = hrs_ra * 15 / self.ra_or_az_pulse_per_deg

            dec_count = (dec_decimal_deg - 90) / self.dec_or_alt_pulse_per_deg
            self.az_ra_steps_sp = float("{:.3f}".format(ra_count))
            self.alt_dec_steps_sp = float("{:.3f}".format(dec_count))

        if self.mount_select == 0:  # EQ
            # check quad 0  NE
            if (quads[1] <= ra_decimal_hrs <= quads[0]) or (
                    q24 == 0 and (ra_decimal_hrs <= quads[0] or ra_decimal_hrs >= quads[1])):
                if q24 == 0:
                    if ra_decimal_hrs >= quads[1]:
                        ra_count = (6 - (ra_decimal_hrs - quads[1])) * 15 / float(self.ra_or_az_pulse_per_deg)
                    else:
                        ra_count = (quads[0] - ra_decimal_hrs) * 15 / float(self.ra_or_az_pulse_per_deg)
                else:
                    ra_count = (quads[0] - ra_decimal_hrs) * 15 / float(self.ra_or_az_pulse_per_deg)
                dec_count = (90 - dec_decimal_deg) * -1 / float(self.dec_or_alt_pulse_per_deg)
                pointer = "NE"

            # check  quad 1 NW
            if (quads[2] <= ra_decimal_hrs <= quads[1]) or (
                    q24 == 1 and (ra_decimal_hrs <= quads[1] or ra_decimal_hrs >= quads[2])):
                if q24 == 1:
                    if ra_decimal_hrs >= quads[2]:
                        ra_count = (ra_decimal_hrs - quads[2]) * 15 * -1 / float(self.ra_or_az_pulse_per_deg)
                    else:
                        ra_count = (6 - (quads[1] - ra_decimal_hrs)) * 15 * -1 / float(self.ra_or_az_pulse_per_deg)
                else:
                    ra_count = (quads[1] - ra_decimal_hrs) * 15 / float(self.ra_or_az_pulse_per_deg)
                dec_count = (90 - dec_decimal_deg) / float(self.dec_or_alt_pulse_per_deg)
                pointer = "NW"

            # check quad 2 SW
            if (quads[3] <= ra_decimal_hrs <= quads[2]) or (
                    q24 == 2 and (ra_decimal_hrs <= quads[2] or ra_decimal_hrs >= quads[3])):
                if q24 == 2:
                    if ra_decimal_hrs >= quads[3]:
                        ra_count = (6 - (ra_decimal_hrs - quads[3])) * 15 * -1 / float(self.ra_or_az_pulse_per_deg)
                    else:
                        ra_count = (quads[2] - ra_decimal_hrs) * 15 * -1 / float(self.ra_or_az_pulse_per_deg)
                else:
                    ra_count = (quads[2] - ra_decimal_hrs) * 15 * -1 / float(self.ra_or_az_pulse_per_deg)
                dec_count = (90 - dec_decimal_deg) / float(self.dec_or_alt_pulse_per_deg)
                pointer = "SW"

            # check quad 3 SE
            if (quads[0] <= ra_decimal_hrs <= quads[3]) or (
                    q24 == 3 and (ra_decimal_hrs <= quads[3] or ra_decimal_hrs >= quads[0])):
                if q24 == 3:
                    if ra_decimal_hrs >= quads[0]:
                        ra_count = (ra_decimal_hrs - quads[0]) * 15 / float(self.ra_or_az_pulse_per_deg)
                    else:
                        ra_count = (6 - (quads[3] - ra_decimal_hrs)) * 15 / float(self.ra_or_az_pulse_per_deg)
                else:
                    ra_count = (ra_decimal_hrs - quads[0]) * 15 / float(self.ra_or_az_pulse_per_deg)
                dec_count = (90 - dec_decimal_deg) * -1 / float(self.dec_or_alt_pulse_per_deg)
                pointer = "SE"
            self.az_ra_steps_sp = "{:.3f}".format(ra_count)
            self.alt_dec_steps_sp = "{:.3f}".format(dec_count)

        #  use alt az set points
        if self.mount_select == 2:
            az_count = azimuth_deg.deg / self.ra_or_az_pulse_per_deg
            alt_count = altitude_deg.deg / self.dec_or_alt_pulse_per_deg

            self.az_ra_steps_sp = "{:.3f}".format(az_count)
            self.alt_dec_steps_sp = "{:.3f}".format(alt_count)


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
    star = 'star'
    custom = 'custom'


class Builder:
    @staticmethod
    def sky_coord(right_ascension: str, declination: str) -> SkyCoord:
        return SkyCoord(right_ascension, declination, frame='icrs')

    @staticmethod
    def earth_location(latitude: float, longitude: float, height: float) -> EarthLocation:
        return EarthLocation(lat=latitude * u.deg, lon=longitude * u.deg, height=height * u.m)
