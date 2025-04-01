import pytest

from aerosim_data import types as aerosim_types
from types import SimpleNamespace

def test_json():
    data = {
        "frame_id": "frame1",
        "position": {
            "posx": 10, "posy": 20, "posz": 30
        }
    }
    json_data = aerosim_types.JsonData(data)
    assert json_data is not None
    assert json_data.get_data() == data

def test_json_dict():
    data = {
        "frame_id": "frame1",
        "position": {
            "posx": 10, "posy": 20, "posz": 30
        }
    }
    json_data = aerosim_types.JsonData(data)
    json_dict = json_data.to_dict()
    assert json_dict["frame_id"] == "frame1"
    assert json_dict["position"]["posx"] == 10
    assert json_dict["position"]["posy"] == 20
    assert json_dict["position"]["posz"] == 30

def test_timestamp():
    timestamp = aerosim_types.TimeStamp.now()
    assert timestamp is not None

def test_timestamp_to_dict():
    timestamp = aerosim_types.TimeStamp.now()
    timestamp_dict = timestamp.to_dict()
    assert timestamp_dict["sec"] == timestamp.sec
    assert timestamp_dict["nanosec"] == timestamp.nanosec

def test_header():
    timestamp_sim = aerosim_types.TimeStamp(0, 0)
    timestamp_platform = aerosim_types.TimeStamp.now()
    frame_id = "frame_id"
    header = aerosim_types.Header(timestamp_sim, timestamp_platform, frame_id)
    assert header is not None

def test_header_to_dict():
    timestamp_sim = aerosim_types.TimeStamp(0, 0)
    timestamp_platform = aerosim_types.TimeStamp.now()
    frame_id = "frame_id"
    header = aerosim_types.Header(timestamp_sim, timestamp_platform, frame_id)
    header_dict = header.to_dict()
    assert header_dict["timestamp_sim"] == timestamp_sim.to_dict()
    assert header_dict["timestamp_platform"] == timestamp_platform.to_dict()
    assert header_dict["frame_id"] == frame_id

def dict_to_namespace(d):
    """Convert a dictionary to a SimpleNamespace, handling nested dictionaries."""
    for key, value in d.items():
        if isinstance(value, dict):
            d[key] = dict_to_namespace(value)
    return SimpleNamespace(**d)

def test_header_attribute_access():
    timestamp_sim = aerosim_types.TimeStamp(0, 0)
    timestamp_platform = aerosim_types.TimeStamp.now()
    frame_id = "frame_id"
    header = aerosim_types.Header(timestamp_sim, timestamp_platform, frame_id)
    header_dict = header.to_dict()
    header_ns = dict_to_namespace(header_dict)
    assert header_ns.timestamp_sim.sec == timestamp_sim.sec
    assert header_ns.timestamp_sim.nanosec == timestamp_sim.nanosec
    assert header_ns.timestamp_platform.sec == timestamp_platform.sec
    assert header_ns.timestamp_platform.nanosec == timestamp_platform.nanosec
    assert header_ns.frame_id == frame_id


def test_vector3():
    vector = aerosim_types.Vector3(1.0, 2.0, 3.0)
    assert vector.x == 1.0
    assert vector.y == 2.0
    assert vector.z == 3.0

def test_vector3_to_dict():
    vector = aerosim_types.Vector3(1.0, 2.0, 3.0)
    vector_dict = vector.to_dict()
    assert vector_dict["x"] == 1.0
    assert vector_dict["y"] == 2.0
    assert vector_dict["z"] == 3.0

def test_quaternion():
    quaternion = aerosim_types.Quaternion(1.0, 0.0, 0.0, 0.0)
    assert quaternion.w == 1.0
    assert quaternion.x == 0.0
    assert quaternion.y == 0.0
    assert quaternion.z == 0.0

def test_quaternion_to_dict():
    quaternion = aerosim_types.Quaternion(1.0, 0.0, 0.0, 0.0)
    quaternion_dict = quaternion.to_dict()
    assert quaternion_dict["w"] == 1.0
    assert quaternion_dict["x"] == 0.0
    assert quaternion_dict["y"] == 0.0
    assert quaternion_dict["z"] == 0.0

def test_pose():
    position = aerosim_types.Vector3(1.0, 2.0, 3.0)
    orientation = aerosim_types.Quaternion(1.0, 0.0, 0.0, 0.0)
    pose = aerosim_types.Pose(position, orientation)
    assert pose is not None

def test_pose_to_dict():
    position = aerosim_types.Vector3(1.0, 2.0, 3.0)
    orientation = aerosim_types.Quaternion(1.0, 0.0, 0.0, 0.0)
    pose = aerosim_types.Pose(position, orientation)
    pose_dict = pose.to_dict()
    assert pose_dict["position"] == position.to_dict()
    assert pose_dict["orientation"] == orientation.to_dict()

def test_camera_info():
    width = 640
    height = 480
    distortion_model = "distortion_model"
    D = [1.0, 2.0, 3.0]
    K = [1.0, 0.0, 0.0, 0.0, 1.0, 0.0, 0.0, 0.0, 1.0]
    R = [1.0, 0.0, 0.0, 0.0, 1.0, 0.0, 0.0, 0.0, 1.0]
    P = [1.0, 0.0, 0.0, 0.0, 0.0, 1.0, 0.0, 0.0, 0.0, 0.0, 1.0, 0.0]
    camera_info = aerosim_types.CameraInfo(width, height, distortion_model, D, K, R, P)
    assert camera_info is not None

def test_camera_info_to_dict():
    width = 640
    height = 480
    distortion_model = "distortion_model"
    D = [1.0, 2.0, 3.0]
    K = [1.0, 0.0, 0.0, 0.0, 1.0, 0.0, 0.0, 0.0, 1.0]
    R = [1.0, 0.0, 0.0, 0.0, 1.0, 0.0, 0.0, 0.0, 1.0]
    P = [1.0, 0.0, 0.0, 0.0, 0.0, 1.0, 0.0, 0.0, 0.0, 0.0, 1.0, 0.0]
    camera_info = aerosim_types.CameraInfo(width, height, distortion_model, D, K, R, P)
    camera_info_dict = camera_info.to_dict()
    assert camera_info_dict["width"] == width
    assert camera_info_dict["height"] == height
    assert camera_info_dict["distortion_model"] == distortion_model
    assert camera_info_dict["d"] == D
    assert camera_info_dict["k"] == K
    assert camera_info_dict["r"] == R
    assert camera_info_dict["p"] == P

def test_image_encoding():
    encoding = aerosim_types.ImageEncoding.RGB8
    assert encoding is not None
    assert isinstance(encoding, aerosim_types.ImageEncoding)

def test_image():
    width = 640
    height = 480
    distortion_model = "distortion_model"
    D = [1.0, 2.0, 3.0]
    K = [1.0, 0.0, 0.0, 0.0, 1.0, 0.0, 0.0, 0.0, 1.0]
    R = [1.0, 0.0, 0.0, 0.0, 1.0, 0.0, 0.0, 0.0, 1.0]
    P = [1.0, 0.0, 0.0, 0.0, 0.0, 1.0, 0.0, 0.0, 0.0, 0.0, 1.0, 0.0]
    camera_info = aerosim_types.CameraInfo(width, height, distortion_model, D, K, R, P)
    encoding = aerosim_types.ImageEncoding.RGB8
    is_bigendian = 0
    step = 640 * 3
    data = [0] * (640 * 480 * 3)
    image = aerosim_types.Image(camera_info, height, width, encoding, is_bigendian, step, data)
    assert image is not None

def test_image_to_dict():
    width = 640
    height = 480
    distortion_model = "distortion_model"
    D = [1.0, 2.0, 3.0]
    K = [1.0, 0.0, 0.0, 0.0, 1.0, 0.0, 0.0, 0.0, 1.0]
    R = [1.0, 0.0, 0.0, 0.0, 1.0, 0.0, 0.0, 0.0, 1.0]
    P = [1.0, 0.0, 0.0, 0.0, 0.0, 1.0, 0.0, 0.0, 0.0, 0.0, 1.0, 0.0]
    camera_info = aerosim_types.CameraInfo(width, height, distortion_model, D, K, R, P)
    encoding = aerosim_types.ImageEncoding.RGB8
    is_bigendian = 0
    step = 640 * 3
    data = [0] * (640 * 480 * 3)
    image = aerosim_types.Image(camera_info, height, width, encoding, is_bigendian, step, data)
    image_dict = image.to_dict()
    assert image_dict["camera_info"] == camera_info.to_dict()
    assert image_dict["height"] == height
    assert image_dict["width"] == width
    assert image_dict["encoding"] == str(encoding)
    assert image_dict["is_bigendian"] == is_bigendian
    assert image_dict["step"] == step
    assert image_dict["data"] == bytes(data)

def test_actor_state():
    position = aerosim_types.Vector3(1.0, 2.0, 3.0)
    orientation = aerosim_types.Quaternion(1.0, 0.0, 0.0, 0.0)
    pose = aerosim_types.Pose(position, orientation)
    actor_state = aerosim_types.ActorState(pose)
    assert actor_state is not None

def test_actor_state_to_dict():
    position = aerosim_types.Vector3(1.0, 2.0, 3.0)
    orientation = aerosim_types.Quaternion(1.0, 0.0, 0.0, 0.0)
    pose = aerosim_types.Pose(position, orientation)
    actor_state = aerosim_types.ActorState(pose)
    actor_state_dict = actor_state.to_dict()
    assert actor_state_dict["pose"] == pose.to_dict()

def test_physical_properties():
    mass = 1.0
    inertia = aerosim_types.Vector3(1.0, 1.0, 1.0)
    moment_of_inertia = aerosim_types.Vector3(1.0, 1.0, 1.0)
    physical_properties = aerosim_types.PhysicalProperties(mass, inertia, moment_of_inertia)
    assert physical_properties is not None

def test_physical_properties_to_dict():
    mass = 1.0
    inertia = aerosim_types.Vector3(1.0, 1.0, 1.0)
    moment_of_inertia = aerosim_types.Vector3(1.0, 1.0, 1.0)
    physical_properties = aerosim_types.PhysicalProperties(mass, inertia, moment_of_inertia)
    physical_properties_dict = physical_properties.to_dict()
    assert physical_properties_dict["mass"] == mass
    assert physical_properties_dict["inertia_tensor"] == inertia.to_dict()
    assert physical_properties_dict["moment_of_inertia"] == moment_of_inertia.to_dict()

def test_actor_model():
    mass = 1.0
    inertia = aerosim_types.Vector3(1.0, 1.0, 1.0)
    moment_of_inertia = aerosim_types.Vector3(1.0, 1.0, 1.0)
    physical_props = aerosim_types.PhysicalProperties(mass, inertia, moment_of_inertia)
    asset_link = "asset_link"
    actor_model = aerosim_types.ActorModel(physical_props, asset_link)
    assert actor_model is not None

def test_actor_model_to_dict():
    mass = 1.0
    inertia = aerosim_types.Vector3(1.0, 1.0, 1.0)
    moment_of_inertia = aerosim_types.Vector3(1.0, 1.0, 1.0)
    physical_props = aerosim_types.PhysicalProperties(mass, inertia, moment_of_inertia)
    asset_link = "asset_link"
    actor_model = aerosim_types.ActorModel(physical_props, asset_link)
    actor_model_dict = actor_model.to_dict()
    assert actor_model_dict["physical_properties"] == physical_props.to_dict()
    assert actor_model_dict["asset_link"] == asset_link

def test_sensor_type():
    sensor_type = aerosim_types.SensorType.Camera
    assert sensor_type is not None
    assert isinstance(sensor_type, aerosim_types.SensorType)

def test_sensor_type_to_string():
    sensor_type = aerosim_types.SensorType.Camera
    assert str(sensor_type) == "Camera"

def test_vehicle_type():
    vehicle_type = aerosim_types.VehicleType.Ground
    assert vehicle_type is not None
    assert isinstance(vehicle_type, aerosim_types.VehicleType)

def test_vehicle_type_to_string():
    vehicle_type = aerosim_types.VehicleType.Aerial
    assert str(vehicle_type) == "Aerial"

def test_vehicle_state():
    position = aerosim_types.Vector3(1.0, 2.0, 3.0)
    orientation = aerosim_types.Quaternion(1.0, 0.0, 0.0, 0.0)
    pose = aerosim_types.Pose(position, orientation)
    state = aerosim_types.ActorState(pose)
    velocity = aerosim_types.Vector3(1.0, 2.0, 3.0)
    angular_velocity = aerosim_types.Vector3(1.0, 2.0, 3.0)
    acceleration = aerosim_types.Vector3(1.0, 2.0, 3.0)
    angualar_acceleration = aerosim_types.Vector3(1.0, 2.0, 3.0)
    vehicle_state = aerosim_types.VehicleState(state, velocity, angular_velocity, acceleration, angualar_acceleration)
    assert vehicle_state is not None

def test_vehicle_state_to_dict():
    position = aerosim_types.Vector3(1.0, 2.0, 3.0)
    orientation = aerosim_types.Quaternion(1.0, 0.0, 0.0, 0.0)
    pose = aerosim_types.Pose(position, orientation)
    state = aerosim_types.ActorState(pose)
    velocity = aerosim_types.Vector3(1.0, 2.0, 3.0)
    acceleration = aerosim_types.Vector3(1.0, 2.0, 3.0)
    angular_velocity = aerosim_types.Vector3(1.0, 2.0, 3.0)
    angular_acceleration = aerosim_types.Vector3(1.0, 2.0, 3.0)
    vehicle_state = aerosim_types.VehicleState(state, velocity, angular_velocity, acceleration, angular_acceleration)
    vehicle_state_dict = vehicle_state.to_dict()
    assert vehicle_state_dict["state"] == state.to_dict()
    assert vehicle_state_dict["velocity"] == velocity.to_dict()
    assert vehicle_state_dict["acceleration"] == acceleration.to_dict()
    assert vehicle_state_dict["angular_velocity"] == angular_velocity.to_dict()
    assert vehicle_state_dict["angular_acceleration"] == angular_acceleration.to_dict()

if __name__ == "__main__":
    pytest.main()