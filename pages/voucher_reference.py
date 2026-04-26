import csv
import os

import streamlit as st

st.title("Voucher Reference Check")
st.write("Enter the name of your reference (voucher) and your email address to confirm you are in their referral list.")

# ── Load CSV ──────────────────────────────────────────────────────────────────
CSV_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "vouchers.csv")


@st.cache_data
def load_voucher_db(path: str) -> dict[str, list[dict]]:
    """Returns {voucher_name_lower: [{vouchee_name, vouchee_email}, ...]}"""
    db: dict[str, list[dict]] = {}
    with open(path, newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            key = row["voucher_name"].strip().lower()
            db.setdefault(key, []).append(
                {
                    "name": row["vouchee_name"].strip(),
                    "email": row["vouchee_email"].strip().lower(),
                }
            )
    return db


try:
    voucher_db = load_voucher_db(CSV_PATH)
except FileNotFoundError:
    st.error("Voucher database not found. Please add data/vouchers.csv.")
    st.stop()

# ── Session state ─────────────────────────────────────────────────────────────
for key, default in {"voucher_result": None, "voucher_checked": False}.items():
    if key not in st.session_state:
        st.session_state[key] = default

# ── Form ──────────────────────────────────────────────────────────────────────
voucher_input = st.text_input("Voucher name", placeholder="e.g. Sarah Chen", key="voucher_name")
email_input = st.text_input("Your email address", placeholder="you@example.com", key="voucher_email")
submitted = st.button("Check Reference")

if submitted:
    voucher_key = voucher_input.strip().lower()
    email_key = email_input.strip().lower()

    if not voucher_input or not email_input:
        st.warning("Please fill in both fields.")
    elif voucher_key not in voucher_db:
        st.error(f'No voucher named "{voucher_input}" exists in the reference database.')
        st.session_state.voucher_checked = True
        st.session_state.voucher_result = None
    else:
        vouchees = voucher_db[voucher_key]
        match = next((v for v in vouchees if v["email"] == email_key), None)
        st.session_state.voucher_checked = True
        st.session_state.voucher_result = match

# ── Result ────────────────────────────────────────────────────────────────────
if st.session_state.voucher_checked:
    if st.session_state.voucher_result:
        name = st.session_state.voucher_result["name"]
        st.success(f"✓ Verified — {name} ({email_input}) is in {voucher_input}'s reference list.")
    elif st.session_state.voucher_result is None and voucher_input and voucher_input.strip().lower() in voucher_db:
        st.error(
            f'Your email address is not in {voucher_input}\'s reference list. '
            "Please contact your reference to confirm they have registered your details."
        )

# ── Debug: show full voucher list (remove in production) ──────────────────────
with st.expander("Browse all vouchers"):
    for voucher, vouchees in sorted(voucher_db.items()):
        st.markdown(f"**{voucher.title()}** vouches for:")
        for v in vouchees:
            st.markdown(f"  - {v['name']} — `{v['email']}`")
