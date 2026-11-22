import os
import json
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
    url = "https://pixabay.com/api/videos/"
    params = {"key": PIXABAY_API_KEY, "q": query, "per_page": 15}
    resp = requests.get(url, params=params, timeout=30)
    resp.raise_for_status()
    hits = resp.json().get("hits", [])

    if not hits:
        params["q"] = "abstract motion"
        resp = requests.get(url, params=params, timeout=30)
        resp.raise_for_status()
        hits = resp.json().get("hits", [])

    urls: list[str] = []
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

    saved_files: list[str] = []
    for idx, u in enumerate(urls[:count], start=1):
        filename = f"background_{idx}.mp4"
        full_path = os.path.join(output_dir, filename)
        r = requests.get(u, stream=True, timeout=60)
        r.raise_for_status()
        with open(full_path, "wb") as f:
            for chunk in r.iter_content(chunk_size=8192):
                if chunk:
                    f.write(chunk)
        saved_files.append(f"assets/{filename}")

    return saved_files
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

    meta_path = os.path.join(OUTPUT_DIR, "script.json")
    with open(meta_path, "w", encoding="utf-8") as f:
        json.dump(
            {
                "title": payload.get("title", "Short"),
                "script": script_text,
                "words": words,
                "wordTimings": word_timings,
                "audioDurationSec": audio_duration_sec,
                "backgrounds": backgrounds,
            },
            f,
            ensure_ascii=False,
            indent=2,
        )
backgrounds = download_multiple_pixabay_videos("motivation", OUTPUT_DIR, count=3)
if not backgrounds:
        raise RuntimeError("Pixabay üzerinde uygun dikey video bulunamadı.")

print("Tüm varlıklar başarıyla hazırlandı!")


if __name__ == "__main__":
    main()
