import os
import random
import asyncio
import subprocess
import edge_tts
from google import genai
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from google_auth_oauthlib.flow import InstalledAppFlow
from google.oauth2.credentials import Credentials

# API açarını environment-dən oxuyuruq
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")

def generate_script():
    client = genai.Client(api_key=GEMINI_API_KEY)
    topics = [
        "eating broccoli for dinner", 
        "playing video games secretly", 
        "waking up early for school", 
        "stealing ice cream from the fridge",
        "doing homework at the last minute",
        "surviving math class without sleeping",
        "trying to sneak out of the house"
    ]
    topic = random.choice(topics)
    
    prompt = f"Write a funny, 15-second monologue for a cute 3D Animated Tomato Kid in English about {topic}. Make it short, funny, and punchy. Return ONLY the spoken dialogue text."
    
    response = client.models.generate_content(
        model="gemini-3.6-flash",
        contents=prompt,
    )
    script_text = response.text.strip().replace('"', '')
    return script_text, topic

async def generate_audio(text, output_file):
    communicate = edge_tts.Communicate(text, "en-US-AnaNeural")
    await communicate.save(output_file)

def create_video(audio_path, output_path, text):
    clean_text = text.replace("'", "").replace(":", "")
    
    color_list = ['red', 'blue', 'green', 'purple', 'orange', 'pink', 'yellow', 'cyan', 'magenta']
    c0 = random.choice(color_list)
    c1 = random.choice(color_list)
    
    command = [
        'ffmpeg', '-y',
        '-f', 'lavfi', '-i', f'gradients=s=1080x1920:rate=30:c0={c0}:c1={c1}',
        '-i', audio_path,
        '-vf', f"drawtext=text='{clean_text}':fontcolor=white:fontsize=38:box=1:boxcolor=black@0.7:x=(w-text_w)/2:y=(h-text_h)/2-100:fix_bounds=true",
        '-c:v', 'libx264', '-c:a', 'aac', '-b:a', '192k',
        '-pix_fmt', 'yuv420p', '-shortest', output_path
    ]
    subprocess.run(command, check=True)

SCOPES = ["https://www.googleapis.com/auth/youtube.upload"]

def upload_to_youtube(video_path, title):
    base_dir = os.path.expanduser('~/autobot')
    if not os.path.exists(base_dir):
        os.makedirs(base_dir, exist_ok=True)
        
    token_path = os.path.join(base_dir, 'token.json')
    secret_path = os.path.join(base_dir, 'client_secret.json')

    credentials = None
    if os.path.exists(token_path):
        credentials = Credentials.from_authorized_user_file(token_path, SCOPES)
        
    if not credentials or not credentials.valid:
        flow = InstalledAppFlow.from_client_secrets_file(secret_path, SCOPES)
        credentials = flow.run_local_server(port=0)
        with open(token_path, 'w') as token:
            token.write(credentials.to_json())

    youtube = build('youtube', 'v3', credentials=credentials)

    body = {
        'snippet': {
            'title': f"{title} 🍅 #shorts #funny #animation #veggies",
            'description': 'Daily Veggie Family Episode! Generated fully automatic by AI bot!',
            'tags': ['shorts', 'veggie', 'funny', 'animation', 'kids'],
            'categoryId': '23'
        },
        'status': {
            'privacyStatus': 'public',
            'selfDeclaredMadeForKids': False
        }
    }

    media = MediaFileUpload(video_path, chunksize=-1, resumable=True)
    response = youtube.videos().insert(part=','.join(body.keys()), body=body, media_body=media).execute()
    print(f"Uğurla Yükləndi! Video ID: {response['id']}")

async def main():
    base_dir = os.path.expanduser('~/autobot')
    if not os.path.exists(base_dir):
        os.makedirs(base_dir, exist_ok=True)
        
    audio_file = os.path.join(base_dir, 'voice.mp3')
    video_file = os.path.join(base_dir, 'final_short.mp4')

    print("1. AI ssenari hazırlayır...")
    script, topic = generate_script()
    
    print("2. Audio səsləndirilir...")
    await generate_audio(script, audio_file)
    
    print("3. FFmpeg təsadüfi rəngli hərəkətli fon yaradıb videonu montajlayır...")
    create_video(audio_file, video_file, script)
    
    print("4. YouTube-a avtomatik yüklənir...")
    upload_to_youtube(video_file, f"Veggie Family: {topic.title()}")

if __name__ == "__main__":
    asyncio.run(main())
