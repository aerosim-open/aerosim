"""
Core simulation module for AeroSim.

This module contains the core simulation classes and functions.
"""

from .simulation import AeroSim
from .config import SimConfig

__all__ = ["AeroSim", "SimConfig"]
