"""
    Description: This script provides a easy to use class for Controlling UR5 Robot and some utility functions.
    Feel free to reach out at junar002@umn.edu in case of any queries.

    Author: Pranay Junare
    Organization: University of Minnesota - Twin Cities
    Date: August 2025
"""

import numpy as np
import rtde_control
import rtde_receive
from .gripper import RobotiqGripper
from typing import List
from scipy.spatial.transform import Rotation as R


DEFAULT_LIGHTNING_IP = '192.168.0.101'
DEFAULT_THUNDER_IP = '192.168.0.102'

LIGHTNING_HOME = [-3.0812793413745325, -2.2725616894164027, -1.6927777528762817, -2.3071934185423792, 0.06523201614618301, 1.5599863529205322]
THUNDER_HOME   = [2.992406129837036, -1.0877228540233155, 1.589470688496725, -0.45235593736682134, -0.1500466505633753, -1.6205437819110315] # Equivalent EEF: [0.55, 0.15, 0.25, np.pi/2, np.pi/2, -np.pi]

SPEED = 0.1
ACCELERATION = 0.1
DT = 0.4  # 0.5
LOOKAHEAD_TIME = 0.2
GAIN =100

class UR5RobotController:
    def __init__(self, arm: str, robot_ip: str, need_control: bool = False, need_gripper: bool = False):
        self._ip = robot_ip if (arm in ["thunder", "lightning"]) and (robot_ip is not None) else DEFAULT_LIGHTNING_IP
        self.home = THUNDER_HOME if arm == 'thunder' else LIGHTNING_HOME
        self.gripper = self._init_gripper() if need_gripper else None
        self.receiver = rtde_receive.RTDEReceiveInterface(self._ip)
        self.controller = rtde_control.RTDEControlInterface(self._ip) if need_control else None
        if self.is_alive:
            print(f"[UR5] Connected to {arm} arm at {self._ip}")

    def _init_gripper(self) -> RobotiqGripper:
        gripper = RobotiqGripper()
        gripper.connect(self._ip, 63352)
        gripper.activate()
        gripper.set_enable(True)
        return gripper

    # ----------------------------
    # Robot State
    # ----------------------------
    def get_eff_pose(self) -> List[float]:
        """Get current TCP pose [x,y,z,Rx,Ry,Rz]."""
        return self.receiver.getActualTCPPose()

    def get_joint_angles(self) -> List[float]:
        """Get current joint angles [rad]."""
        return self.receiver.getActualQ()

    def get_tcp_force(self) -> List[float]:
        """Get wrench (forces/torques) at TCP [Fx,Fy,Fz,Tx,Ty,Tz]."""
        return self.receiver.getActualTCPForce()

    def get_current_pose(self, use_euler=False) -> List[float]:
        """
            Get current TCP pose 
            If use_euler is False, returns rotation vectors [x,y,z,Rx,Ry,Rz].
            If use_euler is True, returns euler angles(in radians) instead of rotation vector.
        """
        if use_euler:
            curr_eef_pose = self.receiver.getActualTCPPose()
            xyz = curr_eef_pose[:3]
            rotvec = curr_eef_pose[3:]
            rpy = R.from_rotvec(rotvec).as_euler('xyz', degrees=False)
            return np.concatenate((xyz, rpy))
        return self.receiver.getActualTCPPose()
    
    def get_current_joints(self) -> List[float]:
        """
            Get current joint angles [rad].
            Robot Contrl: here the joints are the 6 joint angles [J1, J2, J3, J4, J5, J6]
        """
        return self.receiver.getActualQ()
    

    # ----------------------------
    # Motion Control
    # ----------------------------
    def moveJ(self, joints: List[float], speed=SPEED, accel=ACCELERATION, async_flag: bool = False):
        """Move in joint space."""
        self.controller.moveJ(joints, speed, accel, async_flag)

    def moveL(self, pose: List[float], speed=SPEED, accel=ACCELERATION, async_flag: bool = False):
        """Move in Cartesian space (linear)."""
        self.controller.moveL(pose, speed, accel, async_flag)

    def servoJ(self, joints: List[float], speed=SPEED, accel=ACCELERATION):
        """Servo motion in joint space (smooth real-time)."""
        self.controller.servoJ(joints, speed, accel, DT, LOOKAHEAD_TIME, GAIN)

    def servoL(self, pose: List[float], speed=SPEED, accel=ACCELERATION):
        """Servo motion in Cartesian space (smooth real-time). Type: non-blocking"""
        self.controller.servoL(pose, speed, accel, DT, LOOKAHEAD_TIME, GAIN)

    def stop(self):
        """Stop robot immediately."""
        self.controller.stopJ(ACCELERATION)

    def freeDrive(self, enable = True):
        """Enable hand-guiding mode."""
        if enable:
            self.controller.freedriveMode()
        else:
            self.controller.endFreedriveMode()
            
    def go_home(self):
        """Move robot to predefined home pose."""
        self.controller.moveJ(self.home, SPEED, ACCELERATION, False)

    def reset(self):
        """Reset robot controller."""
        self.move_to_joints(self.home, SPEED, ACCELERATION)

    def move_to_pose(self, pose: List[float], speed=SPEED, accel=ACCELERATION, use_euler = False):
        """Move robot to a specific pose [x,y,z,Rx,Ry,Rz]."""
        if use_euler:
            xyz = pose[0:3]
            rpy = pose[3:]
            rotvec = R.from_euler('xyz', rpy).as_rotvec()
            pose = np.concatenate((xyz, rotvec))

        self.controller.servoL(pose, speed, accel, DT, LOOKAHEAD_TIME, GAIN)

    def move_to_joints(self, joints: List[float], speed=SPEED, accel=ACCELERATION):
        """Move robot to a specific joint configuration [J1,J2,J3,J4,J5,J6]."""
        self.controller.servoJ(joints, speed, accel, DT, LOOKAHEAD_TIME, GAIN)


    # ----------------------------
    # I/O Functions
    # ----------------------------
    def set_digital_out(self, pin: int, value: bool):
        """Set digital output pin (0-7)."""
        self.controller.setStandardDigitalOut(pin, value)

    # ----------------------------
    # Gripper
    # ----------------------------
    def gripper_close(self, value=255):
        if self.gripper:
            self.gripper.set(int(value))

    def gripper_open(self, value=0):
        if self.gripper:
            self.gripper.set(int(value))
    
    def get_gripper_state(self):
        # BUG: Define properly
        if self.gripper:
            return self.gripper.get_current_position()
        return None
    
    # ----------------------------
    # Robot Status
    # ----------------------------
    @property
    def is_alive(self):
        """Check if robot controller is connected."""
        return self.receiver.isConnected()


if __name__ == "__main__":
    robot = UR5RobotController('thunder', need_control=True, need_gripper=False)
    print("[UR5] Current pose:", robot.get_eff_pose())
    print("[UR5] Current joints:", robot.get_joint_angles())
    robot.go_home()
