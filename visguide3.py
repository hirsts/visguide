import argparse
import os
import RPi.GPIO as GPIO
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


### Setup the button
def button_callback(channel):
    logger.info("Button was pushed!")
    # Implement the action to be taken when the button is pressed

# Setup GPIO Pins
GPIO.setmode(GPIO.BCM)
GPIO.setup(17, GPIO.IN, pull_up_down=GPIO.PUD_UP)
GPIO.add_event_detect(17, GPIO.FALLING, callback=button_callback, bouncetime=200)


### Initialize the webcam
cap = cv2.VideoCapture(0)
# Check if the webcam is opened correctly
if not cap.isOpened():
    raise IOError("Cannot open webcam")
# Wait for the camera to initialize and adjust light levels
time.sleep(2)

# Create an OpenAI client
client = OpenAI()

# Set the ElevenLabs API key 
set_api_key(os.environ.get("ELEVENLABS_API_KEY"))

# Define a function to encode an image as base64
def encode_image(image_path):
    while True:
        try:
            with open(image_path, "rb") as image_file:
                return base64.b64encode(image_file.read()).decode("utf-8")
        except IOError as e:
            if e.errno != errno.EACCES:
                logger.error(f"IOError encountered: {e}")
                raise
            logger.debug("Waiting for file to become accessible...")
            time.sleep(0.1)

def play_audio(text):
    try:
        audio = generate(text, voice=os.environ.get("ELEVENLABS_VOICE_ID"))

        unique_id = base64.urlsafe_b64encode(os.urandom(30)).decode("utf-8").rstrip("=")
        dir_path = os.path.join("narration", unique_id)
        os.makedirs(dir_path, exist_ok=True)
        file_path = os.path.join(dir_path, "audio.wav")

        with open(file_path, "wb") as f:
            f.write(audio)

        play(audio)
    except Exception as e:
        logger.error(f"Error in play_audio: {e}")

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
            start_time = time.time()
            image_path = os.path.join(os.getcwd(), "./frames/frame.jpg")

            base64_image = encode_image(image_path)
            timings['image_encoding'] += time.time() - start_time

            logger.info("👀 VisGuide is watching...")
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
        # Add any cleanup code here
        finally:
            # This block will execute whether an exception occurred or not
            GPIO.cleanup()  # Clean up GPIO to ensure no resources are left open
            # Add any other cleanup code here if needed
            exit(0)

    # Report timings
    for operation, time_taken in timings.items():
        logger.info(f"{operation}: {time_taken:.2f} seconds")

if __name__ == "__main__":
    main()
