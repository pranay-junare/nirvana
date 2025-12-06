# Script to stream RGB frames from a RealSense camera to a Unity application via WebSocket

import pyrealsense2 as rs
import cv2
import numpy as np
import asyncio
import websockets

UNITY_SERVER_URL = "ws://10.131.236.50:8766/video"   # change IP as needed

CAMERA_INVERTED = False
CAMERA_FLIP = True

# 1. Detect all RealSense serial numbers
def get_serial_numbers():
    context = rs.context()
    devices = context.query_devices()
    serials = [device.get_info(rs.camera_info.serial_number) for device in devices]
    return serials

# 2. Initialize ONE pipeline (choose index)
def init_single_pipeline(serial):
    pipeline = rs.pipeline()
    config = rs.config()
    config.enable_device(serial)
    config.enable_stream(rs.stream.color, 640, 480, rs.format.bgr8, 30)
    pipeline.start(config)
    return pipeline

# 3. Get only RGB frame (This is a BLOCKING function)
def get_rgb_frame(pipeline):
    frames = pipeline.wait_for_frames() # This call blocks!
    color_frame = frames.get_color_frame()

    if not color_frame:
        return None

    color_image = np.asanyarray(color_frame.get_data())

    if CAMERA_INVERTED:
        color_image = cv2.rotate(color_image, cv2.ROTATE_180)
    if CAMERA_FLIP:
        color_image = cv2.flip(color_image, 1)

    return color_image

# 4. Stream RGB to Unity via WebSocket
async def stream_rgb(pipeline):
    uri = UNITY_SERVER_URL
    print("[WS] Connecting to Unity at:", uri)

    try:
        async with websockets.connect(uri) as ws:
            print("[WS] Connected → streaming RGB frames...")

            while True:
                # --- THIS IS THE FIX ---
                # Run the blocking get_rgb_frame() in a separate thread
                # so it doesn't freeze the main asyncio loop.
                frame = await asyncio.to_thread(get_rgb_frame, pipeline)
                # -----------------------

                if frame is None:
                    continue

                # encode frame as JPEG
                _, jpg = cv2.imencode(".jpg", frame)

                # send bytes
                await ws.send(jpg.tobytes())

    except (websockets.exceptions.ConnectionClosedError, websockets.exceptions.ConnectionClosedOK):
        print("[WS] Connection to Unity lost.")
    except Exception as e:
        print(f"[WS] An error occurred: {e}")

# MAIN
if __name__ == "__main__":
    serials = get_serial_numbers()
    print("RealSense cameras detected:", serials)

    if len(serials) == 0:
        print("No RealSense cameras connected!")
        exit()

    # choose ONE camera (e.g., first one), change index as needed
    selected_serial = serials[0]
    print("Using RealSense:", selected_serial)

    pipeline = init_single_pipeline(selected_serial)

    try:
        asyncio.run(stream_rgb(pipeline))
    except KeyboardInterrupt:
        print("\n[Main] Stream stopped by user.")
    finally:
        pipeline.stop()
        print("[Main] RealSense pipeline stopped.")