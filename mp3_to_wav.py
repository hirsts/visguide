
import os
from pydub import AudioSegment

# Directory where your MP3 files are stored
source_directory = "assets/mp3"

# Directory where you want to store the WAV files
destination_directory = "assets/wav"

# Create the destination directory if it doesn't exist
if not os.path.exists(destination_directory):
    os.makedirs(destination_directory)

# Loop through all files in the source directory
for filename in os.listdir(source_directory):
    if filename.endswith(".mp3"):
        mp3_path = os.path.join(source_directory, filename)
        wav_path = os.path.join(destination_directory, filename.replace(".mp3", ".wav"))

        # Convert mp3 file to wav file
        sound = AudioSegment.from_mp3(mp3_path)
        sound.export(wav_path, format="wav")
        print(f"Converted {filename} to WAV and saved in {destination_directory}")
