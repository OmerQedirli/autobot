import os
import random
import asyncio
import subprocess
import json
from google import genai
import edge_tts
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

# Yeni google-genai klientinin yaradılması
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")
client = genai.Client(api_key=GEMINI_API_KEY)

SCOPES = ["https://www.googleapis.com/auth/youtube.upload"]

def generate_script():
    """Yeni google-genai vasitəsilə tərəvəz dialoqları yaradır"""
    prompt = """
    Sən YouTube Shorts üçün absurd, yumoristik və viral tərəvəz dialoqları yazan süni intellektsən.
    Hər dəfə tamamilə fərqli iki tərəvəz seç (məsələn: Pomidor və Bibər, və ya Badımcan və Sarımsaq, və s.).
    Onlar arasında gündəlik həyatdan, soyuducudan və ya absurd fəlsəfədən bəhs edən qısa, 3-4 cümləlik gülməli dialoq qur.
    
    Cavabı qətiyyən əlavə sözlər yazmadan, yalnız aşağıdakı formatda JSON kimi qaytar:
    [
      {"char": "Pomidor", "voice": "az-AZ-BabakNeural", "text": "Hər kəs məni salata doğrayır, artıq psixoloqa getməliyəm."},
      {"char": "Bibər", "voice": "az-AZ-BanuNeural", "text": "Sən hələ yaxşıdarsan, mənə baxanda adamların gözü yaşarır!"}
    ]
    Yalnız yuxarıdakı kimi düzgün JSON massivi qaytar, başqa heç bir izahat və ya markdown işarəsi yazma.
    """
    
    # Model adı mövcud stabil versiya ilə dəyişdirildi
    response = client.models.generate_content(
        model='gemini-1.5-flash',
        contents=prompt,
    )
    clean_text = response.text.replace("```json", "").replace("```", "").strip()
    return json.loads(clean_text)

async def generate_audio(dialogues):
    audio_files = []
    for i, item in enumerate(dialogues):
        filename = f"audio_{i}.mp3"
        voice = item["voice"]
        text = item["text"]
        
        communicate = edge_tts.Communicate(text, voice)
        await communicate.save(filename)
        audio_files.append((filename, item["char"], text))
    return audio_files

def create_video(audio_files):
    output_audio = "combined_audio.mp3"
    
    concat_cmd = ["ffmpeg", "-y"]
    for audio_file, _, _ in audio_files:
        concat_cmd.extend(["-i", audio_file])
    
    filter_str = "".join([f"[{i}:a]" for i in range(len(audio_files))]) + f"concat=n={len(audio_files)}:v=0:a=1[a]"
    concat_cmd.extend(["-filter_complex", filter_str, "-map", "[a]", output_audio])
    subprocess.run(concat_cmd, check=True)
    
    video_output = "final_short.mp4"
    video_cmd = [
        "ffmpeg", "-y",
        "-f", "lavfi", "-i", "color=c=navy:s=1080x1920:r=30",
        "-i", output_audio,
        "-c:v", "libx264", "-tune", "stillimage",
        "-c:a", "aac", "-b:a", "192k",
        "-shortest",
        video_output
    ]
    subprocess.run(video_cmd, check=True)
    return video_output

def upload_to_youtube(video_path):
    token_path = os.path.expanduser("~/autobot/token.json")
    client_secret_path = os.path.expanduser("~/autobot/client_secret.json")

    creds = Credentials.from_authorized_user_file(token_path, SCOPES)
    youtube = build("youtube", "v3", credentials=creds)

    body = {
        "snippet": {
            "title": "Tərəvəzlərin Gizli Həyatı 😂 #shorts",
            "description": "Süni intellekt tərəfindən avtomatlaşdırılmış absurd tərəvəz dialoqları!",
            "tags": ["shorts", "funny", "vegetables", "ai"],
            "categoryId": "23"
        },
        "status": {
            "privacyStatus": "public",
            "selfDeclaredMadeForKids": False
        }
    }

    media = MediaFileUpload(video_path, chunksize=-1, resumable=True)
    request = youtube.videos().insert(part="snippet,status", body=body, media_body=media)
    
    response = None
    while response is None:
        status, response = request.next_chunk()
        if status:
            print(f"Yüklənmə faizi: {int(status.progress() * 100)}%")
            
    print("Video uğurla YouTube-a yükləndi!")

async def main():
    print("Ssenari yaradılır...")
    dialogues = generate_script()
    print(f"Yaranan dialoq: {dialogues}")
    
    print("Səslər sintez olunur...")
    audio_files = await generate_audio(dialogues)
    
    print("Video montaj edilir...")
    video_path = create_video(audio_files)
    
    print("YouTube-a yüklənir...")
    upload_to_youtube(video_path)

if __name__ == "__main__":
    asyncio.run(main())
