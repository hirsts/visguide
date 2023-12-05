import argparse
import os
import threading
from threading import Lock
from logging.handlers import SysLogHandler
from dotenv import load_dotenv
import cv2
from PIL import Image
import numpy as np
import base64
import time
import subprocess
import logging
import errno
import simpleaudio as sa
import keyboard
from openai import OpenAI
from elevenlabs import generate, set_api_key, stream

# Get options from command line arguments
parser = argparse.ArgumentParser()
parser.add_argument("-v", "--verbose", action="store_true")
parser.add_argument("-d", "--debug", action="store_true")
parser.add_argument("-s", "--syslog", action="store_true")
args = parser.parse_args()

# Set the logging level based on the verbose and debug options
if args.verbose:
    logging.basicConfig(format='%(asctime)s.%(msecs)03d - %(levelname)s - %(message)s',
                        datefmt='%Y-%m-%d %H:%M:%S',
                        level=logging.INFO)
elif args.debug:
    logging.basicConfig(format='%(asctime)s.%(msecs)03d - %(levelname)s - %(message)s',
                        datefmt='%Y-%m-%d %H:%M:%S',
                        level=logging.DEBUG)
else:
    logging.basicConfig(level=logging.WARNING)

# Set the logging level based on the verbose and debug options
logger = logging.getLogger()

# If the syslog option is present, send logs to the syslog server
if args.syslog:
    syslog_handler = SysLogHandler(address=('splunk.local', 8516))
    logger.addHandler(syslog_handler)


# Define a function to check if the script is running on a Raspberry Pi
def is_running_on_raspberry_pi():
    try:
        with open("/sys/firmware/devicetree/base/model", "r") as f:
            if "Raspberry Pi" in f.read():
                return True
    except Exception:
        return False

# Conditional imports for Raspberry Pi specific modules
if is_running_on_raspberry_pi():
    import RPi.GPIO as GPIO
    logger.info("Running on Raspberry Pi, GPIO module imported")
else:
    logger.info("Not running on Raspberry Pi, GPIO module not imported")

# load the environment variables from the .env file if they are not set
if 'OPENAI_API_KEY' not in os.environ or 'ELEVENLABS_API_KEY' not in os.environ or 'ELEVENLABS_VOICE_ID' not in os.environ:
        # If not set, check for .env file and load it
        dotenv_path = os.path.join(os.path.dirname(__file__), '.env')
        if os.path.exists(dotenv_path):
            load_dotenv(dotenv_path)
            logger.info('.env file found and loaded')
        else:
            logger.warning('Required environment variables are not set and no .env file found')


# Constants for press detection
SINGLE_PRESS_MAX = 0.5  # Max duration for a single press (seconds)
DOUBLE_PRESS_INTERVAL = 0.5  # Max interval between double presses (seconds)
TRIPLE_PRESS_INTERVAL = 0.5  # Max interval between triple presses (seconds)
LONG_PRESS_MIN = 1  # Min duration for a long press (seconds)

# Global variables to track press patterns
last_press_time = 0
press_count = 0
press_start_time = 0
press_lock = Lock()  # Thread lock for synchronizing access to global variables
button_state = False

# Key press event handler
def keyboard_event(event):
    if event.event_type == keyboard.KEY_DOWN:
        # Only handle key down events for the space key
        if event.name == 'space':
            #logger.debug(f"Keyboard event detected: {event.event_type}")
            #logger.debug(f"keyboard_event - calling on_key_press")
            on_key_press(event)

    elif event.event_type == keyboard.KEY_UP:
        # Only handle key up events for the space key
        if event.name == 'space':
            on_key_release(event)

# Key press event handler
def on_key_press(event):
    global press_start_time, button_state
    if button_state==False:
        with press_lock:
            press_start_time = time.time()
            button_state = True
            #logger.debug(f"on_key_press - Press start time: {press_start_time}")

# Key release event handler
def on_key_release(event):
    global press_start_time, press_count, button_state
    #logger.debug(f"event.name = {event.name} was released!!!!!!")

    if button_state==True:
        button_state = False
        with press_lock:  
            press_duration = time.time() - press_start_time
            #logger.debug(f"on_key_release - press_duration = {press_duration}")
            if press_duration >= LONG_PRESS_MIN:
                #logger.debug("LONG PRESS DETECTED")
                handle_long_press()
            else:
                press_count += 1
                threading.Timer(SINGLE_PRESS_MAX, check_press_count, [press_duration]).start()

# This might be needed for the GPIO button press and so keeping for now
# Key press process is working on Mac keyboard
# def button_pressed(channel):
#     logger.debug(f"{channel} Button was pressed!")
#     global press_start_time
#     press_start_time = time.time()
#     logger.debug(f"Press start time: {press_start_time}")
    
# def button_released(channel):
#     logger.debug(f"{channel} Button was released!")
#     global press_start_time, press_count
#     press_duration = time.time() - press_start_time
#     logger.debug(f"Press duration: {press_duration}")

#     if press_duration >= LONG_PRESS_MIN:
#         handle_long_press()
#     else:
#         press_count += 1
#         threading.Timer(SINGLE_PRESS_MAX, check_press_count).start()

def check_press_count(press_duration):
    global press_count
    with press_lock:
        if press_count == 1:
            handle_single_press(press_duration)
        elif press_count == 2:
            handle_double_press()
        elif press_count == 3:
            handle_triple_press()
        press_count = 0


# Handlers for different press types
def handle_single_press(press_duration):
    if press_duration < SINGLE_PRESS_MAX:
        logger.info("Single Press Detected")
        # Implement single press action

def handle_double_press():
    global press_count
    press_count = 0
    logger.info("Double Press Detected")
    # Implement double press action

def handle_triple_press():
    global press_count
    press_count = 0
    logger.info("Triple Press Detected")
    # Implement triple press action

def handle_long_press():
    global press_count
    press_count = 0
    logger.info("Long Press Detected")
    # Implement long press action

# Update the GPIO setup
if is_running_on_raspberry_pi():
    GPIO.setmode(GPIO.BCM)
    GPIO.setup(17, GPIO.IN, pull_up_down=GPIO.PUD_UP)
    GPIO.add_event_detect(17, GPIO.RISING, callback=on_key_press)
    GPIO.add_event_detect(17, GPIO.FALLING, callback=on_key_release)


# Update listen_for_key function to call button_callback on key press and release
def listen_for_key():
    # Add hooks for key press and release
    keyboard.hook(keyboard_event)

    # Loop to keep the thread alive
    while True:
        time.sleep(1)

############################################################################################################

# # Setup the button
# def button_callback(channel):
#     logger.info("Button was pushed!")
#     # Implement the action to be taken when the button is pressed

# # Setup the key press event handler
# def key_press_callback():
#     # e.name will contain the name of the key pressed
#     logger.info("Space key was pressed")
#     # Implement the action to be taken when the key is pressed

# def listen_for_key():
#     # Using wait method in a loop
#     while True:
#         keyboard.wait('space')  # Change 'space' to the key you want to listen for
#         # key_press_callback()
#         button_callback(17)

# # Setup GPIO Pins
# if is_running_on_raspberry_pi():
#     # Setup GPIO Pins only if on Raspberry Pi
#     GPIO.setmode(GPIO.BCM)
#     GPIO.setup(17, GPIO.IN, pull_up_down=GPIO.PUD_UP)
#     GPIO.add_event_detect(17, GPIO.FALLING, callback=button_callback, bouncetime=200)

# Initialize the webcam
cap = cv2.VideoCapture(0)
# Check if the webcam is opened correctly
if not cap.isOpened():
    logger.warning("Failed to open webcam")
    raise IOError("Cannot open webcam")
    exit(1)
# Wait for the camera to initialize and adjust light levels
time.sleep(2)

# Create an OpenAI client
client = OpenAI()

# Set the ElevenLabs API key 
set_api_key(os.environ.get("ELEVENLABS_API_KEY"))

def check_internet(timeout=60, max_response_time=30):  # Default timeout is 60 seconds, and default max_response_time is 30ms
    hostname = "8.8.8.8"
    start_time = time.time()

    while time.time() - start_time < timeout:
        # Use subprocess to get the ping statistics
        try:
            ping_response = subprocess.check_output(
                ["ping", "-c", "1", hostname],
                stderr=subprocess.STDOUT,  # Redirect stderr to stdout
                universal_newlines=True
            )

            # Extract the time from the ping response
            ping_time = float(ping_response.split("time=")[1].split(" ms")[0])
            if ping_time <= max_response_time:
                logger.info(f"Internet connection detected with ping time: {ping_time} ms")
                return True
            else:
                logger.warning(f"Slow internet response time: {ping_time} ms")
                
                # Play the user warning audio file
                wave_obj = sa.WaveObject.from_wave_file("./assets/wav/slow_internet.wav")
                play_obj = wave_obj.play()
                play_obj.wait_done()
                return True
        except subprocess.CalledProcessError:
            # This block is executed if the ping command fails
            logger.warning("Ping command failed")

        # Sleep for a short duration before retrying
        time.sleep(1)

    logger.warning("No internet connection detected within the given time frame")
    # Play the user warning audio file
    wave_obj = sa.WaveObject.from_wave_file("./assets/wav/No_internet.wav")
    play_obj = wave_obj.play()
    play_obj.wait_done()
    return False


def capture_image():
    ret, frame = cap.read()
    if ret:
        # Convert the frame to a PIL image
        pil_img = Image.fromarray(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))

        # Resize the image
        max_size = 250
        ratio = max_size / max(pil_img.size)
        new_size = tuple([int(x*ratio) for x in pil_img.size])
        resized_img = pil_img.resize(new_size, Image.LANCZOS)

        # Convert the PIL image back to an OpenCV image
        frame = cv2.cvtColor(np.array(resized_img), cv2.COLOR_RGB2BGR)

        # Encode the image as base64
        frame_jpg = cv2.imencode('.jpg', frame)[1]
        frame = base64.b64encode(frame_jpg).decode("utf-8")

        # If debugging, save the frame as an image file
        if args.debug:
            # Create a folder to store the frames if it doesn't exist
            folder = "frames"
            if not os.path.exists(folder):
                logger.debug("Creating folder to store frames")
                os.makedirs(folder, exist_ok=True)
            path = f"{folder}/frame.jpg"
            logger.debug(f"Saving frame to {path}")
            cv2.imwrite(path, frame_jpg)
        # Delete the JPG version of the frame to save memory
        del frame_jpg
        # Return the base64 encoded image
        return frame
    else:
        logger.warning("Failed to capture image")

def play_audio(text):
    try:
        # Calls the ElevenLabs API to generate an audio stream
        audio_stream = generate(text, stream=True, voice=os.environ.get("ELEVENLABS_VOICE_ID"))
        # Uses the ElevenLabs stream function to play the audio stream
        stream(audio_stream)
    except Exception as e:
        logger.error(f"Error in play_audio: {e}")


# FUNC: Generates the OpenAI "user" script
# TODO: Explore if this an optimal prompt for each request.
def generate_new_line(base64_image):
    return [
        {
            "role": "user",
            "content": [
                {"type": "text", "text": "Describe this image"},
                {
                    "type": "image_url",
                    "image_url": f"data:image/jpeg;base64,{base64_image}",
                },
            ],
        },
    ]

# FUNC: Send image to OPENAI to get text summary back
def analyze_image(base64_image, script):
    try:
        context = os.environ.get('CONTEXT', """
            You are a guide for the blind. Describe the image with a focus on major features with a priority on risk. 
            For example if there is a door ahead, is it opened or closed and how many paces is it. Another example would be where there is a road ahead, how many paces is it, is it busy or quiet. 
            Dont repeat yourself and keep each description to 4 seconds.
            Assume the image is always the view ahead.
        """)
        response = client.chat.completions.create(
            model="gpt-4-vision-preview",
            messages=[
                {
                    "role": "system",
                    "content": context,
                },
            ]
            + script
            + generate_new_line(base64_image),
            max_tokens=500,
        )
        response_text = response.choices[0].message.content
        return response_text
    except Exception as e:
        logger.error(f"Error in analyze_image: {e}")
        raise

def main():
    script = []
    timings = {'image_encoding': 0, 'analysis': 0, 'audio_playback': 0}
    # Set up keyboard event listener
    listener_thread = threading.Thread(target=listen_for_key, daemon=True) # This makes the thread exit when the main program exits
    listener_thread.start()

    while True:
        try:
            # Start the timers
            start_time = time.time()

            # Capture the image
            base64_image = capture_image()

            logger.info(" Sending image for narration ...")
            analysis_start_time = time.time()
            analysis = analyze_image(base64_image, script=script)
            timings['analysis'] += time.time() - analysis_start_time

            logger.info("🎙️ VisGuide says:")
            logger.info(analysis)

            playback_start_time = time.time()
            play_audio(analysis)
            timings['audio_playback'] += time.time() - playback_start_time

            script = script + [{"role": "assistant", "content": analysis}]

            time.sleep(5)
        except Exception as e:
            logger.error(f"An error occurred in main loop: {e}")
            continue
        except KeyboardInterrupt:
            logger.info("Script interrupted by user, exiting gracefully.")
            # Cleanup GPIO pins if on Raspberry Pi
            if is_running_on_raspberry_pi():
                GPIO.cleanup()
            cap.release()
            cv2.destroyAllWindows()
            exit(0)

    # Report timings
    for operation, time_taken in timings.items():
        logger.info(f"{operation}: {time_taken:.2f} seconds")


    
# Check for internet connectivity by pinging Google DNS
while not check_internet(timeout=60, max_response_time=30):
    logger.info("Waiting for internet connection...")
    time.sleep(1)

# Visguide is ready
# Play audio file ./assets/visguide_is_ready.mp3 to indicate that VisGuide app is ready
# load the mp3 audio file
wave_obj = sa.WaveObject.from_wave_file("./assets/wav/VisGuide_is_ready.wav")
# play the audio file
play_obj = wave_obj.play()

if __name__ == "__main__":
    main()
