# VisGuide
This is a solution to provide partially sighted and blind people with guidance and to avoid obstacles and risk

# Setup

## Install instructions for VisGuide on RPI Zero 2
## Start with a new "Raspberry Pi OS of Raspberry Pi OS (Legacy, 64-bit) Full"

### Increase swap to 2048. This is overkill and could be smaller but I had 64GB to play with
sudo nano /etc/dphys-swapfile
### Expand root file system to entire disk / sd
sudo raspi-config --expand-rootfs
sudo reboot

### Updata the system and install fundamental packages
sudo apt update && sudo apt upgrade
sudo apt install python3-virtualenv git build-essential zlib1g-dev libncurses5-dev libgdbm-dev libnss3-dev libssl-dev libreadline-dev libffi-dev python3-dev libasound2-dev
pip install glances

### Get the VisGuide project and install dependencies
git clone https://github.com/hirsts/visguide
cd visguide
virtualenv visguide-env
source visguide-env/bin/activate
which python
python -m pip install -r requirements.txt

### Start capturing frames ready for processing
python capture.py

### Run the main VisGuide process
open new terminal
source visguide-env/bin/activate
#### clone or choose a voice in eleven labs
#### get the voice ID from the ElevenLabs VoiceLab
#### Either run the below or update the .env file and run `source .env`
export ELEVENLABS_API_KEY="{key}"
export OPENAI_API_KEY="{key}"
export ELEVENLABS_VOICE_ID="{key}"


### Run the main process
python narrator.py