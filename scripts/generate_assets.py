import asyncio
import json
import os
import requests
import edge_tts
from google import genai

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
    Además, dame 1 palabra o frase corta en inglés (máximo 2 palabras) para buscar un video vertical de fondo en Pixabay.

    Responde ÚNICAMENTE con un JSON válido con esta estructura exacta:
    {{
      "title": "Título llamativo corto",
      "search_query": "night city",
      "script": "Texto completo de la narración en español."
    }}
    """

    response = client.models.generate_content(
        model="gemini-3-flash",
        contents=prompt,
    )

    raw_text = response.text.strip()
    if raw_text.startswith("```"):
        raw_text = raw_text.split("```")[1]
        if raw_text.startswith("json"):
            raw_text = raw_text[4:]
    raw_text = raw_text.strip()

    return json.loads(raw_text)


async def generate_voiceover(text: str, output_path: str, voice: str = "es-MX-DaliaNeural"):
    communicate = edge_tts.Communicate(text=text, voice=voice)
    await communicate.save(output_path)


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


def main():
    topic = os.environ.get("VIDEO_TOPIC", "datos curiosos que no sabías")
    print("1. Gemini ile İspanyolca senaryo üretiliyor...")
    payload = generate_spanish_script(topic=topic)

    script_text = payload["script"]
    search_query = payload["search_query"]
    print(f"Başlık: {payload.get('title', '')}")
    print(f"Pixabay arama kelimesi: {search_query}")

    words = script_text.split()
    meta_path = os.path.join(OUTPUT_DIR, "script.json")
    with open(meta_path, "w", encoding="utf-8") as f:
        json.dump(
            {
                "title": payload.get("title", "Short"),
                "script": script_text,
                "words": words,
            },
            f,
            ensure_ascii=False,
            indent=2,
        )

    audio_path = os.path.join(OUTPUT_DIR, "voiceover.mp3")
    print("2. Edge-TTS ile seslendirme oluşturuluyor...")
    asyncio.run(generate_voiceover(script_text, audio_path))

    video_path = os.path.join(OUTPUT_DIR, "background.mp4")
    print("3. Pixabay'den arka plan videosu indiriliyor...")
    download_pixabay_vertical_video(search_query, video_path)

    print("Tüm varlıklar başarıyla hazırlandı!")


if __name__ == "__main__":
    main()
