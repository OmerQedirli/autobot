import os
import asyncio
import subprocess
import json
from google import genai
import edge_tts
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")
client = genai.Client(api_key=GEMINI_API_KEY)

SCOPES = ["https://www.googleapis.com/auth/youtube.upload"]

def generate_script():
    """Generates funny vegetable dialogues and background color themes in English using gemini-3.6-flash"""
    prompt = """
    You are an AI that writes absurd, humorous, and viral vegetable dialogues for YouTube Shorts in English.
    Choose two completely different vegetables each time (e.g., Tomato and Pepper, or Broccoli and Garlic).
    Choose a vibrant background color for the video that matches the vibe (options: navy, darkred, darkgreen, purple, midnightblue).
    
    Create a short, funny 3-4 sentence dialogue between them.
    Return the response ONLY as a valid JSON object without any markdown formatting, following this exact structure:
    {
      "bg_color": "darkred",
      "dialogues": [
        {"char": "Tomato", "voice": "en-US-GuyNeural", "text": "Everyone chops me into a salad, I seriously need a therapist."},
        {"char": "Pepper", "voice": "en-US-AriaNeural", "text": "You think you have it bad? Look at me, I make people cry just by existing!"}
      ]
    }
    Return ONLY the raw JSON. No markdown code blocks, no extra text.
    """
    
    response = client.models.generate_content(
        model='gemini-3.6-flash',
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

def create_video(audio_files, bg_color, dialogues):
    output_audio = "combined_audio.mp3"
    
    # Merge all audio parts together
    concat_cmd = ["ffmpeg", "-y"]
    for audio_file, _, _ in audio_files:
        concat_cmd.extend(["-i", audio_file])
    
    filter_str = "".join([f"[{i}:a]" for i in range(len(audio_files))]) + f"concat=n={len(audio_files)}:v=0:a=1[a]"
    concat_cmd.extend(["-filter_complex", filter_str, "-map", "[a]", output_audio])
    subprocess.run(concat_cmd, check=True)
    
    # Build text filters to display character names and texts dynamically on screen
    # FFmpeg drawtext filter can render text directly without external images
    drawtext_filters = []
    
    video_output = "final_short.mp4"
    video_cmd = [
        "ffmpeg", "-y",
        "-f", "lavfi", f"-i", f"color=c={bg_color}:s=1080x1920:r=30",
        "-i", output_audio,
        "-vf", "drawtext=text='THE SECRET LIFE OF VEGETABLES':fontcolor=white:fontsize=50:x=(w-text_w)/2:y=200,drawtext=text='COMEDY SHORTS':fontcolor=yellow:fontsize=35:x=(w-text_w)/2:y=270",
        "-c:v", "libx264", "-tune", "stillimage",
        "-c:a", "aac", "-b:a", "192k",
        "-shortest",
        video_output
    ]
    subprocess.run(video_cmd, check=True)
    return video_output

def upload_to_youtube(video_path):
    token_path = os.path.expanduser("~/autobot/token.json")
    creds = Credentials.from_authorized_user_file(token_path, SCOPES)
    youtube = build("youtube", "v3", credentials=creds)

    body = {
        "snippet": {
            "title": "The Secret Life of Vegetables 😂 #shorts",
            "description": "Automated absurd vegetable dialogues generated completely by AI!",
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
            print(f"Upload progress: {int(status.progress() * 100)}%")
            
    print("Video successfully uploaded to YouTube!")

async def main():
    print("Generating script and design choices...")
    data = generate_script()
    bg_color = data.get("bg_color", "navy")
    dialogues = data.get("dialogues", [])
    print(f"Generated data: {data}")
    
    print("Synthesizing voices...")
    audio_files = await generate_audio(dialogues)
    
    print("Rendering video...")
    video_path = create_video(audio_files, bg_color, dialogues)
    
    print("Uploading to YouTube...")
    upload_to_youtube(video_path)

if __name__ == "__main__":
    asyncio.run(main())
