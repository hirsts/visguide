import cv2
import os
import logging
import sys
import select
import threading

# Setup logging
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')

def non_blocking_input(key_pressed_event, stop_event):
    while not stop_event.is_set():
        if select.select([sys.stdin], [], [], 0.1)[0]:
            line = sys.stdin.readline().strip()
            if line == 'c':
                logging.info("Captured keypress 'c'")
                key_pressed_event.set()  # Set the event to indicate 'c' was pressed
            elif line == 'q':
                logging.info("Captured keypress 'q'")
                stop_event.set()  # Set the event to indicate the script should stop

def save_frame_camera_key(device_num, dir_path, basename, ext='jpg', resolution=(1280, 720)):
    cap = cv2.VideoCapture(device_num)

    if not cap.isOpened():
        logging.error("Camera not opened.")
        return

    # Set the resolution
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, resolution[0])
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, resolution[1])

    os.makedirs(dir_path, exist_ok=True)
    base_path = os.path.join(dir_path, basename)

    n = 0
    key_pressed_event = threading.Event()
    stop_event = threading.Event()
    input_thread = threading.Thread(target=non_blocking_input, args=(key_pressed_event, stop_event))
    input_thread.start()

    logging.info("Type 'c' to capture a frame, followed by Enter. Type 'q' to quit, followed by Enter.")

    while not stop_event.is_set():
        ret, frame = cap.read()
        if not ret:
            logging.error("Failed to read frame from camera.")
            break

        if key_pressed_event.is_set():
            file_name = '{}_{}.{}'.format(base_path, n, ext)
            cv2.imwrite(file_name, frame)
            logging.info(f"Captured frame saved as {file_name}")
            n += 1
            key_pressed_event.clear()  # Clear the event after capturing the frame

    # Properly release resources
    cap.release()

save_frame_camera_key(0, './frames/', 'camera_capture', resolution=(640, 480))
