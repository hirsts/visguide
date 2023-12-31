import sys
import fileinput
import threading
from threading import Lock
from dotenv import load_dotenv
import cv2
from PIL import Image
import numpy as np
import base64
import time
import subprocess
import simpleaudio as sa
from openai import OpenAI
from elevenlabs import play, Voice, VoiceSettings, set_api_key, generate, stream
import argparse
import logging
from logging.handlers import SysLogHandler
import os  # Ensure os is imported for session ID generation

# FUNC: Custom logging formatter with Session ID
class CustomFormatter(logging.Formatter):
    def __init__(self, session_id, fmt, datefmt=None):
        self.session_id = session_id
        super(CustomFormatter, self).__init__(fmt, datefmt)

    def format(self, record):
        # First, format the record with the original formatting.
        formatted_message = super(CustomFormatter, self).format(record)
        # Now, insert the session ID.
        return formatted_message.replace("{session_id}", self.session_id)


# ACTION: Parse command line arguments
parser = argparse.ArgumentParser()
parser.add_argument("-v", "--verbose", action="store_true")
parser.add_argument("-d", "--debug", action="store_true")
parser.add_argument("-s", "--syslog", action="store_true")
parser.add_argument("-t", "--target_host", type=str, help="Target host for syslog")
parser.add_argument("-p", "--target_port", type=int, help="Target port for syslog")
args = parser.parse_args()

# ACTION: Generate a unique session ID
session_id = os.urandom(8).hex()

# ACTION: Set the logging level based on the verbose and debug options
if args.verbose:
    logging_level = logging.INFO
elif args.debug:
    logging_level = logging.DEBUG
else:
    logging_level = logging.WARNING

# ACTION: Common format with placeholder for session ID
common_format = '%(asctime)s.%(msecs)03d - SID:{session_id} - MSG:%(levelname)s - %(message)s'
date_format = '%Y-%m-%d %H:%M:%S'

# ACTION: Configure the root logger
logger = logging.getLogger()
logger.setLevel(logging_level)

# ACTION: Create and set formatter with session ID for all handlers
formatter = CustomFormatter(session_id, common_format, date_format)

# Set syslog server and port
syslog_server = args.target_host if args.target_host else "splunk.local"
syslog_port = args.target_port if args.target_port else 8516

# Add syslog handler if needed
if args.syslog:
    syslog_handler = SysLogHandler(address=(syslog_server, syslog_port))
    syslog_handler.setFormatter(formatter)
    logger.addHandler(syslog_handler)

# Always add a console handler
console_handler = logging.StreamHandler()
console_handler.setFormatter(formatter)
logger.addHandler(console_handler)

# Example usage of the logger
logger.debug("TIMING:Start TYPE:Func DESC:is_running_on_raspberry_pi() RESULT:None")
logger.info("Info message for testing")
logger.warning("Warning message for testing")

# Splunk search to visualize the timing of the different functions
# (index=visguide ("TIMING:Start" OR "TIMING:End"))
# | transaction DESC SID startswith="TIMING:Start" endswith="TIMING:End" 
# | eval duration=(duration * 1000) 
# | table _time, DESC, duration
# | sort _time

# FUNC: Define a function to check if the script is running on a Raspberry Pi
def is_running_on_raspberry_pi():
    logger.debug("TIMING:Start TYPE:Func DESC:is_running_on_raspberry_pi() RESULT:None")
    try:
        with open("/sys/firmware/devicetree/base/model", "r") as f:
            if "Raspberry Pi" in f.read():
                logger.debug("TIMING:Start TYPE:Func DESC:is_running_on_raspberry_pi() RESULT:True")
                return True
    except Exception:
        logger.debug("TIMING:End TYPE:Func DESC:is_running_on_raspberry_pi() RESULT:False")
        return False

# FUNC: A function to set the default PulseAudio sink (audio output)
# When running at start up the session audio is routed to the HDMI output
# This function is used after checking that the BT speaker it connected to route the session audio to the BT speaker
def set_default_sink(sink_index):
    """
    Sets the default PulseAudio sink (audio output) to the given sink index.

    Parameters:
    sink_index (str): The index or name of the PulseAudio sink to set as default.
    """
    try:
        # Constructing the command
        command = ["pactl", "set-default-sink", str(sink_index)]

        # Executing the command
        subprocess.run(command, check=True)
        print(f"Default sink set to {sink_index}")

    except subprocess.CalledProcessError as e:
        print(f"An error occurred: {e}")
    except Exception as e:
        print(f"Unexpected error: {e}")

# FUNC: A function to get the list of connected Bluetooth devices
def get_connected_devices():
    try:
        cmd = "bluetoothctl devices | cut -f2 -d' ' | while read uuid; do bluetoothctl info $uuid; done | grep -e 'Device\\|Connected\\|Name'"
        result = subprocess.check_output(cmd, shell=True, text=True)
        return result
    except subprocess.CalledProcessError as e:
        print(f"An error occurred: {e}")
        return ""

# FUNC: A function to check if a specific Bluetooth device is connected
def is_device_connected(device_name):
    output = get_connected_devices()
    devices = output.split("Device ")

    for device in devices[1:]:  # Skip the first split as it's empty
        if device_name in device:
            return "Connected: yes" in device

    return False

def is_sink_ready():
    try:
        cmd = "pactl list sinks short"
        result = subprocess.check_output(cmd, shell=True, text=True)
        return "bluez_sink.70_BF_92_A2_DA_5E.a2dp_sink" in result and "SUSPENDED" in result
    except subprocess.CalledProcessError as e:
        print(f"Error checking sink status: {e}")
        return False

def wait_for_device_and_sink(device_name, timeout=60):
    start_time = time.time()
    while time.time() - start_time < timeout:
        if is_device_connected(device_name) and is_sink_ready():
            print("Device and sink are ready.")
            return True
        time.sleep(1)  # Wait for 1 second before checking again
    print("Timeout waiting for device and sink.")
    return False

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

# ACTION: Conditional imports for Raspberry Pi specific modules
if is_running_on_raspberry_pi():
    logger.debug("TIMING:Start TYPE:Action DESC:is_running_on_raspberry_pi() RESULT:True")
    import RPi.GPIO as GPIO
    logger.debug("TIMING:End TYPE:Action DESC:is_running_on_raspberry_pi() RESULT:RPi.GPIO imported")

    # ACTION: Check if the Bluetooth device is connected
    logger.debug("TIMING:Start TYPE:Action DESC:Check if Bluetooth device is connected RESULT:None")
    device_name = "Jabra Speak 710"
    # Loop until the device is connected
    while not wait_for_device_and_sink(device_name):
        sys.stdout.write(f"\rDevice '{device_name}' is not connected. Checking again...")
        sys.stdout.flush()  # Flush the buffer to ensure the output is displayed
        time.sleep(1)  # Wait for 1 second before checking again
    # Once connected, set the default audio output to the Bluetooth speaker
    set_default_sink("1")
    logger.debug("TIMING:End TYPE:Action DESC:Check if Bluetooth device is connected RESULT:Device connected")
else:
    import keyboard
    logger.debug("TIMING:End TYPE:Action DESC:is_running_on_raspberry_pi() RESULT:RPi.GPIO not imported. keyboard imported")

# ACTION: load the environment variables from the .env file if they are not set
logger.debug("TIMING:Start TYPE:Action DESC:Load .env RESULT:None")
if 'OPENAI_API_KEY' not in os.environ or 'ELEVENLABS_API_KEY' not in os.environ or 'ELEVENLABS_VOICE_ID' not in os.environ:
        # If not set, check for .env file and load it
        dotenv_path = os.path.join(os.path.dirname(__file__), '.env')
        if os.path.exists(dotenv_path):
            load_dotenv(dotenv_path)
            logger.debug("TIMING:End TYPE:Action DESC:Load .env RESULT:Loaded")
        else:
            logger.warning("TIMING:End TYPE:Action DESC:Load .env RESULT:File not found")


# ACTION: Define global variables
logger.debug("TIMING:Start TYPE:Action DESC:Define global variables RESULT:None")
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
global Action, script, timings
Action = "None"
interrupt_main_process = False
stop_audio_stream = False
imagenum = 0
voice_id = os.environ.get("ELEVENLABS_VOICE_ID")
device_name = "Jabra Speak 710"
logger.debug("TIMING:End TYPE:Action DESC:Define global variables RESULT:Done")

# FUNC: Space Key press event handler
def keyboard_event(event):
    logger.debug("TIMING:Start TYPE:Func DESC:Keyboard Event RESULT:None")
    if event.event_type == keyboard.KEY_DOWN:
        # Only handle key down events for the space key
        if event.name == 'space':
            #logger.debug(f"Keyboard event detected: {event.event_type}")
            #logger.debug(f"keyboard_event - calling on_key_press")
            logger.debug("TIMING:End TYPE:Func DESC:Keyboard Event RESULT:Key Down")
            on_key_press()

    elif event.event_type == keyboard.KEY_UP:
        # Only handle key up events for the space key
        if event.name == 'space':
            logger.debug("TIMING:End TYPE:Func DESC:Keyboard Event RESULT:Key Up")
            on_key_release()

# FUNC: Key press event handler
def on_key_press():
    global press_start_time, button_state
    if button_state==False:
        with press_lock:
            press_start_time = time.time()
            button_state = True
            #logger.debug(f"on_key_press - Press start time: {press_start_time}")

# Key release event handler
def on_key_release():
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

# ACTION: Preload into variables the prompts from prompts.txt. Each line is a key value pair separated by an equals sign
# Open the prompts.txt file
logger.debug("TIMING:Start TYPE:Action DESC:Preload prompts RESULT:None")
with open('./prompts.txt') as f:
    # each line is a key value pair separated by an equals sign
    # read each line, one at a time, and split it into a key and value
    for line in f:
        key, value = line.split('=')
        # remove any whitespace from the key and value
        key = key.strip()
        value = value.strip()
        # Assign the value to a global variable with the key as the variable name
        globals()[key] = value
        # Log the value of the global variable
        # logger.debug(f"Value of global variable {key}: {globals()[key]}")
    # List each global variable that starts with PROMPT
    #logger.debug(f"List of global variables that start with PROMPT: {[key for key in globals().keys() if key.startswith('PROMPT')]}")
logger.debug("TIMING:End TYPE:Action DESC:Preload prompts RESULT:Prompts loaded")
if os.environ.get('VISSTYLE') == 'Guide':
    context = os.environ.get('PROMPT_Guide')
elif os.environ.get('VISSTYLE') == 'Tourist':
    context = os.environ.get('PROMPT_Tourist')

# FUNC: Define a function to find a line in a file starting with something specific and replace it with a new line
def replace_line_in_file(file_path, line_starts_with, new_line):
    logger.debug("TIMING:Start TYPE:Func DESC:replace_line_in_file RESULT:None")
        # Read the file line by line
    for line in fileinput.input(file_path, inplace=True):
        if line.strip().startswith(line_starts_with):
            line = new_line
        sys.stdout.write(line)
    logger.debug("TIMING:End TYPE:Func DESC:replace_line_in_file RESULT:Done")


# FUNC: Handlers for different press types
def handle_single_press(press_duration):
    logger.debug("TIMING:Start TYPE:Func DESC:handle_single_press RESULT:None")
    global context, Action, interrupt_main_process, voice_id
    if press_duration < SINGLE_PRESS_MAX:
        logger.info("Single Press Detected")
        voice_id = os.environ.get("ELEVENLABS_VOICE_ID")
        # Set the stop_audio_stream flag to True
        stop_audio_stream = True
        # Set the Action variable to equal Single
        Action = "Single"
        logger.debug(f"Single Press Loop: Action = {Action}")
        # Set the context variable to equal the value of the PROMPT_Guide global variable
        context = globals()['PROMPT_Guide']

        interrupt_main_process = True
        # Play the camera click sound
        wave_obj = sa.WaveObject.from_wave_file("./assets/wav/camera-capture.wav")
        play_obj = wave_obj.play()
        logger.debug("TIMING:End TYPE:Func DESC:handle_single_press RESULT:Single press executed")
    else:
        logger.debug("TIMING:End TYPE:Func DESC:handle_single_press RESULT:Longer than single press duration")


def handle_double_press():
    logger.debug("TIMING:Start TYPE:Func DESC:handle_double_press RESULT:None")
    global context, press_count, Action, stop_audio_stream, voice_id
    voice_id = os.environ.get("TOURIST_VOICE_ID")
    press_count = 0
    logger.info("Double Press Detected")
    # Implement double press action
    stop_audio_stream = True
    Action = "Single"
    logger.debug(f"Double Press Loop: Action = {Action}")
    # Set the context variable to equal the value of the PROMPT_Guide global variable
    context = globals()['PROMPT_Tourist']
    logger.debug(f"Double Press Loop: context = {context}")
    # Play the camera click sound
    wave_obj = sa.WaveObject.from_wave_file("./assets/wav/camera-capture.wav")
    play_obj = wave_obj.play()
    time.sleep(0.2)
    play_obj = wave_obj.play()
    logger.debug("TIMING:End TYPE:Func DESC:handle_double_press RESULT:Double press executed")

def handle_triple_press():
    logger.debug("TIMING:Start TYPE:Func DESC:handle_triple_press RESULT:None")
    global press_count, voice_id
    press_count = 0
    logger.info("Triple Press Detected")
    # Implement triple press action
    # Toggle the style based on the current style
    if os.environ.get('VISSTYLE') == 'Guide':
        os.environ['VISSTYLE'] = 'Tourist'
        voice_id = os.environ.get("TOURIST_VOICE_ID") 
        # Play the user warning audio file
        wave_obj = sa.WaveObject.from_wave_file("./assets/wav/You_have_selected_tourist_style_narration.wav")
        play_obj = wave_obj.play()
        logger.info("VISSTYLE set to Tourist")
        replace_line_in_file(".env", "export VISSTYLE", f"export VISSTYLE=\"{os.environ.get('VISSTYLE')}\"\n")

    elif os.environ.get('VISSTYLE') == 'Tourist':
        os.environ['VISSTYLE'] = 'Guide'
        voice_id = os.environ.get("ELEVENLABS_VOICE_ID") 
        # Play the user warning audio file
        wave_obj = sa.WaveObject.from_wave_file("./assets/wav/You_have_selected_guide_style_narration.wav")
        play_obj = wave_obj.play()
        logger.info("VISSTYLE set to Guide")
        replace_line_in_file(".env", "export VISSTYLE", f"export VISSTYLE=\"{os.environ.get('VISSTYLE')}\"\n")

    else:
        logger.warning("VISSTYLE environment variable not set")
        os.environ['VISSTYLE'] = 'Guide'
        logger.info("VISSTYLE set to Guide")
        logger.debug(f"VISSTYLE = {os.environ.get('VISSTYLE')}")
        # Play the user warning audio file
        wave_obj = sa.WaveObject.from_wave_file("./assets/wav/You_have_selected_guide_style_narration.wav")
        play_obj = wave_obj.play()
        replace_line_in_file(".env", "export VISSTYLE", f"export VISSTYLE=\"{os.environ.get('VISSTYLE')}\"\n")
    play_obj.wait_done()
    logger.debug("TIMING:End TYPE:Func DESC:handle_triple_press RESULT:Triple press executed")


def handle_long_press():
    logger.debug("TIMING:Start TYPE:Func DESC:handle_long_press RESULT:None")
    global press_count
    press_count = 0
    logger.info("Long Press Detected")
    # Implement long press action
    # Set the VISMODE environment variable
    if os.environ.get('VISMODE') == 'Single':
        os.environ['VISMODE'] = 'Continuous'
        # Play the user warning audio file
        wave_obj = sa.WaveObject.from_wave_file("./assets/wav/You_have_selected_continuous_mode.wav")
        play_obj = wave_obj.play()
        play_obj.wait_done()
        logger.info("VISMODE set to Continuous")
    elif os.environ.get('VISMODE') == 'Continuous':
        os.environ['VISMODE'] = 'Single'
        # Play the user warning audio file
        wave_obj = sa.WaveObject.from_wave_file("./assets/wav/You_have_selected_single_mode.wav")
        play_obj = wave_obj.play()
        logger.info("VISMODE set to Single")
    else:
        logger.warning("VISMODE environment variable not set")
        os.environ['VISMODE'] = 'Single'
        logger.info("VISMODE set to Single")
        logger.debug(f"VISMODE = {os.environ.get('VISMODE')}")
        # Play the user warning audio file
        wave_obj = sa.WaveObject.from_wave_file("./assets/wav/You_have_selected_single_mode.wav")
        play_obj = wave_obj.play()
    # Write the updated value to the .env file
    # replace_line_in_file(".env", "export VISMODE", f"export VISMODE=\"{os.environ.get('VISMODE')}\"\n")
    play_obj.wait_done()
    logger.debug("TIMING:End TYPE:Func DESC:handle_long_press RESULT:Long press executed")



# FUNC: GPIO event handler
def GPIO_press(channel):
    logger.debug("TIMING:Start TYPE:Func DESC:GPIO_press RESULT:None")
    #logger.info(f"{channel} Button was pressed!")
    #logger.debug(f"State of : {GPIO.input(channel)}")
    # Implement the action to be taken when the button is pressed
    on_key_press()
    # Wait for GPIO button to be released by checking the state of the button
    while GPIO.input(channel) == 0:
        pass
    on_key_release()
    logger.debug("TIMING:End TYPE:Func DESC:GPIO_press RESULT:GPIO press executed")

# Update the GPIO setup
# After running "sudo rpi-update && sudo apt update && sudo apt upgrade -y" on the Raspberry Pi, the GPIO following needs to be applied
# sudo chown root.gpio /dev/gpiomem
# sudo chmod g+rw /dev/gpiomem
logger.debug("TIMING:Start TYPE:Action DESC:If RPi load GPIO RESULT:None")
if is_running_on_raspberry_pi():
    GPIO.setmode(GPIO.BCM)
    GPIO.setup(17, GPIO.IN, pull_up_down=GPIO.PUD_UP)
    GPIO.add_event_detect(17, GPIO.FALLING, callback=GPIO_press, bouncetime=200)
logger.debug("TIMING:End TYPE:Action DESC:If RPi load GPIO RESULT:GPIO setup complete")

# FUNC: Update listen_for_key function to call button_callback on key press and release
def listen_for_key():
    # Add hooks for key press and release
    keyboard.hook(keyboard_event)

    # Loop to keep the thread alive
    while True:
        time.sleep(1)

# ACTION: Initialize the webcam
logger.debug("TIMING:Start TYPE:Action DESC:Initialize the webcam RESULT:None")
cap = cv2.VideoCapture(0)
# Check if the webcam is opened correctly
if not cap.isOpened():
    logger.warning("Failed to open webcam")
    raise IOError("Cannot open webcam")
    exit(1)
# Wait for the camera to initialize and adjust light levels
time.sleep(2)
logger.debug("TIMING:End TYPE:Action DESC:Initialize the webcam RESULT:Webcam initialized")

# ACTION: Create an OpenAI client
logger.debug("TIMING:Start TYPE:Action DESC:Create OpenAI client RESULT:None")
client = OpenAI()
logger.debug("TIMING:Start TYPE:Action DESC:Create OpenAI client RESULT:Created")

# # Set the ElevenLabs API key 
# set_api_key(os.environ.get("ELEVENLABS_API_KEY"))

# FUNC: Check if the internet is connected by pinging Google DNS
def check_internet(timeout=60, max_response_time=30):  # Default timeout is 60 seconds, and default max_response_time is 30ms
    logger.debug("TIMING:Start TYPE:Func DESC:Check the internet RESULT:None")
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
                logger.debug("TIMING:End TYPE:Func DESC:Check the internet RESULT:Good Internet connection detected")
                return True
            else:
                logger.warning(f"Slow internet response time: {ping_time} ms")
                
                # Play the user warning audio file
                wave_obj = sa.WaveObject.from_wave_file("./assets/wav/slow_internet.wav")
                play_obj = wave_obj.play()
                play_obj.wait_done()
                logger.debug("TIMING:End TYPE:Func DESC:Check the internet RESULT:Slow Internet connection detected")
                return True
        except subprocess.CalledProcessError:
            # This block is executed if the ping command fails
            # logger.warning("Ping command failed")
            logger.debug("TIMING:End TYPE:Func DESC:Check the internet RESULT:No Internet connection detected")

        # Sleep for a short duration before retrying
        time.sleep(1)

    logger.warning("No internet connection detected within the given time frame")
    # Play the user warning audio file
    wave_obj = sa.WaveObject.from_wave_file("./assets/wav/No_internet.wav")
    play_obj = wave_obj.play()
    play_obj.wait_done()
    return False

# FUNC: Capture an image from the webcam and return it as a base64 encoded string
def capture_image():
    global imagenum
    logger.debug("TIMING:Start TYPE:Func DESC:Capture image RESULT:None")

    # Clear the camera buffer by reading a few frames
    # This fixed the issue of the same image being used each time
    logger.debug("TIMING:Start TYPE:Sub Func DESC:Clear camera buffer RESULT:None")
    for _ in range(5):  # Adjust the range as needed
        cap.read()  # Read and discard frame
    logger.debug("TIMING:End TYPE:Sub Func DESC:Clear camera buffer RESULT:Camera buffer cleared")

    ret, frame = cap.read()
    if ret:

        # Mirror the image
        # frame = cv2.flip(frame, 1)

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
            logger.debug("TIMING:Start TYPE:Sub Func DESC:Write image to file RESULT:None")
            # Create a folder to store the frames if it doesn't exist
            folder = "frames"
            if not os.path.exists(folder):
                logger.debug("Creating folder to store frames")
                os.makedirs(folder, exist_ok=True)
            else:
                logger.debug("Folder to store frames already exists")
                delete_frames(folder)
            imagenum += 1
            path = f"{folder}/frame{imagenum}.jpg"
            logger.debug(f"Saving frame to {path}")
            cv2.imwrite(path, frame_jpg)
            logger.debug("TIMING:End TYPE:Sub Func DESC:Write image to file RESULT:File written to disk")
        # Delete the JPG version of the frame to save memory
        del frame_jpg
        # Return the base64 encoded image
        logger.debug("TIMING:End TYPE:Func DESC:Capture image RESULT:Completed and returned frame")
        return frame
    else:
        #logger.warning("Failed to capture image")
        logger.debug("TIMING:End TYPE:Func DESC:Capture image RESULT:Completed func but failed to capture image")

# FUNC: Calls the ElevenLabs API to generate an audio stream and plays it
def play_audio(text):
    logger.debug("TIMING:Start TYPE:Func DESC:play_audio RESULT:None")
    global stop_audio_stream, voice_id
    #logger.debug(f"play_audio func started - stop_audio_stream = {stop_audio_stream}")
    stop_audio_stream = False
    #logger.debug(f"play_audio func step 2 - stop_audio_stream = {stop_audio_stream}")
    set_api_key(os.environ.get("ELEVENLABS_API_KEY"))
    try:
        # Calls the ElevenLabs API to generate an audio stream
        logger.debug("TIMING:Start TYPE:Sub Func DESC:generate audio using Elevenlabs RESULT:None")
        # logger.debug(f"play_audio func step 3 - call generate from API - stop_audio_stream = {stop_audio_stream}")
        audio_stream = generate(
            text=text,
            voice=Voice(
                voice_id=(f"{voice_id}"),
                settings=VoiceSettings(stability=0.71, similarity_boost=0.5, style=0.0, use_speaker_boost=True)),
            model="eleven_turbo_v2",
            stream=True,
            stream_chunk_size=4096
        )
        logger.debug("TIMING:End TYPE:Sub Func DESC:generate audio using Elevenlabs RESULT:Audio generated")
        
        # Play audio stream without chunking
        logger.debug("TIMING:Start TYPE:Sub Func DESC:stream audio RESULT:None")
        # logging.debug(f"play_audio func step 5 - Playing stream - stop_audio_stream = {stop_audio_stream}")
        stream(audio_stream)
        logger.debug("TIMING:End TYPE:Sub Func DESC:stream audio RESULT:Audio streamed")
        
        # Reset the stop flag
        # logging.debug(f"play_audio func step 6 - Playing finished - stop_audio_stream = {stop_audio_stream}")
        stop_audio_stream = False
       
    except Exception as e:
        logger.error(f"Error in play_audio: {e}")

    logger.debug("TIMING:End TYPE:Func DESC:play_audio RESULT:Paying audio completed")


# FUNC: Generates the OpenAI "user" script
# TODO: Explore if this an optimal prompt for each request.
def generate_new_line(base64_image):
    logger.debug("TIMING:Start TYPE:Func DESC:generate_new_line RESULT:None")
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
    logger.debug("TIMING:Start TYPE:Func DESC:analyze_image RESULT:None")
    global context
    try:
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
        logger.debug("TIMING:End TYPE:Func DESC:analyze_image RESULT:Image analyzed")
        return response_text
    except Exception as e:
        # logger.error(f"Error in analyze_image: {e}")
        logger.debug(f"TIMING:End TYPE:Func DESC:analyze_image RESULT:{e}")
        raise

# Main single loop process
def single_loop():
    logger.debug("TIMING:Start TYPE:Func DESC:single_loop RESULT:None")
    global Action, script, timings, voice_id, context
    # Start the timers
    start_time = time.time()
    
    # Capture the image
    logger.debug("TIMING:Start TYPE:Action DESC:single_loop call capture RESULT:None")
    base64_image = capture_image()
    logger.debug("TIMING:End TYPE:Action DESC:single_loop call capture RESULT:Capture image completed")

    # logger.info(" Sending image for narration ...")
    logger.debug("TIMING:Start TYPE:Action DESC:single_loop call analyze_image RESULT:None")
    analysis_start_time = time.time()
    analysis = analyze_image(base64_image, script=script)
    timings['analysis'] += time.time() - analysis_start_time
    logger.debug(f"TIMING:Start TYPE:Action DESC:single_loop call analyze_image RESULT:{analysis}")
    del base64_image
    logger.info("🎙️ VisGuide says:")
    logger.info(analysis)

    playback_start_time = time.time()
    #play_audio_in_thread(analysis)
    # logging.debug(f"single_loop - calling play_audio")
    logger.debug("TIMING:Start TYPE:Action DESC:single_loop call play_audio RESULT:None")
    play_audio(analysis)
    timings['audio_playback'] += time.time() - playback_start_time
    logger.debug("TIMING:Start TYPE:Action DESC:single_loop call play_audio RESULT:Audio playback completed")

    script = script + [{"role": "assistant", "content": analysis}]
    logger.debug("TIMING:End TYPE:Func DESC:single_loop RESULT:Single loop executed")


# Main loop
def main():
    global Action, script, timings, interrupt_main_process
    script = []
    timings = {'image_encoding': 0, 'analysis': 0, 'audio_playback': 0}
    # Set up keyboard event listener only if running on a non-Raspberry Pi device
    if not is_running_on_raspberry_pi():
        logger.debug("Running on a non-Raspberry Pi device, setting up keyboard event listener")
        listener_thread = threading.Thread(target=listen_for_key, daemon=True) # This makes the thread exit when the main program exits
        listener_thread.start()

    while True:
        # Check if the main process needs to be interrupted
        if interrupt_main_process:
            # Reset necessary variables or perform any cleanup
            Action = "None"
            script = []
            timings = {'image_encoding': 0, 'analysis': 0, 'audio_playback': 0}

            # Reset the interrupt flag
            interrupt_main_process = False

            # Optionally, add a delay or logging
            logger.info("Restarting main process...")
            time.sleep(1)

        while True:
            try:
                # If environment variable = single, run single loop
                # logger.debug(f"Main Loop: Action = {Action}")
                # logger.debug(f"Main Loop: VISMODE = {os.environ.get('VISMODE')}")
                if os.environ.get('VISMODE') == 'Single':
                    # Wait for the button press
                    if Action == "Single":
                        single_loop()
                        Action = "None"
                # If environment variable = continuous, run continuous loop
                elif os.environ.get('VISMODE') == 'Continuous':
                    single_loop()
                    time.sleep(5)
                time.sleep(1)
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

# Reload the camera driver
# logger.debug("TIMING:Start TYPE:Action DESC:Reload camera driver RESULT:None")
# reload_camera_driver("bcm2835-v4l2")
# logger.debug("TIMING:End TYPE:Action DESC:Reload camera driver RESULT:Camera driver reloaded")
    
# Check for internet connectivity by pinging Google DNS
while not check_internet(timeout=60, max_response_time=100):
    logger.info("Waiting for internet connection...")
    time.sleep(1)

# Visguide is ready
# Play audio file ./assets/visguide_is_ready.wav to indicate that VisGuide app is ready
# load the wav audio file
wave_obj = sa.WaveObject.from_wave_file("./assets/wav/VisGuide_is_ready.wav")
# play the audio file
play_obj = wave_obj.play()
print("VisGuide is ready")

if __name__ == "__main__":
    main()
