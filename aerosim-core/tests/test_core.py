import pytest

from aerosim_core import Vector3, Rotator, Actor, Ellipsoid, Geoid
from aerosim_core import lla_to_ned, ned_to_lla, lla_to_cartesian, ned_to_cartesian, cartesian_to_lla, cartesian_to_ned

def test_Vector3Creation():
    v = Vector3(x=1.0, y=2.0, z=3.0)
    assert v.x == 1
    assert v.y == 2
    assert v.z == 3

def test_RotatorCreation():
    r = Rotator(yaw=4.0, pitch=5.0, roll=6.0)
    assert r.yaw == 4.0
    assert r.pitch == 5.0
    assert r.roll == 6.0

def test_ActorCreation():
    a = Actor(actor_name = "TestActor", actor_type = 0,semantics="EmptySemantics", position=Vector3(x=1.0, y=2.0, z=3.0), rotation=Rotator(yaw=4.0, pitch=5.0, roll=6.0))
    assert a.actor_name == "TestActor"
    assert a.position.x == 1
    assert a.position.y == 2
    assert a.position.z == 3
    assert a.rotation.yaw == 4
    assert a.rotation.pitch == 5
    assert a.rotation.roll == 6
    # Assert that the default values are set
    assert a.velocity_linear.x == 0
    assert a.velocity_linear.y == 0
    assert a.velocity_linear.z == 0

    assert a.velocity_angular.x == 0
    assert a.velocity_angular.y == 0
    assert a.velocity_angular.z == 0

def test_wgs84_ellipsoid_creation():
    e = Ellipsoid.wgs84();

    assert e.equatorial_radius == 6378137.0
    assert e.flattening_factor == 1.0 / 298.257223563
    assert e.polar_radius == e.equatorial_radius * (1.0 - e.flattening_factor)

def test_custom_ellipsoid_creation():
    e = Ellipsoid.custom(1234532.3, 1.0 / 231.5826273);

    assert e.equatorial_radius == 1234532.3
    assert e.flattening_factor == 1.0 / 231.5826273
    assert e.polar_radius == e.equatorial_radius * (1.0 - e.flattening_factor)

def test_egm08_geoid_creation():
    g = Geoid.egm08();
    height = g.get_geoid_height(-37.813628, 144.963058)

    assert height == 4.63

if __name__ == "__main__":
    pytest.main()
