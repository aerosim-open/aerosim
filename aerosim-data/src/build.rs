use std::process::Command;

fn main() {
    // Generate Rust bindings from ROS2 IDL
    Command::new("ros2").args(&["run", "rosidl_generator_rs", "generate_rust", "idl/"]).status().unwrap();

    // Generate C++ bindings from ROS2 IDL
    Command::new("ros2").args(&["run", "rosidl_generator_cpp", "generate_cpp", "idl/"]).status().unwrap();

    // Generate Python bindings from ROS2 IDL
    Command::new("ros2").args(&["run", "rosidl_generator_py", "generate_py", "idl/"]).status().unwrap();
}