import asyncio
import json
import numpy as np
from typing import Dict
from gymnasium.spaces import Box
import websockets

from robot_control.mujoco_gym_app import MujocoGymAppHighFidelity
from robot_control.utils.target import Target


VR_IP = "100.70.51.33"
VR_PORT = 8765
SCALE_POS   = 0.8 # 0.6 works well
SCALE_ROT   = 2.0
RIGHT_HOME = [0.4, 0.4, 0.4]
LEFT_HOME = [-0.4, 0.4, 0.4]


class MoveVR(MujocoGymAppHighFidelity):

    def __init__(self, robot_config_file=None, scene_file=None):
        super().__init__(
            robot_config_file, scene_file,
            Box(low=-np.inf, high=np.inf),
            Box(low=-np.inf, high=np.inf),
            osc_use_admittance=True,
            render_mode="human"
        )

        self.right_wp  = np.array(RIGHT_HOME)
        self.left_wp   = np.array(LEFT_HOME)
        self.right_rot = np.array([0, -np.pi/2, 0])
        self.left_rot  = np.array([0, -np.pi/2, 0])

        self.right_grip = 0
        self.left_grip  = 0

        self.right_activated = False
        self.left_activated  = False

        self.right_home_activated = False
        self.left_home_activated  = False

        self.curr_right_controller: Dict[str, np.ndarray] = dict()
        self.curr_right_controller["pos"] = np.array([0.20, 0.75, 0.25])
        self.curr_right_controller["rot"] = np.array([0, 0, 0])

        self.curr_right_robot: Dict[str, np.ndarray] = dict()
        self.curr_right_robot["pos"] = np.array(RIGHT_HOME)
        self.curr_right_robot["rot"] = np.array([0, -np.pi/2, 0])
        

        self.curr_left_controller: Dict[str, np.ndarray] = dict()
        self.curr_left_controller["pos"] = np.array([-0.1, 1.0, 0.35])
        self.curr_left_controller["rot"] = np.array([0, 0, 0])

        self.curr_left_robot: Dict[str, np.ndarray] = dict()
        self.curr_left_robot["pos"] = np.array(LEFT_HOME)
        self.curr_left_robot["rot"] = np.array([0, -np.pi/2, 0])

    @property
    def default_start_pt(self): 
        return None


    # ==========================================================
    #  VR LISTENER → server like your working script
    # ==========================================================
    async def vr_listener(self):
        async def handler(websocket):
            print("🟢 VR client connected!")

            try:
                async for message in websocket:
                    print("📥 Data:", message)
                    try:
                        safe_message = (
                                            message.replace("False", "false")
                                                .replace("True", "true")
                                                .replace("None", "null")
                                        )
                                                                
                        self.apply_vr_input(json.loads(safe_message))
                    except Exception as e:
                        print("⚠ Bad JSON:", e)

            except websockets.exceptions.ConnectionClosed:
                print("🔴 VR client disconnected")

        print(f"🟡 VR server waiting at {VR_IP}:{VR_PORT}")
        async with websockets.serve(handler, VR_IP, VR_PORT):
            await asyncio.Future()   # run forever


    def apply_vr_input(self, msg):
        R, L = msg["right"], msg["left"]

        # Activation buttons
        self.right_activated = True if R["push"] > 0.5 else False
        self.left_activated  = True if L["push"] > 0.5 else False

        # Home buttons
        self.right_home_activated = R["button"]
        self.left_home_activated  = L["button"]
        if self.right_home_activated:
            self.right_wp  = np.array(RIGHT_HOME)
            self.right_rot = np.array([0, -np.pi/2, 0])
            print("🏠 Right arm returned to home position.")
        if self.left_home_activated:
            self.left_wp  = np.array(LEFT_HOME)
            self.left_rot = np.array([0, -np.pi/2, 0])
            print("🏠 Left arm returned to home position.")

        # Right arm
        if self.right_activated:        
            # Right position adjustment
            right_pos = (np.array(R["pos"]) - self.curr_right_controller["pos"]) * SCALE_POS 
            temp = right_pos[2]
            right_pos[2] = right_pos[1]
            right_pos[1] = -temp
            right_pos[0] = -right_pos[0]

            # Right rotation adjustment
            right_rot = np.array(R["rot"]) * SCALE_ROT
            right_rot[0] = 0 # roll
            right_rot[1] = 0  # pitch
            right_rot[2] = right_rot[2] # yaw

            self.right_wp = right_pos + self.curr_right_robot["pos"]
            self.right_rot = right_rot + self.curr_right_robot["rot"]
            self.right_grip = -1.0 if R["trigger"] < 0.5 else 0
        else:
            self.curr_right_controller["pos"] = np.array(R["pos"])
            self.curr_right_controller["rot"] = np.array(R["rot"])
            self.curr_right_robot["pos"] = self.right_wp
            self.curr_right_robot["rot"] = self.right_rot

        # Left arm
        if self.left_activated:
            # Left position adjustment
            left_pos = (np.array(L["pos"]) - self.curr_left_controller["pos"]) * SCALE_POS
            temp = left_pos[2]
            left_pos[2] = left_pos[1]
            left_pos[1] = -temp
            left_pos[0] = -left_pos[0]

            # Left rotation adjustment
            left_rot = np.array(L["rot"]) * SCALE_ROT
            left_rot[0] = 0 # roll
            left_rot[1] = 0  # pitch
            left_rot[2] = left_rot[2] # yaw

            self.left_wp  = left_pos + self.curr_left_robot["pos"]
            self.left_rot = left_rot + self.curr_left_robot["rot"]
            self.left_grip  = -1.0 if L["trigger"] < 0.5 else 0
        else:
            self.curr_left_controller["pos"] = np.array(L["pos"])
            self.curr_left_controller["rot"] = np.array(L["rot"])
            self.curr_left_robot["pos"] = self.left_wp
            self.curr_left_robot["rot"] = self.left_rot


        print("✅ VR input applied.",
              f"\nR_pos: {self.right_wp} | R_grip: {self.right_grip} | R_rot: {self.right_rot}"
              f"\nL_pos: {self.left_wp} | L_grip: {self.left_grip} | L_rot: {self.left_rot}"
        )

    async def sim_loop(self):
        targets = {"base": Target(), "ur5right": Target(), "ur5left": Target()}
        right_grip_index = 7
        left_grip_index  = 14
        while True:
            targets["ur5right"].set_xyz(self.right_wp)
            targets["ur5right"].set_abg(self.right_rot)

            targets["ur5left"].set_xyz(self.left_wp)
            targets["ur5left"].set_abg(self.left_rot)

            ctrl = np.zeros_like(self.data.ctrl)
            idx, f = self.controller.generate(targets)
            for i, v in zip(idx, f): ctrl[i] = v
            ctrl[right_grip_index] = self.right_grip  # Z = close, X = open
            ctrl[left_grip_index]  = self.left_grip   # M = close, , = open


            self.do_simulation(ctrl, self.frame_skip)
            self.render()
            await asyncio.sleep(0.01)


    # ==========================================================
    # Both run forever — program never quits
    # ==========================================================
    async def run_async(self):
        await asyncio.gather(self.vr_listener(), self.sim_loop())


if __name__ == "__main__":
    # mujoco = MoveVR("move_to_point.yaml", "kinect_environment.xml")
    # mujoco = MoveVR("move_to_point.yaml", "quad_insert.xml")
    # mujoco = MoveVR("move_to_point.yaml", "scene_google.xml")
    mujoco = MoveVR("move_to_point.yaml", "scene_vr.xml")

    asyncio.run(mujoco.run_async())
