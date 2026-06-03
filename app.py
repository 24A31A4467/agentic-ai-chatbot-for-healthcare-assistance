import email
from urllib import response

from apscheduler.schedulers.background import BackgroundScheduler
from datetime import datetime
import pytz
import os
import json
from flask import Flask, request, jsonify, Response, render_template, redirect, url_for
from flask_cors import CORS
from google import genai
from dotenv import load_dotenv
import requests
import random
import time
from services.email_service import send_otp_email
from services.email_service import (
    send_appointment_email,
    send_emergency_email,
    send_medication_reminder_email
)

load_dotenv()
import hashlib

USERS_FILE = "users.json"

def load_users():
    if os.path.exists(USERS_FILE):
        with open(USERS_FILE, "r") as f:
            return json.load(f)
    return {}

def save_users(users):
    with open(USERS_FILE, "w") as f:
        json.dump(users, f, indent=4)

def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()


app = Flask(__name__)
scheduler = BackgroundScheduler()
scheduler.start()
app.secret_key = "healthai_secret_key"
CORS(app, resources={r"/*": {"origins": "*"}})

# ── Gemini Client ─────────────────────────────────────────────────────────────
client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))

HISTORY_DIR = "chat_histories"
os.makedirs(HISTORY_DIR, exist_ok=True)

def get_history_file(email):
    safe = email.replace('@','_').replace('.','_')
    return os.path.join(HISTORY_DIR, f"{safe}.json")
MODEL = "gemini-2.5-flash"

SYSTEM_INSTRUCTION = """You are "Autonomous Agent Care", an advanced autonomous healthcare AI assistant.

CORE CAPABILITIES:

1. SYMPTOM ANALYSIS
- Analyze user symptoms carefully.
- Ask clarifying medical questions when necessary.
- Always classify severity with exactly one tag: [SEVERITY:Mild], [SEVERITY:Moderate], [SEVERITY:Severe], or [SEVERITY:Emergency]
- Never prescribe medications.
- Always end with: ⚠️ This is not medical advice.

2. EMERGENCY DETECTION
If the user reports chest pain, difficulty breathing, severe bleeding, loss of consciousness, stroke symptoms, suicidal thoughts, severe allergic reaction:
- Begin response with [EMERGENCY_DETECTED]
- Provide calm first-aid guidance
- Ask for confirmation to call emergency services.

3. APPOINTMENT BOOKING
For Moderate or Severe (non-emergency) symptoms, recommend a doctor.
When all details collected (date, time, location, specialist), include:
[BOOK_APPOINTMENT:{"date":"...","time":"...","location":"...","specialist":"...","reason":"..."}]

4. MEDICATION REMINDERS
When user wants reminders and all details collected:
[SET_REMINDER:{"medicine":"...","dosage":"...","frequency":"...","duration":"..."}]

5. EMAIL
After booking/emergency:
[SEND_EMAIL:{"to":"patient@example.com","subject":"...","body":"..."}]

6. PROACTIVE BEHAVIOR
Suggest hydration, rest, follow-ups. Be proactive.

7. SAFETY
Never diagnose definitively. Never prescribe. Always end with disclaimer.

8. TONE: Calm, empathetic, professional, reassuring.

9. HOSPITAL RECOMMENDATION
When severity is Moderate, Severe, or Emergency, detect the medical specialty needed and include exactly one tag:
[SPECIALTY:General] for general symptoms
[SPECIALTY:Cardiology] for chest pain, heart issues
[SPECIALTY:Neurology] for headache, stroke, seizures
[SPECIALTY:Orthopedics] for bone, joint, fracture issues
[SPECIALTY:Pediatrics] for children's symptoms
[SPECIALTY:Psychiatry] for mental health issues
[SPECIALTY:Ophthalmology] for eye problems
[SPECIALTY:ENT] for ear, nose, throat issues
[SPECIALTY:Gynecology] for women's health issues
[SPECIALTY:Dermatology] for skin issues
[SPECIALTY:Emergency] for life threatening emergencies
9. HOSPITAL RECOMMENDATION
When severity is Moderate, Severe, or Emergency — always include this tag:
[SPECIALTY:SpecialtyName]
Examples:
- chest pain → [SPECIALTY:Cardiology]
- child fever → [SPECIALTY:Pediatrics]
- breathing issue → [SPECIALTY:Pulmonology]
- broken bone → [SPECIALTY:Orthopedics]
- eye problem → [SPECIALTY:Ophthalmology]
- mental health → [SPECIALTY:Psychiatry]
- ear problem → [SPECIALTY:ENT]
- skin rash → [SPECIALTY:Dermatology]
- stomach pain → [SPECIALTY:Gastroenterology]
- general fever → [SPECIALTY:General Medicine]"""


# ── Memory Helpers ────────────────────────────────────────────────────────────
def load_chat_history(email=None):
    if email:
        path = get_history_file(email)
    else:
        path = os.path.join(HISTORY_DIR, "default.json")
    if os.path.exists(path):
        with open(path, "r") as f:
            return json.load(f)
    return []

def serialize_history(curated_history):
    result = []
    for turn in curated_history:
        try:
            role = turn.role if hasattr(turn, 'role') else turn.get('role', 'user')
            parts = turn.parts if hasattr(turn, 'parts') else turn.get('parts', [])
            text_parts = []
            for part in parts:
                if hasattr(part, 'text'):
                    text_parts.append({"text": part.text})
                elif isinstance(part, dict) and 'text' in part:
                    text_parts.append({"text": part['text']})
            if text_parts:
                result.append({"role": role, "parts": text_parts})
        except Exception:
            continue
    return result

def save_chat_history(curated_history, email=None):
    serialized = serialize_history(curated_history)
    if email:
        path = get_history_file(email)
    else:
        path = os.path.join(HISTORY_DIR, "default.json")
    with open(path, "w") as f:
        json.dump(serialized, f, indent=4)
    print(f"--- Saved {len(serialized)} messages for {email or 'default'} ---")


def trigger_zapier(url, event_type, data):
    try:
        payload = {"event": event_type, **data}
        requests.post(url, json=payload)
        print(f"--- Zapier triggered: {event_type} ---")
    except Exception as e:
        print(f"Zapier error: {e}")


# ── Chat Session ──────────────────────────────────────────────────────────────
def create_chat(email=None):
    past_history = load_chat_history(email)
    print(f"--- Loaded {len(past_history)} past messages for {email or 'default'} ---")
    return client.chats.create(
        model=MODEL,
        history=past_history,
        config={"system_instruction": SYSTEM_INSTRUCTION}
    )

chat = create_chat()


# ── Page Routes ───────────────────────────────────────────────────────────────
@app.route("/")
def index():
    return render_template("auth.html")   # Login page loads first

@app.route("/home")
def home():
    return render_template("index.html")  # Chatbot loads after login

@app.route("/hospital_finder")
@app.route("/hospital-finder")
def hospital_finder():
    return render_template("hospital_finder.html")

@app.route("/auth")
def auth():
    return render_template("auth.html")   # Direct auth access


# ── Chat Routes ───────────────────────────────────────────────────────────────
@app.route("/chat", methods=["POST"])
def chat_endpoint():
    data         = request.get_json(force=True, silent=True) or {}
    user_message = data.get("message", "").strip()
    user_email   = data.get("email", None)  # ← get email from request

    if not user_message:
        return jsonify({"error": "Empty message"}), 400

    def generate():
        global chat
        try:
            response = chat.send_message_stream(user_message)
            full_response = ""
            for chunk in response:
                if chunk.text:
                    full_response += chunk.text
                    yield f"data: {json.dumps({'chunk': chunk.text})}\n\n"

            save_chat_history(chat._curated_history, user_email)  # ← save per user
            yield f"data: {json.dumps({'done': True, 'full': full_response})}\n\n"

        except Exception as e:
            print(f"Gemini error: {e}")
            yield f"data: {json.dumps({'error': str(e)})}\n\n"

    return Response(generate(), mimetype="text/event-stream",
        headers={"Cache-Control":"no-cache","X-Accel-Buffering":"no","Access-Control-Allow-Origin":"*"})

# ── OTP Store (in memory) ─────────────────────────────
otp_store = {}  # { email: { otp, expiry } }

@app.route("/send-otp", methods=["POST"])
def send_otp():
    data  = request.get_json(force=True, silent=True) or {}
    email = data.get("email", "").strip().lower()

    if not email or "@" not in email:
        return jsonify({"error": "Invalid email"}), 400

    # Generate 6 digit OTP
    otp = str(random.randint(100000, 999999))

    # Store with 10 min expiry
    otp_store[email] = {
        "otp":    otp,
        "expiry": time.time() + 600  # 10 minutes
    }

    # Send real email
    success = send_otp_email(email, otp)

    if success:
        print(f"--- ✅ OTP sent to {email}: {otp} ---")
        return jsonify({"status": "sent"})
    else:
        return jsonify({"error": "Failed to send email"}), 500


@app.route("/verify-otp", methods=["POST"])
def verify_otp():
    data    = request.get_json(force=True, silent=True) or {}
    email   = data.get("email", "").strip().lower()
    entered = data.get("otp", "").strip()

    if email not in otp_store:
        return jsonify({"verified": False, "error": "No OTP sent to this email"}), 400

    stored = otp_store[email]

    # Check expiry
    if time.time() > stored["expiry"]:
        del otp_store[email]
        return jsonify({"verified": False, "error": "OTP expired. Please request a new one."}), 400

    # Check OTP
    if entered == stored["otp"]:
        del otp_store[email]  # delete after use
        return jsonify({"verified": True})
    else:
        return jsonify({"verified": False, "error": "Incorrect OTP"}), 400
@app.route("/clear", methods=["POST"])
def clear_history():
    global chat
    data       = request.get_json(force=True, silent=True) or {}
    user_email = data.get("email", None)

    if user_email:
        path = get_history_file(user_email)
        if os.path.exists(path):
            os.remove(path)
    else:
        # Clear default
        path = os.path.join(HISTORY_DIR, "default.json")
        if os.path.exists(path): os.remove(path)

    chat = create_chat(user_email)
    print(f"--- Chat memory cleared for {user_email or 'default'} ---")
    return jsonify({"status": "cleared"})


@app.route("/history", methods=["GET"])
def get_history():
    return jsonify(load_chat_history())


# ── Zapier Routes ─────────────────────────────────────────────────────────────
# ── Email Routes (No Zapier) ──────────────────────────────────────────────────
@app.route("/zapier/reminder", methods=["POST"])
def zapier_reminder():
    data = request.get_json(force=True, silent=True) or {}

    medicine  = data.get("medicine")
    dosage    = data.get("dosage")
    frequency = data.get("frequency")
    duration  = data.get("duration")
    email     = data.get("email", os.getenv("GMAIL_ADDRESS"))
    send_time = data.get("send_time")  # Format: "HH:MM" e.g. "08:30"

    details = {
        "medicine":  medicine,
        "dosage":    dosage,
        "frequency": frequency,
        "duration":  duration
    }

    if send_time:
        try:
            hour, minute = map(int, send_time.split(":"))

            # Schedule email at exact time every day
            scheduler.add_job(
                func=send_medication_reminder_email,
                trigger="cron",
                hour=hour,
                minute=minute,
                args=[email, details],
                id=f"reminder_{medicine}_{hour}_{minute}",
                replace_existing=True
            )

            print(f"--- ✅ Reminder scheduled at {send_time} for {medicine} ---")
            return jsonify({"status": "scheduled", "time": send_time})

        except Exception as e:
            print(f"--- ❌ Scheduler error: {e} ---")
            return jsonify({"error": str(e)}), 500
    else:
        # No time given — send immediately
        success = send_medication_reminder_email(email, details)
        return jsonify({"status": "sent" if success else "failed"})


@app.route("/zapier/appointment", methods=["POST"])
def zapier_appointment():
    data = request.get_json(force=True, silent=True) or {}
    success = send_appointment_email(
        to_email=data.get("email", os.getenv("GMAIL_ADDRESS")),
        details=data
    )
    return jsonify({"status": "sent" if success else "failed"})


@app.route("/zapier/emergency", methods=["POST"])
def zapier_emergency():
    data = request.get_json(force=True, silent=True) or {}
    print(f"--- Emergency data received: {data} ---")
    emergency_contact = {
        "patient_name": data.get("patient_name", "Unknown"),
        "name":         data.get("emergency_name", ""),
        "email":        data.get("emergency_email", ""),
        "relation":     data.get("emergency_relation", ""),
        "phone":        data.get("emergency_phone", "")
    }
    print(f"--- Sending to emergency contact: {emergency_contact} ---")
    success = send_emergency_email(
        to_email=os.getenv("GMAIL_ADDRESS"),
        emergency_contact=emergency_contact
    )
    return jsonify({"status": "sent" if success else "failed"})


@app.route("/get-hospitals", methods=["POST"])
def get_hospitals():
    data     = request.get_json(force=True, silent=True) or {}
    lat      = data.get("lat")
    lng      = data.get("lng")
    specialty = data.get("specialty", "General Medicine")
    radius   = data.get("radius", 10000)  # meters

    try:
        query = f"""
        [out:json][timeout:30];
        (
          node["amenity"="hospital"](around:{radius},{lat},{lng});
          way["amenity"="hospital"](around:{radius},{lat},{lng});
          relation["amenity"="hospital"](around:{radius},{lat},{lng});
          node["amenity"="clinic"](around:{radius},{lat},{lng});
          way["amenity"="clinic"](around:{radius},{lat},{lng});
          relation["amenity"="clinic"](around:{radius},{lat},{lng});
          node["healthcare"~"hospital|clinic"](around:{radius},{lat},{lng});
          way["healthcare"~"hospital|clinic"](around:{radius},{lat},{lng});
          relation["healthcare"~"hospital|clinic"](around:{radius},{lat},{lng});
        );
        out body;>;out skel qt;
        """
        response = requests.get(
            "https://overpass-api.de/api/interpreter",
            params={"data": query},
            timeout=25
        )
        # CORRECT:
        elements = response.json().get("elements", [])
        return jsonify({"elements": elements, "specialty": specialty})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/register", methods=["POST"])
def register():
    data     = request.get_json(force=True, silent=True) or {}
    email    = data.get("email", "").strip().lower()
    phone    = data.get("phone", "").strip()
    password = data.get("password", "").strip()
    name     = data.get("name", "").strip()

    if not email or not password:
        return jsonify({"error": "Email and password required"}), 400

    users = load_users()

    # Check if email already registered
    if email in users:
        return jsonify({"error": "email_exists"}), 400

    # Check if phone already registered
    for u in users.values():
        if u.get("phone") == phone:
            return jsonify({"error": "phone_exists"}), 400

    # Save new user
    users[email] = {
        "name":             name,
        "email":            email,
        "phone":            phone,
        "password":         hash_password(password),
        "emergency_name":   data.get("emergency_name", ""),
        "emergency_email":  data.get("emergency_email", ""),
        "emergency_phone":  data.get("emergency_phone", ""),
        "emergency_relation": data.get("emergency_relation", ""),
        "created_at":       __import__('datetime').datetime.now().isoformat()
    }
    save_users(users)
    print(f"--- ✅ New user registered: {email} ---")
    return jsonify({"status": "registered"})


@app.route("/login", methods=["POST"])
def login():
    data     = request.get_json(force=True, silent=True) or {}
    email    = data.get("email", "").strip().lower()
    password = data.get("password", "").strip()

    if not email or not password:
        return jsonify({"error": "Email and password required"}), 400

    users = load_users()

    if email not in users:
        return jsonify({"error": "not_registered"}), 400

    if users[email]["password"] != hash_password(password):
        return jsonify({"error": "wrong_password"}), 400

    user = users[email]
    schat = create_chat(email)
    # Load user's previous chat
    chat = create_chat(email)
    print(f"--- ✅ User logged in: {email} ---")
    # Load user's previous chat
    return jsonify({
        "status":             "success",
        "name":               user.get("name"),
        "email":              email,
        "phone":              user.get("phone"),
        "emergency_name":     user.get("emergency_name"),
        "emergency_email":    user.get("emergency_email"),
        "emergency_phone":    user.get("emergency_phone"),
        "emergency_relation": user.get("emergency_relation"),
    })

@app.route("/overpass-proxy", methods=["POST"])
def overpass_proxy():
    data = request.get_json(force=True, silent=True) or {}
    query = data.get("query", "")
    if not query:
        return jsonify({"error": "No query"}), 400

    mirrors = [
        "https://overpass-api.de/api/interpreter",
        "https://overpass.kumi.systems/api/interpreter",
        "https://maps.mail.ru/osm/tools/overpass/api/interpreter",
    ]
    for mirror in mirrors:
        try:
            r = requests.post(
                mirror,
                data={"data": query},
                timeout=20,
                headers={"User-Agent": "HealthAI/1.0"}
            )
            if r.ok:
                elements = r.json().get("elements", [])
                return jsonify({"elements": elements})
        except Exception as e:
            print(f"Mirror {mirror} failed: {e}")
            continue

    return jsonify({"error": "All mirrors failed", "elements": []}), 503


# ── Run ───────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    os.makedirs("templates", exist_ok=True)
    print("--- 🏥 Autonomous Agent Care running at http://localhost:5000 ---")
    app.run(debug=True, port=5000, threaded=True)
# ── Run ───────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    os.makedirs("templates", exist_ok=True)
    print("--- 🏥 Autonomous Agent Care running at http://localhost:5000 ---")
    app.run(debug=True, port=5000, threaded=True)