import random
import smtplib
import time
from email.mime.text import MIMEText

import streamlit as st

st.title("Email OTP Verification")
st.write("Enter an email address to receive a one-time passcode.")

# ── Config ──────────────────────────────────────────────────────────────────
# Store sender credentials in .streamlit/secrets.toml:
#   [email]
#   address = "you@gmail.com"
#   password = "your-app-password"
OTP_EXPIRY_SECONDS = 300  # 5 minutes


def _send_otp(recipient: str, code: str) -> None:
    sender = st.secrets["email"]["address"]
    password = st.secrets["email"]["password"]

    body = f"Your verification code is: {code}\n\nThis code expires in 5 minutes."
    msg = MIMEText(body)
    msg["Subject"] = "Your OTP Verification Code"
    msg["From"] = sender
    msg["To"] = recipient

    with smtplib.SMTP("smtp.gmail.com", 587) as server:
        server.starttls()
        server.login(sender, password)
        server.sendmail(sender, recipient, msg.as_string())


def _generate_otp() -> str:
    return str(random.randint(100_000, 999_999))


# ── Session state defaults ───────────────────────────────────────────────────
for key, default in {
    "otp_code": None,
    "otp_sent_at": None,
    "otp_email": None,
    "otp_verified": False,
    "otp_attempts": 0,
}.items():
    if key not in st.session_state:
        st.session_state[key] = default

MAX_ATTEMPTS = 5

# ── Already verified ─────────────────────────────────────────────────────────
if st.session_state.otp_verified:
    st.success(f"✓ Email verified: {st.session_state.otp_email}")
    if st.button("Verify a different email"):
        for key in ("otp_code", "otp_sent_at", "otp_email", "otp_verified", "otp_attempts"):
            st.session_state[key] = None if key != "otp_verified" else False
            if key == "otp_attempts":
                st.session_state[key] = 0
        st.rerun()
    st.stop()

# ── Step 1: enter email and request OTP ─────────────────────────────────────
email = st.text_input("Email address", placeholder="user@example.com", key="otp_email_input")

col1, col2 = st.columns([1, 3])
with col1:
    send_clicked = st.button("Send OTP", disabled=not email)

if send_clicked and email:
    code = _generate_otp()
    try:
        _send_otp(email, code)
        st.session_state.otp_code = code
        st.session_state.otp_sent_at = time.time()
        st.session_state.otp_email = email
        st.session_state.otp_attempts = 0
        st.success(f"Code sent to {email}. Check your inbox.")
    except Exception as e:
        st.error(f"Failed to send email: {e}")

# ── Step 2: enter OTP ────────────────────────────────────────────────────────
if st.session_state.otp_code:
    elapsed = time.time() - st.session_state.otp_sent_at
    remaining = OTP_EXPIRY_SECONDS - elapsed

    if remaining <= 0:
        st.warning("Your code has expired. Request a new one.")
        st.session_state.otp_code = None
        st.rerun()

    st.info(f"Code sent to **{st.session_state.otp_email}** · expires in {int(remaining // 60)}m {int(remaining % 60)}s")

    entered = st.text_input("Enter the 6-digit code", max_chars=6, placeholder="123456")

    if st.button("Verify", disabled=not entered):
        if st.session_state.otp_attempts >= MAX_ATTEMPTS:
            st.error("Too many incorrect attempts. Please request a new code.")
            st.session_state.otp_code = None
        elif entered == st.session_state.otp_code:
            st.session_state.otp_verified = True
            st.rerun()
        else:
            st.session_state.otp_attempts += 1
            left = MAX_ATTEMPTS - st.session_state.otp_attempts
            st.error(f"Incorrect code. {left} attempt(s) remaining.")
