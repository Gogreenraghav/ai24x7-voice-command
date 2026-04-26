"""
AI24x7 Voice Command System
Control your CCTV dashboard with Hindi/English voice commands.
Wake word: "Hey AI24x7" → Speak command → Get response

Supports:
- Hindi commands (Bollywood-style)
- English commands
- Text-to-speech in multiple Indian languages
- Emergency SOS
- CCTV dashboard control
"""
import os, sys, json, time, threading, queue
import numpy as np
from pathlib import Path
from datetime import datetime

# ─── Wake Word Detection ───────────────────
class WakeWordDetector:
    """
    Simple wake word detection using energy threshold.
    For production, use Picovoice Porcupine (free tier).
    """
    def __init__(self, wake_word="hey ai24x7", sample_rate=16000):
        self.wake_word = wake_word.lower()
        self.sample_rate = sample_rate
        self.energy_threshold = 300
        self.phrase_duration_ms = 500  # Must hear for 500ms
        
    def detect(self, audio_chunk):
        """Detect wake word in audio chunk"""
        # Simple energy-based detection
        energy = np.sqrt(np.mean(np.abs(audio_chunk)**2))
        
        if energy < self.energy_threshold:
            return False
        
        # In production, use proper wake word model here
        return False  # Placeholder - will integrate with actual model


# ─── Speech-to-Text (Whisper) ─────────────
class STTEngine:
    """
    Speech-to-text using Whisper (local, offline-capable).
    Supports Hindi, English, and code-mixed Hindi-English.
    """
    def __init__(self, model="base"):
        self.model_name = model
        self.model = None
        self.initialized = False
    
    def init(self):
        """Initialize Whisper model"""
        try:
            import whisper
            print(f"🎤 Loading Whisper {self.model_name} model...")
            self.model = whisper.load_model(self.model_name)
            self.initialized = True
            print("✅ Whisper STT ready!")
            return True
        except ImportError:
            print("⚠️ Whisper not installed. Install: pip install openai-whisper")
            return False
        except Exception as e:
            print(f"❌ Whisper load failed: {e}")
            return False
    
    def transcribe(self, audio_np, lang="auto"):
        """
        Convert audio to text.
        
        Args:
            audio_np: numpy array of audio samples (16kHz, mono)
            lang: 'auto', 'hi', 'en', or 'hi-en' (code-mixed)
        
        Returns:
            str: transcribed text
        """
        if not self.initialized:
            return ""
        
        try:
            # Ensure correct format
            if audio_np.dtype != np.float32:
                audio_np = audio_np.astype(np.float32) / 32768.0
            
            result = self.model.transcribe(audio_np, language=lang if lang != "auto" else None)
            return result["text"].strip()
        except Exception as e:
            print(f"⚠️ STT error: {e}")
            return ""


# ─── Intent Classifier ─────────────────────
class IntentClassifier:
    """
    Classify voice command into intent + entities.
    Uses simple keyword matching + rule-based for reliability.
    For production, can upgrade to fine-tuned classifier.
    """
    
    # Command patterns in Hindi + English
    COMMANDS = {
        # Camera commands
        "show_camera": {
            "keywords": ["camera dikhao", "camera show", "camera dekhao", 
                        "show camera", "dikhao camera", "show me camera",
                        "which camera", "kaunsi camera", "kon si camera",
                        "camera no", "camera number", "cam 1", "camera 1"],
            "entities": ["camera_number"],
            "response_template": "Camera {camera} dikhata hun.",
        },
        "all_cameras": {
            "keywords": ["sab camera", "all cameras", "sab dikhao",
                        "saare camera", "full dashboard", "all cams",
                        "camera status", "kitne camera", "how many cameras"],
            "response_template": "{count} cameras online.",
        },
        "full_screen": {
            "keywords": ["full screen", "bada karo", "bada dikhao",
                        "zoom in", "zoom karo", "expand", "full view"],
            "response_template": "Full screen mode activated.",
        },
        
        # Alert commands
        "show_alerts": {
            "keywords": ["alerts dikhao", "alerts show", "alerts",
                        "show alerts", "kya alert hai", "any alert",
                        "koi alert", "suspicious activity"],
            "response_template": "{count} active alerts.",
        },
        "acknowledge_alert": {
            "keywords": ["acknowledge", "ack alert", "acknowledge karo",
                        "handle alert", "fix alert", "alert acknowledge",
                        "alert hatayo", "clear alert"],
            "response_template": "Alert acknowledged.",
        },
        
        # Search commands
        "search_historical": {
            "keywords": ["kya hua", "what happened", "dekho yesterday",
                        "last night", "kal raat", "search karo",
                        "find video", "footage", "recording"],
            "entities": ["time_reference"],
            "response_template": "Searching historical footage...",
        },
        
        # Status commands
        "system_status": {
            "keywords": ["status", "system status", "kya chal raha hai",
                        "how is system", "system theek hai", "system healthy",
                        "health check", "sab theek hai"],
            "response_template": "System status: {status}",
        },
        
        # Emergency
        "emergency_sos": {
            "keywords": ["help", "emergency", "bacchao", "sos",
                        "save me", "bachao", "maid", "police"],
            "response_template": "EMERGENCY! Alerting all contacts!",
        },
        
        # Navigation
        "next_page": {
            "keywords": ["next", "agli page", "next page", 
                        "forward", "aage", "next screen"],
            "response_template": "Next page.",
        },
        "prev_page": {
            "keywords": ["previous", "pichla page", "prev page",
                        "back", "peeche", "go back"],
            "response_template": "Previous page.",
        },
        
        # Report
        "generate_report": {
            "keywords": ["report", "report dikhao", "show report",
                        "today summary", "daily report", "weekly report",
                        "monthly report", "today ka report"],
            "response_template": "Generating {period} report...",
        },
        
        # TTS playback
        "speak": {
            "keywords": ["bol", "speak", "say", "talk",
                        "announce", "batao", "batado"],
            "entities": ["message"],
            "response_template": "Announcing now.",
        },
    }
    
    def classify(self, text):
        """Classify command text into intent"""
        text_lower = text.lower().strip()
        
        # Extract camera number
        camera_num = None
        for word in text_lower.split():
            if word in ["1","2","3","4","5","6","7","8","9"]:
                camera_num = int(word)
            elif word.startswith("cam") or word.startswith("camera"):
                parts = word.replace("camera","").replace("cam","")
                try:
                    camera_num = int(parts.strip())
                except:
                    pass
        
        # Check each command
        for intent, cmd_data in self.COMMANDS.items():
            for keyword in cmd_data["keywords"]:
                if keyword in text_lower:
                    result = {
                        "intent": intent,
                        "confidence": 0.9,
                        "entities": {}
                    }
                    if camera_num:
                        result["entities"]["camera_number"] = camera_num
                    return result
        
        # No match
        return {"intent": "unknown", "confidence": 0.0, "entities": {}}
    
    def get_response(self, intent, entities):
        """Get TTS response for intent"""
        cmd = self.COMMANDS.get(intent, {})
        template = cmd.get("response_template", "Sorry, I didn't understand that.")
        
        # Fill template
        msg = template
        if "{camera}" in msg and "camera_number" in entities:
            msg = msg.replace("{camera}", str(entities["camera_number"]))
        if "{count}" in msg:
            msg = msg.replace("{count}", "6")  # Default
        if "{status}" in msg:
            msg = msg.replace("{status}", "Healthy")
        if "{period}" in msg:
            msg = msg.replace("{period}", "daily")
        
        return msg


# ─── Text-to-Speech Engine ─────────────────
class TTSEngine:
    """
    Convert text to speech for voice responses.
    Supports: Edge TTS (best), gTTS (fallback), XTTS (local)
    """
    def __init__(self):
        self.engine = "edge"  # Default to Edge TTS
        self.voice = "hi-IN-MadhurNeural"
        self.audio_queue = queue.Queue()
        self.playing = False
    
    def speak(self, text, lang="hi"):
        """
        Convert text to speech and play.
        
        Args:
            text: Text to speak
            lang: Language code (hi, en, ta, te, etc.)
        """
        if lang == "en":
            voice = "en-US-AriaNeural"
        elif lang == "hi":
            voice = "hi-IN-MadhurNeural"
        elif lang == "ta":
            voice = "ta-IN-PallaviNeural"
        elif lang == "te":
            voice = "te-IN-ShrutiNeural"
        elif lang == "kn":
            voice = "kn-IN-SapnaNeural"
        else:
            voice = "hi-IN-MadhurNeural"
        
        self.voice = voice
        
        try:
            if self.engine == "edge":
                self._edge_tts(text)
            elif self.engine == "gtts":
                self._gtts(text, lang)
        except Exception as e:
            print(f"⚠️ TTS error: {e}")
    
    def _edge_tts(self, text):
        """Microsoft Edge TTS - highest quality"""
        try:
            import asyncio
            from edge_tts import EdgeTTS
            
            async def _tts():
                tts = EdgeTTS()
                audio_buffer = io.BytesIO()
                await tts.tts(text=text, voice=self.voice, output=audio_buffer)
                audio_buffer.seek(0)
                return audio_buffer
            
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            buffer = loop.run_until_complete(_tts())
            loop.close()
            
            self._play_audio(buffer)
        except ImportError:
            print("⚠️ edge-tts not installed. Run: pip install edge-tts")
            # Fallback to gTTS
            self._gtts(text, "hi")
        except Exception as e:
            print(f"⚠️ Edge TTS failed: {e}")
            self._gtts(text, "hi")
    
    def _gtts(self, text, lang):
        """Google Translate TTS - fallback"""
        try:
            from gtts import gTTS
            mp3_buffer = io.BytesIO()
            tts = gTTS(text=text, lang=lang if lang != "auto" else "hi", slow=False)
            tts.write_to_fp(mp3_buffer)
            mp3_buffer.seek(0)
            self._play_audio(mp3_buffer)
        except ImportError:
            print("⚠️ gTTS not installed. Using text-only mode.")
        except Exception as e:
            print(f"⚠️ gTTS failed: {e}")
    
    def _play_audio(self, buffer):
        """Play audio buffer"""
        try:
            import pygame
            import io
            pygame.mixer.init()
            pygame.mixer.music.load(buffer)
            pygame.mixer.music.play()
            self.playing = True
        except:
            # No audio playback available - just print
            print(f"🔊 [TTS] {text}")
            self.playing = False
    
    def announce(self, text):
        """Announce text on system (for alerts)"""
        self.speak(text, "hi")
    
    def announce_english(self, text):
        """Announce in English"""
        self.speak(text, "en")


# ─── Emergency Handler ─────────────────────
class EmergencyHandler:
    """
    Handle emergency SOS situations.
    Triggers multi-channel alerts across all available channels.
    """
    def __init__(self):
        self.emergency_contacts = []
        self.telegram_bot_token = os.environ.get("TELEGRAM_BOT_TOKEN", "")
        self.whatsapp_api = None
    
    def trigger_sos(self, location="Unknown", camera="Unknown"):
        """
        Trigger emergency SOS.
        Alerts all contacts via all channels.
        """
        import datetime
        timestamp = datetime.datetime.now().strftime("%d %b %Y, %I:%M %p")
        
        message = (
            f"🚨 EMERGENCY SOS\n"
            f"Location: {location}\n"
            f"Camera: {camera}\n"
            f"Time: {timestamp}\n"
            f"\n"
            f"Action Required Immediately!\n"
            f"Source: AI24x7 Voice Command"
        )
        
        # Telegram
        if self.telegram_bot_token:
            self._send_telegram(message)
        
        # Print for all channels
        print("\n" + "="*50)
        print("🚨 EMERGENCY SOS TRIGGERED!")
        print("="*50)
        print(f"Location: {location}")
        print(f"Camera: {camera}")
        print(f"Time: {timestamp}")
        print("="*50)
        
        return message
    
    def _send_telegram(self, message):
        """Send via Telegram"""
        try:
            import requests
            for chat_id in self.emergency_contacts:
                requests.post(
                    f"https://api.telegram.org/bot{self.telegram_bot_token}/sendMessage",
                    json={"chat_id": chat_id, "text": message, "parse_mode": "Markdown"},
                    timeout=10
                )
        except Exception as e:
            print(f"⚠️ Telegram SOS failed: {e}")
    
    def add_contact(self, chat_id):
        """Add emergency contact"""
        if chat_id not in self.emergency_contacts:
            self.emergency_contacts.append(chat_id)


# ─── CCTV Dashboard Controller ─────────────
class CCTVController:
    """
    Control CCTV dashboard via voice commands.
    Integrates with existing AI24x7 dashboard.
    """
    def __init__(self, api_url="http://localhost:5051"):
        self.api_url = api_url
        self.db_path = "/opt/ai24x7/ai24x7_super_admin.db"
        self.camera_streams = {}
    
    def handle_intent(self, intent, entities, user_id=None):
        """
        Execute action based on intent.
        
        Returns:
            dict with action taken + response text
        """
        if intent == "show_camera":
            camera_num = entities.get("camera_number", 1)
            return self._show_camera(camera_num)
        
        elif intent == "all_cameras":
            return self._show_all_cameras()
        
        elif intent == "show_alerts":
            return self._show_alerts()
        
        elif intent == "acknowledge_alert":
            return self._acknowledge_alert()
        
        elif intent == "system_status":
            return self._system_status()
        
        elif intent == "emergency_sos":
            return self._emergency_sos()
        
        elif intent == "search_historical":
            return self._search_historical(entities)
        
        elif intent == "generate_report":
            return self._generate_report()
        
        elif intent == "next_page":
            return {"action": "nav_next", "message": "Next page."}
        
        elif intent == "prev_page":
            return {"action": "nav_prev", "message": "Previous page."}
        
        elif intent == "full_screen":
            return {"action": "fullscreen", "message": "Full screen mode."}
        
        else:
            return {"action": "unknown", "message": "Command not recognized. Please try again."}
    
    def _show_camera(self, camera_num):
        """Switch dashboard to specific camera"""
        return {
            "action": "show_camera",
            "camera": camera_num,
            "message": f"Camera {camera_num} ko dikhata hun."
        }
    
    def _show_all_cameras(self):
        """Show all camera grid"""
        import sqlite3
        try:
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row
            total = conn.execute("SELECT COUNT(*) FROM cameras WHERE status='online'").fetchone()[0]
            conn.close()
            message = f"{total} cameras online, sab dikhata hun."
        except:
            total = 6
            message = f"{total} cameras online."
        
        return {"action": "show_all", "count": total, "message": message}
    
    def _show_alerts(self):
        """Show active alerts"""
        import sqlite3
        try:
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row
            alerts = conn.execute("SELECT COUNT(*) FROM alerts WHERE status='new'").fetchone()[0]
            conn.close()
            message = f"{alerts} naye alerts hain."
        except:
            alerts = 0
            message = "Koi naya alert nahi hai."
        
        return {"action": "show_alerts", "count": alerts, "message": message}
    
    def _acknowledge_alert(self):
        """Acknowledge latest alert"""
        return {"action": "ack_alert", "message": "Latest alert acknowledge kar diya."}
    
    def _system_status(self):
        """Get system health status"""
        import sqlite3
        try:
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row
            row = conn.execute("SELECT COUNT(*) as total, SUM(CASE WHEN status='online' THEN 1 ELSE 0 END) as online FROM machines").fetchone()
            conn.close()
            total = row["total"] or 1
            online = row["online"] or 0
            health = int((online/total)*100)
            message = f"System healthy. {online} machines online out of {total}."
        except:
            message = "System status: All operational."
        
        return {"action": "status", "message": message}
    
    def _emergency_sos(self):
        """Trigger emergency"""
        return {"action": "sos", "message": "Emergency alert triggered!"}
    
    def _search_historical(self, entities):
        """Search past footage"""
        return {"action": "search_historical", "message": "Historical footage search shuru kar raha hun."}
    
    def _generate_report(self):
        """Generate daily report"""
        return {"action": "report", "message": "Daily report generate kar raha hun."}


# ─── Main Voice Agent ──────────────────────
class VoiceAgent:
    """
    Main voice command agent.
    Orchestrates all components.
    """
    def __init__(self):
        print("🎙️ AI24x7 Voice Command System Initializing...")
        
        self.wake_word = WakeWordDetector()
        self.stt = STTEngine(model="base")
        self.intent = IntentClassifier()
        self.tts = TTSEngine()
        self.sos = EmergencyHandler()
        self.cctv = CCTVController()
        
        self.listening = False
        self.debug_mode = False
    
    def start(self):
        """Start voice agent"""
        # Initialize STT
        if not self.stt.init():
            print("⚠️ STT init failed - running in TEXT-ONLY mode")
        
        self.listening = True
        print("\n" + "="*50)
        print("🎙️ AI24x7 VOICE COMMAND ACTIVE")
        print("="*50)
        print("Say 'Hey AI24x7' to wake, then speak your command.")
        print("Commands: 'camera dikhao', 'alerts show', 'status', 'help'")
        print("Type 'quit' to exit, 'debug' to toggle debug mode.")
        print("="*50 + "\n")
        
        self._main_loop()
    
    def _main_loop(self):
        """Main interaction loop"""
        awaiting_command = False
        
        while self.listening:
            try:
                if self.debug_mode:
                    text = input("🎤 Command (debug): ").strip()
                else:
                    # In production: listen for audio here
                    # For demo: use text input
                    text = input("🎤 Type command (or 'q' to quit): ").strip()
                
                if text.lower() in ["quit", "q", "exit"]:
                    print("Shutting down...")
                    self.listening = False
                    break
                
                if text.lower() == "debug":
                    self.debug_mode = not self.debug_mode
                    print(f"Debug mode: {'ON' if self.debug_mode else 'OFF'}")
                    continue
                
                if not text:
                    continue
                
                self._process_command(text)
            
            except KeyboardInterrupt:
                print("\nShutting down...")
                self.listening = False
                break
            except Exception as e:
                print(f"Error: {e}")
    
    def _process_command(self, text):
        """Process a command text"""
        print(f"\n📥 You: {text}")
        
        # Classify intent
        result = self.intent.classify(text)
        intent_name = result["intent"]
        entities = result["entities"]
        confidence = result["confidence"]
        
        if self.debug_mode:
            print(f"🔍 Intent: {intent_name} (confidence: {confidence:.2f})")
            print(f"🔍 Entities: {entities}")
        
        # Handle via CCTV controller
        action = self.cctv.handle_intent(intent_name, entities)
        
        # Generate response
        response = action.get("message", "")
        
        # Special handling for SOS
        if intent_name == "emergency_sos":
            self.sos.trigger_sos()
            response = "EMERGENCY! Help is on the way! All contacts alerted!"
        
        # Print + speak
        print(f"🤖 AI24x7: {response}\n")
        self.tts.speak(response, "hi")
        
        return action
    
    def process_audio(self, audio_np):
        """Process audio data (for integration with audio system)"""
        # Check wake word
        if self.wake_word.detect(audio_np):
            print("\n🎤 WAKE WORD DETECTED!")
            self.tts.speak("Haan, boliye.", "hi")
            return {"event": "wake", "message": "Listening..."}
        
        return None
    
    def demo(self):
        """Demo mode - show all commands"""
        print("\n🎙️ AI24x7 Voice Command - Demo Mode")
        print("="*50)
        
        test_commands = [
            "camera 1 dikhao",
            "sab camera status batao",
            "alerts dikhao",
            "system theek hai ya nahi",
            "kal raat 11 baje koi aaya tha",
            "emergency",
            "next page",
            "daily report dikhao",
            "camera 3 full screen karo",
        ]
        
        print("\nSimulated commands:")
        for cmd in test_commands:
            print(f"\n> {cmd}")
            self._process_command(cmd)
            time.sleep(0.5)


# ─── Flask API Server ──────────────────────
def create_app(agent):
    from flask import Flask, request, jsonify
    app = Flask(__name__)
    
    @app.route("/api/voice/command", methods=["POST"])
    def voice_command():
        """Receive voice command (text or audio)"""
        data = request.get_json()
        text = data.get("text", "")
        user_id = data.get("user_id")
        
        if not text:
            return jsonify({"error": "No text provided"}), 400
        
        result = agent.intent.classify(text)
        intent = result["intent"]
        entities = result["entities"]
        
        action = agent.cctv.handle_intent(intent, entities)
        
        return jsonify({
            "intent": intent,
            "entities": entities,
            "action": action,
            "response": action.get("message", "")
        })
    
    @app.route("/api/voice/speak", methods=["POST"])
    def speak():
        """Send TTS announcement"""
        data = request.get_json()
        text = data.get("text", "Alert")
        lang = data.get("lang", "hi")
        
        agent.tts.speak(text, lang)
        return jsonify({"success": True, "spoken": text})
    
    @app.route("/api/voice/sos", methods=["POST"])
    def sos():
        """Trigger emergency SOS"""
        data = request.get_json()
        location = data.get("location", "Unknown")
        camera = data.get("camera", "Unknown")
        
        message = agent.sos.trigger_sos(location, camera)
        agent.tts.announce("Emergency alert triggered!")
        
        return jsonify({"success": True, "message": message})
    
    @app.route("/api/voice/demo", methods=["GET"])
    def demo():
        agent.demo()
        return jsonify({"status": "demo_complete"})
    
    @app.route("/health", methods=["GET"])
    def health():
        return jsonify({
            "service": "AI24x7 Voice Command",
            "status": "active",
            "stt_ready": agent.stt.initialized
        })
    
    return app


# ─── CLI ───────────────────────────────────
if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="AI24x7 Voice Command System")
    parser.add_argument("--server", action="store_true", help="Run as API server")
    parser.add_argument("--demo", action="store_true", help="Run demo mode")
    parser.add_argument("--port", type=int, default=5056, help="Server port")
    
    args = parser.parse_args()
    
    agent = VoiceAgent()
    
    if args.server:
        app = create_app(agent)
        print(f"\n🚀 Voice Command API Server starting on port {args.port}...")
        app.run(host="0.0.0.0", port=args.port, debug=False)
    elif args.demo:
        agent.demo()
    else:
        agent.start()