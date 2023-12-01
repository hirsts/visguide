import os
from openai import OpenAI
import base64
import json
import time
import simpleaudio as sa
import errno
from elevenlabs import generate, play, set_api_key, voices

### This is visguide-api.py ###




def encode_image(image_path):
    while True:
        try:
            with open(image_path, "rb") as image_file:
                return base64.b64encode(image_file.read()).decode("utf-8")
        except IOError as e:
            if e.errno != errno.EACCES:
                # Not a "file in use" error, re-raise
                raise
            # File is being written to, wait a bit and retry
            time.sleep(0.1)

# Define a function called analyze_image that posts a base64 image and parameters the VisGuide API
def analyze_image(base64_image, parameters=None, script=None):
    # Use the CONTEXT environment variable if it's set, otherwise use the default prompt
    context = os.environ.get('CONTEXT', """
        You are a guide for blind people and your goal is to help them to understand whats happening in the picture. You also need to advise of major features along with an approximate distance in metres.    
        The image is facing forward from the user and assume that the user is traveling in the direction of the image. Advise them of any obstacles in their path and any risks they should be aware of.
        """)
    # Use the PARAMETERS environment variable if it's set, otherwise use the default prompt

    parameters = os.enviro.get('VISGUIDE_PARAMETERS', {
        "max_tokens": 64,
        "temperature": 0.8,
        "top_p": 1,
        "frequency_penalty": 0.0,
        "presence_penalty": 0.0,
        "best_of": 1,
    })
    # Use the VISGUIDE_API_KEY environment variable if it's set, otherwise use the default prompt
    api_key = os.environ.get('VISGUIDE_API_KEY', "YOUR_API_KEY_HERE")
    # Use the VISGUIDE_API_URL environment variable if it's set, otherwise use the default prompt
    api_url = os.environ.get('VISGUIDE_API_URL', "https://hook.us1.make.com/6i6zpz27o4351bda655awavqsuuqvr31")
    # Use the VISGUIDE_API_MODEL environment variable if it's set, otherwise use the default prompt
    model = os.environ.get('VISGUIDE_API_MODEL', "visguide")
    # Use the VISGUIDE_API_VERSION environment variable if it's set, otherwise use the default prompt
    version = os.environ.get('VISGUIDE_API_VERSION', "v1")
    # Use the VISGUIDE_API_TIMEOUT environment variable if it's set, otherwise use the default prompt
    timeout = os.environ.get('VISGUIDE_API_TIMEOUT', 30)

    # Send the request to the VisGuide API
    response = requests.post(
        f"{api_url}",
        json={
            "context": context,
            "parameters": parameters,
            "script": script,
            "image": base64_image,
        },
        headers={"Authorization": f"Bearer {api_key}"},
        timeout=timeout,
    )

    # Return the response
    return response.json()

def main():

    while True:
        # path to your image
        image_path = os.path.join(os.getcwd(), "./frames/frame.jpg")

        # getting the base64 encoding
        base64_image = encode_image(image_path)

        # analyze posture
        print("👀 Sending image to VisGuide API......")
        narrative = analyze_image(base64_image, script=script)

        print("🎙️ VisGuide says:")
        print(narrative.text)

        play_audio(analysis)

        script = script + [{"role": "assistant", "content": analysis}]

        # wait for 5 seconds
        time.sleep(5)


if __name__ == "__main__":
    main()
