from __future__ import annotations

import pycountry
import reverse_geocoder as rg
from PIL import Image
from PIL.ExifTags import GPSTAGS
from PIL.ExifTags import TAGS
from PIL.Image import Exif

# TODO: pycountry and reverse_geocoder can only output in English...


# https://auth0.com/blog/read-edit-exif-metadata-in-photos-with-python/
def dms_coordinates_to_dd_coordinates(coordinates, coordinates_ref):
    decimal_degrees = coordinates[0] + coordinates[1] / 60 + coordinates[2] / 3600

    if coordinates_ref == "S" or coordinates_ref == "W":
        decimal_degrees = -decimal_degrees

    return decimal_degrees


def exif_to_dict(gps_info):
    gps_data = {}
    for t in gps_info:
        sub_decoded = GPSTAGS.get(t, t)
        gps_data[sub_decoded] = gps_info[t]

    return gps_data


def get_location_info(coordinates):
    location_info = rg.search(coordinates)[0]
    location_info["country"] = pycountry.countries.get(alpha_2=location_info["cc"])
    return location_info


def coordinates_to_country_data(gps_info):
    gps_info = exif_to_dict(gps_info)
    gps_latitude = gps_info["GPSLatitude"]
    gps_latitude_ref = gps_info["GPSLatitudeRef"]
    gps_longitude = gps_info["GPSLongitude"]
    gps_longitude_ref = gps_info["GPSLongitudeRef"]
    decimal_latitude = dms_coordinates_to_dd_coordinates(gps_latitude, gps_latitude_ref)
    decimal_longitude = dms_coordinates_to_dd_coordinates(
        gps_longitude,
        gps_longitude_ref,
    )
    coordinates = (decimal_latitude, decimal_longitude)
    return get_location_info(coordinates)


def get_location_name(gps_info):
    location_info = coordinates_to_country_data(gps_info)
    city = location_info["name"]
    # state = location_info["admin1"]
    # cc = location_info["cc"]
    country = location_info["country"]
    return city, country.name


# https://github.com/python-pillow/Pillow/issues/5863
def get_exif(file_name) -> Exif:
    image: Image.Image = Image.open(file_name)
    return image.getexif()


def get_geo(exif):
    for key, value in TAGS.items():
        if value == "GPSInfo":
            break
    gps_info = exif.get_ifd(key)
    return {GPSTAGS.get(key, key): value for key, value in gps_info.items()}


def get_exif_ifd(exif):
    for key, value in TAGS.items():
        if value == "ExifOffset":
            break
    info = exif.get_ifd(key)
    return {TAGS.get(key, key): value for key, value in info.items()}
