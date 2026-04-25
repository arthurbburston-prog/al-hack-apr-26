import streamlit as st
import requests
import json
import time
from urllib.parse import urlparse, quote
from typing import Dict, List, Optional, Any
from datetime import datetime


# ── API Configuration ──────────────────────────────────────────────────────

API_TIMEOUT = 30  # seconds per API call

def _get_api_key(key: str) -> Optional[str]:
    """Get API key from secrets, return None if not configured."""
    try:
        return st.secrets[key]
    except KeyError:
        return None


# ── API Query Functions ────────────────────────────────────────────────────

def query_orcid(orcid: str) -> Optional[Dict]:
    """Query ORCID API for researcher profile."""
    if not orcid:
        return None

    try:
        url = f"https://pub.orcid.org/v3.0/{orcid}/record"
        headers = {"Accept": "application/json"}
        response = requests.get(url, headers=headers, timeout=API_TIMEOUT)
        response.raise_for_status()

        data = response.json()
        return {
            "source": "ORCID",
            "data": data,
            "url": url,
            "timestamp": datetime.now().isoformat()
        }
    except Exception:
        return None


def query_openalex(name: str) -> Optional[Dict]:
    """Query OpenAlex for author information."""
    try:
        url = f"https://api.openalex.org/authors?search={quote(name)}"
        response = requests.get(url, timeout=API_TIMEOUT)
        response.raise_for_status()

        data = response.json()
        if data.get("results"):
            return {
                "source": "OpenAlex",
                "data": data,
                "url": url,
                "timestamp": datetime.now().isoformat()
            }
    except Exception:
        pass
    return None


def query_pubmed(name: str, field: str = "") -> Optional[Dict]:
    """Query PubMed for publications."""
    try:
        # First search for author
        search_url = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi"
        search_params = {
            "db": "pubmed",
            "term": f"{name}[Author]",
            "retmax": "3",
            "retmode": "json"
        }

        search_response = requests.get(search_url, params=search_params, timeout=API_TIMEOUT)
        search_response.raise_for_status()
        search_data = search_response.json()

        pmids = search_data.get("esearchresult", {}).get("idlist", [])
        if not pmids:
            return None

        # Get abstracts for top 3 results
        summary_url = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esummary.fcgi"
        summary_params = {
            "db": "pubmed",
            "id": ",".join(pmids[:3]),
            "retmode": "json"
        }

        summary_response = requests.get(summary_url, params=summary_params, timeout=API_TIMEOUT)
        summary_response.raise_for_status()
        summary_data = summary_response.json()

        return {
            "source": "PubMed",
            "data": summary_data,
            "url": search_url,
            "timestamp": datetime.now().isoformat()
        }
    except Exception:
        return None


def query_google_scholar(name: str) -> Optional[Dict]:
    """Query Google Scholar via web search (simplified)."""
    try:
        # This is a simplified implementation - in production you'd want proper Google Scholar API
        # For now, we'll simulate with a web search
        search_term = f'"{name}" site:scholar.google.com'
        url = f"https://www.google.com/search?q={quote(search_term)}"

        # Note: This would require proper scraping or Google Custom Search API
        # For demo purposes, we'll return a placeholder
        return {
            "source": "Google Scholar",
            "data": {"note": "Google Scholar search would require API key or scraping implementation"},
            "url": url,
            "timestamp": datetime.now().isoformat()
        }
    except Exception:
        return None


def query_opencorporates(company: str) -> Optional[Dict]:
    """Query OpenCorporates for company information."""
    if not company:
        return None

    try:
        api_key = _get_api_key("OPENCORPORATES_API_KEY")
        url = f"https://api.opencorporates.com/v0.4/companies/search"
        params = {"q": company}
        if api_key:
            params["api_token"] = api_key

        response = requests.get(url, params=params, timeout=API_TIMEOUT)
        response.raise_for_status()

        data = response.json()
        if data.get("results", {}).get("companies"):
            return {
                "source": "OpenCorporates",
                "data": data,
                "url": url,
                "timestamp": datetime.now().isoformat()
            }
    except Exception:
        pass
    return None


def query_web_search(name: str, institution: str = "", field: str = "") -> Optional[Dict]:
    """Perform web search for professional footprint."""
    try:
        # Simplified web search - in production use proper search API
        search_terms = [name]
        if institution:
            search_terms.append(institution)
        if field:
            search_terms.append(field)

        search_query = " ".join(search_terms)
        url = f"https://www.google.com/search?q={quote(search_query)}"

        return {
            "source": "Web Search",
            "data": {"note": "Web search would require search API implementation"},
            "url": url,
            "timestamp": datetime.now().isoformat()
        }
    except Exception:
        return None


# ── Analysis Functions ─────────────────────────────────────────────────────

def extract_name_from_email(email: str) -> str:
    """Extract likely name from email prefix."""
    if "@" in email:
        prefix = email.split("@")[0]
        # Convert common separators to spaces
        name = prefix.replace(".", " ").replace("_", " ").replace("-", " ")
        return name.title()
    return ""


def analyze_affiliation_confirmed(name: str, email: str, institution: str, company: str, sources: List[Dict]) -> bool:
    """Determine if affiliation is confirmed."""
    email_domain = email.split("@")[1] if "@" in email else ""

    # Check for institutional domains
    institutional_domains = [".edu", ".ac.uk", ".gov", ".org"]
    is_institutional_email = any(domain in email_domain for domain in institutional_domains)

    # Look for confirmation in sources
    for source in sources:
        if source and source.get("source") in ["OpenAlex", "ORCID"]:
            # Check if institution/company appears in the data
            data_str = json.dumps(source.get("data", {}))
            if institution and institution.lower() in data_str.lower():
                return True
            if company and company.lower() in data_str.lower():
                return True

    return False


def analyze_role_consistent(name: str, use_case: str, sources: List[Dict]) -> Optional[bool]:
    """Determine if role is consistent with use case."""
    # Extract field from use case (simplified)
    field_keywords = ["research", "academic", "medical", "engineering", "science", "clinical"]

    use_case_field = None
    for keyword in field_keywords:
        if keyword in use_case.lower():
            use_case_field = keyword
            break

    if not use_case_field:
        return None  # Cannot determine

    # Check sources for consistency
    publications_found = False
    for source in sources:
        if source and source.get("source") in ["PubMed", "OpenAlex", "Google Scholar"]:
            data_str = json.dumps(source.get("data", {}))
            if use_case_field in data_str.lower():
                publications_found = True
                break

    return publications_found if publications_found else None


def generate_flags(name: str, email: str, institution: str, company: str, sources: List[Dict]) -> List[str]:
    """Generate flags based on analysis."""
    flags = []

    # Check for name collisions (simplified - check if multiple results)
    openalex_results = [s for s in sources if s and s.get("source") == "OpenAlex"]
    if openalex_results and len(openalex_results[0].get("data", {}).get("results", [])) > 3:
        flags.append("name_collision")

    # Check institution/company not found
    affiliation_found = False
    for source in sources:
        if source and source.get("source") in ["OpenAlex", "Web Search"]:
            data_str = json.dumps(source.get("data", {}))
            if (institution and institution.lower() in data_str.lower()) or \
               (company and company.lower() in data_str.lower()):
                affiliation_found = True
                break

    if not affiliation_found and (institution or company):
        flags.append("institution_not_found")

    # Email domain mismatch
    email_domain = email.split("@")[1] if "@" in email else ""
    if institution and email_domain not in institution.lower().replace(" ", ""):
        flags.append("email_domain_mismatch")

    return flags


def generate_evidence(sources: List[Dict]) -> List[Dict]:
    """Generate evidence list from sources."""
    evidence = []

    for source in sources:
        if source:
            # Extract excerpt (simplified - just take a sample)
            data_str = json.dumps(source.get("data", {}))[:200] + "..."

            evidence.append({
                "source_url": source.get("url", ""),
                "excerpt": f"Data from {source.get('source')}: {data_str}",
                "date": source.get("timestamp", "")
            })

    return evidence


# ── Main Check Function ────────────────────────────────────────────────────

def perform_professional_footprint_check(
    name: str,
    email: str,
    linkedin_url: str = "",
    institution: str = "",
    company: str = "",
    use_case: str = ""
) -> Dict:
    """Perform the professional footprint verification check."""

    sources = []

    # Query sources in order (stop when confidence is high and flags resolved)
    confidence = "low"
    flags = []

    # 1. ORCID (skipped - not in input)
    # 2. OpenAlex
    openalex_result = query_openalex(name)
    if openalex_result:
        sources.append(openalex_result)

    # 3. PubMed
    pubmed_result = query_pubmed(name)
    if pubmed_result:
        sources.append(pubmed_result)

    # 4. Google Scholar
    scholar_result = query_google_scholar(name)
    if scholar_result:
        sources.append(scholar_result)

    # 5. OpenCorporates
    if company:
        opencorp_result = query_opencorporates(company)
        if opencorp_result:
            sources.append(opencorp_result)

    # 6. Web search
    web_result = query_web_search(name, institution or company)
    if web_result:
        sources.append(web_result)

    # Analyze results
    affiliation_confirmed = analyze_affiliation_confirmed(name, email, institution, company, sources)
    role_consistent = analyze_role_consistent(name, use_case, sources)
    flags = generate_flags(name, email, institution, company, sources)
    evidence = generate_evidence(sources)

    # Determine confidence
    if not flags and affiliation_confirmed:
        confidence = "high"
    else:
        confidence = "low"

    # Generate summary
    summary_parts = []
    if affiliation_confirmed:
        summary_parts.append("Professional affiliation confirmed")
    else:
        summary_parts.append("Professional affiliation not confirmed")

    if role_consistent is True:
        summary_parts.append("and role appears consistent with stated use case")
    elif role_consistent is False:
        summary_parts.append("but role consistency unclear")
    else:
        summary_parts.append("and role consistency could not be determined")

    if flags:
        summary_parts.append(f"({', '.join(flags)})")

    summary = ". ".join(summary_parts)

    # Build result
    result = {
        "confidence": confidence,
        "affiliation_confirmed": affiliation_confirmed,
        "role_consistent": role_consistent,
        "evidence": evidence,
        "flags": flags,
        "summary": summary,
        "cost_usd": 0.0  # Placeholder - would calculate based on API usage
    }

    return result


# ── Streamlit UI ───────────────────────────────────────────────────────────

def main():
    st.title("Professional Footprint Verification")
    st.subheader("Verify professional/research credentials against public sources")

    st.write("""
    This check analyzes a person's publicly visible professional footprint to determine
    if their stated use case is plausibly consistent with their background.
    """)

    # Input form
    with st.form("footprint_check"):
        col1, col2 = st.columns(2)

        with col1:
            name = st.text_input("Full Name", placeholder="Dr. Jane Smith")
            email = st.text_input("Email Address", placeholder="jane.smith@university.edu")

        with col2:
            institution = st.text_input("Institution (optional)", placeholder="Stanford University")
            company = st.text_input("Company (optional)", placeholder="Research Corp")

        linkedin_url = st.text_input("LinkedIn URL (optional)", placeholder="https://linkedin.com/in/janesmith")

        use_case = st.text_area(
            "Use Case (2-4 sentences)",
            placeholder="Describe how this person intends to use the product. Include their field of work and research interests.",
            height=100
        )

        submitted = st.form_submit_button("Run Footprint Check")

    if submitted:
        if not name or not email or not use_case:
            st.error("Please provide name, email, and use case.")
            return

        with st.spinner("Analyzing professional footprint across multiple sources..."):
            try:
                result = perform_professional_footprint_check(
                    name=name,
                    email=email,
                    linkedin_url=linkedin_url,
                    institution=institution,
                    company=company,
                    use_case=use_case
                )

                # Display raw JSON result
                st.success("Analysis Complete")
                st.json(result)

                # Show confidence indicator
                if result["confidence"] == "high":
                    st.success("🎉 High confidence verification")
                else:
                    st.warning("⚠️ Low confidence - review flags and evidence")

            except Exception as e:
                st.error(f"Error during analysis: {str(e)}")


if __name__ == "__main__":
    main()
