from trafilatura import fetch_url, extract
from google import genai
import re
import io
import wave
from dotenv import load_dotenv

load_dotenv()


# Split up article for tts
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


def generate_wav(chunks, job_id, on_progress):
    # Send to gemini for tts
    client = genai.Client()
    out = None

    try:
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

            data = response.candidates[0].content.parts[0].inline_data.data

            # Write the output file as chunks come back, only one chunk's audio in memory at a time
            with wave.open(io.BytesIO(data), "rb") as w:
                if out is None:
                    out = wave.open(f"{job_id}.wav", "wb")
                    out.setparams(w.getparams())
                while frames := w.readframes(48000):
                    out.writeframes(frames)

            if index + 1 < len(chunks):
                on_progress(index + 1, len(chunks))

            del response, data
    finally:
        if out is not None:
            out.close()


def convert_article(url, job_id, on_progress):
    print(f"Fetching {url}")

    downloaded = fetch_url(url)
    article = extract(downloaded)

    if not article:
        raise ValueError("No article text found")

    chunks = split_article(article)
    on_progress(0, len(chunks))

    print(f"Requests required: {len(chunks)}")

    # generate_wav(chunks, job_id, on_progress=on_progress)
