import os
import argparse
import logging
from logging.handlers import SysLogHandler
from dotenv import load_dotenv
from elevenlabs import Voice, VoiceSettings, set_api_key, generate, stream

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

# load the environment variables from the .env file if they are not set
if 'OPENAI_API_KEY' not in os.environ or 'ELEVENLABS_API_KEY' not in os.environ or 'ELEVENLABS_VOICE_ID' not in os.environ:
        # If not set, check for .env file and load it
        dotenv_path = os.path.join(os.path.dirname(__file__), '.env')
        if os.path.exists(dotenv_path):
            load_dotenv(dotenv_path)
            logger.info('.env file found and loaded')
        else:
            logger.warning('Required environment variables are not set and no .env file found')


# Set your API key
set_api_key(os.environ.get("ELEVENLABS_API_KEY"))
voice_id = os.environ.get("ELEVENLABS_VOICE_ID")

def text_stream():
    yield "Hi there, I'm Eleven. "
    yield "I'm a text to speech API and "
    yield "I can speak in many languages. "
    yield "I can even speak in different voices "
    yield "and this is using the elevenlabs turbo model. "

audio_stream = generate(
    text=text_stream(),
    voice=Voice(
        voice_id=voice_id,
        settings=VoiceSettings(stability=0.71, similarity_boost=0.5, style=0.0, use_speaker_boost=True)),
    model="eleven_turbo_v2",
    stream=True
)

logging.info("Audio stream generated")
stream(audio_stream)