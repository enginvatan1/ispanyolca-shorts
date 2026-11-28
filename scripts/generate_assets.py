import os
import json
from random import random
import time
import asyncio
import requests
import edge_tts
from google import genai
from google.genai import types

GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")
PIXABAY_API_KEY = os.environ.get("PIXABAY_API_KEY")
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
CHAT_ID = os.environ.get("CHAT_ID")

OUTPUT_DIR = os.path.join("public", "assets")
os.makedirs(OUTPUT_DIR, exist_ok=True)


def generate_spanish_script(topic: str = "curiosidades sorprendentes") -> dict:
    client = genai.Client(api_key=GEMINI_API_KEY)

    prompt = f"""
Eres un creador de contenido viral para YouTube Shorts en español de México.
Tema: {topic}

Crea un guion corto de unos 35-45 segundos (aproximadamente 85-110 palabras) en español natural de México.
Además, dame 1 palabra o frase corta en inglés (máximo 2 palabras) para buscar un video vertical de fondo.

Responde ÚNICAMENTE con un JSON válido con esta estructura exacta:
{{
  "title": "Título llamativo corto",
  "search_query": "night city",
  "description": "Resumen breve de 1-2 frases y 4 hashtags como #EfectoDopamina #Motivacion #Habitos #Shorts",
  "script": "Texto completo de la narración en español."
}}
"""

    for attempt in range(4):
        try:
            response = client.models.generate_content(
                model="gemini-3.5-flash",
                contents=prompt,
                config=types.GenerateContentConfig(
                    response_mime_type="application/json",
                ),
            )
            break
        except Exception as e:
            if attempt < 3 and ("503" in str(e) or "UNAVAILABLE" in str(e)):
                wait_sec = (attempt + 1) * 5
                print(f"Gemini yoğun (503), {wait_sec} sn sonra tekrar deneniyor...")
                time.sleep(wait_sec)
            else:
                raise

    raw_text = response.text.strip()
    if raw_text.startswith("```"):
        raw_text = raw_text.split("```")[1]
        if raw_text.startswith("json"):
            raw_text = raw_text[4:]
    raw_text = raw_text.strip()
    return json.loads(raw_text)


async def generate_voiceover(text: str, output_path: str, voice: str = "es-MX-DaliaNeural"):
    communicate = edge_tts.Communicate(text=text, voice=voice)
    timings = []
    with open(output_path, "wb") as f:
        async for chunk in communicate.stream():
            if chunk["type"] == "audio":
                f.write(chunk["data"])
            elif chunk["type"] == "WordBoundary":
                timings.append({
                    "text": chunk["text"],
                    "start": round(chunk["offset"] / 10_000_000, 3),
                    "end": round((chunk["offset"] + chunk["duration"]) / 10_000_000, 3),
                })
    return timings


def download_pixabay_vertical_video(query: str, output_path: str) -> bool:
    url = "https://pixabay.com/api/videos/"
    params = {
        "key": PIXABAY_API_KEY,
        "q": query,
        "per_page": 10,
    }
    resp = requests.get(url, params=params, timeout=30)
    resp.raise_for_status()
    hits = resp.json().get("hits", [])

    if not hits:
        params["q"] = "abstract motion"
        resp = requests.get(url, params=params, timeout=30)
        resp.raise_for_status()
        hits = resp.json().get("hits", [])

    if not hits:
        raise RuntimeError("Pixabay üzerinde uygun video bulunamadı.")

    selected_url = None
    for hit in hits:
        videos = hit.get("videos", {})
        for quality in ["large", "medium", "small"]:
            v = videos.get(quality)
            if v and v.get("url"):
                width = v.get("width", 0)
                height = v.get("height", 0)
                if height >= width:
                    selected_url = v["url"]
                    break
        if selected_url:
            break

    if not selected_url:
        for hit in hits:
            videos = hit.get("videos", {})
            for quality in ["large", "medium", "small"]:
                v = videos.get(quality)
                if v and v.get("url"):
                    selected_url = v["url"]
                    break
            if selected_url:
                break

    if not selected_url:
        raise RuntimeError("İndirilebilir video bağlantısı bulunamadı.")

    video_resp = requests.get(selected_url, stream=True, timeout=60)
    video_resp.raise_for_status()
    with open(output_path, "wb") as f:
        for chunk in video_resp.iter_content(chunk_size=8192):
            if chunk:
                f.write(chunk)
    return True

def download_multiple_pixabay_videos(query: str, output_dir: str, count: int = 3) -> list[str]:
    import random

    url = "https://pixabay.com/api/videos/"
    queries = [q for q in [query, "motivation", "abstract motion", "dark aesthetic", "focus mindset"] if q]
    chosen_query = random.choice(queries)
    page = random.randint(1, 3)

    params = {
        "key": PIXABAY_API_KEY,
        "q": chosen_query,
        "per_page": 20,
        "page": page,
    }
    resp = requests.get(url, params=params, timeout=30)
    resp.raise_for_status()
    hits = resp.json().get("hits", [])

    if not hits:
        params["q"] = "abstract motion"
        params["page"] = 1
        resp = requests.get(url, params=params, timeout=30)
        resp.raise_for_status()
        hits = resp.json().get("hits", [])

    if not hits:
        raise RuntimeError("Pixabay üzerinde uygun dikey video bulunamadı.")

    random.shuffle(hits)
    urls = []
    for hit in hits:
        videos = hit.get("videos", {})
        for quality in ["large", "medium", "small"]:
            v = videos.get(quality)
            if v and v.get("url"):
                width = v.get("width", 0)
                height = v.get("height", 0)
                if height >= width and v["url"] not in urls:
                    urls.append(v["url"])
                    break
        if len(urls) >= count:
            break

    if not urls:
        for hit in hits:
            videos = hit.get("videos", {})
            for quality in ["large", "medium", "small"]:
                v = videos.get(quality)
                if v and v.get("url") and v["url"] not in urls:
                    urls.append(v["url"])
                    break
            if len(urls) >= count:
                break

    if not urls:
        raise RuntimeError("İndirilebilir video bağlantısı bulunamadı.")

    downloaded_files = []
    for idx, video_url in enumerate(urls[:count], start=1):
        filename = f"background_{idx}.mp4"
        full_path = os.path.join(output_dir, filename)
        video_resp = requests.get(video_url, stream=True, timeout=60)
        video_resp.raise_for_status()
        with open(full_path, "wb") as f:
            for chunk in video_resp.iter_content(chunk_size=8192):
                if chunk:
                    f.write(chunk)
        downloaded_files.append(f"assets/{filename}")

    return downloaded_files
import urllib.parse
import subprocess


def download_pollinations_backgrounds(query: str, output_dir: str, count: int = 3) -> list[str]:
    prompts = [
        f"dark moody cinematic vertical scene representing {query}, dramatic rim lighting, deep shadows, minimalist dopamine neuroscience vibe, 4k",
        f"abstract glowing neural pathways and calm night atmosphere for {query}, moody indigo and amber lighting, ultra detailed vertical composition",
        f"solitary focused person in dark atmospheric room contemplating {query}, subtle motion feel, cinematic contrast, vertical frame"
    ]
    downloaded_files = []
    for idx, p in enumerate(prompts[:count], start=1):
        encoded_prompt = urllib.parse.quote(p)
        seed = (int(time.time() * 1000) + idx * 7919) % 900000 + 1000
        img_url = f"https://image.pollinations.ai/prompt/{encoded_prompt}?width=1080&height=1920&seed={seed}&nologo=true"
        temp_img = os.path.join(output_dir, f"poll_{idx}.jpg")
        out_mp4 = os.path.join(output_dir, f"background_{idx}.mp4")
        try:
            resp = requests.get(img_url, timeout=60)
            resp.raise_for_status()
            with open(temp_img, "wb") as f:
                f.write(resp.content)
            subprocess.run(
                [
                    "ffmpeg", "-y", "-loop", "1", "-i", temp_img,
                    "-t", "15", "-vf", "scale=1080:1920,zoompan=z='min(zoom+0.0008,1.12)':d=375:s=1080x1920:fps=25",
                    "-c:v", "libx264", "-pix_fmt", "yuv420p", out_mp4
                ],
                check=True,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL
            )
            if os.path.exists(temp_img):
                os.remove(temp_img)
            downloaded_files.append(f"assets/background_{idx}.mp4")
        except Exception as err:
            print(f"Pollinations görsel {idx} alınamadı ({err}), Pixabay yedeğine geçiliyor...")
            fallback = download_multiple_pixabay_videos(query, output_dir, count=count)
            return fallback
    return downloaded_files
def main():
    topic = os.environ.get("VIDEO_TOPIC", "habitos para vencer la procrastinacion")
    print("1. Gemini ile İspanyolca senaryo üretiliyor...")
    payload = generate_spanish_script(topic=topic)

    script_text = payload["script"]
    search_query = payload["search_query"]
    print(f"Başlık: {payload.get('title', '')}")
    print(f"Pixabay arama kelimesi: {search_query}")

    words = script_text.split()
    audio_path = os.path.join(OUTPUT_DIR, "voiceover.mp3")
    print("2. Edge-TTS ile seslendirme oluşturuluyor...")
    word_timings = asyncio.run(generate_voiceover(script_text, audio_path))
    audio_duration_sec = word_timings[-1]["end"] if word_timings else 0.0

    backgrounds = download_pollinations_backgrounds(search_query or topic, OUTPUT_DIR, count=3)
    if not backgrounds:
        raise RuntimeError("Arka plan videoları oluşturulamadı.")

    meta_path = os.path.join(OUTPUT_DIR, "script.json")
    with open(meta_path, "w", encoding="utf-8") as f:
        json.dump(
            {
                "title": payload.get("title", "Short"),
                "script": script_text,
                "words": words,
                "description": payload.get("description") or f"{payload.get('title', 'Efecto Dopamina')} #EfectoDopamina",
                "wordTimings": word_timings,
                "audioDurationSec": audio_duration_sec,
                "backgrounds": backgrounds,
            },
            f,
            ensure_ascii=False,
            indent=2,
        )

print("Tüm varlıklar başarıyla hazırlandı!")


if __name__ == "__main__":
    main()
