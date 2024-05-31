import os
from openai import OpenAI
from dotenv import load_dotenv, find_dotenv
from moviepy.editor import VideoFileClip, AudioFileClip, TextClip, CompositeVideoClip, CompositeAudioClip, vfx
import random
import math
from elevenlabs.client import ElevenLabs
from elevenlabs import save
import moviepy.config as moviepy_config

# Set the path to the ImageMagick executable
moviepy_config.change_settings({"IMAGEMAGICK_BINARY": "C:/Program Files/ImageMagick-7.1.1-Q16-HDRI/magick.exe"})


prompt = """
  please generate a random devotion base on a random Bible passage.   

  guidelines to formatting:  
  - choose a passage of 1 or 2 Bible verses.
  - output the name of the book of the Bible, followed by the chapter number,
  followed by the verse number(s) that you choose. If multiple verses are
  chosen, output the word "through" between the 1st and 2nd selected verse
  numbers (example: Mark 4 1 through 2).
  - output the verse(s).
  - output an encouraging devotion consisting of 4 sentences.

  example output: 
  John 3 16 through 17  

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

# generate the voice over
def get_voice_over(input_text):

  audio = eleven_client.generate(
    text = input_text,
    
    voice = "Daniel"     # Daniel: onwK4e9ZLuTAKqWW03F9,    Josh: TxGEqnHWrfWFTfGW9XjX
  )

  save(audio, "mp/voice_over.mp3")

  # slow down the audio
  audio_clip = AudioFileClip("mp/voice_over.mp3")
  slowed_clip = audio_clip.fx(vfx.speedx, .9)
  slowed_clip.write_audiofile("mp/slow_voice_over.mp3")

  # TODO: increase pitch of voice

  audio_clip.close()
  slowed_clip.close()


# create subclip for background with pre-made voice over
def create_video(video_path, audio_path, music_path, output_path):
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
  audio_file = open(audio_path, "rb")
  transcript = client.audio.transcriptions.create(
    file=audio_file,
    model="whisper-1",
    response_format="verbose_json",
    timestamp_granularities=["word"]
  )
  subs = []
  # print(transcript)
  prev_end = 0
  next_start_increase = 0.1
  for obj in transcript.words:
    text = obj['word']
    start = obj['start']
    end = obj['end']    

    # adjust the start n end times for when the timestamps are wrong
    start += next_start_increase
    next_start_increase = 0.0
    if start != prev_end:
      start = prev_end
    if start >= end:
      end += 0.1
      next_start_increase = 0.1
    prev_end = end

    txt_clip = TextClip(
      text,
      fontsize=45,
      font="Arial-Bold",
      color='white',
      stroke_color='black',
      stroke_width=2
    )
    txt_clip = txt_clip.set_start(start).set_end(end).set_position(('center', 'center'))
    subs.append(txt_clip)
    # print(f"{text} ", end='')
  print("\n")

  background_video = CompositeVideoClip([background_video] + subs)

  # save the output and close clips
  background_video.write_videofile(output_path)
  audio_clip.close()
  background_video.close()
  music.close()
  for clip in subs:
    clip.close()



if __name__ == "__main__":
  video_path      = "mp/minecraft.mp4"           # original source for background video
  music_path      = "mp/music1.mp3"              # rource for background music
  voice_over_path = "mp/slow_voice_over.mp3"
  output_path     = "mp/output3.mp4"

  devo = get_devotion()
  print(devo)
  get_voice_over(devo)                                                    # creates "mp/voice_over.mp3" and "mp/slow_voice_over.mp3"
  create_video(video_path, voice_over_path, music_path, output_path)      # creates "mp/output.mp4"



# ------------------------------------------------- TESTING -------------------------------------------------

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