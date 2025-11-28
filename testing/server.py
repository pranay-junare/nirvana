import asyncio
import websockets
RECEIVER_IP = "100.70.51.33" # my local IP address
RECEIVER_PORT = 8765
i = 0

async def handler(websocket):
    """
    A simple handler that waits for messages (values) and prints them.
    """
    print(f"A client (your Quest) connected!")
    
    try:
        # This loop waits forever for new messages from this client
        async for message in websocket:
            # 'message' is the value you sent from Unity.
            global i
            i = i+1
            if i % 10 == 0:  # Print every 10th message to reduce console spam
                print(f"[Client says]: {message}")
            
    except websockets.exceptions.ConnectionClosed:
        print("Client disconnected.")

async def main():
    # Start the WebSocket server and run it forever
    async with websockets.serve(handler, RECEIVER_IP, RECEIVER_PORT):
        print(f"Minimal server started at {RECEIVER_IP}:{RECEIVER_PORT}...")
        print("Waiting for a client (your Quest) to connect...")
        await asyncio.Future()  # Run forever

if __name__ == "__main__":
    asyncio.run(main())