import re

import requests
import streamlit as st

st.title("Payment Identity Check")
st.write(
    "Checks whether a card is identity-obfuscating (prepaid/gift) and whether "
    "the billing details are consistent with the claimed identity."
)

BINLIST_URL = "https://lookup.binlist.net/"

AVS_CODES = {
    "Y": ("Full match", "green", "Street and ZIP both match."),
    "A": ("Street match only", "orange", "Street matches but ZIP does not."),
    "Z": ("ZIP match only", "orange", "ZIP matches but street does not."),
    "N": ("No match", "red", "Neither street nor ZIP match."),
    "U": ("Unavailable", "gray", "Bank did not return AVS data."),
    "G": ("International", "gray", "Non-US card, AVS not supported."),
    "R": ("Retry", "gray", "System unavailable, try again."),
    "S": ("Not supported", "gray", "Card issuer does not support AVS."),
    "E": ("Error", "red", "AVS error."),
    "W": ("ZIP+4 match", "orange", "9-digit ZIP matches but street does not."),
    "X": ("Full match (9-digit ZIP)", "green", "Street and 9-digit ZIP both match."),
}

CVV_CODES = {
    "M": ("Match", "green", "CVV matches."),
    "N": ("No match", "red", "CVV does not match — card may be compromised."),
    "P": ("Not processed", "gray", "CVV not processed."),
    "S": ("Not present", "orange", "CVV not provided by cardholder."),
    "U": ("Unsupported", "gray", "Card issuer does not support CVV."),
}

FUNDING_RISK = {
    "credit": ("Credit", "green", "Linked to a real account holder."),
    "debit": ("Debit", "green", "Linked to a real bank account."),
    "prepaid": ("Prepaid / Gift card", "red", "High obfuscation risk — no verified cardholder identity."),
    "unknown": ("Unknown", "gray", "Card type could not be determined."),
}


def _bin_lookup(bin6: str) -> dict:
    resp = requests.get(
        f"{BINLIST_URL}{bin6}",
        headers={"Accept-Version": "3"},
        timeout=8,
    )
    if resp.status_code == 404:
        raise ValueError("BIN not found in database.")
    resp.raise_for_status()
    return resp.json()


def _fuzzy_name_match(name_a: str, name_b: str) -> tuple[bool, str]:
    """Returns (match, reason). Simple tokenized overlap check."""
    a_tokens = set(re.sub(r"[^a-z ]", "", name_a.lower()).split())
    b_tokens = set(re.sub(r"[^a-z ]", "", name_b.lower()).split())
    if not a_tokens or not b_tokens:
        return False, "One or both names are empty."
    overlap = a_tokens & b_tokens
    # Require at least last name (any meaningful token) to match
    score = len(overlap) / max(len(a_tokens), len(b_tokens))
    if score >= 0.5:
        return True, f"Shared tokens: {', '.join(sorted(overlap))}"
    return False, f"Only {len(overlap)} shared token(s): {', '.join(sorted(overlap)) or 'none'}"


# ── Tabs ─────────────────────────────────────────────────────────────────────
tab1, tab2 = st.tabs(["BIN / Card Type", "Payment Consistency"])

# ── Tab 1: BIN Lookup ────────────────────────────────────────────────────────
with tab1:
    st.subheader("Is the card identity-obfuscating?")
    st.caption("Looks up the first 6–8 digits of a card number to detect prepaid/gift cards.")

    bin_input = st.text_input(
        "Card BIN (first 6 digits — safe to enter, no full card number needed)",
        placeholder="411111",
        max_chars=8,
        key="pay_bin",
    )

    if st.button("Look up BIN", disabled=not bin_input):
        if not re.fullmatch(r"\d{6,8}", bin_input.strip()):
            st.warning("Enter 6–8 digits only.")
        else:
            with st.spinner("Querying BIN database..."):
                try:
                    data = _bin_lookup(bin_input.strip())

                    funding = (data.get("type") or "unknown").lower()
                    label, color, note = FUNDING_RISK.get(funding, FUNDING_RISK["unknown"])
                    st.markdown(f"**Card funding type:** :{color}[{label}]")
                    st.caption(note)

                    brand = data.get("brand") or "Unknown"
                    country = (data.get("country") or {}).get("name") or "Unknown"
                    bank = (data.get("bank") or {}).get("name") or "Unknown"

                    col1, col2, col3 = st.columns(3)
                    col1.metric("Brand", brand)
                    col2.metric("Issuing country", country)
                    col3.metric("Issuing bank", bank)

                    if funding == "prepaid":
                        st.error(
                            "Prepaid/gift cards carry no verified cardholder identity. "
                            "Consider requiring a credit or debit card for this transaction."
                        )

                    with st.expander("Full BIN data"):
                        st.json(data)

                except ValueError as e:
                    st.error(str(e))
                except requests.RequestException as e:
                    st.error(f"BIN lookup failed: {e}")

    st.divider()
    st.caption("Uses binlist.net — free, rate-limited (~10 req/hr without a key). BIN only; no full card number is needed or transmitted.")

# ── Tab 2: Payment Consistency ───────────────────────────────────────────────
with tab2:
    st.subheader("Are payment details consistent with claimed identity?")
    st.caption(
        "Paste in the AVS/CVV codes returned by your payment processor (Stripe, Braintree, etc.) "
        "and compare names. No card numbers are entered or sent here."
    )

    col_a, col_b = st.columns(2)
    with col_a:
        st.markdown("**Claimed identity**")
        claimed_name = st.text_input("Full name (as entered at checkout)", placeholder="Jane Smith", key="pay_claimed_name")
        claimed_country = st.text_input("Claimed country (2-letter ISO)", placeholder="US", max_chars=2, key="pay_claimed_country")

    with col_b:
        st.markdown("**Payment processor response**")
        card_name = st.text_input("Name on card (if returned by processor)", placeholder="J SMITH", key="pay_card_name")
        avs_code = st.selectbox(
            "AVS result code",
            options=["(not checked)"] + list(AVS_CODES.keys()),
            key="pay_avs_code",
        )
        cvv_code = st.selectbox(
            "CVV result code",
            options=["(not checked)"] + list(CVV_CODES.keys()),
            key="pay_cvv_code",
        )
        card_country = st.text_input("Card-issuing country from BIN lookup", placeholder="US", max_chars=2, key="pay_card_country")

    if st.button("Run consistency check"):
        flags = []
        passes = []

        # AVS
        if avs_code != "(not checked)":
            avs_label, avs_color, avs_note = AVS_CODES[avs_code]
            if avs_color == "green":
                passes.append(f"AVS: {avs_label} — {avs_note}")
            elif avs_color == "orange":
                flags.append(f"AVS partial mismatch: {avs_label} — {avs_note}")
            elif avs_color == "red":
                flags.append(f"AVS failure: {avs_label} — {avs_note}")

        # CVV
        if cvv_code != "(not checked)":
            cvv_label, cvv_color, cvv_note = CVV_CODES[cvv_code]
            if cvv_color == "green":
                passes.append(f"CVV: {cvv_label} — {cvv_note}")
            else:
                flags.append(f"CVV: {cvv_label} — {cvv_note}")

        # Name match
        if claimed_name and card_name:
            match, reason = _fuzzy_name_match(claimed_name, card_name)
            if match:
                passes.append(f"Name match: {reason}")
            else:
                flags.append(f"Name mismatch: claimed '{claimed_name}' vs card '{card_name}' — {reason}")
        elif claimed_name and not card_name:
            flags.append("Name on card not provided — could not verify name consistency.")

        # Country match
        if claimed_country and card_country:
            if claimed_country.upper() == card_country.upper():
                passes.append(f"Country match: both are {claimed_country.upper()}")
            else:
                flags.append(
                    f"Country mismatch: claimed {claimed_country.upper()} but card issued in {card_country.upper()}"
                )

        # Results
        st.subheader("Findings")
        for p in passes:
            st.success(p)
        for f in flags:
            st.error(f)

        if not passes and not flags:
            st.info("No checks were run — enter at least one data point above.")
        elif not flags:
            st.success("All checks passed. No inconsistencies detected.")
        elif len(flags) >= 2:
            st.error(f"{len(flags)} red flags detected. Review this transaction before fulfilling.")
        else:
            st.warning("1 flag — use judgement based on order value and context.")

    st.divider()
    st.caption(
        "AVS and CVV codes come from your payment processor — this page just interprets them. "
        "Name matching is a simple token overlap; it does not call any external API. "
        "Country comparison relies on BIN lookup from Tab 1."
    )
