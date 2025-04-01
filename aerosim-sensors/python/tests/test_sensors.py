import pytest

from aerosim_data import types
from aerosim_sensors import Sensor
from aerosim_sensors import SensorManager
from aerosim_sensors import adsb_functions


def test_adsb_identification():
    hex_string = "8D4840D6202CC371C32CE0576098"
    result = adsb_functions.parse_message(hex_string)
    output = result.to_dict()
    assert output["message"]["icao"] == "4840D6"
    assert output["message"]["message_extended_quitter"]["tc"] == 4
    assert output["message"]["message_extended_quitter"]["ca"] == 0
    assert output["message"]["message_extended_quitter"]["cn"] == "KLM1023"
    assert output["message"]["parity"] == "815D82"

def test_adsb_airborne_position():
    hex_string = "8D40621D58C382D690C8AC2863A7"
    message = adsb_functions.parse_message(hex_string)
    output = message.to_dict()
    assert output["message"]["icao"] == "40621D"
    assert output["message"]["message_extended_quitter"]["tc"] == 11
    assert output["message"]["message_extended_quitter"]["ss"] == 0
    assert output["message"]["message_extended_quitter"]["saf"] == 0
    assert output["message"]["message_extended_quitter"]["alt"] == 38000
    assert not output["message"]["message_extended_quitter"]["t"]
    assert output["message"]["message_extended_quitter"]["f"] == 0
    assert output["message"]["message_extended_quitter"]["alt_source"] == "Barometric"
    assert output["message"]["message_extended_quitter"]["lat_cpr"] == 93000
    assert output["message"]["message_extended_quitter"]["lon_cpr"] == 51372
    assert output["message"]["parity"] == "2863A7"

def test_adsb_surface_position():
    hex_string = "8C4841753A9A153237AEF0F275BE"
    message = adsb_functions.parse_message(hex_string)
    output = message.to_dict()
    assert output["message"]["icao"] == "484175"
    assert output["message"]["message_extended_quitter"]["mov"] == 29
    assert not output["message"]["message_extended_quitter"]["s"]
    assert output["message"]["message_extended_quitter"]["trk"] == 77
    assert not output["message"]["message_extended_quitter"]["t"]
    assert output["message"]["message_extended_quitter"]["f"] == 0
    assert output["message"]["message_extended_quitter"]["lat_cpr"] == 21704
    assert output["message"]["message_extended_quitter"]["lon_cpr"] == 114039
    assert output["message"]["parity"] == "8793AD"

def test_adsb_airborne_velocity_ground():
    hex_string = "8D485020994409940838175B284F"
    message = adsb_functions.parse_message(hex_string)
    output = message.to_dict()
    assert output["message"]["icao"] == "485020"
    assert output["message"]["message_extended_quitter"]["st"] == 1
    assert output["message"]["message_extended_quitter"]["nac_v"] == 8
    assert output["message"]["message_extended_quitter"]["vr_src"] == "Barometric"
    assert output["message"]["message_extended_quitter"]["s_vr"] == 1
    assert output["message"]["message_extended_quitter"]["vr"] == 14
    assert output["message"]["message_extended_quitter"]["reserved"] == 0
    assert output["message"]["message_extended_quitter"]["s_dif"] == 0
    assert output["message"]["message_extended_quitter"]["d_alt"] == 550
    assert output["message"]["message_extended_quitter"]["heading"] == 182.88037109375
    assert output["message"]["message_extended_quitter"]["ground_speed"] == 159.20113064925135
    assert output["message"]["message_extended_quitter"]["vertical_rate"] == -832
    assert output["message"]["parity"] == "5B284F"

def test_adsb_airborne_velocity_air():
    hex_string = "8DA05F219B06B6AF189400CBC33F"
    message = adsb_functions.parse_message(hex_string)
    output = message.to_dict()
    assert output["message"]["icao"] == "A05F21"
    assert output["message"]["message_extended_quitter"]["st"] == 3
    assert output["message"]["message_extended_quitter"]["nac_v"] == 0
    assert output["message"]["message_extended_quitter"]["vr_src"] == "Geometric"
    assert output["message"]["message_extended_quitter"]["s_vr"] == 1
    assert output["message"]["message_extended_quitter"]["vr"] == 37
    assert output["message"]["message_extended_quitter"]["reserved"] == 0
    assert output["message"]["message_extended_quitter"]["s_dif"] == 0
    assert output["message"]["message_extended_quitter"]["d_alt"] == 0
    assert not output["message"]["message_extended_quitter"]["heading"]
    assert not output["message"]["message_extended_quitter"]["ground_speed"]
    assert not output["message"]["message_extended_quitter"]["vertical_rate"]
    assert output["message"]["parity"] == "CBC33F"

if __name__ == "__main__":
    pytest.main()
