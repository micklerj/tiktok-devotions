import os
from openai import OpenAI
from dotenv import load_dotenv, find_dotenv
from moviepy.editor import VideoFileClip, AudioFileClip, TextClip, CompositeVideoClip, CompositeAudioClip, vfx
import random
from elevenlabs.client import ElevenLabs
from elevenlabs import save
import moviepy.config as moviepy_config
import re
import requests
import json
import base64

# Set the path to the ImageMagick executable
moviepy_config.change_settings({"IMAGEMAGICK_BINARY": "C:/Program Files/ImageMagick-7.1.1-Q16-HDRI/magick.exe"})


prompt = """
  please generate a random devotion base on a random Bible passage.   

  guidelines to formatting:  
  - choose a passage of 1 or 2 Bible verses, and NO more.
  - output the name of the book of the Bible, followed by the chapter number,
  followed by the verse number(s) that you choose, followed by a period. If multiple verses are
  chosen, output the word "through" between the 1st and 2nd selected verse
  numbers (example: Mark 4 1 through 2.).
  - output the verse(s).
  - output an encouraging devotion consisting of 4 sentences.

  example output: 
  John 3 16 through 17.  

  For God so loved the world that he gave his one and only Son, that whoever
  believes in him shall not perish but have eternal life. For God did not send
  his Son into the world to condemn the world, but to save the world through him.

  We find a profound declaration of God's love for humanity. These verses remind
  us that God's love is unconditional and boundless, extending to every individual
  without exception. Through Jesus Christ, God offers us the gift of salvation,
  not to condemn us, but to bring us into a life of eternal abundance and freedom.
  Let us embrace this incredible love, sharing it with others as we walk in the
  light of His grace.
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

  # TODO: add passage to pool of already used passages so we dont re-use

  return devotion

# generate the voice over    and    save timestamps
def get_voice_over(input_text):

  # Daniel: onwK4e9ZLuTAKqWW03F9,   Josh: TxGEqnHWrfWFTfGW9XjX,   James: ZQe5CZNOzWyzPSCn5a3c,   Michael: flq6f7yk4E4fJM5XTYuZ
  # TODO: automatically choose random voice, background video, and music
  VOICE_ID = "flq6f7yk4E4fJM5XTYuZ"  
  XI_API_KEY = os.getenv("XI_API_KEY")

  url = f"https://api.elevenlabs.io/v1/text-to-speech/{VOICE_ID}/with-timestamps"

  headers = {
    "Content-Type": "application/json",
    "xi-api-key": XI_API_KEY
  }

  data = {
    "text": ( input_text ),
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

  # save the voice over mp3 file
  with open('mp/voice_over.mp3', 'wb') as f:
    f.write(audio_bytes)

  # the 'alignment' entry contains the mapping between input characters and their timestamps
  characters = response_dict['alignment']['characters']
  start_times = response_dict['alignment']['character_start_times_seconds']
  end_times = response_dict['alignment']['character_end_times_seconds']

  
  start_of_word_reached = False
  for char, start, end in zip(characters, start_times, end_times):
    if (char.isspace() or char == '-') and start_of_word_reached:
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



if __name__ == "__main__":
  video_path      = "mp/background1.mp4"           # original source for background video
  music_path      = "mp/music2.mp3"                # rource for background music
  voice_over_path = "mp/voice_over.mp3"
  output_path     = "mp/output5.mp4"

  devo = get_devotion()
  print(devo)
  get_voice_over(devo)                                                          # creates "mp/voice_over.mp3"
  create_video(devo, video_path, voice_over_path, music_path, output_path)      # creates "mp/output.mp4"



# ------------------------------------------------- TESTING -------------------------------------------------

  # devo = """
  #   Philippians 4 13.

  #   I can do all this through him who gives me strength.

  #   In this powerful verse, we are reminded that through Christ, we have the strength to overcome any challenge or obstacle. 
  #   Our faith in Him empowers us to face each day with confidence and courage. Let us lean on His promises and trust in His 
  #   provision, knowing that we are never alone in our struggles.
  # """

  # audio_file = open("mp/slowed_voice_.mp3", "rb")
  # transcript = client.audio.transcriptions.create(
  #   file=audio_file,
  #   model="whisper-1",
  #   response_format="verbose_json",
  #   timestamp_granularities=["word"]
  # )

  # # print(transcript.words)

  # for i in transcript.words:
  #   literal = i['word']
  #   print(f'{literal} ', end='')


  # slowed audio
  # audio_clip = AudioFileClip("mp/my_voice_over.mp3")
  # audio_clip = audio_clip.fx(vfx.speedx, .9)
  # audio_clip.write_audiofile("mp/slowed_voice1.mp3")