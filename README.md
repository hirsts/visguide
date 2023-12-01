# VisGuide
This is a solution to provide partially sighted and blind people with guidance and to avoid obstacles and risk. This currently provides a description of whats in front and notable items and issues. Future versions will enable interactivity such as the user being able to ask "where is the bus stop" or "can you see the toilets".

> visguide.py runs each step of the process locally which is inefficient and creates latency. visguide-api.py uses the external VisGuide service which speeds up the process to provide a more realtime service for the user. Use visguide.py for now and this document will be updated once the VisGuide API is fully working.

> Testing was performed using a Plantronics BT Headset which worked great. To add this it was easiest to use the Raspberry Pi desktop to add it like a normal consumer BT device. It now auto connects to both the mobile and VisGuide when you power it on. Future versions will work with other headsets and also allow the user to press the "talk" button and speak commands to VisGuide.

![Picture of VisGuide and Headset](https://github.com/hirsts/visguide/blob/main/image.jpeg?raw=true)

# Setup

* Install instructions for VisGuide on RPI Zero 2
* Start with a new "Raspberry Pi OS of Raspberry Pi OS (Legacy, 64-bit) Full"

### Increase swap to 2048
This is overkill and could be smaller but I had 64GB to play with. You might not NEED this.
```bash
sudo nano /etc/dphys-swapfile
```

### Expand root file system to entire disk / sd
```bash
sudo raspi-config --expand-rootfs
sudo reboot
```


### Update the system and install fundamental packages
Some of these packages might not be needed as they are used for compiling and building but its ok to have them for now.
```bash
sudo apt update && sudo apt upgrade
sudo apt install python3-virtualenv git build-essential zlib1g-dev libncurses5-dev libgdbm-dev libnss3-dev libssl-dev libreadline-dev libffi-dev python3-dev libasound2-dev
pip install glances
```

### Get the VisGuide project and install dependencies
NOTE: The last step can take a while but shouldn't need to compile anything. If it take hours, something is wrong, maybe you started with the wrong RPi image.
```bash
git clone https://github.com/hirsts/visguide
cd visguide
virtualenv visguide-env
source visguide-env/bin/activate
python -m pip install -r requirements.txt
```

### Start capturing frames ready for processing
This will start capturing the image from the camera and overwrite the frame/frame.jpg image each time. The image size is small to try and minimise traffic and latency.
```bash 
python capture.py
```

### Setup the main VisGuide process
open new terminal session and activate the python environment
```bash
source visguide-env/bin/activate
```
### Elevenlabs

* Clone or choose a voice in eleven labs
* Get the voice ID from the ElevenLabs VoiceLab
* Either run the below or update the .env file and run `source .env`

**_NOTE:_** Don't miss using the quotes
```bash
export ELEVENLABS_API_KEY="<apikey>"
export ELEVENLABS_VOICE_ID="<voice-id>"
```

### OpenAI
You will need an API Key from OpenAI and you can follow the instructions from here to get it:\
 https://www.maisieai.com/help/how-to-get-an-openai-api-key-for-chatgpt

Once you have your key either run the below or update the .env file and rerun `source .env`\
**_NOTE:_** Don't miss using the quotes
```bash
export OPENAI_API_KEY="<apikey>"
```


### Run the main process
```bash
python visguide.py
```