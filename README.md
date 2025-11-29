# nirvana
XR based Teleoperation framework 


## Installation
```bash
conda env create -f requirements/env.yaml
pip install -r requirements/requirements.txt
conda activate nirvana
```

## Run
```bash
python -m robot_control.examples.move_to_point
python -m robot_control.examples.teleop_keyboard
python -m robot_control.examples.teleop_vr
```

## ToDo
- [x] App for sending quest-controller commands
- [x] Bimanual UR5 MujoCo Setup
- [x] Websocket server for communication
- [x] Keyboard based teleoperation
- [ ] Gripper control with trigger
- [ ] Visualize the XR controller inputs(matplotlib, cv2, etc) 
- [ ] Mapping functions from XR-controller to Robot commands
- [ ] Push based activatation
- [ ] App: Renaming, check for Video stream
 


## Notes
For Simulator

- x/-x: left/right (-0.8 to 0.8)
- y/-y: out-screen/into-screen (0.2 to 0.8)
- z/-z: up/down(0.2 to 1.0)