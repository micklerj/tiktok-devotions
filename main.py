import os
from openai import OpenAI
from dotenv import load_dotenv, find_dotenv
from moviepy.editor import VideoFileClip, AudioFileClip, TextClip, CompositeVideoClip, CompositeAudioClip, vfx
import random
from elevenlabs.client import ElevenLabs
import moviepy.config as moviepy_config
import re
import requests
import json
import base64

# Set the path to the ImageMagick executable
moviepy_config.change_settings({"IMAGEMAGICK_BINARY": "C:/Program Files/ImageMagick-7.1.1-Q16-HDRI/magick.exe"})


prompt1 = """
  please generate a random devotion as if it is written by gen z based on a random Bible passage.   

  guidelines to formatting:  
  - choose a passage of 1 or 2 Bible verses, and NO more. Do not choose any of these passages: 
"""
prompt2 = """
  - output the name of the book of the Bible, followed by the chapter number,
  followed by the verse number(s) that you choose, followed by a period. If multiple verses are
  chosen, output the word "through" between the 1st and 2nd selected verse
  numbers (example: Mark 4 1 through 2.).
  - output the verse(s).
  - output an encouraging devotion consisting of exactly 4 sentences using gen z vocabulary and slang.

  example output: 
  John 3 16 through 17.  

  For God so loved the world that he gave his one and only Son, that whoever
  believes in him shall not perish but have eternal life. For God did not send
  his Son into the world to condemn the world, but to save the world through him.

  Yo, these verses are all about how insanely deep God's love is for all of us.
  It's like, no matter who you are or what you've done, His love is always there.
  Through Jesus, God's giving us this epic gift of salvation, not to judge or condemn
  us, but to bring us into a life that's full of eternal vibes and total freedom. 
  Let's vibe with this amazing love, spread it around, and live in the light of His grace.
"""

load_dotenv(find_dotenv())
client = OpenAI()
eleven_client = ElevenLabs(
  api_key=os.getenv("XI_API_KEY"), 
)


# timestamps for subtitles
sub_start_times = []
sub_end_times   = []

# generate the devotion with chatGPT
def get_devotion():

  # check the previous passages that we have already used
  previous_devos = ""
  with open('stats.txt', 'r') as file:
    is_passage = False
    for line in file:
      if line.strip() == "---------------- end of passages ----------------":
        is_passage = False
      if is_passage:
        previous_devos += line.strip() + ", "
      if line.strip() == "----------- previously used passages: -----------":
        is_passage = True

  prompt = prompt1 + previous_devos[:-2] + prompt2
  
  # TODO: make loop to double check that a repeat passage was not chosen

  # api call to generate the devotion
  response = client.chat.completions.create(
    model="gpt-3.5-turbo",
    temperature=0.8,
    max_tokens=250,
    messages=[
      {"role": "system", "content": "You are a helpful assistant."},
      {"role": "user", "content": prompt}
    ]
  )
  devotion = response.choices[0].message.content

  # add passage to pool of already used passages so we dont re-use
  lines = []
  with open('stats.txt', 'r') as file:
    for line in file:
      if line.strip() == "---------------- end of passages ----------------":
        lines.append(devotion.split('.')[0] + "\n")
      lines.append(line)
  
  with open("stats.txt", 'w') as file:
    file.writelines(lines)

  return devotion

# generate the voice over with 11 labs    and    save timestamps
def get_voice_over(input_text, voice_over_path):

  XI_API_KEY = os.getenv("XI_API_KEY")

  # choose random voice
  voice_choice = random.randint(1, 3)
  speaker_name = ""
  if voice_choice == 1:
    VOICE_ID = "onwK4e9ZLuTAKqWW03F9"    # Daniel 
    speaker_name = "Daniel"
  elif voice_choice == 2:
    VOICE_ID = "TxGEqnHWrfWFTfGW9XjX"    # Josh 
    speaker_name = "Josh"
  else:
    VOICE_ID = "flq6f7yk4E4fJM5XTYuZ"    # Michael 
    speaker_name = "Michael"

  # update stats.txt
  lines = []
  with open('stats.txt', 'r') as file:
    for line in file:
      if line.strip():
        if line.strip().split()[0] == speaker_name:
          cnt = int(line.strip().split()[-1])             # previous count
          new_line = line.strip()[:(len(str(cnt)) * -1)]  # remove previous count
          cnt += 1                                        # increment count
          lines.append(new_line + str(cnt) + "\n")        # updated line with new count 
          continue
      lines.append(line)
  
  with open("stats.txt", 'w') as file:
    file.writelines(lines)


  url = f"https://api.elevenlabs.io/v1/text-to-speech/{VOICE_ID}/with-timestamps"

  headers = {
    "Content-Type": "application/json",
    "xi-api-key": XI_API_KEY
  }

  data = {
    "text": ( input_text ),
    "model_id": "eleven_multilingual_v2",
    "voice_settings": {
      "stability": 0.25,
      "similarity_boost": 0.65
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

  # save the voice over mp3 file
  with open(voice_over_path, 'wb') as f:
    f.write(audio_bytes)

  # the 'alignment' entry contains the mapping between input characters and their timestamps
  characters = response_dict['alignment']['characters']
  start_times = response_dict['alignment']['character_start_times_seconds']
  end_times = response_dict['alignment']['character_end_times_seconds']

  # save timestamps
  start_of_word_reached = False
  for char, start, end in zip(characters, start_times, end_times):
    if (char.isspace() or char == '-' or char == '—') and start_of_word_reached:
      sub_end_times.append(end) 
      start_of_word_reached = False

    elif not char.isspace() and not start_of_word_reached:
      sub_start_times.append(start)
      start_of_word_reached = True

    # print(f"[{char}, {start}, {end}] ", end='')

  sub_end_times.append(end_times[-1])  # end time of last word

# create the whole video
def create_video(devo, video_path, audio_path, music_path, output_path):
  audio_clip = AudioFileClip(audio_path)
  audio_length = int(audio_clip.duration) + 1

  background_video = VideoFileClip(video_path)
  vid_length = background_video.duration

  if vid_length < audio_length:
    print("Error: Video is shorter than audio_length.")
    return
  start = random.randint(0, int(vid_length) - int(audio_length))
  end = start + audio_length

  background_video = background_video.subclip(start,end)

  # overlay the music and speech on the video
  music = AudioFileClip(music_path)
  music = music.volumex(0.1)
  music_length = music.duration
  start = random.randint(0, int(music_length) - int(audio_length))
  end = start + audio_length
  music = music.subclip(start, end)
  audio_clip = CompositeAudioClip([audio_clip, music])
  background_video = background_video.set_audio(audio_clip)

  # crop
  vid_h = background_video.h
  vid_w = vid_h / 16 * 9
  background_video = background_video.crop(width=vid_w, height=vid_h, x_center=background_video.w/2, y_center=background_video.h/2)

  # add subtitles
  # TODO: maybe have multiple words displayed at a time
  subs = []
  devo_words = re.findall(r"\b[\w']+\b", devo)
  for word, start, end in zip(devo_words, sub_start_times, sub_end_times):

    txt_clip = TextClip(
      word,
      fontsize=45,
      font="Arial-Bold",
      color='white',
      stroke_color='black',
      stroke_width=2
    )
    txt_clip = txt_clip.set_start(start).set_end(end).set_position(('center', 'center'))
    subs.append(txt_clip)

  background_video = CompositeVideoClip([background_video] + subs)

  # save the output and close clips
  background_video.write_videofile(output_path)
  audio_clip.close()
  background_video.close()
  music.close()
  for clip in subs:
    clip.close()
  
  # update stats.txt
  lines = []
  with open('stats.txt', 'r') as file:
    for line in file:
      if line.strip():
        if line.strip().split()[0] == music_path[3:-4]:
          cnt = int(line.strip().split()[-1])             # previous count
          new_line = line.strip()[:(len(str(cnt)) * -1)]  # remove previous count
          cnt += 1                                        # increment count
          lines.append(new_line + str(cnt) + "\n")        # updated line with new count 
          continue
        if line.strip().split()[0] == video_path[3:-4]:
          cnt = int(line.strip().split()[-1])             # previous count
          new_line = line.strip()[:(len(str(cnt)) * -1)]  # remove previous count
          cnt += 1                                        # increment count
          lines.append(new_line + str(cnt) + "\n")        # updated line with new count 
          continue
      lines.append(line)
  
  with open("stats.txt", 'w') as file:
    file.writelines(lines)



if __name__ == "__main__":

  # choose random background video
  random_num = random.randint(1, 3)
  background_choice = str(random_num)
  video_path = "mp/background" + background_choice + ".mp4"                     # original source for background video
  
  # choose random background music
  random_num = random.randint(1, 2)
  music_choice = str(random_num)
  music_path = "mp/music" + music_choice + ".mp3"                               # rource for background music
  
  voice_over_path = "mp/voice_over.mp3"
  output_path     = "mp/output7.mp4"

  devo = get_devotion()
  print(devo)
  get_voice_over(devo, voice_over_path)                                         # creates "mp/voice_over.mp3"
  create_video(devo, video_path, voice_over_path, music_path, output_path)      # creates "mp/output.mp4"

