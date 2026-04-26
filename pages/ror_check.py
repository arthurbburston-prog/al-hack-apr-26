import streamlit as st
from pages.ror_utils import search_ror_institution, check_email_domain_match


def main():
    st.title("ROR Institution Check")
    st.subheader("Verify if researcher email domain is from a ROR-listed institution")

    st.write("""
    This check validates that a researcher's email domain is registered with their claimed institution in the ROR (Research Organization Registry) database.
    """)

    col1, col2 = st.columns(2)

    with col1:
        email = st.text_input("Researcher Email", placeholder="researcher@university.edu")

    with col2:
        institution_name = st.text_input("Institution Name", placeholder="Stanford University")

    if st.button("Check Email Domain", key="ror_check_button"):
        if not email or not institution_name:
            st.error("Please provide both email and institution name")
        else:
            with st.spinner("Checking ROR database..."):
                ror_response = search_ror_institution(institution_name)

                if ror_response["status"] == "error":
                    st.error(f"**Error:** {ror_response['message']}")
                    st.info("Could not retrieve institution information from ROR database.")
                else:
                    status, confidence, evidence = check_email_domain_match(email, ror_response["data"])

                    st.divider()

                    if status == "pass":
                        st.success("✓ **PASS** - Email domain verified with institution")
                    else:
                        st.error("✗ **FAIL** - Email domain does not match institution")

                    st.metric("Confidence Score", f"{confidence * 100:.0f}%")

                    st.subheader("Evidence & Details")

                    with st.expander("View detailed evidence", expanded=True):
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
                                st.divider()
                                if item["matched"]:
                                    st.write("✓ **Match Result:** Email domain matches the following institution domain(s):")
                                    for match in item["matched_institutions"]:
                                        st.write(f"  - {match['name']} (Domain: `{match['matched_domain']}`)")
                                else:
                                    st.write("✗ **Match Result:** No matching domain found")


if __name__ == "__main__":
    main()
