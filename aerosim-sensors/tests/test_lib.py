import pytest
from aerosim_sensors import Sensor, SensorManager, GNSS


def test_sensor_creation():
    sensor = Sensor("Altitude", 25.0)
    assert sensor.name == "Altitude"
    assert sensor.get_value() == 25.0


def test_sensor_set_value():
    sensor = Sensor("Altitude", 25.0)
    sensor.set_value(30.0)
    assert sensor.get_value() == 30.0


def test_sensor_manager_creation():
    manager = SensorManager()
    assert len(manager.get_all_sensors()) == 0


def test_sensor_manager_add_sensor():
    manager = SensorManager()
    sensor = Sensor("Altitude", 25.0)
    manager.add_sensor(sensor)
    assert len(manager.get_all_sensors()) == 1
    assert manager.get_all_sensors()[0].name == "Altitude"


def test_sensor_manager_get_sensor():
    manager = SensorManager()
    sensor = Sensor("Altitude", 25.0)
    manager.add_sensor(sensor)
    retrieved_sensor = manager.get_sensor(0)
    assert retrieved_sensor is not None
    assert retrieved_sensor.name == "Altitude"
    assert retrieved_sensor.get_value() == 25.0


def test_sensor_manager_get_sensor_out_of_bounds():
    manager = SensorManager()
    assert manager.get_sensor(0) is None


def test_sensor_manager_get_all_sensors():
    manager = SensorManager()
    sensor1 = Sensor("Altitude", 25.0)
    sensor2 = Sensor("Pressure", 1.0)
    manager.add_sensor(sensor1)
    manager.add_sensor(sensor2)
    sensors = manager.get_all_sensors()
    assert len(sensors) == 2
    assert sensors[0].name == "Altitude"
    assert sensors[1].name == "Pressure"

def test_gnss_velocity():
    gnss = GNSS(latitude=0.0, longitude=0.0, altitude=0.0)
    (n, e, d) = gnss.velocity
    assert(n == 0.0)
    assert(e == 0.0)
    assert(d == 0.0)

    gnss.velocity = (1.0, 1.0, 1.0)
    (n, e, d) = gnss.velocity
    assert(n == 1.0)
    assert(e == 1.0)
    assert(d == 1.0)


def test_gnss_to_mercator():
    ny_longitude = -73.935242
    ny_latitude = 40.730610
    gnss = GNSS(latitude=ny_latitude, longitude=ny_longitude, altitude=0.0)

    expected_x = -8230433.491117454
    expected_y = 4972687.535733602
    mercator = gnss.to_mercator()

    delta_error = 1e-9
    assert(abs(mercator[0] - expected_x) < delta_error)
    assert(abs(mercator[1] - expected_y) < delta_error)


def test_mercator_to_gnss():
    expected_longitude = -73.935242
    expected_latitude = 40.730610
    gnss = GNSS(latitude=expected_latitude, longitude=expected_longitude, altitude=0.0)
    x, y = gnss.to_mercator()
    gnss.from_mercator(x, y, 0.0)

    delta_error = 1e-9
    assert(abs(gnss.longitude - expected_longitude) < delta_error)
    assert(abs(gnss.latitude - expected_latitude) < delta_error)


def test_calculate_distance():
    la_longitude = -118.243683
    la_latitude = 34.052235
    la = GNSS(latitude=la_latitude, longitude=la_longitude, altitude=0.0)

    ny_longitude = -73.935242
    ny_latitude = 40.730610
    ny = GNSS(latitude=ny_latitude, longitude=ny_longitude, altitude=0.0)

    expected_distance = 3950255.6541545927
    distance = la.calculate_distance(ny)

    delta_error = 1e-3
    assert(abs(distance - expected_distance) < delta_error)


def test_gnss_ned_1():
    reference = GNSS(latitude=37.6194495, longitude=-122.3767776, altitude=0.0)
    target = GNSS(latitude=37.6194495, longitude=-122.3767776, altitude=0.0)

    n, e, d = reference.to_ned(target)
    expected_n = 0.0
    expected_e = 0.0
    expected_d = 0.0

    delta_error = 1e-3
    assert(abs(n - expected_n) < delta_error)
    assert(abs(e - expected_e) < delta_error)
    assert(abs(d - expected_d) < delta_error)


def test_gnss_ned_2():
    reference = GNSS(latitude=37.6194495, longitude=-122.3767776, altitude=0.0)
    target = GNSS(latitude=37.6420439, longitude=-122.4094735, altitude=304.8)

    n, e, d = reference.to_ned(target)
    expected_n = 2_508.363_922_893_28
    expected_e = -2_885.801_523_071_885_6
    expected_d = -303.653_321_176_709_3

    delta_error = 1e-3
    assert(abs(n - expected_n) < delta_error)
    assert(abs(e - expected_e) < delta_error)
    assert(abs(d - expected_d) < delta_error)


def test_gnss_ned_3():
    reference = GNSS(latitude=37.6194495, longitude=-122.3767776, altitude=0.0)
    target = GNSS(latitude=37.6481151, longitude=-122.4247364, altitude=0.0)

    n, e, d = reference.to_ned(target)
    expected_n = 3_182.663_395_732_058
    expected_e = -4_232.386_955_261_773
    expected_d = 2.198_932_524_063_9

    delta_error = 1e-3
    assert(abs(n - expected_n) < delta_error)
    assert(abs(e - expected_e) < delta_error)
    assert(abs(d - expected_d) < delta_error)

def test_translate():
    sensor = GNSS(latitude=0.0, longitude=0.0, altitude=0.0)
    sensor.translate(1000.0, 500.0, 0.0)

    expected_latitude = 0.004491576415997162
    expected_longitude = 0.008983152841195215

    delta_error = 1e-6
    assert(abs(sensor.latitude - expected_latitude) < delta_error)
    assert(abs(sensor.longitude - expected_longitude) < delta_error)


if __name__ == "__main__":
    pytest.main()
