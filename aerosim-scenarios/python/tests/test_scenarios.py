import pytest
from pathlib import Path
from aerosim_scenarios import Scenario
from aerosim_scenarios import read_scenario_json
from aerosim_scenarios import write_scenario_json

@pytest.fixture
def json_file_path():
    return str(Path(__file__).parent / "test_scenario.json")

@pytest.fixture
def updated_json_file_path():
    return str(Path(__file__).parent / "test_updated_scenario.json")

def test_read_json(json_file_path, updated_json_file_path):
    # Read JSON
    readscenario = read_scenario_json(json_file_path)
    readscenario.description = "Updated description"

    assert readscenario.scenario_id is not None
    assert readscenario.description == "Updated description"
    assert readscenario.time_of_day is not None
    assert len(readscenario.weather) > 0
    assert readscenario.cesium_height_offset_map is not None
    assert len(readscenario.actors) > 0
    assert len(readscenario.trajectories) > 0
    assert len(readscenario.sensor_setup) > 0

    # Write updated JSON
    write_scenario_json(updated_json_file_path, readscenario)

def test_write_json(json_file_path, updated_json_file_path):
    # Read JSON
    readscenario = read_scenario_json(json_file_path)
    readscenario.description = "Updated description"

    # Write updated JSON
    write_scenario_json(updated_json_file_path, readscenario)

    # Read updated JSON
    updated_scenario = read_scenario_json(updated_json_file_path)

    assert updated_scenario.description == "Updated description"

if __name__ == "__main__":
    pytest.main()
    print(readscenario.description)
    print(readscenario.time_of_day)
    for weather in readscenario.weather:
        print(weather.weather_id)
        print(weather.config_file)
    print(readscenario.cesium_height_offset_map)
    for actor in readscenario.actors:
        print(actor.actor_id)
        print(actor.config_file)
        print(actor.id)
        print(actor.usd)
        print(actor.transform)
        print(actor.state)
    for trajectories in readscenario.trajectories:
        print(trajectories.trajectory_id)
        print(trajectories.object_id)
        print(trajectories.config_file)
        print(trajectories.trajectory)
    for sensor in readscenario.sensor_setup:
        print(sensor.id)
        print(sensor.sensor_type)
        print(sensor.relative_transform)

    # Define the path to the updated JSON file
    updated_json_file_path = Path(__file__).parent / "test_updated_scenario.json"
    write_scenario_json(updated_json_file_path, readscenario)

if __name__ == "__main__":
    pytest.main()
