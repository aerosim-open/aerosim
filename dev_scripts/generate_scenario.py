from aerosim_scenarios import read_scenario_json
from aerosim_scenarios import ConfigGenerator
import json
import os


# --------------------------------------------
# Write trajectories to json files
def WriteTrajectories(trajectories):
    os.makedirs("trajectories/scenarios_generated/", exist_ok=True)
    for trajectory in trajectories:
        # Convert the array of Point objects to a list of dictionaries
        points_dict = [point.to_dict() for point in trajectory.trajectory]
        with open(
            "trajectories/scenarios_generated/" + trajectory.object_id + ".json", "w"
        ) as json_file:
            json.dump(points_dict, json_file, indent=trajectory.trajectory.__len__())


def WriteConfigFile(json_config_string):
    with open(
        "config/scenarios_generated_sim_config_trajectories.json", "w"
    ) as json_file:
        json_file.write(json_config_string)


# --------------------------------------------
# Create a scenario object
ScenarioParsed = read_scenario_json(
    "../aerosim-scenarios/scenarios/IntrudersInLACatalina.json"
)

WriteTrajectories(ScenarioParsed.trajectories)
spawn_actors = []
WriteConfigFile(ConfigGenerator(ScenarioParsed).generate_json())
