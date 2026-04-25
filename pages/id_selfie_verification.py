import base64
import streamlit as st
import anthropic

st.title("ID + Selfie Verification")
st.subheader("Verify your identity using a government ID and a selfie")


def _secret(key):
    try:
        return st.secrets[key]
    except Exception:
        return ""


with st.sidebar:
    st.header("Anthropic Credentials")
    api_key = st.text_input(
        "Anthropic API Key",
        type="password",
        value=_secret("ANTHROPIC_API_KEY"),
    )

if not api_key:
    st.warning("Enter your Anthropic API Key in the sidebar to begin.")
    st.stop()

st.markdown("### Step 1 — Upload your Government ID")
id_file = st.file_uploader(
    "Government ID (passport, driver's license, national ID)",
    type=["jpg", "jpeg", "png", "webp"],
    key="id_upload",
)

st.markdown("### Step 2 — Take or upload a Selfie")
selfie_camera = st.camera_input("Take a selfie", key="selfie_cam")
if selfie_camera is None:
    selfie_file = st.file_uploader(
        "Or upload a selfie photo",
        type=["jpg", "jpeg", "png", "webp"],
        key="selfie_upload",
    )
else:
    selfie_file = None

selfie = selfie_camera or selfie_file

if id_file and selfie:
    st.markdown("---")
    if st.button("Verify Identity", type="primary"):
        with st.spinner("Analyzing your documents with AI…"):
            try:
                id_bytes = id_file.read()
                id_b64 = base64.standard_b64encode(id_bytes).decode()
                id_media = id_file.type or "image/jpeg"

                selfie_bytes = selfie.read()
                selfie_b64 = base64.standard_b64encode(selfie_bytes).decode()
                selfie_media = getattr(selfie, "type", None) or "image/jpeg"

                client = anthropic.Anthropic(api_key=api_key)

                system_prompt = (
                    "You are an identity-verification expert. "
                    "You will be given two images: (1) a government-issued ID document and "
                    "(2) a selfie of the person being verified. "
                    "Your job is to:\n"
                    "  • Determine whether the ID appears to be a genuine, physical government "
                    "document (not a printout, screenshot, photocopy, or digital mock-up).\n"
                    "  • Extract the full name and date of birth shown on the ID.\n"
                    "  • Compare the facial photo on the ID with the selfie and decide whether "
                    "they depict the same person.\n"
                    "Return your verdict in exactly this format:\n\n"
                    "RESULT: PASS or FAIL\n"
                    "NAME: <name from ID or 'Not readable'>\n"
                    "DOB: <date of birth from ID or 'Not readable'>\n"
                    "EXPLANATION: <2-4 sentences explaining your decision>\n\n"
                    "Be conservative: if you cannot confidently confirm all three checks "
                    "(authentic document, readable identity, face match), return FAIL."
                )

                response = client.messages.create(
                    model="claude-sonnet-4-6",
                    max_tokens=512,
                    system=[
                        {
                            "type": "text",
                            "text": system_prompt,
                            "cache_control": {"type": "ephemeral"},
                        }
                    ],
                    messages=[
                        {
                            "role": "user",
                            "content": [
                                {"type": "text", "text": "Image 1 — Government ID:"},
                                {
                                    "type": "image",
                                    "source": {
                                        "type": "base64",
                                        "media_type": id_media,
                                        "data": id_b64,
                                    },
                                },
                                {"type": "text", "text": "Image 2 — Selfie:"},
                                {
                                    "type": "image",
                                    "source": {
                                        "type": "base64",
                                        "media_type": selfie_media,
                                        "data": selfie_b64,
                                    },
                                },
                                {
                                    "type": "text",
                                    "text": (
                                        "Please verify this person's identity. "
                                        "Check that (1) the ID is a genuine physical document, "
                                        "(2) extract the name and date of birth, and "
                                        "(3) confirm the face on the ID matches the selfie."
                                    ),
                                },
                            ],
                        }
                    ],
                )

                text = next(
                    (b.text for b in response.content if b.type == "text"), ""
                )

                passed = "RESULT: PASS" in text.upper()
                name_line = next(
                    (l for l in text.splitlines() if l.upper().startswith("NAME:")),
                    "NAME: Not readable",
                )
                dob_line = next(
                    (l for l in text.splitlines() if l.upper().startswith("DOB:")),
                    "DOB: Not readable",
                )
                explanation_line = next(
                    (
                        l
                        for l in text.splitlines()
                        if l.upper().startswith("EXPLANATION:")
                    ),
                    "",
                )

                name_val = name_line.split(":", 1)[-1].strip()
                dob_val = dob_line.split(":", 1)[-1].strip()
                explanation_val = explanation_line.split(":", 1)[-1].strip()

                st.markdown("---")
                if passed:
                    st.success("✅  VERIFICATION PASSED")
                else:
                    st.error("❌  VERIFICATION FAILED")

                col1, col2 = st.columns(2)
                with col1:
                    st.metric("Name on ID", name_val)
                with col2:
                    st.metric("Date of Birth", dob_val)

                if explanation_val:
                    st.info(explanation_val)

            except anthropic.AuthenticationError:
                st.error("Invalid Anthropic API key. Please check your credentials.")
            except anthropic.BadRequestError as e:
                st.error(f"Request error: {e.message}")
            except anthropic.APIStatusError as e:
                st.error(f"API error {e.status_code}: {e.message}")
            except Exception as e:
                st.error(f"Unexpected error: {e}")
elif id_file or selfie:
    st.info("Please provide both a government ID and a selfie to continue.")
