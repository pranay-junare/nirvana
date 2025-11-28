import asyncio
import websockets
import json
import matplotlib.pyplot as plt
from collections import deque

RECEIVER_IP = "100.70.51.33"
RECEIVER_PORT = 8765

# store streaming history
N = 400
xs, ys, zs = deque(maxlen=N), deque(maxlen=N), deque(maxlen=N)

# create figure
plt.ion()
fig, ax = plt.subplots(3, 1, figsize=(10,7), sharex=True)

lines = {
    "x": ax[0].plot([], [], label="X", linewidth=2)[0],
    "y": ax[1].plot([], [], label="Y", linewidth=2)[0],
    "z": ax[2].plot([], [], label="Z", linewidth=2)[0],
}

for i,name in enumerate(["X","Y","Z"]):
    ax[i].set_ylabel(name)
    ax[i].grid(True)

ax[-1].set_xlabel("Frame Index (time)")

async def handler(ws):
    idx = 0
    print("Receiving VR stream...")

    async for msg in ws:
        try:
            data = json.loads(msg)          # incoming JSON
            px,py,pz = data["right"]["pos"] # extract values

            xs.append(px)
            ys.append(py)
            zs.append(pz)
            idx += 1

            # --- FIXED: always pass sequences to set_data() ---
            t = list(range(len(xs)))  # x-axis is index series

            lines["x"].set_data(t, list(xs))
            lines["y"].set_data(t, list(ys))
            lines["z"].set_data(t, list(zs))

            # auto-scroll window
            for i in range(3):
                ax[i].set_xlim(max(0, idx-N), idx)

            plt.pause(0.001)

        except Exception as e:
            print("Parse error:", e)

async def main():
    async with websockets.serve(handler, RECEIVER_IP, RECEIVER_PORT):
        print(f"Live plot running on {RECEIVER_IP}:{RECEIVER_PORT}")
        await asyncio.Future()

if __name__ == "__main__":
    asyncio.run(main())
