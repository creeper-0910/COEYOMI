import os

from dotenv import load_dotenv

load_dotenv()

url_regex = r'http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\\(\\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+'

default_uuid = "3c37646f-3881-5374-2a83-149267990abc"
default_id = 0
engine_path = os.getcwd()+"\\COEIROINK\\engine\\engine.exe"
ffmpeg_path = os.getcwd()+"\\bin\\ffmpeg.exe"
engine_api  = "http://localhost:50032"

in_voice = {}
call_channel = {}