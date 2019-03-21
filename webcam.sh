#!/bin/bash

DATE=$(date +"%Y-%m-%d_%H%M")
DST_DIR="/home/pi/webcam"

fswebcam -r 800x600 --no-banner -S 30 --set brightness=80% /home/pi/webcam/$DATE.jpg
cp $DST_DIR/$DATE.jpg $DST_DIR/lastest.jpg
