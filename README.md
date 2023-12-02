# VisGuide
This is a solution to provide partially sighted and blind people with guidance and to avoid obstacles and risk. This currently provides a description of whats in front, notable items and issues. Future versions will enable interactivity such as the user being able to ask "where is the bus stop" or "can you see the toilets".


# Setup

* Install instructions are focused on VisGuide on RPI Zero 2. 
* They do also work for MAC but you would be better using Conda in place of Virtualenv
* If deploying on RPi Zero, start with a new "Raspberry Pi OS of Raspberry Pi OS (Legacy, 64-bit) Full". 32-bit Lite OS will NOT work.

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
cd visguide
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
#### Narrative Prompts
The prompts used to create the narrative are either used from the environment variable CONTEXT or a default defined in the code if CONTEXT isn't populated. Sample prompts are stored in prompts.txt

To use either your own, or one of the example prompts, use:\
**_NOTE:_** Don't forget to use the quote marks
```bash
export CONTEXT="<prompt>"
```
### Run the main process
```bash
python visguide.py
```
### Logging & Debug
Python logging is implemented and there are two command line options. If you add "-v" to the command line then INFO level logging is applied with millisecond timing. the second option is "-d" or "--debug" with enables detailed debug logging.\
> **_NOTE_**: Logging is currently to console only as dont want to slow down the end the end process with writing to disk, or in the case of the RPi Zero, the SD card which is slow.

# VisGuide Development Notes
> visguide.py runs each step of the process locally which is inefficient and creates latency. visguide-api.py uses the external VisGuide service which speeds up the process to provide a more realtime service for the user. Use visguide.py for now and this document will be updated once the VisGuide API is fully working.

> Testing was performed using a Plantronics BT Headset which worked great. To add this it was easiest to use the Raspberry Pi desktop to add it like a normal consumer BT device. It now auto connects to both the mobile and VisGuide when you power it on. Future versions will work with other headsets and also allow the user to press the "talk" button and speak commands to VisGuide.

> Costs on OpenAI and Elevenlabs need investigating. Also need to explore using our own AI services to manage costs, reduce latency and to preserve privacy. This could by Ollama models behind an API gateway or maybe using "themartian" for routing.

> Speeding it up: The next iteration of dev will take two specific approaches to speed up the user experience. **_First;_** grabbing the camera image will become part of the main visguide.py to negate the need for writing the image to disk and just using it from memory and the **_second;_** is to chunk the narration into sentences and send each to ElevenLabs separately to provide the WAV audio. This will hopefully result in a faster start of narration and whilst the first sentence is being played, the remainder is being rendered ready for playing.

> Hallucination: Whilst testing is has become apparent that there is fundamental hallucination happening as it described me as wearing glasses but I'm not! I need to explore prompts that prevent such fundamental hallucination. What if it hallucinates and says that its safe to cross the road and it isn't....

> MAC vs RPi: I need to explore how to get the script to ignore errors and issues relating to RPi when running on a MAC.

![Picture of VisGuide and Headset](https://github.com/hirsts/visguide/blob/main/image.jpeg?raw=true)
