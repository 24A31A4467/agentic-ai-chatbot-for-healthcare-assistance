import smtplib
import os
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from dotenv import load_dotenv

load_dotenv()

GMAIL         = os.getenv("GMAIL_ADDRESS")
GMAIL_PASSWORD = os.getenv("GMAIL_APP_PASSWORD")


def send_email(to_email, subject, body):
    """Core function — sends any email via Gmail."""
    try:
        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"]    = f"HealthAI Assistant <{GMAIL}>"
        msg["To"]      = to_email

        msg.attach(MIMEText(body, "html"))

        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
            server.login(GMAIL, GMAIL_PASSWORD)
            server.sendmail(GMAIL, to_email, msg.as_string())

        print(f"--- ✅ Email sent to {to_email} ---")
        return True

    except Exception as e:
        print(f"--- ❌ Email error: {e} ---")
        return False


# ── 1. OTP Email ──────────────────────────────────────────────────────────────
def send_otp_email(to_email, otp):
    subject = "🔐 Your HealthAI Verification Code"
    body = f"""
    <div style="font-family:Arial,sans-serif;max-width:500px;margin:auto;padding:30px;
                border-radius:12px;border:1px solid #e0e0e0;">
        <h2 style="color:#0a4d68;">HealthAI Verification</h2>
        <p>Your one-time verification code is:</p>
        <div style="font-size:36px;font-weight:bold;color:#00c9a7;
                    letter-spacing:10px;padding:20px 0;">{otp}</div>
        <p style="color:#666;">This code is valid for <b>10 minutes.</b></p>
        <p style="color:#999;font-size:12px;">If you didn't request this, ignore this email.</p>
    </div>
    """
    return send_email(to_email, subject, body)


# ── 2. Appointment Email ──────────────────────────────────────────────────────
def send_appointment_email(to_email, details):
    subject = "📅 Appointment Confirmation — HealthAI"
    body = f"""
    <div style="font-family:Arial,sans-serif;max-width:500px;margin:auto;padding:30px;
                border-radius:12px;border:1px solid #e0e0e0;">
        <h2 style="color:#0a4d68;">Appointment Confirmed ✅</h2>
        <p>Your appointment has been booked successfully.</p>
        <table style="width:100%;border-collapse:collapse;margin-top:16px;">
            <tr style="background:#f4f9f9;">
                <td style="padding:10px;font-weight:bold;color:#0a4d68;">Specialist</td>
                <td style="padding:10px;">{details.get('specialist', 'N/A')}</td>
            </tr>
            <tr>
                <td style="padding:10px;font-weight:bold;color:#0a4d68;">Date</td>
                <td style="padding:10px;">{details.get('date', 'N/A')}</td>
            </tr>
            <tr style="background:#f4f9f9;">
                <td style="padding:10px;font-weight:bold;color:#0a4d68;">Time</td>
                <td style="padding:10px;">{details.get('time', 'N/A')}</td>
            </tr>
            <tr>
                <td style="padding:10px;font-weight:bold;color:#0a4d68;">Location</td>
                <td style="padding:10px;">{details.get('location', 'N/A')}</td>
            </tr>
            <tr style="background:#f4f9f9;">
                <td style="padding:10px;font-weight:bold;color:#0a4d68;">Reason</td>
                <td style="padding:10px;">{details.get('reason', 'N/A')}</td>
            </tr>
        </table>
        <p style="margin-top:20px;color:#666;">Please arrive 10 minutes early.</p>
        <p style="color:#999;font-size:12px;">⚠️ This is an automated message from HealthAI.</p>
    </div>
    """
    return send_email(to_email, subject, body)


# ── 3. Emergency Alert Email ──────────────────────────────────────────────────
def send_emergency_email(to_email, emergency_contact=None):
    subject = "🚨 EMERGENCY ALERT — HealthAI"

    # ── Email 1: To Doctor/Provider ──────────────────
    provider_body = f"""
    <div style="font-family:Arial,sans-serif;max-width:550px;margin:auto;padding:30px;
                border-radius:12px;border:2px solid #ff4d6d;background:#fff;">
        <div style="background:#ff4d6d;padding:16px;border-radius:8px;text-align:center;margin-bottom:20px;">
            <h2 style="color:white;margin:0;font-size:22px;">🚨 MEDICAL EMERGENCY ALERT</h2>
        </div>
        <p style="font-size:15px;color:#333;">A patient has triggered an emergency alert 
        via <strong>HealthAI Assistant</strong> and requires <strong>immediate medical attention.</strong></p>
        <table style="width:100%;border-collapse:collapse;margin:16px 0;border-radius:8px;overflow:hidden;">
            <tr style="background:#fff0f3;">
                <td style="padding:12px;font-weight:bold;color:#cc0000;width:40%;">Patient Name</td>
                <td style="padding:12px;color:#333;">{emergency_contact.get('patient_name','Unknown') if emergency_contact else 'Unknown'}</td>
            </tr>
            <tr style="background:#fff8f8;">
                <td style="padding:12px;font-weight:bold;color:#cc0000;">Emergency Contact</td>
                <td style="padding:12px;color:#333;">{emergency_contact.get('name','N/A') if emergency_contact else 'N/A'}</td>
            </tr>
            <tr style="background:#fff0f3;">
                <td style="padding:12px;font-weight:bold;color:#cc0000;">Contact Relation</td>
                <td style="padding:12px;color:#333;">{emergency_contact.get('relation','N/A') if emergency_contact else 'N/A'}</td>
            </tr>
            <tr style="background:#fff8f8;">
                <td style="padding:12px;font-weight:bold;color:#cc0000;">Contact Phone</td>
                <td style="padding:12px;color:#333;">{emergency_contact.get('phone','N/A') if emergency_contact else 'N/A'}</td>
            </tr>
            <tr style="background:#fff0f3;">
                <td style="padding:12px;font-weight:bold;color:#cc0000;">Contact Email</td>
                <td style="padding:12px;color:#333;">{emergency_contact.get('email','N/A') if emergency_contact else 'N/A'}</td>
            </tr>
        </table>
        <div style="background:#fff0f3;padding:14px;border-radius:8px;border-left:4px solid #ff4d6d;">
            <p style="color:#cc0000;font-weight:bold;margin:0;">
            ⚡ Please contact the patient or their emergency contact immediately!
            </p>
        </div>
        <p style="color:#999;font-size:12px;margin-top:16px;text-align:center;">
        Sent automatically by HealthAI Assistant</p>
    </div>
    """
    send_email(to_email, subject, provider_body)

    # ── Email 2: To Emergency Contact (Family/Friend) ─
    if emergency_contact and emergency_contact.get('email'):
        patient_name = emergency_contact.get('patient_name', 'Your family member')
        contact_name = emergency_contact.get('name', 'there')
        relation     = emergency_contact.get('relation', 'relative')
        phone        = emergency_contact.get('phone', 'N/A')

        family_body = f"""
        <div style="font-family:Arial,sans-serif;max-width:550px;margin:auto;padding:30px;
                    border-radius:12px;border:2px solid #ff4d6d;background:#fff;">

            <div style="background:#ff4d6d;padding:16px;border-radius:8px;
                        text-align:center;margin-bottom:20px;">
                <h2 style="color:white;margin:0;font-size:22px;">🚨 URGENT — ACTION REQUIRED</h2>
            </div>

            <p style="font-size:16px;color:#333;margin-bottom:16px;">
            Dear <strong>{contact_name}</strong>,</p>

            <p style="font-size:15px;color:#333;line-height:1.7;">
            This is an <strong style="color:#cc0000;">urgent emergency alert</strong> 
            from <strong>HealthAI Assistant</strong> regarding your 
            <strong>{relation}</strong>, <strong>{patient_name}</strong>.
            </p>

            <div style="background:#fff0f3;border:1px solid #ffcccc;border-radius:10px;
                        padding:18px;margin:20px 0;">
                <h3 style="color:#cc0000;margin:0 0 12px 0;font-size:16px;">
                ⚠️ Patient Details</h3>
                <table style="width:100%;border-collapse:collapse;">
                    <tr>
                        <td style="padding:8px 0;color:#666;width:40%;font-weight:bold;">
                        Patient Name</td>
                        <td style="padding:8px 0;color:#333;font-weight:bold;font-size:15px;">
                        {patient_name}</td>
                    </tr>
                    <tr>
                        <td style="padding:8px 0;color:#666;font-weight:bold;">
                        Your Relation</td>
                        <td style="padding:8px 0;color:#333;">{relation}</td>
                    </tr>
                    <tr>
                        <td style="padding:8px 0;color:#666;font-weight:bold;">
                        Condition</td>
                        <td style="padding:8px 0;color:#cc0000;font-weight:bold;">
                        🚨 Medical Emergency Reported</td>
                    </tr>
                    <tr>
                        <td style="padding:8px 0;color:#666;font-weight:bold;">
                        Alert Time</td>
                        <td style="padding:8px 0;color:#333;">
                        {__import__('datetime').datetime.now().strftime('%d %b %Y, %I:%M %p')}</td>
                    </tr>
                </table>
            </div>

            <div style="background:#fff8e1;border:1px solid #ffcc00;border-radius:10px;
                        padding:16px;margin-bottom:20px;">
                <h3 style="color:#cc8800;margin:0 0 10px 0;font-size:14px;">
                📋 Immediate Actions Required:</h3>
                <ol style="color:#333;font-size:14px;line-height:2;margin:0;padding-left:18px;">
                    <li>Call <strong>{patient_name}</strong> immediately</li>
                    <li>If unreachable, go to their location right away</li>
                    <li>Call emergency services <strong style="color:#cc0000;">108</strong> 
                    if needed</li>
                    <li>Stay calm and provide reassurance</li>
                </ol>
            </div>

            <div style="background:#f0fff4;border:1px solid #00cc88;border-radius:10px;
                        padding:14px;text-align:center;">
                <p style="color:#006644;font-weight:bold;margin:0;font-size:14px;">
                📞 Patient's registered phone: <strong>{phone}</strong></p>
            </div>

            <p style="color:#999;font-size:12px;margin-top:20px;text-align:center;
                      border-top:1px solid #eee;padding-top:12px;">
            This alert was automatically triggered by HealthAI Assistant.<br/>
            If this was a false alarm, please verify directly with {patient_name}.
            </p>
        </div>
        """
        send_email(emergency_contact['email'], subject, family_body)
        print(f"--- ✅ Emergency email sent to family: {emergency_contact['email']} ---")
        return True


# ── 4. Medication Reminder Email ──────────────────────────────────────────────
def send_medication_reminder_email(to_email, details):
    subject = "💊 Medication Reminder — HealthAI"
    body = f"""
    <div style="font-family:Arial,sans-serif;max-width:500px;margin:auto;padding:30px;
                border-radius:12px;border:1px solid #e0e0e0;">
        <h2 style="color:#0a4d68;">💊 Medication Reminder Set</h2>
        <p>Your medication reminder has been configured successfully.</p>
        <table style="width:100%;border-collapse:collapse;margin-top:16px;">
            <tr style="background:#f4f9f9;">
                <td style="padding:10px;font-weight:bold;color:#0a4d68;">Medicine</td>
                <td style="padding:10px;">{details.get('medicine', 'N/A')}</td>
            </tr>
            <tr>
                <td style="padding:10px;font-weight:bold;color:#0a4d68;">Dosage</td>
                <td style="padding:10px;">{details.get('dosage', 'N/A')}</td>
            </tr>
            <tr style="background:#f4f9f9;">
                <td style="padding:10px;font-weight:bold;color:#0a4d68;">Frequency</td>
                <td style="padding:10px;">{details.get('frequency', 'N/A')}</td>
            </tr>
            <tr>
                <td style="padding:10px;font-weight:bold;color:#0a4d68;">Duration</td>
                <td style="padding:10px;">{details.get('duration', 'N/A')}</td>
            </tr>
        </table>
        <p style="margin-top:20px;color:#666;">
        Please take your medicine as prescribed. 
        Never skip doses without consulting your doctor.</p>
        <p style="color:#999;font-size:12px;">⚠️ This is not medical advice.</p>
    </div>
    """
    return send_email(to_email, subject, body)