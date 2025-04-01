from typing import Tuple
import numpy as np
from scipy.spatial.transform import Rotation as R

def rotation_difference(euler1: Tuple[float, float, float],
                        euler2: Tuple[float, float, float],
                        convention: str = 'zyx',
                        degrees: bool = True) -> float:
    r1 = R.from_euler(convention, euler1, degrees=degrees)
    r2 = R.from_euler(convention, euler2, degrees=degrees)
    r_rel = r1.inv() * r2
    rotvec = r_rel.as_rotvec()
    angle_diff_rad = np.linalg.norm(rotvec)
    return np.degrees(angle_diff_rad) if degrees else angle_diff_rad

def scipy_quat_to_euler(quaternion: np.ndarray) -> Tuple[float, float, float]:
    rotation = R.from_quat(quaternion, scalar_first=True)
    euler_angles = rotation.as_euler('zyx', degrees=True)
    roll, pitch, yaw = euler_angles
    return roll, pitch, yaw

def main():
    tolerance = 0.2 # in degrees
    quat = [0.139, 0.846, -0.289, -0.424] # w x y z
    rust_euler = [38.290534674450114, -52.91577716187425, -179.05906459363663] # from quaternion.rs (Extrensic rotation)
    rpy = scipy_quat_to_euler(quat)
    diff = rotation_difference(rpy, rust_euler)
    assert diff < tolerance
    print("Test passed!")

if __name__ == "__main__":
    main()
