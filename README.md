# AI24x7 Voice Command System 🗣️

Control your AI24x7 CCTV dashboard with Hindi & English voice commands.

## What It Does

Say "Hey AI24x7" → Speak your command → Get instant response!

```
Examples:
"Camera 3 dikhao"         → Shows Camera 3 feed
"Alerts dikhao"           → Shows all active alerts
"System status batao"     → Reports system health
"Emergency!"              → Triggers SOS to all contacts
"Kal raat 11 baje koi aaya tha?" → Searches historical footage
"Report dikhao"           → Generates daily report
```

## Features

- **Wake Word Detection** - "Hey AI24x7" activates system
- **Hindi Commands** - Bollywood-style Hindi supported  
- **English Commands** - Full English support
- **Code-Mixed** - Hinglish commands work too!
- **Text-to-Speech** - Hindi announcements for alerts
- **Emergency SOS** - Voice-activated panic button
- **API Server** - REST API for integration
- **Works Offline** - Local STT processing

## Installation

```bash
pip install -r requirements.txt

# Or individual packages:
pip install openai-whisper edge-tts gtts flask
```

## Quick Start

```bash
# Text demo mode (no mic needed)
python voice_agent.py

# API server mode
python voice_agent.py --server

# Demo all commands
python voice_agent.py --demo
```

## API Endpoints

```
POST /api/voice/command  - Send voice/text command
POST /api/voice/speak    - Send TTS announcement
POST /api/voice/sos      - Trigger emergency SOS
GET  /api/voice/demo     - Run demo sequence
GET  /health             - Service health check
```

## Supported Languages

| Language | Code | Voice |
|----------|------|-------|
| Hindi | hi | MadhurNeural |
| English | en | AriaNeural |
| Tamil | ta | PallaviNeural |
| Telugu | te | ShrutiNeural |
| Kannada | kn | SapnaNeural |
| Bengali | bn | TanishkaNeural |
| Marathi | mr | AarohiNeural |

## TTS Engines

1. **Edge TTS** (Default) - Microsoft, best quality, needs internet
2. **gTTS** (Fallback) - Google Translate, free, needs internet
3. **XTTS v2** (Local) - Coqui, offline capable, highest quality

## Command Reference

| Command | Intent | Response |
|---------|--------|----------|
| "camera 1 dikhao" | show_camera | Shows camera 1 |
| "sab camera" | all_cameras | Grid of all cameras |
| "alerts" | show_alerts | Lists active alerts |
| "acknowledge" | acknowledge_alert | Clears latest alert |
| "status" | system_status | System health report |
| "help / bacchao" | emergency_sos | Triggers SOS |
| "next / agla" | next_page | Navigate forward |
| "back / pichla" | prev_page | Navigate back |
| "full screen" | full_screen | Maximizes view |
| "report" | generate_report | Creates daily report |

## Architecture

```
User Voice → Wake Word → Whisper STT → Intent Classifier 
   → CCTV Controller → Action → TTS Response
```

## Integration

Connects with:
- AI24x7 Super Admin Dashboard (port 5051)
- WhatsApp Bot (port 5054)
- SMS Alerts (port 5055)
- TTS Module (multi-language)

## License

Proprietary - GOUP CONSULTANCY SERVICES LLP
https://ai24x7.cloud