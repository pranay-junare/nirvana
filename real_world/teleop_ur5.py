import asyncio
import json
import numpy as np
import websockets
from typing import Dict
from scipy.spatial.transform import Rotation as R

from ur5_robot.ur5 import UR5RobotController   # ⬅ ensure correct import path


# =============================== CONFIG ===============================
VR_IP       = "10.131.249.198"
VR_PORT     = 8765

SCALE_POS   = 0.6       # motion speed scaling
SCALE_ROT   = 1.5       # rotation scaling
Z_FLIP      = True      # VR → UR coord adjust (optional fine tune)

ARM = "lightning"
ROBOT_IP = '10.33.55.90'
USE_GRIPPER = True       # set False if no gripper
# ====================================================================


class UR5VRControl:

    def __init__(self):
        print("[INIT] Connecting to UR5...")
        self.robot = UR5RobotController(ARM, robot_ip=ROBOT_IP, need_control=True, need_gripper=USE_GRIPPER)

        if not self.robot.is_alive:
            raise RuntimeError("❌ UR5 connection failed.")

        print(f"🟢 Connected to UR5 ({ARM}). Moving Home...")
        self.robot.go_home()
        asyncio.sleep(2)

        # VR reference frames
        self.vr_init = None
        self.curr_controller = {"pos": np.zeros(3), "rot": np.zeros(3)}
        self.curr_robot_pose = np.array(self.robot.get_current_pose(use_euler=True))

        # Live state
        self.pose_target = self.curr_robot_pose.copy()
        self.grip_state  = 1   # 1=open, 0=close


    # ==========================================================
    # VR INPUT HANDLER
    # ==========================================================
    def apply_vr(self, msg):
        R_hand = msg["right"]

        if self.vr_init is None:
            self.vr_init = msg
            print("🎮 VR tracking initialized")
            return

        activated = True if R_hand["push"] > 0.5 else False
        home_flag = R_hand["button"]

        # -------------------------------- HOME
        if home_flag:
            print("🏠 Returning to Home pose")
            self.robot.go_home()
            self.curr_robot_pose = np.array(self.robot.get_current_pose(use_euler=True))
            return

        # -------------------------------- ACTIVE MOTION
        if activated:
            # ===== position control =====
            delta = (np.array(R_hand["pos"]) - self.curr_controller["pos"]) * SCALE_POS

            #  Pose coordinate re-map (tune this only if needed)
            temp = delta[2]
            delta[2] = delta[0]
            delta[0] = temp
            delta[1] = -delta[1]

            target_pos = self.curr_robot_pose[:3] + delta
            print("Computed target pos:", target_pos)
            
            # ===== rotation control =====
            raw_rot = np.array(R_hand["rot"]) * SCALE_ROT
            yaw = -raw_rot[2]

            target_rot = np.zeros(3)
            target_rot[0] = -np.pi/2
            target_rot[1] = yaw
            target_rot[2] = 0

            self.pose_target = np.concatenate([target_pos, target_rot])

            # ===== gripper =====
            self.grip_state = 0 if R_hand["trigger"] > 0.5 else 1   # squeeze→close

        else:
            # Update reference frame when released
            self.curr_controller["pos"] = np.array(R_hand["pos"])
            self.curr_controller["rot"] = np.array(R_hand["rot"])
            self.curr_robot_pose = np.array(self.robot.get_current_pose(use_euler=True))


        print(f"➡ PoseTarget = {self.pose_target[:3]}  | Grip={self.grip_state}")


    # ==========================================================
    # VR LISTENER (WEBSOCKET SERVER)
    # ==========================================================
    async def vr_listener(self):
        async def handler(ws):
            print("🟢 VR Client Connected!")
            try:
                async for msg in ws:
                    try:
                        msg = msg.replace("False","false").replace("True","true").replace("None","null")
                        self.apply_vr(json.loads(msg))
                    except Exception as e:
                        print("⚠ JSON Error:", e)
            except websockets.exceptions.ConnectionClosed:
                print("🔴 VR Disconnected")

        print(f"🟡 Waiting for VR stream @ {VR_IP}:{VR_PORT}")
        async with websockets.serve(handler, VR_IP, VR_PORT):
            await asyncio.Future()


    # ==========================================================
    # ROBOT COMMAND LOOP (REAL-TIME SERVO)
    # ==========================================================
    async def robot_loop(self):
        while True:
            # print(f"Moving to Pose: {self.pose_target}")
            self.robot.move_to_pose(self.pose_target, use_euler=True)
            # print(f"Current Pose: {self.robot.get_current_pose(use_euler=True)}")

            if USE_GRIPPER:
                if self.grip_state == 0: self.robot.gripper_close()
                else: self.robot.gripper_open()

            await asyncio.sleep(0.01)   # 100Hz loop


    async def run(self):
        await asyncio.gather(self.vr_listener(), self.robot_loop())


# ========================= MAIN ============================
if __name__ == "__main__":
    tele = UR5VRControl()
    asyncio.run(tele.run())
