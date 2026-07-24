import asyncio
import edge_tts
TEXT = "Hello Saksham! This is your ai assistant."
VOICE = "hi-IN-SwaraNeural"
OUTPUT_FILE = "voice.mp3"

async def generate_voice():
  # edge_tts uses the Communicate class
  communicate = edge_tts.Communicate(TEXT, VOICE)
  await communicate.save(OUTPUT_FILE)

if __name__ == '__main__':
  asyncio.run(generate_voice())