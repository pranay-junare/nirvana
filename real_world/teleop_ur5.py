###############################################################
#     REAL UR5 TELEOP — STRUCTURE 1:1 SAME AS SIMULATION      #
###############################################################
import asyncio
import json
import numpy as np
import websockets
from typing import Dict

from ur5_robot.ur5 import UR5RobotController  # <-- your existing driver


# ======================== CONFIG ============================
VR_IP       = "10.131.249.198"
VR_PORT     = 8765

SCALE_POS   = 0.8
SCALE_ROT   = 0.7

RIGHT_HOME  = [-0.40, 0.40, 0.40]
LEFT_HOME   = [ 0.40, 0.40, 0.40]

ROBOT_IP    = "10.33.55.90"
ARM = "lightning"
USE_GRIPPER = True
# =============================================================



class MoveVR_UR5:

    def __init__(self):
        print("🔵 Connecting to UR5...")

        self.right_activated = False
        self.left_activated  = False

        self.right_home_activated = False
        self.left_home_activated  = False

        # Keep exact same naming + structure
        self.curr_right_controller = {"pos": np.array([0.20, 0.75, 0.25]),
                                      "rot": np.array([0,0,0])}
        self.curr_left_controller  = {"pos": np.array([-0.1,1.0,0.35]),
                                      "rot": np.array([0,0,0])}

        # ==== Real Robot Connection ====
        self.robot = UR5RobotController(
            ARM, robot_ip=ROBOT_IP,
            need_control=True, need_gripper=USE_GRIPPER
        )

        if not self.robot.is_alive:
            raise RuntimeError("❌ UR5 connection failed.")

        print("🟢 UR5 Connected — Going Home")
        self.robot.go_home()

        # Track real robot reference same as sim
        lightning_pose = np.array(self.robot.get_current_pose(use_euler=True))
        self.curr_right_robot = {"pos": lightning_pose[:3], "rot": lightning_pose[3:]}
        self.curr_left_robot  = {"pos": lightning_pose[:3], "rot": lightning_pose[3:]}

        # Initial Target points 
        self.right_wp  = self.curr_right_robot["pos"]
        self.left_wp   = self.curr_left_robot["pos"]

        self.right_rot = self.curr_right_robot["rot"]
        self.left_rot  = self.curr_left_robot["rot"]

        self.right_grip = 0
        self.left_grip  = 0

        RIGHT_HOME = self.curr_right_robot["pos"]
        LEFT_HOME  = self.curr_left_robot["pos"]



    # ================================================================
    # VR Input (same structure as simulation apply_vr_input)
    # ================================================================
    def apply_vr_input_real(self, msg):

        R, L = msg["right"], msg["left"]

        self.right_activated = True if R["push"]>0.5 else False
        self.left_activated  = True if L["push"]>0.5 else False

        self.right_home_activated = R["button"]
        self.left_home_activated  = L["button"]

        # ================= HOME RETURN =================
        if self.right_home_activated:
            print("🏠 Right Arm → HOME")
            self.right_wp = np.array(RIGHT_HOME)
            # self.right_rot = np.array([0,-np.pi/2,0])
            # self.robot.go_home()

        if self.left_home_activated:
            print("🏠 Left Arm → HOME")
            self.left_wp = np.array(LEFT_HOME)
            # self.left_rot = np.array([0,-np.pi/2,0])
            # self.robot.go_home()


        # ================= RIGHT ARM =================
        if self.right_activated:
            delta = (np.array(R["pos"]) - self.curr_right_controller["pos"]) * SCALE_POS
            temp = delta[2]
            delta[2] = -delta[0]
            delta[0] = temp
            delta[1] = -delta[1]

            delta_rot = (np.array(R["rot"]) - self.curr_right_controller["rot"]) * SCALE_ROT
            delta_rot[0] = 0
            delta_rot[2] = 0

            self.right_wp  = self.curr_right_robot["pos"] + delta
            self.right_rot = self.curr_right_robot["rot"] + delta_rot
            self.right_grip = -1.0 if R["trigger"]<0.5 else 0

        else:
            self.curr_right_controller["pos"] = np.array(R["pos"])
            self.curr_right_controller["rot"] = np.array(R["rot"])
            self.curr_right_robot["pos"] = self.right_wp
            self.curr_right_robot["rot"] = self.right_rot


        # ================= LEFT ARM =================
        if self.left_activated:
            delta = (np.array(L["pos"]) - self.curr_left_controller["pos"]) * SCALE_POS

            delta[0] = -delta[0]
            temp = delta[2]
            delta[2] = delta[1]
            delta[1] = -temp

            left_rot = np.array(L["rot"]) * SCALE_ROT
            left_rot[0] = 0
            left_rot[1] = 0

            self.left_wp  = self.curr_left_robot["pos"] + delta
            self.left_rot = self.curr_left_robot["rot"] + left_rot
            self.left_grip = -1.0 if L["trigger"]<0.5 else 0

        else:
            self.curr_left_controller["pos"] = np.array(L["pos"])
            self.curr_left_controller["rot"] = np.array(L["rot"])
            self.curr_left_robot["pos"] = self.left_wp
            self.curr_left_robot["rot"] = self.left_rot


        print(f"\n▶ Real Robot Input:"
              f"\n Right  → pos {self.right_wp} | rot {self.right_rot} | grip {self.right_grip}"
              f"\n Left   → pos {self.left_wp}  | rot {self.left_rot}  | grip {self.left_grip}")


    # ================================================================
    # VR LISTENER (same as simulation)
    # ================================================================
    async def vr_listener(self):
        async def handler(ws):
            print("🟢 VR Client Connected")
            try:
                async for msg in ws:
                    msg = msg.replace("False","false").replace("True","true").replace("None","null")
                    self.apply_vr_input_real(json.loads(msg))
            except websockets.exceptions.ConnectionClosed:
                print("🔴 VR Disconnected")

        print(f"🟡 Waiting for VR @ {VR_IP}:{VR_PORT}")
        async with websockets.serve(handler,VR_IP,VR_PORT):
            await asyncio.Future()



    # ================================================================
    # Robot Servo Loop (equivalent to sim_loop)
    # ================================================================
    async def robot_loop(self):
        while True:
            pose = np.concatenate([self.right_wp, self.right_rot])
            self.robot.move_to_pose(pose, use_euler=True)

            if USE_GRIPPER:
                if self.right_grip==-1: self.robot.gripper_open()
                else: self.robot.gripper_close()

            await asyncio.sleep(0.01) # Same 100 Hz update



    async def run_async(self):
        await asyncio.gather(
            self.vr_listener(),
            self.robot_loop()
        )



# ============================= MAIN ============================
if __name__=="__main__":
    controller = MoveVR_UR5()
    asyncio.run(controller.run_async())
