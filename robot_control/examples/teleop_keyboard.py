import time as time_lib
from typing import Dict
import numpy as np
from gymnasium.spaces import Box
from pynput import keyboard

from robot_control.mujoco_gym_app import MujocoGymAppHighFidelity
from robot_control.utils.target import Target


class MoveTest(MujocoGymAppHighFidelity):
    """
    Keyboard-teleoperated dual UR5 controller with POS + ROT control.
    """

    def __init__(self, robot_config_file=None, scene_file=None):
        super().__init__(
            robot_config_file, scene_file,
            Box(low=-np.inf, high=np.inf),
            Box(low=-np.inf, high=np.inf),
            osc_use_admittance=True,
            render_mode="human"
        )

        # --- INITIAL STATES ---
        self.right_wp = np.array([0.5, 0.45, 0.5])
        self.left_wp  = np.array([-0.3, 0.45, 0.5])
        self.right_rot = np.array([0, -np.pi/2, 0])   # roll pitch yaw
        self.left_rot  = np.array([0, -np.pi/2, 0])

        self.pos_step = 0.015      # movement increment
        self.rot_step = 0.05       # rotation increment (rad)

        self.right_grip = 0
        self.left_grip  = 0


        keyboard.Listener(on_press=self.on_key).start()

    @property
    def default_start_pt(self):
        return None

    def on_key(self, key):
        try:
            k = key.char.lower()

            # ---------------- RIGHT ARM POSITION ----------------
            if k == "w": self.right_wp[2] += self.pos_step
            if k == "s": self.right_wp[2] -= self.pos_step
            if k == "a": self.right_wp[0] += self.pos_step
            if k == "d": self.right_wp[0] -= self.pos_step
            if k == "q": self.right_wp[1] += self.pos_step
            if k == "e": self.right_wp[1] -= self.pos_step

            # ---------------- RIGHT ARM ROTATION ----------------
            if k == "t": self.right_rot[0] += self.rot_step   # roll +
            if k == "g": self.right_rot[0] -= self.rot_step   # roll -
            if k == "f": self.right_rot[1] += self.rot_step   # pitch +
            if k == "h": self.right_rot[1] -= self.rot_step   # pitch -
            if k == "r": self.right_rot[2] += self.rot_step   # yaw +
            if k == "y": self.right_rot[2] -= self.rot_step   # yaw -

            # ---------------- LEFT ARM POSITION ----------------
            if k == "i": self.left_wp[2] += self.pos_step
            if k == "k": self.left_wp[2] -= self.pos_step
            if k == "j": self.left_wp[0] += self.pos_step
            if k == "l": self.left_wp[0] -= self.pos_step
            if k == "u": self.left_wp[1] += self.pos_step
            if k == "o": self.left_wp[1] -= self.pos_step

            # ---------------- LEFT ARM ROTATION ----------------
            if k == "8": self.left_rot[0] += self.rot_step   # roll +
            if k == "5": self.left_rot[0] -= self.rot_step   # roll -
            if k == "7": self.left_rot[1] += self.rot_step   # pitch +
            if k == "9": self.left_rot[1] -= self.rot_step   # pitch -
            if k == "6": self.left_rot[2] += self.rot_step   # yaw +
            if k == "3": self.left_rot[2] -= self.rot_step   # yaw -

            # --------- RIGHT GRIPPER ------------
            if k == "z": self.right_grip = 0  # close
            if k == "x": self.right_grip = -1  # open

            # --------- LEFT GRIPPER -------------
            if k == "m": self.left_grip = 0   # close
            if k == ",": self.left_grip = -1   # open


        except:
            if key == keyboard.Key.esc:
                print("Exiting...")
                exit()

    def run(self):
        targets: Dict[str, Target] = {
            "base": Target(),
            "ur5right": Target(),
            "ur5left": Target(),
        }

        right_grip_index = 7
        left_grip_index  = 14
        
        while True:
            targets["ur5right"].set_xyz(self.right_wp)
            targets["ur5right"].set_abg(self.right_rot)

            targets["ur5left"].set_xyz(self.left_wp)
            targets["ur5left"].set_abg(self.left_rot)

            # Debug:
            # print("CTRL LEN =", len(self.data.ctrl))
            # for i in range(self.model.nu):
            #     print(i, self.model.actuator(i).name, self.model.actuator(i).ctrlrange)  #[0.0] - In Torque mode
            # print("Gripper control range:", self.model.actuator(right_grip_index).ctrlrange)


            ctrl = np.zeros_like(self.data.ctrl)
            ctrlr_output = self.controller.generate(targets)
            for idx, f in zip(*ctrlr_output):
                ctrl[idx] = f

            # --- Apply gripper control ---
            ctrl[right_grip_index] = self.right_grip  # Z = close, X = open
            ctrl[left_grip_index]  = self.left_grip   # M = close, , = open


            self.do_simulation(ctrl, self.frame_skip)
            self.render()


if __name__ == "__main__":
    MoveTest("move_to_point.yaml", "kinect_environment.xml").run()
