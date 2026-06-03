"""
voice_chatbot.py
────────────────────────────────────────────────────────────────
Voice-enabled Healthcare Chatbot — Speech-to-Text Integration
Integrates SpeechRecognition (Google backend) with Gemini chatbot.

Dependencies:
    pip install SpeechRecognition pyaudio

Usage:
    Run directly:   python voice_chatbot.py
    Import module:  from voice_chatbot import run_voice_assistant
────────────────────────────────────────────────────────────────
"""

import sys
import time
import requests
import json
import speech_recognition as sr
try:
    import speech_recognition as sr
except ImportError:
    print("Error: speech_recognition module not found. Please install it using 'pip install SpeechRecognition'")
    sys.exit(1)

# ──────────────────────────────────────────────────────────────
# STUB — replace with your actual Gemini chatbot function
# ──────────────────────────────────────────────────────────────
def gemini_chatbot(user_input: str) -> str:
    """
    Sends voice-recognised text to your running Flask chatbot
    at localhost:5000/chat and returns the full response.
    Make sure your app.py (Flask server) is running first!
    """
    try:
        response = requests.post(
            "http://localhost:5000/chat",
            json={"message": user_input, "email": None},
            stream=True,
            timeout=30
        )

        full_response = ""

        # Your app.py streams chunks — collect them all
        for line in response.iter_lines():
            if line:
                line = line.decode("utf-8")
                if line.startswith("data: "):
                    data = json.loads(line[6:])
                    if "chunk" in data:
                        full_response += data["chunk"]
                    elif "done" in data:
                        break
                    elif "error" in data:
                        return f"Chatbot error: {data['error']}"

        return full_response if full_response else "No response received."

    except requests.exceptions.ConnectionError:
        return "❌ Cannot connect to chatbot. Make sure app.py is running on port 5000."
    except Exception as e:
        return f"❌ Error: {e}"

# ──────────────────────────────────────────────────────────────
# CONSTANTS — tune these to your environment
# ──────────────────────────────────────────────────────────────
AMBIENT_NOISE_DURATION  = 1      # seconds to sample ambient noise
LISTEN_TIMEOUT          = 10     # max seconds to wait for speech to start
PHRASE_TIME_LIMIT       = 15     # max seconds for a single utterance
PAUSE_THRESHOLD         = 0.9    # seconds of silence that ends a phrase
LANGUAGE                = "en-US"  # BCP-47 language tag for Google STT
RETRY_DELAY             = 2      # seconds to wait before re-listening after error


# ──────────────────────────────────────────────────────────────
# INITIALISE RECOGNISER (module-level, shared across calls)
# ──────────────────────────────────────────────────────────────
recognizer = sr.Recognizer()

# Fine-tune VAD sensitivity:
#   pause_threshold  – silence duration (s) that signals end-of-speech
#   energy_threshold – mic volume threshold; auto-adjusted below
recognizer.pause_threshold = PAUSE_THRESHOLD


# ──────────────────────────────────────────────────────────────
# HELPER: pretty console output
# ──────────────────────────────────────────────────────────────
def _print_section(label: str, content: str, symbol: str = "─") -> None:
    """Print a clearly labelled, bordered console block."""
    width = 60
    print(f"\n{symbol * width}")
    print(f"  {label}")
    print(f"{symbol * width}")
    print(f"  {content}")
    print(f"{symbol * width}")


# ──────────────────────────────────────────────────────────────
# CORE: listen to the microphone and return recognised text
# ──────────────────────────────────────────────────────────────
def listen_for_voice() -> str | None:
    """
    Open the default microphone, adjust for ambient noise, capture
    one patient utterance, and transcribe it via Google Speech-to-Text.

    Returns:
        str   – The recognised transcript (stripped).
        None  – If speech could not be recognised or an error occurred.

    Error categories handled:
        UnknownValueError   – Microphone picked up audio but STT failed.
        RequestError        – Network / Google API unreachable.
        WaitTimeoutError    – No speech detected within LISTEN_TIMEOUT.
        OSError             – No microphone found or device error.
    """
    try:
        with sr.Microphone() as mic:
            # ── Step 1: calibrate energy threshold to current background noise
            print("\n  🎙  Adjusting for ambient noise — please wait…", end="", flush=True)
            recognizer.adjust_for_ambient_noise(mic, duration=AMBIENT_NOISE_DURATION)
            print(f" done  (energy threshold = {recognizer.energy_threshold:.0f})")

            # ── Step 2: wait for the patient to speak
            print("  🟢  Listening… (speak now)\n")
            audio = recognizer.listen(
                mic,
                timeout=LISTEN_TIMEOUT,
                phrase_time_limit=PHRASE_TIME_LIMIT,
            )

    except OSError as exc:
        # Microphone not found, permission denied, or device error
        print(f"\n  ❌  Microphone error: {exc}")
        print("      Check that a microphone is connected and accessible.")
        return None

    except sr.WaitTimeoutError:
        # No speech detected before LISTEN_TIMEOUT expired
        print("\n  ⏱  No speech detected — timed out. Please try again.")
        return None

    # ── Step 3: send captured audio to Google Speech Recognition
    try:
        text = recognizer.recognize_google(audio, language=LANGUAGE)
        return text.strip()

    except sr.UnknownValueError:
        # Audio was captured but could not be transcribed
        print("\n  🔇  Could not understand the audio. Please speak clearly and try again.")
        return None

    except sr.RequestError as exc:
        # Network issue or Google API returned an error
        print(f"\n  🌐  Google Speech API error: {exc}")
        print("      Check your internet connection.")
        return None


# ──────────────────────────────────────────────────────────────
# CORE: obtain input — voice OR typed fallback
# ──────────────────────────────────────────────────────────────
def get_patient_input(mode: str = "voice") -> str | None:
    """
    Collect patient input in the requested mode.

    Args:
        mode: "voice"  – microphone (default)
              "text"   – typed keyboard input
              "hybrid" – try voice first, fall back to text on failure

    Returns:
        Recognised / typed text, or None if nothing was captured.
    """
    if mode == "text":
        raw = input("\n  ✏️  Type your message (or 'quit' to exit): ").strip()
        return raw if raw else None

    if mode == "voice":
        return listen_for_voice()

    if mode == "hybrid":
        result = listen_for_voice()
        if result is None:
            print("  ℹ️  Voice failed — switching to text input.")
            raw = input("  ✏️  Type your message (or 'quit' to exit): ").strip()
            return raw if raw else None
        return result

    raise ValueError(f"Unknown mode '{mode}'. Choose 'voice', 'text', or 'hybrid'.")


# ──────────────────────────────────────────────────────────────
# CORE: process one full turn (STT → Gemini → display)
# ──────────────────────────────────────────────────────────────
def process_turn(mode: str = "voice") -> bool:
    """
    Execute a single conversation turn.

    Returns:
        True  – continue the loop.
        False – user requested exit.
    """
    # ── Step 1: get patient input
    user_text = get_patient_input(mode=mode)

    if user_text is None:
        # Nothing captured; pause briefly then retry
        time.sleep(RETRY_DELAY)
        return True

    # ── Step 2: check for exit commands
    if user_text.lower() in {"quit", "exit", "stop", "bye", "goodbye"}:
        print("\n  👋  Session ended. Take care!")
        return False

    # ── Step 3: display what was heard / typed
    _print_section("🗣  Patient Said", user_text)

    # ── Step 4: pass recognised text to the Gemini chatbot
    print("\n  ⏳  Processing your request…")
    try:
        response = gemini_chatbot(user_text)
    except Exception as exc:                          # broad catch for chatbot errors
        print(f"\n  ❌  Chatbot error: {exc}")
        print("      The chatbot encountered a problem. Please try again.")
        return True

    # ── Step 5: display the chatbot's response
    _print_section("🤖  Healthcare Assistant", response, symbol="═")

    return True


# ──────────────────────────────────────────────────────────────
# MAIN: continuous assistant loop
# ──────────────────────────────────────────────────────────────
def run_voice_assistant(mode: str = "voice") -> None:
    """
    Run the healthcare voice assistant in a continuous loop until
    the user says / types a quit command or presses Ctrl+C.

    Args:
        mode: "voice" | "text" | "hybrid"
    """
    print("\n" + "═" * 60)
    print("  🏥  Healthcare Voice Assistant — Starting Up")
    print(f"  Mode : {mode.upper()}")
    print(f"  Lang : {LANGUAGE}")
    print("═" * 60)
    print("  Say (or type) 'quit' / 'exit' at any time to end.\n")

    try:
        while True:
            keep_going = process_turn(mode=mode)
            if not keep_going:
                break

    except KeyboardInterrupt:
        print("\n\n  ⛔  Session interrupted by user. Goodbye!")

    finally:
        print("\n" + "═" * 60)
        print("  Healthcare Voice Assistant — Session Closed")
        print("═" * 60 + "\n")


# ──────────────────────────────────────────────────────────────
# ENTRY POINT
# ──────────────────────────────────────────────────────────────
if __name__ == "__main__":
    # Optionally pass mode via command-line: python voice_chatbot.py text
    input_mode = sys.argv[1] if len(sys.argv) > 1 else "voice"

    if input_mode not in {"voice", "text", "hybrid"}:
        print(f"Unknown mode '{input_mode}'. Use: voice | text | hybrid")
        sys.exit(1)

    run_voice_assistant(mode=input_mode)