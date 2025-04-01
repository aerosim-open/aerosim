cmake_minimum_required(VERSION 3.8)
project(aerosim_data)

find_package(ament_cmake REQUIRED)
find_package(rosidl_default_generators REQUIRED)

rosidl_generate_interfaces(${PROJECT_NAME}
  "idl/pose.msg"
  "idl/camera_info.msg"
  "idl/compressed_image.msg"
  "idl/image.msg"
  "idl/imu.msg"
  "idl/laser_scan.msg"
  "idl/vehicle.msg"
  "idl/actor.msg"
)

ament_package()