import os
from dotenv import load_dotenv, find_dotenv

from elevenlabs import save
from elevenlabs.client import ElevenLabs

load_dotenv(find_dotenv())

client = ElevenLabs(
  api_key=os.getenv("XI_API_KEY"), 
)

audio = client.generate(
  text="1, 2, 3.",
  voice="Daniel",
)

save(audio, "test.mp3")