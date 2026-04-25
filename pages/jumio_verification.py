import streamlit as st
import requests
import uuid

st.title("Jumio ID Verification")
st.subheader("Government ID + Selfie verification via Jumio")

BASE_URLS = {
    "US (AMER)": "https://retrieval.amer-1.jumio.ai",
    "EU": "https://retrieval.eu-1.jumio.ai",
    "SGP": "https://retrieval.sgp-1.jumio.ai",
}

def _secret(key):
    try:
        return st.secrets[key]
    except Exception:
        return ""

with st.sidebar:
    st.header("Jumio Credentials")
    api_token = st.text_input(
        "API Token",
        type="password",
        value=_secret("JUMIO_API_TOKEN"),
    )
    api_secret = st.text_input(
        "API Secret",
        type="password",
        value=_secret("JUMIO_API_SECRET"),
    )
    datacenter = st.selectbox("Datacenter", list(BASE_URLS.keys()))

for key in ("account_id", "workflow_id", "jumio_url"):
    if key not in st.session_state:
        st.session_state[key] = None


def create_workflow(base_url, token, secret):
    ref = str(uuid.uuid4())
    r = requests.post(
        f"{base_url}/api/v1/accounts",
        auth=(token, secret),
        headers={"Content-Type": "application/json"},
        json={"customerInternalReference": ref, "userReference": ref},
        timeout=15,
    )
    r.raise_for_status()
    account_id = r.json()["accountId"]

    # Workflow key 2 = ID + face liveness (gov ID + selfie)
    r = requests.post(
        f"{base_url}/api/v1/accounts/{account_id}/workflow-executions",
        auth=(token, secret),
        headers={"Content-Type": "application/json"},
        json={
            "customerInternalReference": ref,
            "workflowDefinition": {"key": 2},
            "web": {},
        },
        timeout=15,
    )
    r.raise_for_status()
    data = r.json()
    return account_id, data["workflowExecution"]["id"], data["web"]["href"]


def get_results(base_url, token, secret, account_id, workflow_id):
    r = requests.get(
        f"{base_url}/api/v1/accounts/{account_id}/workflow-executions/{workflow_id}",
        auth=(token, secret),
        timeout=15,
    )
    r.raise_for_status()
    return r.json()


if not api_token or not api_secret:
    st.warning("Enter your Jumio API Token and Secret in the sidebar to begin.")
    st.stop()

base_url = BASE_URLS[datacenter]

if st.session_state.jumio_url is None:
    st.write("Click **Start Verification** to open a Jumio session where you will upload your government ID and take a selfie.")
    if st.button("Start Verification", type="primary"):
        with st.spinner("Creating Jumio session..."):
            try:
                account_id, workflow_id, url = create_workflow(base_url, api_token, api_secret)
                st.session_state.account_id = account_id
                st.session_state.workflow_id = workflow_id
                st.session_state.jumio_url = url
                st.rerun()
            except requests.HTTPError as e:
                st.error(f"Jumio API error {e.response.status_code}: {e.response.text}")
            except Exception as e:
                st.error(f"Error: {e}")
else:
    st.info("Complete the ID + selfie steps in the frame below, then click **Check Results**.")
    st.components.v1.iframe(st.session_state.jumio_url, height=620, scrolling=True)

    col1, col2 = st.columns(2)
    with col1:
        if st.button("Check Results", type="primary"):
            with st.spinner("Fetching results from Jumio..."):
                try:
                    results = get_results(
                        base_url,
                        api_token,
                        api_secret,
                        st.session_state.account_id,
                        st.session_state.workflow_id,
                    )
                    st.success("Results retrieved!")
                    st.json(results)
                except requests.HTTPError as e:
                    st.error(f"Jumio API error {e.response.status_code}: {e.response.text}")
                except Exception as e:
                    st.error(f"Error: {e}")
    with col2:
        if st.button("Reset / New Verification"):
            for key in ("account_id", "workflow_id", "jumio_url"):
                st.session_state[key] = None
            st.rerun()
