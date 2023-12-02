import argparse
import os
from logging.handlers import SysLogHandler
from dotenv import load_dotenv
import cv2
from PIL import Image
import numpy as np
import base64
import time
import logging
import errno
import simpleaudio as sa
from openai import OpenAI
from elevenlabs import generate, play, set_api_key, voices

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

# Setup GPIO Pins
if is_running_on_raspberry_pi():
    # Setup GPIO Pins only if on Raspberry Pi
    GPIO.setmode(GPIO.BCM)
    GPIO.setup(17, GPIO.IN, pull_up_down=GPIO.PUD_UP)
    GPIO.add_event_detect(17, GPIO.FALLING, callback=button_callback, bouncetime=200)

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

# Setup the button
def button_callback(channel):
    logger.info("Button was pushed!")
    # Implement the action to be taken when the button is pressed

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

        
        
        # If debugging, save the frame as an image file
        # if args.debug:
            # Create a folder to store the frames if it doesn't exist
            # folder = "frames"
            # if not os.path.exists(folder):
            #     logger.debug("Creating folder to store frames")
            #     os.makedirs(folder, exist_ok=True)
            # path = f"{folder}/frame.jpg"
            # logger.debug(f"Saving frame to {path}")
            # cv2.imwrite(path, frame)


def play_audio(text):
    try:
        # Calls the ElevenLabs API to generate audio and the resulting WAV is the variable "audio"
        audio = generate(text, voice=os.environ.get("ELEVENLABS_VOICE_ID"))

        # unique_id = base64.urlsafe_b64encode(os.urandom(30)).decode("utf-8").rstrip("=")
        # dir_path = os.path.join("narration", unique_id)
        # os.makedirs(dir_path, exist_ok=True)
        # file_path = os.path.join(dir_path, "audio.wav")

        # with open(file_path, "wb") as f:
        #    f.write(audio)

        play(audio)
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

    while True:
        try:
            # Start the timers
            start_time = time.time()

            # Get the image
            # image_path = os.path.join(os.getcwd(), "./frames/frame.jpg")

            # Encode the image as base64
            # base64_image = encode_image(image_path)
            # timings['image_encoding'] += time.time() - start_time

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
            GPIO.cleanup()
            cap.release()
            cv2.destroyAllWindows()
            exit(0)

    # Report timings
    for operation, time_taken in timings.items():
        logger.info(f"{operation}: {time_taken:.2f} seconds")

if __name__ == "__main__":
    main()
