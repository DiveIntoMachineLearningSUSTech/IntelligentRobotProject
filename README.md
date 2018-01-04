## Usage:
```
export ROS_MASTER_URI=http://hostip:11311
export ROS_IP=`hostname -I`
catkin_make
source devel/setup.bash
python recongnize.py
```