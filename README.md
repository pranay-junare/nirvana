# Nirvana
Nirvana is a XR based Teleoperation framework: A generalized, robot-agnostic, simulator-agnostic VR-based teleoperation framework that works seamlessly across simulation and real robots for scalable data collection and human-in-the-loop control.

## Demo
![alt text](assets/teaser.gif)

## Installation
```bash
git clone https://github.com/pranay-junare/nirvana.git
conda env create -f requirements/nirvana.yaml
pip install -r requirements/requirements.txt
conda activate nirvana
```

## Run
### 1. Simulated Mujoco UR5-bimanual setup:
```bash
# script to move the robot
cd nirvana/simulation/mujoco
python -m robot_control.examples.move_to_point

# script to perform teleop using Keyboard
python -m robot_control.examples.teleop_keyboard

# script to perform teleop using Meta Quest VR
python -m robot_control.examples.teleop_vr
```

`Note`: We use few objects(eg: shoe, candybox) from [`Google Scanned Objects dataset` ](https://arxiv.org/pdf/2204.11918). More information on how to import them in your Mujoco scene can be found [here](https://github.com/kevinzakka/mujoco_scanned_objects).

### 2. Realworld UR5 setup:
```bash
cd nirvana/real_world
python teleop_ur5.py
```

### 3. Unity App setup:
```bash

```


## ToDo
- [x] App for sending quest-controller commands
- [x] Bimanual UR5 MujoCo Setup
- [x] Websocket server for communication
- [x] Keyboard based teleoperation
- [x] Gripper control with trigger
- [x] Mapping functions from XR-controller to Robot commands
- [x] Push based activatation, Right arm control
- [x] Add sample objects(Google scan objects) for grasping demo
- [x] App: Renaming, check for Video stream, send buttons
- [ ] (Optional) App: Visualize Mujoco world and XR controller inputs in VR 
 



## License

MIT

<!-- ## Notes
For Simulator

- x/-x: left/right (-0.8 to 0.8)
- y/-y: out-screen/into-screen (0.2 to 0.8)
- z/-z: up/down(0.2 to 1.0) -->