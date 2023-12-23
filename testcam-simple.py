import cv2
import os
import logging
import sys
import select

# Setup logging
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')

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
    logging.info("Type 'c' to capture a frame, followed by Enter. Type 'q' to quit, followed by Enter.")

    while True:
        ret, frame = cap.read()
        if not ret:
            logging.error("Failed to read frame from camera.")
            break

        # Non-blocking check for keypress
        if select.select([sys.stdin], [], [], 0)[0]:
            line = sys.stdin.readline().strip()
            if line == 'c':
                file_name = '{}_{}.{}'.format(base_path, n, ext)
                cv2.imwrite(file_name, frame)
                logging.info(f"Captured frame saved as {file_name}")
                n += 1
            elif line == 'q':
                logging.info("Quitting.")
                break

    # Properly release resources
    cap.release()

# Delete all frames in the frames directory
for file in os.listdir('./frames'):
    os.remove(os.path.join('./frames', file))
    

save_frame_camera_key(0, './frames/', 'camera_capture', resolution=(640, 480))
