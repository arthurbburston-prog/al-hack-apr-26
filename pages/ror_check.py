import streamlit as st
import requests
from urllib.parse import urlparse
from typing import Dict, List, Tuple, Optional


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
                # Step 1: Search for institution in ROR
                ror_response = search_ror_institution(institution_name)
                
                if ror_response["status"] == "error":
                    st.error(f"**Error:** {ror_response['message']}")
                    st.info("Could not retrieve institution information from ROR database.")
                else:
                    # Step 2: Check email domain match
                    status, confidence, evidence = check_email_domain_match(
                        email, 
                        ror_response["data"]
                    )
                    
                    # Display results
                    st.divider()
                    
                    if status == "pass":
                        st.success(f"✓ **PASS** - Email domain verified with institution")
                    else:
                        st.error(f"✗ **FAIL** - Email domain does not match institution")
                    
                    # Confidence score
                    st.metric("Confidence Score", f"{confidence * 100:.0f}%")
                    
                    # Evidence
                    st.subheader("Evidence & Details")
                    
                    with st.expander("View detailed evidence", expanded=True):
                        for i, item in enumerate(evidence):
                            if item["type"] == "email_domain":
                                st.write(f"📧 **Email Domain:** `{item['value']}`")
                            
                            elif item["type"] == "institution_info":
                                st.write(f"🏫 **Institution:** {item['institution_name']}")
                                st.write(f"   - **ROR ID:** {item['ror_id']}")
                                if item['domains']:
                                    st.write(f"   - **Registered Domains:** {', '.join([f'`{d}`' for d in item['domains']])}")
                                else:
                                    st.write(f"   - **Registered Domains:** None found")
                            
                            elif item["type"] == "match_result":
                                st.divider()
                                if item["matched"]:
                                    st.write(f"✓ **Match Result:** Email domain matches the following institution domain(s):")
                                    for match in item["matched_institutions"]:
                                        st.write(f"  - {match['name']} (Domain: `{match['matched_domain']}`)")
                                else:
                                    st.write(f"✗ **Match Result:** No matching domain found")


if __name__ == "__main__":
    main()
