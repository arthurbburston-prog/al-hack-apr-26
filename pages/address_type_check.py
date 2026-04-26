import requests
import streamlit as st

st.title("Address Type Check")
st.write("Checks whether a US address is residential, commercial, or a CMRA using the Smarty API.")

# Requires in .streamlit/secrets.toml:
#   [smarty]
#   auth_id = "your-smarty-auth-id"
#   auth_token = "your-smarty-auth-token"

SMARTY_URL = "https://us-street.api.smarty.com/street-address"

DPV_MATCH = {
    "Y": ("Confirmed", "green", "Address is deliverable."),
    "S": ("Confirmed (no secondary)", "orange", "Deliverable but secondary info (apt/suite) was ignored."),
    "D": ("Missing secondary", "orange", "Deliverable but requires a secondary number (apt/suite)."),
    "N": ("Not confirmed", "red", "Address could not be confirmed as deliverable."),
}

RDI_LABELS = {
    "Residential": ("Residential", "green", "Home address. Carriers may apply residential surcharges."),
    "Commercial": ("Commercial", "blue", "Business or commercial address."),
}


def _lookup_address(street: str, city: str, state: str, zipcode: str) -> dict:
    auth_id = st.secrets["smarty"]["auth_id"]
    auth_token = st.secrets["smarty"]["auth_token"]

    resp = requests.get(
        SMARTY_URL,
        params={
            "auth-id": auth_id,
            "auth-token": auth_token,
            "street": street,
            "city": city,
            "state": state,
            "zipcode": zipcode,
            "candidates": 1,
        },
        timeout=10,
    )
    resp.raise_for_status()

    data = resp.json()
    if not data:
        raise ValueError("Address not found or not deliverable.")

    candidate = data[0]
    components = candidate.get("components", {})
    metadata = candidate.get("metadata", {})
    analysis = candidate.get("analysis", {})

    standardized = " ".join(filter(None, [
        candidate.get("delivery_line_1", ""),
        candidate.get("delivery_line_2", ""),
    ]))
    city_state_zip = candidate.get("last_line", "")

    return {
        "standardized": f"{standardized}, {city_state_zip}".strip(", "),
        "rdi": metadata.get("rdi", ""),
        "cmra": analysis.get("dpv_cmra", ""),
        "vacant": analysis.get("dpv_vacant", ""),
        "active": analysis.get("active", ""),
        "dpv_match_code": analysis.get("dpv_match_code", ""),
        "county": metadata.get("county_name", ""),
        "zip_type": metadata.get("zip_type", ""),
    }


# ── Form ─────────────────────────────────────────────────────────────────────
with st.form("address_form"):
    street = st.text_input("Street address", placeholder="123 Main St Apt 4B")
    col1, col2, col3 = st.columns([3, 1, 1])
    with col1:
        city = st.text_input("City", placeholder="Springfield")
    with col2:
        state = st.text_input("State", placeholder="IL", max_chars=2)
    with col3:
        zipcode = st.text_input("ZIP", placeholder="62701", max_chars=10)
    submitted = st.form_submit_button("Check Address")

if submitted:
    if not street:
        st.warning("Street address is required.")
    elif not any([city, state, zipcode]):
        st.warning("Please provide at least a city/state or ZIP code.")
    else:
        with st.spinner("Checking with Smarty..."):
            try:
                result = _lookup_address(
                    street.strip(),
                    city.strip(),
                    state.strip().upper(),
                    zipcode.strip(),
                )

                st.subheader("Result")
                st.write(f"**Standardized address:** {result['standardized']}")

                # Deliverability
                dpv = result["dpv_match_code"]
                if dpv in DPV_MATCH:
                    label, color, note = DPV_MATCH[dpv]
                    st.markdown(f"**Deliverability:** :{color}[{label}]")
                    st.caption(note)

                st.divider()

                # Address type
                col_a, col_b, col_c = st.columns(3)

                with col_a:
                    rdi = result["rdi"]
                    if rdi in RDI_LABELS:
                        label, color, note = RDI_LABELS[rdi]
                        st.markdown(f"**Type:** :{color}[{label}]")
                        st.caption(note)
                    elif rdi:
                        st.info(f"Type: {rdi}")
                    else:
                        st.caption("Type: unknown")

                with col_b:
                    cmra = result["cmra"]
                    if cmra == "Y":
                        st.markdown("**CMRA:** :orange[Yes]")
                        st.caption("Commercial Mail Receiving Agency (e.g. UPS Store, Mailboxes Etc.)")
                    elif cmra == "N":
                        st.markdown("**CMRA:** :green[No]")
                        st.caption("Not a mail forwarding address.")
                    else:
                        st.caption("CMRA: unknown")

                with col_c:
                    vacant = result["vacant"]
                    if vacant == "Y":
                        st.markdown("**Vacant:** :red[Yes]")
                        st.caption("Address has been vacant for 90+ days.")
                    elif vacant == "N":
                        st.markdown("**Vacant:** :green[No]")
                        st.caption("Address appears occupied.")
                    else:
                        st.caption("Vacant: unknown")

                if result["county"]:
                    st.caption(f"County: {result['county']}")

                with st.expander("Raw Smarty fields"):
                    st.json(result)

            except ValueError as e:
                st.error(str(e))
            except requests.RequestException as e:
                st.error(f"Request failed: {e}")

st.divider()
st.caption(
    "Uses the Smarty US Street Address API (free tier: 250 lookups/month). "
    "Returns residential/commercial type, CMRA flag, and vacancy status. "
    "Register at smarty.com to get an auth-id and auth-token."
)
