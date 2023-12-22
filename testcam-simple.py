import cv2
import os
import logging
import keyboard

# Setup logging
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')

def save_frame_camera_key(device_num, dir_path, basename, ext='jpg'):
    cap = cv2.VideoCapture(device_num)

    if not cap.isOpened():
        logging.error("Camera not opened.")
        return

    os.makedirs(dir_path, exist_ok=True)
    base_path = os.path.join(dir_path, basename)

    n = 0
    logging.info("Press 'c' to capture a frame. Press 'q' to quit.")

    while True:
        try:
            if keyboard.is_pressed('c'):  # Capturing the image
                logging.debug("Detected 'c' keypress.")
                ret, frame = cap.read()
                if not ret:
                    logging.error("Failed to read frame from camera.")
                    break

                file_name = '{}_{}.{}'.format(base_path, n, ext)
                cv2.imwrite(file_name, frame)
                logging.info(f"Captured frame saved as {file_name}")
                n += 1
                while keyboard.is_pressed('c'):
                    pass  # Wait for key release

            if keyboard.is_pressed('q'):  # Quitting the program
                logging.info("Detected 'q' keypress. Quitting.")
                break
        # Uncomment the following line to see any specific errors
        # except Exception as e:
        #     logging.error(f"Error occurred: {e}")
        #     break

    # Properly release resources
    cap.release()

save_frame_camera_key(0, './frames/', 'camera_capture')
