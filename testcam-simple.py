import cv2
import os
import logging

# Setup logging
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')

def save_frame_camera_key(device_num, dir_path, basename, ext='jpg', delay=1, window_name='frame'):
    cap = cv2.VideoCapture(device_num)

    if not cap.isOpened():
        logging.error("Camera not opened.")
        return

    os.makedirs(dir_path, exist_ok=True)
    base_path = os.path.join(dir_path, basename)

    # Create a minimal window for keypress events
    cv2.namedWindow(window_name, cv2.WINDOW_NORMAL)
    cv2.resizeWindow(window_name, 1, 1)

    n = 0
    while True:
        ret, frame = cap.read()
        if not ret:
            logging.error("Failed to read frame from camera.")
            break

        # Display an empty frame to capture keypress
        cv2.imshow(window_name, frame)

        key = cv2.waitKey(delay) & 0xFF
        if key == ord('c'):
            file_name = '{}_{}.{}'.format(base_path, n, ext)
            cv2.imwrite(file_name, frame)
            logging.info(f"Captured frame saved as {file_name}")
            n += 1
        elif key == ord('q'):
            logging.info("Quitting.")
            break

    # Properly release resources
    cap.release()
    cv2.destroyAllWindows()

logging.info("Press 'c' to capture a frame. Press 'q' to quit.")
save_frame_camera_key(0, './frames/', 'camera_capture')
