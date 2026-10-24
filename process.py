from trafilatura import fetch_url, extract
import sys
from google import genai
import re
import io
import wave
from dotenv import load_dotenv

load_dotenv()

url = sys.argv[1]
print(f"Fetching {url}")

downloaded = fetch_url(url)
article = extract(downloaded)


### Split up article for tts
def split_article(text, max_words=1400):
    paragraphs = [p.strip() for p in text.splitlines() if p.strip()]

    units = []

    for paragraph in paragraphs:
        if len(paragraph.split()) <= max_words:
            units.append(paragraph)
            continue

        # Split unusually long paragraphs into sentences
        sentences = re.split(r"(?<=[.!?])\s+", paragraph)

        for sentence in sentences:
            words = sentence.split()

            # Handle exceptionally long sentences too.
            for i in range(0, len(words), max_words):
                units.append(" ".join(words[i : i + max_words]))

    chunks = []
    current = []
    current_words = 0

    for unit in units:
        count = len(unit.split())

        if current and current_words + count > max_words:
            chunks.append("\n\n".join(current))
            current = []
            current_words = 0

        current.append(unit)
        current_words += count

    if current:
        chunks.append("\n\n".join(current))

    return chunks


chunks = split_article(article)
print(f"Requests required: {len(chunks)}")

### Send to gemini for tts
client = genai.Client()

wav_parts = []

for index, chunk in enumerate(chunks):
    print(f"Processing chunk {index + 1}...")

    response = client.models.generate_content(
        model="gemini-3.8-flash-tts",
        contents=[
            {
                "role": "user",
                "parts": [
                    {
                        "text": chunk,
                        "speech_metadata": {
                            "style": "Read this as a polished nonfiction audiobook narrated by a warm, intelligent British speaker. Use a natural contemporary neutral southern English accent - clear, elegant, and authentic, never theatrical, exaggerated, or caricatured. Speak with calm confidence and a conversational tone, as though explaining the subject to an interested listener. Use measured pacing, clear articulation, and natural variation in pitch and emphasis. Slow slightly for important ideas, definitions, figures, and transitions. Add brief pauses between sections and after major points. Pronounce names and place names carefully and consistently. Use British pronunciation and vocabulary where appropriate, but do not rewrite the author’s wording unnecessarily. The overall result should sound like a professionally produced British nonfiction audiobook: engaging, thoughtful, accessible, and easy to follow over a long listening session."
                        },
                    }
                ],
            }
        ],
        config={
            "response_modalities": ["AUDIO"],
            "speech_config": {"voice_config": {"voice": "Algenib"}},
        },
    )

    wav_parts.append(response.candidates[0].content.parts[0].inline_data.data)

### Combine wavs and save
with wave.open("article.wav", "wb") as out:
    for i, data in enumerate(wav_parts):
        with wave.open(io.BytesIO(data), "rb") as w:
            if i == 0:
                out.setparams(w.getparams())  # take format from the first chunk
            out.writeframes(w.readframes(w.getnframes()))
