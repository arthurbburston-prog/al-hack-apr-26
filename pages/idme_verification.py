import streamlit as st
import requests
import urllib.parse

st.title("ID.me Identity Verification")
st.subheader("Government ID + Selfie verification via ID.me")

AUTHORIZE_URL = "https://api.id.me/oauth/authorize"
TOKEN_URL = "https://api.id.me/token"
ATTRIBUTES_URL = "https://api.id.me/api/public/v3/attributes.json"

SCOPES = ["military", "student", "responder", "government", "teacher"]


def _secret(key):
    try:
        return st.secrets[key]
    except Exception:
        return ""


with st.sidebar:
    st.header("ID.me Credentials")
    client_id = st.text_input(
        "Client ID",
        type="password",
        value=_secret("IDME_CLIENT_ID"),
    )
    client_secret = st.text_input(
        "Client Secret",
        type="password",
        value=_secret("IDME_CLIENT_SECRET"),
    )
    redirect_uri = st.text_input(
        "Redirect URI",
        value=_secret("IDME_REDIRECT_URI") or "http://localhost:8501",
        help="Must match the redirect URI registered in your ID.me developer dashboard.",
    )
    scope = st.selectbox("Verification Scope", SCOPES)

if not client_id or not client_secret:
    st.warning("Enter your ID.me Client ID and Client Secret in the sidebar to begin.")
    st.stop()

# OAuth callback: ID.me redirects back here with ?code=...
code = st.query_params.get("code")

if code:
    with st.spinner("Exchanging authorization code for token..."):
        try:
            token_r = requests.post(
                TOKEN_URL,
                data={
                    "code": code,
                    "client_id": client_id,
                    "client_secret": client_secret,
                    "redirect_uri": redirect_uri,
                    "grant_type": "authorization_code",
                },
                timeout=15,
            )
            token_r.raise_for_status()
            access_token = token_r.json()["access_token"]

            attr_r = requests.get(
                ATTRIBUTES_URL,
                headers={"Authorization": f"Bearer {access_token}"},
                timeout=15,
            )
            attr_r.raise_for_status()
            attributes = attr_r.json()

            st.success("Verification complete!")
            st.json(attributes)

        except requests.HTTPError as e:
            st.error(f"ID.me API error {e.response.status_code}: {e.response.text}")
        except Exception as e:
            st.error(f"Error: {e}")

    if st.button("Start New Verification"):
        st.query_params.clear()
        st.rerun()

else:
    auth_params = {
        "client_id": client_id,
        "redirect_uri": redirect_uri,
        "response_type": "code",
        "scope": scope,
    }
    auth_url = f"{AUTHORIZE_URL}?{urllib.parse.urlencode(auth_params)}"

    st.write(
        "Click **Start Verification** to open ID.me's hosted flow where you will "
        "upload a government ID and take a selfie."
    )
    st.link_button("Start ID.me Verification", auth_url, type="primary")
    st.caption(f"After verification, ID.me will redirect back to: `{redirect_uri}`")
