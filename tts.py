import os
from dotenv import load_dotenv, find_dotenv

import requests
import json
import base64

load_dotenv(find_dotenv())

devo = """Philippians 4 13.

  I can do all this through him who gives me strength.

  In this powerful verse, we are reminded that through Christ, we have the strength to overcome any challenge or obstacle.
  Our faith in Him empowers us to face each day with confidence and courage. Let us lean on His promises and trust in His
  provision."""

VOICE_ID = "onwK4e9ZLuTAKqWW03F9"  # onwK4e9ZLuTAKqWW03F9 TxGEqnHWrfWFTfGW9XjX
XI_API_KEY = os.getenv("XI_API_KEY")

url = f"https://api.elevenlabs.io/v1/text-to-speech/{VOICE_ID}/with-timestamps"

headers = {
  "Content-Type": "application/json",
  "xi-api-key": XI_API_KEY
}

data = {
  "text": ( devo ),
  "model_id": "eleven_multilingual_v2",
  "voice_settings": {
    "stability": 0.5,
    "similarity_boost": 0.75
  }
}

response = requests.post(
  url,
  json=data,
  headers=headers,
)

if response.status_code != 200:
  print(f"Error encountered, status: {response.status_code}, "
    f"content: {response.text}")
  quit()

# convert the response which contains bytes into a JSON string from utf-8 encoding
json_string = response.content.decode("utf-8")

# parse the JSON string and load the data as a dictionary
response_dict = json.loads(json_string)

# the "audio_base64" entry in the dictionary contains the audio as a base64 encoded string, 
# we need to decode it into bytes in order to save the audio as a file
audio_bytes = base64.b64decode(response_dict["audio_base64"])

with open('mp/test_voice.mp3', 'wb') as f:
  f.write(audio_bytes)

# the 'alignment' entry contains the mapping between input characters and their timestamps
# print(response_dict['alignment'])

characters = response_dict['alignment']['characters']
start_times = response_dict['alignment']['character_start_times_seconds']
end_times = response_dict['alignment']['character_end_times_seconds']

sub_start_times = []
sub_end_times = []
start_of_word_reached = False
for char, start, end in zip(characters, start_times, end_times):
  if char.isspace() and start_of_word_reached:
    sub_end_times.append(end)
    start_of_word_reached = False

  elif not char.isspace() and not start_of_word_reached:
    sub_start_times.append(start)
    start_of_word_reached = True

  print(f"[{char}, {start}, {end}] ", end='')

sub_end_times.append(end_times[-1])  # end time of last word

for i in sub_start_times:
  print(f'{i}   ', end='')
for i in sub_end_times:
  print(f'{i}   ', end='')


 # audio = eleven_client.generate(
  #   text = input_text,
    
  #   voice = "Daniel"     # Daniel: onwK4e9ZLuTAKqWW03F9,    Josh: TxGEqnHWrfWFTfGW9XjX,    James: ZQe5CZNOzWyzPSCn5a3c    Michael: flq6f7yk4E4fJM5XTYuZ
  # )

  # save(audio, "mp/voice_over.mp3")

  # # slow down the audio
  # audio_clip = AudioFileClip("mp/voice_over.mp3")
  # slowed_clip = audio_clip.fx(vfx.speedx, .9)
  # slowed_clip.write_audiofile("mp/slow_voice_over.mp3")


  # audio_clip.close()
  # slowed_clip.close()