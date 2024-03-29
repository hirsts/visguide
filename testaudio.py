import os
import io
import argparse
import logging
import multiprocessing
import threading
from logging.handlers import SysLogHandler
import simpleaudio as sa
from dotenv import load_dotenv
from elevenlabs import play, Voice, VoiceSettings, set_api_key, generate, stream

# Get options from command line arguments
parser = argparse.ArgumentParser()
parser.add_argument("-v", "--verbose", action="store_true")
parser.add_argument("-d", "--debug", action="store_true")
parser.add_argument("-s", "--syslog", action="store_true")
args = parser.parse_args()

# stop_event = threading.Event()

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

# load the environment variables from the .env file if they are not set
if 'OPENAI_API_KEY' not in os.environ or 'ELEVENLABS_API_KEY' not in os.environ or 'ELEVENLABS_VOICE_ID' not in os.environ:
        # If not set, check for .env file and load it
        dotenv_path = os.path.join(os.path.dirname(__file__), '.env')
        if os.path.exists(dotenv_path):
            load_dotenv(dotenv_path)
            logger.info('.env file found and loaded')
        else:
            logger.warning('Required environment variables are not set and no .env file found')

# def play_stream(audio_stream):
#     global stop_audio_stream
#     try:
#         while not stop_event.is_set():
#             try:
#                 stream(audio_stream)
#             except Exception as e:
#                 logger.error(e)
#                 break

#     finally:
#         # Close the audio stream once done
#         audio_stream.close()




# class CustomThread(threading.Thread):
#     def __init__(self, *args, **kwargs):
#         super(CustomThread, self).__init__(*args, **kwargs)
#         self._stopper = threading.Event()
    
#     def stop(self):
#         self._stopper.set()

#     def stopped(self):
#         return self._stopper.is_set()

#     def run(self):
#         while not self.stopped():
#           stream(audio_stream)

# Set your API key
set_api_key(os.environ.get("ELEVENLABS_API_KEY"))
voice_id = os.environ.get("ELEVENLABS_VOICE_ID")

text = "Hi there, I'm Eleven. I'm a text to speech API and I can speak in many languages. I can even speak in different voices and this is using the elevenlabs turbo model. "

# default output: mp3_44100_128
audio_stream = generate(
    text=text,
    voice=Voice(
        voice_id=voice_id,
        settings=VoiceSettings(stability=0.71, similarity_boost=0.5, style=0.0, use_speaker_boost=True)),
    model="eleven_turbo_v2",
    stream=True,
    stream_chunk_size=4096
)

# if __name__ == "__main__":
#     t = CustomThread()
#     t.start()
#     # create a loop to wait for user input
#     while True:
#         # get the user input
#         user_input = input("Enter 'q' to quit: ")
#         # check if the user input is 'q'
#         if user_input == 'q':
#             logger.info("Stopping audio stream")
#             t.stop()
#         break

# # Multiprocessing to play the audio in the background
# audio_thread = threading.Thread(target=stream, args=(audio_stream,))
# audio_thread.start()

# Use SimpleAudio to play the audio stream
audio_bytes = io.BytesIO(audio_stream)
play_obj = sa.play_buffer(audio_bytes, 1, 2, 44100)


# wave_obj = sa.WaveObject.from_wave_read(audio_stream)
# play_obj = wave_obj.play()

# create a loop to wait for user input
while True:
    # get the user input
    user_input = input("Enter 'q' to quit: ")
    # check if the user input is 'q'
    if user_input == 'q':
        logger.info("Stopping audio stream")
        play_obj.stop()
    break