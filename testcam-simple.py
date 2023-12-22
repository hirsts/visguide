import cv2
import os
import logging
from pynput import keyboard

# Setup logging
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')

def on_press(key, cap, base_path, ext, n, listener):
    try:
        if key.char == 'c':  # Capturing the image
            ret, frame = cap.read()
            if not ret:
                logging.error("Failed to read frame from camera.")
                return False

            file_name = '{}_{}.{}'.format(base_path, n[0], ext)
            cv2.imwrite(file_name, frame)
            logging.info(f"Captured frame saved as {file_name}")
            n[0] += 1
        elif key.char == 'q':  # Quitting the program
            logging.info("Quitting.")
            listener.stop()
    except AttributeError:
        pass  # Ignore other keypresses

def save_frame_camera_key(device_num, dir_path, basename, ext='jpg'):
    cap = cv2.VideoCapture(device_num)

    if not cap.isOpened():
        logging.error("Camera not opened.")
        return

    os.makedirs(dir_path, exist_ok=True)
    base_path = os.path.join(dir_path, basename)
    n = [0]  # Use a list to allow modification within on_press

    # Setting up the listener for keypresses
    listener = keyboard.Listener(
            on_press=lambda key: on_press(key, cap, base_path, ext, n, listener))
    listener.start()
    listener.join()

    # Properly release resources
    cap.release()

logging.info("Press 'c' to capture a frame. Press 'q' to quit.")
save_frame_camera_key(0, './frames/', 'camera_capture')
