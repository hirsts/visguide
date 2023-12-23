import cv2
import os
import logging
import sys
import select
import subprocess

# Setup logging
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')

FRAMES_DIR = './frames'
EXT = 'jpg'

def reload_camera_driver(module_name):
    try:
        # Unload the camera module
        subprocess.run(['sudo', 'modprobe', '-r', module_name], check=True)
        logging.info(f"Camera driver {module_name} unloaded successfully.")
        
        # Load the camera module
        subprocess.run(['sudo', 'modprobe', module_name], check=True)
        logging.info(f"Camera driver {module_name} loaded successfully.")
    except subprocess.CalledProcessError as e:
        logging.error(f"Failed to reload camera driver: {e}")

def delete_frames(directory):
    for file in os.listdir(directory):
        file_path = os.path.join(directory, file)
        try:
            os.remove(file_path)
            logging.info(f"Deleting file: {file_path}")
        except FileNotFoundError:
            logging.error(f"File not found: {file_path}")
        except Exception as e:
            logging.error(f"Error deleting file {file_path}: {e}")

def initialize_camera(device_num, resolution=(1280, 720)):
    cap = cv2.VideoCapture(device_num)
    if not cap.isOpened():
        logging.error("Camera not opened.")
        return None
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, resolution[0])
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, resolution[1])
    return cap

def save_frame_camera_key(device_num, dir_path, basename, resolution=(1280, 720)):
    cap = initialize_camera(device_num, resolution)
    if cap is None:
        return

    os.makedirs(dir_path, exist_ok=True)
    base_path = os.path.join(dir_path, basename)

    logging.info("Type 'c' to capture a frame, followed by Enter. Type 'q' to quit, followed by Enter.")
    
    n = 0  # Initialize frame counter
    while True:
        ret, frame = cap.read()
        if not ret:
            logging.error("Failed to read frame from camera.")
            break

        # Non-blocking check for keypress
        if select.select([sys.stdin], [], [], 0)[0]:
            line = sys.stdin.readline().strip()
            if line == 'c':
                file_name = f'{base_path}_{n}.{EXT}'
                cv2.imwrite(file_name, frame)
                logging.info(f"Captured frame saved as {file_name}")
                n += 1  # Increment frame counter
            elif line == 'q':
                logging.info("Quitting.")
                break

    cap.release()

# Reload the camera driver to ensure it's loaded properly
reload_camera_driver('bcm2835-v4l2')

# Delete all frames in the frames directory
delete_frames(FRAMES_DIR)

# Save frames from the camera
save_frame_camera_key(0, FRAMES_DIR, 'camera_capture', resolution=(1280, 720))
