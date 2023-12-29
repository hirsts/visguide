#!/bin/bash

# Define the log file
LOG_FILE="/var/log/visguide.log"

# Navigate to the visguide directory
cd /home/shirst/visguide >> $LOG_FILE 2>&1

# Activate the virtual environment
source /home/shirst/visguide/visguide-env/bin/activate >> $LOG_FILE 2>&1

# Run the Python script
python3 /home/shirst/visguide/visguide.py >> $LOG_FILE 2>&1

