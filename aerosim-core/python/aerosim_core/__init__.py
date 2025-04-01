# aerosim_core classes
from aerosim_core._aerocore import Actor
from aerosim_core._aerocore import Rotator
from aerosim_core._aerocore import Ellipsoid
from aerosim_core._aerocore import Geoid
from aerosim_core._aerocore import WorldCoordinate

# coordinate system conversion util functions
from aerosim_core._aerocore import lla_to_ned
from aerosim_core._aerocore import ned_to_lla
from aerosim_core._aerocore import lla_to_cartesian
from aerosim_core._aerocore import ned_to_cartesian
from aerosim_core._aerocore import cartesian_to_lla
from aerosim_core._aerocore import cartesian_to_ned
from aerosim_core._aerocore import msl_to_hae
from aerosim_core._aerocore import hae_to_msl
from aerosim_core._aerocore import generate_trajectory
from aerosim_core._aerocore import generate_trajectory_linear
from aerosim_core._aerocore import generate_trajectory_from_adsb_csv
from aerosim_core._aerocore import msl_to_hae_with_offset
from aerosim_core._aerocore import hae_to_msl_with_offset
from aerosim_core._aerocore import haversine_distance_meters
from aerosim_core._aerocore import bearing_deg
from aerosim_core._aerocore import deviation_from_course_meters
from aerosim_core._aerocore import read_config_file

from .utils import (
    feet_to_meters,
    meters_to_feet,
    feet_per_sec_to_knots,
    knots_to_feet_per_sec,
    meters_per_sec_to_knots,
    knots_to_meters_per_sec,
)
from .fmu_utils import register_fmu3_var, register_fmu3_param

# For 'from aerosim_core import *'
__all__ = [
    "Actor",
    "Rotator",
    "Ellipsoid",
    "Geoid",
    "WorldCoordinate",
    "lla_to_ned",
    "ned_to_lla",
    "lla_to_cartesian",
    "ned_to_cartesian",
    "cartesian_to_lla",
    "cartesian_to_ned",
    "msl_to_hae",
    "hae_to_msl",
    "msl_to_hae_with_offset",
    "hae_to_msl_with_offset",
    "haversine_distance_meters",
    "bearing_deg",
    "deviation_from_course_meters",
    "feet_to_meters",
    "meters_to_feet",
    "feet_per_sec_to_knots",
    "knots_to_feet_per_sec",
    "meters_per_sec_to_knots",
    "knots_to_meters_per_sec",
    "register_fmu3_var",
    "register_fmu3_param",
    "generate_trajectory",
    "generate_trajectory_linear",
    "generate_trajectory_from_adsb_csv",
]
