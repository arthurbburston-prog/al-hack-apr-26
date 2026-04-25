import streamlit as st
import requests
import random
import smtplib
import time
from email.mime.text import MIMEText
from urllib.parse import urlparse
from typing import Dict, List, Tuple, Optional


# ── ROR Check Functions ──────────────────────────────────────────────────────

def extract_email_domain(email: str) -> Optional[str]:
    """Extract domain from email address."""
    if "@" not in email:
        return None
    return email.split("@")[1].lower()


def search_ror_institution(institution_name: str) -> Dict:
    """
    Search for an institution in the ROR database.

    Returns:
        Dict with status, data, and error message
    """
    try:
        # ROR API search endpoint
        url = "https://api.ror.org/organizations"
        params = {"query": institution_name}

        response = requests.get(url, params=params, timeout=10)
        response.raise_for_status()

        data = response.json()

        if data.get("number_of_results", 0) == 0:
            return {
                "status": "error",
                "data": None,
                "message": f"No institutions found matching '{institution_name}'"
            }

        # Return the top result
        results = data.get("items", [])
        if results:
            return {
                "status": "success",
                "data": results,
                "message": None
            }

        return {
            "status": "error",
            "data": None,
            "message": "No results returned from ROR API"
        }

    except requests.exceptions.Timeout:
        return {
            "status": "error",
            "data": None,
            "message": "Request to ROR API timed out"
        }
    except requests.exceptions.RequestException as e:
        return {
            "status": "error",
            "data": None,
            "message": f"Failed to contact ROR API: {str(e)}"
        }
    except Exception as e:
        return {
            "status": "error",
            "data": None,
            "message": f"Unexpected error: {str(e)}"
        }


def extract_domains_from_institution(institution: Dict) -> List[str]:
    """Extract all domains associated with a ROR institution."""
    domains = []

    # Get primary domain from links
    if "links" in institution:
        for link in institution.get("links", []):
            if link.get("type") == "website":
                # Note: ROR API uses "value" not "href"
                url = link.get("value", "")
                if url:
                    domain = urlparse(url).netloc.lower()
                    if domain.startswith("www."):
                        domain = domain[4:]
                    if domain:
                        domains.append(domain)

    # Also check the "domains" field in ROR (if available)
    if "domains" in institution:
        for domain_entry in institution.get("domains", []):
            if isinstance(domain_entry, str):
                domain = domain_entry.lower()
                if domain.startswith("www."):
                    domain = domain[4:]
                if domain:
                    domains.append(domain)
            elif isinstance(domain_entry, dict) and "domain" in domain_entry:
                domain = domain_entry["domain"].lower()
                if domain.startswith("www."):
                    domain = domain[4:]
                if domain:
                    domains.append(domain)

    return list(set(domains))  # Remove duplicates


def check_email_domain_match(email: str, institution_data: List[Dict]) -> Tuple[str, float, List[Dict]]:
    """
    Check if email domain matches any domain in the institution data.

    Returns:
        Tuple of (status: str, confidence: float, evidence: List[Dict])
    """
    email_domain = extract_email_domain(email)

    if not email_domain:
        return "fail", 0.0, [{"type": "error", "message": "Invalid email format"}]

    evidence = []
    evidence.append({
        "type": "email_domain",
        "value": email_domain,
        "description": f"Extracted domain from email"
    })

    matched_institutions = []

    for institution in institution_data:
        inst_name = institution.get("name", "Unknown")
        inst_id = institution.get("id", "")

        institution_domains = extract_domains_from_institution(institution)

        evidence.append({
            "type": "institution_info",
            "institution_name": inst_name,
            "ror_id": inst_id,
            "domains": institution_domains,
            "description": f"Domains associated with {inst_name}"
        })

        # Check for exact domain match
        for domain in institution_domains:
            if email_domain == domain:
                matched_institutions.append({
                    "name": inst_name,
                    "ror_id": inst_id,
                    "matched_domain": domain
                })

    if matched_institutions:
        evidence.append({
            "type": "match_result",
            "matched": True,
            "matched_institutions": matched_institutions,
            "description": "Email domain matches institution domain(s)"
        })
        return "pass", 1.0, evidence
    else:
        evidence.append({
            "type": "match_result",
            "matched": False,
            "matched_institutions": [],
            "description": "Email domain does not match any institution domain"
        })
        return "fail", 0.0, evidence


# ── Email OTP Functions ──────────────────────────────────────────────────────

def _send_otp(recipient: str, code: str) -> None:
    """Send OTP code via email."""
    try:
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
    except KeyError:
        st.error("Email credentials not configured. Please set up email secrets.")
        raise


def _generate_otp() -> str:
    """Generate a 6-digit OTP code."""
    return str(random.randint(100_000, 999_999))


# ── Main Combined Check ──────────────────────────────────────────────────────

def main():
    st.title("ROR + Email OTP Combined Check")
    st.subheader("Complete verification: Institution domain check + Email ownership verification")

    st.write("""
    This check performs two-step verification:
    1. **ROR Domain Check**: Verify the email domain is registered for the claimed institution
    2. **Email OTP**: Confirm you own the email address (only if ROR check passes)
    """)

    # ── Session State Initialization ──────────────────────────────────────────
    session_keys = {
        # ROR check state
        "ror_status": None,
        "ror_confidence": 0.0,
        "ror_evidence": [],
        "ror_completed": False,

        # Email OTP state
        "otp_code": None,
        "otp_sent_at": None,
        "otp_verified": False,
        "otp_attempts": 0,
        "otp_email": None,

        # Combined state
        "check_started": False,
        "current_step": "input",  # input -> ror_check -> otp_check -> complete
    }

    for key, default in session_keys.items():
        if key not in st.session_state:
            st.session_state[key] = default

    # ── Step Navigation ──────────────────────────────────────────────────────
    if st.session_state.current_step == "complete":
        if st.button("Start New Check"):
            # Reset all state
            for key in session_keys:
                st.session_state[key] = session_keys[key]
            st.rerun()
        st.stop()

    # ── Step 1: Input Collection ─────────────────────────────────────────────
    if st.session_state.current_step == "input":
        st.header("📝 Step 1: Enter Details")

        col1, col2 = st.columns(2)

        with col1:
            email = st.text_input("Researcher Email", placeholder="researcher@university.edu")

        with col2:
            institution_name = st.text_input("Institution Name", placeholder="Stanford University")

        if st.button("Start Verification", disabled=not (email and institution_name)):
            st.session_state.check_started = True
            st.session_state.current_step = "ror_check"
            st.session_state.ror_email = email
            st.session_state.ror_institution = institution_name
            st.rerun()

    # ── Step 2: ROR Check ────────────────────────────────────────────────────
    elif st.session_state.current_step == "ror_check":
        st.header("🏫 Step 2: Institution Domain Verification")

        with st.spinner("Checking ROR database..."):
            # Perform ROR check
            ror_response = search_ror_institution(st.session_state.ror_institution)

            if ror_response["status"] == "error":
                st.error(f"**ROR Check Failed:** {ror_response['message']}")
                st.info("❌ Cannot proceed to email verification due to institution lookup failure.")
                if st.button("Try Again"):
                    st.session_state.current_step = "input"
                    st.rerun()
                st.stop()

            # Check email domain match
            status, confidence, evidence = check_email_domain_match(
                st.session_state.ror_email,
                ror_response["data"]
            )

            st.session_state.ror_status = status
            st.session_state.ror_confidence = confidence
            st.session_state.ror_evidence = evidence
            st.session_state.ror_completed = True

        # Display ROR results
        if status == "pass":
            st.success("✅ **ROR Check PASSED** - Email domain verified with institution")
            st.info("Proceeding to email ownership verification...")
            st.session_state.current_step = "otp_check"
            time.sleep(2)  # Brief pause for user to see result
            st.rerun()
        else:
            st.error("❌ **ROR Check FAILED** - Email domain does not match institution")
            st.session_state.current_step = "complete"

            # Show evidence
            with st.expander("View ROR Check Details", expanded=True):
                for item in evidence:
                    if item["type"] == "email_domain":
                        st.write(f"📧 **Email Domain:** `{item['value']}`")
                    elif item["type"] == "institution_info":
                        st.write(f"🏫 **Institution:** {item['institution_name']}")
                        st.write(f"   - **ROR ID:** {item['ror_id']}")
                        if item['domains']:
                            st.write(f"   - **Registered Domains:** {', '.join([f'`{d}`' for d in item['domains']])}")
                        else:
                            st.write("   - **Registered Domains:** None found")
                    elif item["type"] == "match_result":
                        st.write(f"🔍 **Result:** {item['description']}")

            if st.button("Try Different Details"):
                st.session_state.current_step = "input"
                st.rerun()

    # ── Step 3: Email OTP Check ──────────────────────────────────────────────
    elif st.session_state.current_step == "otp_check":
        st.header("📧 Step 3: Email Ownership Verification")

        # Only proceed if ROR passed
        if st.session_state.ror_status != "pass":
            st.error("Cannot perform email verification - ROR check did not pass")
            st.session_state.current_step = "complete"
            st.rerun()

        # Email OTP logic (adapted from email_otp.py)
        OTP_EXPIRY_SECONDS = 300  # 5 minutes
        MAX_ATTEMPTS = 5

        # Use the same email from ROR check
        email = st.session_state.ror_email

        st.info(f"📧 Verifying ownership of: **{email}**")

        # ── Already verified ─────────────────────────────────────────────────
        if st.session_state.otp_verified:
            st.success(f"✅ **COMPLETE SUCCESS!** Email ownership verified for {email}")
            st.session_state.current_step = "complete"

            # Show combined results
            st.balloons()
            col1, col2 = st.columns(2)
            with col1:
                st.metric("ROR Domain Check", "PASSED", "✅")
            with col2:
                st.metric("Email OTP Check", "PASSED", "✅")

            if st.button("View Detailed Results"):
                with st.expander("ROR Check Evidence", expanded=True):
                    for item in st.session_state.ror_evidence:
                        if item["type"] == "email_domain":
                            st.write(f"📧 **Email Domain:** `{item['value']}`")
                        elif item["type"] == "institution_info":
                            st.write(f"🏫 **Institution:** {item['institution_name']}")
                            st.write(f"   - **ROR ID:** {item['ror_id']}")
                            if item['domains']:
                                st.write(f"   - **Registered Domains:** {', '.join([f'`{d}`' for d in item['domains']])}")
                        elif item["type"] == "match_result":
                            st.write(f"🔍 **Result:** {item['description']}")

                with st.expander("Email OTP Details"):
                    st.write(f"✅ Code verified for: {st.session_state.otp_email}")
                    st.write(f"📅 Verified at: {time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(st.session_state.otp_sent_at))}")

            st.stop()

        # ── Send OTP ─────────────────────────────────────────────────────────
        col1, col2 = st.columns([3, 1])
        with col1:
            send_clicked = st.button("Send Verification Code", key="send_otp")

        if send_clicked:
            code = _generate_otp()
            try:
                _send_otp(email, code)
                st.session_state.otp_code = code
                st.session_state.otp_sent_at = time.time()
                st.session_state.otp_email = email
                st.session_state.otp_attempts = 0
                st.success(f"📧 Code sent to {email}. Check your inbox.")
            except Exception as e:
                st.error(f"Failed to send email: {e}")

        # ── Enter OTP ────────────────────────────────────────────────────────
        if st.session_state.otp_code:
            elapsed = time.time() - st.session_state.otp_sent_at
            remaining = OTP_EXPIRY_SECONDS - elapsed

            if remaining <= 0:
                st.warning("⏰ Code expired. Request a new one.")
                st.session_state.otp_code = None
                st.rerun()

            st.info(f"⏱️ Code sent to **{email}** · expires in {int(remaining // 60)}m {int(remaining % 60)}s")

            entered = st.text_input("Enter the 6-digit code", max_chars=6, placeholder="123456", key="otp_input")

            if st.button("Verify Code", disabled=not entered):
                if st.session_state.otp_attempts >= MAX_ATTEMPTS:
                    st.error("🚫 Too many incorrect attempts. Request a new code.")
                    st.session_state.otp_code = None
                elif entered == st.session_state.otp_code:
                    st.session_state.otp_verified = True
                    st.success("✅ Email verified successfully!")
                    time.sleep(1)
                    st.rerun()
                else:
                    st.session_state.otp_attempts += 1
                    left = MAX_ATTEMPTS - st.session_state.otp_attempts
                    st.error(f"❌ Incorrect code. {left} attempt(s) remaining.")

        # ── Back to ROR Check ────────────────────────────────────────────────
        st.divider()
        if st.button("← Back to Institution Check"):
            st.session_state.current_step = "input"
            st.rerun()


if __name__ == "__main__":
    main()
