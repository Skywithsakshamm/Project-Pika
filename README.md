# 🌸 Project Pika — Selvie AI Desktop Assistant

Welcome to **Project Pika**, featuring **Selvie** — a voice-first Windows personal desktop AI companion built for **Saksham**.

> **"ONE VOICE → ONE ASSISTANT → MANY ACTIONS"**  
> *Always with you, right from the moment you open your laptop.*

---

## 🌟 What is Selvie?

Selvie is an AI desktop companion living inside your laptop. She greets you on Windows startup with a natural **Indian female voice**, organizes your daily tasks, creates focus schedules to reduce stress, sets reminders with native Windows toast notifications, and launches applications through simple voice commands.

👉 **Full Implementation & Source Code:** Head directly to [`AI Assistent/`](./AI%20Assistent/) to explore the complete codebase, architecture, and docs!

---

## 🚀 Quick Launch (Selvie Desktop Assistant)

Navigate to `AI Assistent/`:
```bash
cd "AI Assistent"
pip install -r requirements.txt
python run_selvie.py
```
Or double-click `run_selvie.bat` for instant 1-click startup!

### Key Features:
- 🎙️ **Voice-First Floating Assistant**: Minimalist glassmorphic overlay with dynamic audio waveform visualizer and `Ctrl + Space` global hotkey.
- 🇮🇳 **Natural Indian Female Voice**: Powered by Edge-TTS (`en-IN-NeerjaExpressiveNeural` / `hi-IN-SwaraNeural`) with offline SAPI5 fallback.
- 🧠 **Local LLM Brain**: Powered by Ollama (`llama3.1`) + sub-20ms ultra-fast offline intent parser.
- 🧘 **Stress-Reduction Daily Scheduler**: Focus blocks, 15-minute breaks, and workload balancing.
- ⏰ **Background Reminders**: Native Windows toast notifications and spoken reminders.
- 🛡️ **Safety Confirmation Guard**: Verification modal before any sensitive operations.

---

## 🎙️ Core TTS Engine (Project Pika Prototype)

Project Pika also contains the standalone fast TTS prototype using Microsoft Edge TTS:

```bash
pip install edge-tts
python main.py
```

---

## 👤 Author

**Saksham Tiwari**
