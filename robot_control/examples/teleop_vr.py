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
SCALE_POS   = 1 # 0.6 works well
SCALE_ROT   = 0
GRIP_THRESH = 0.5
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

        self.curr_right_controller = np.array([0.20, 0.75, 0.25])
        
        self.curr_robot_position = np.array(RIGHT_HOME)
        
        self.vr_data_init = None  


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
                    # print("📥 Data:", message)
                    try:
                        self.apply_vr_input(json.loads(message))
                    except Exception as e:
                        print("⚠ Bad JSON:", e)

            except websockets.exceptions.ConnectionClosed:
                print("🔴 VR client disconnected")

        print(f"🟡 VR server waiting at {VR_IP}:{VR_PORT}")
        async with websockets.serve(handler, VR_IP, VR_PORT):
            await asyncio.Future()   # run forever


    def apply_vr_input(self, msg):
        R, L = msg["right"], msg["left"]

        if self.vr_data_init is None:
            self.vr_data_init = msg  # first-time init
            print("🎮 VR data initialized.", self.vr_data_init)
            return

        self.right_activated = True if R["push"] > 0.5 else False
        self.left_activated  = True if L["push"] > 0.5 else False

        if self.right_activated:        
            # right_pos = (np.array(R["pos"]) - np.array([0.20, 0.75, 0.25])) * SCALE_POS 
            right_pos = (np.array(R["pos"]) - self.curr_right_controller) * SCALE_POS 
            temp = right_pos[2]
            right_pos[2] = right_pos[1]
            right_pos[1] = temp
            right_pos[0] = -right_pos[0]

            self.right_wp = right_pos + self.curr_robot_position
            self.right_rot = np.array(R["rot"]) * SCALE_ROT + np.array([0, -np.pi/2, 0])
            self.right_grip = -1.0 if R["trigger"] < 0.5 else 0
        else:
            self.curr_right_controller = np.array(R["pos"])
            self.curr_robot_position = self.right_wp
            print("🟡 Right controller position updated:", self.curr_right_controller)

        if self.left_activated:
            self.left_wp  = np.array(L["pos"]) * SCALE_POS + np.array(LEFT_HOME)
            self.left_rot  = np.array(L["rot"]) * SCALE_ROT + np.array([0, -np.pi/2, 0])
            self.left_grip  = -1.0 if L["trigger"] < 0.5 else 0

        print("✅ VR input applied.",
              f"R_pos: {self.right_wp}, R_rot: {self.right_rot}, R_grip: {self.right_grip} | "
              f"L_pos: {self.left_wp}, L_rot: {self.left_rot}, L_grip: {self.left_grip}"
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
    mujoco = MoveVR("move_to_point.yaml", "kinect_environment.xml")
    asyncio.run(mujoco.run_async())
