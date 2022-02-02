import csv
from typing import List

from astropy.coordinates import solar_system_ephemeris
from starlette import status


class DataFile:
    # Lazy load
    _ngc: List[dict] = None
    _messer: List[dict] = None
    _star: List[dict] = None

    _ngc_key = 'NGC'
    _messer_key = 'M'
    _star_key = 'Star Name'

    _ngc_tooltip = 'Description'
    _messer_tooltip = 'Description'
    _star_tooltip = 'description'

    @classmethod
    def read(cls, filename: str) -> List[dict]:
        results: List[dict] = []
        with open(filename) as file:
            reader = csv.DictReader(file)
            for row in reader:
                results.append(row)

        return results

    @classmethod
    def ngc(cls) -> List[dict]:
        if not cls._ngc:
            cls._ngc = cls.read('src/data/NGCData.csv')

        return cls._ngc

    @classmethod
    def messer(cls) -> List[dict]:
        if not cls._messer:
            cls._messer = cls.read('src/data/Messer.csv')

        return cls._messer

    @classmethod
    def star(cls) -> List[dict]:
        if not cls._star:
            cls._star = cls.read('src/data/NamedStars.csv')

        return cls._star

    @classmethod
    def solar_system(cls):
        return solar_system_ephemeris.bodies

    @classmethod
    def get_ngc(cls, key: str):
        try:
            return next(
                row
                for row in cls.ngc()
                if row[cls._ngc_key] == key
            )
        except Exception as e:
            raise status.HTTP_404_NOT_FOUND

    @classmethod
    def get_messer(cls, key: str):
        try:
            return next(
                row
                for row in cls.messer()
                if row[cls._messer_key] == key
            )
        except Exception as e:
            raise status.HTTP_404_NOT_FOUND

    @classmethod
    def get_star(cls, key: str):
        try:
            return next(
                row
                for row in cls.star()
                if row[cls._star_key] == key
            )
        except Exception as e:
            raise status.HTTP_404_NOT_FOUND

    @classmethod
    def build_select_ngc(cls) -> dict:
        return {
            row[cls._ngc_key]: row[cls._ngc_tooltip]
            for row in cls.ngc()
        }

    @classmethod
    def build_select_messer(cls) -> dict:
        return {
            row[cls._messer_key]: row[cls._messer_tooltip]
            for row in cls.messer()
        }

    @classmethod
    def build_select_star(cls) -> dict:
        return {
            row[cls._star_key]: row[cls._star_tooltip]
            for row in cls.star()
        }
