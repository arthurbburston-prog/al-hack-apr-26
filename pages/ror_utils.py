import requests
from urllib.parse import urlparse
from typing import Dict, List, Tuple, Optional


def extract_email_domain(email: str) -> Optional[str]:
    """Extract domain from email address."""
    if "@" not in email:
        return None
    return email.split("@")[1].lower()


def search_ror_institution(institution_name: str) -> Dict:
    """Search for an institution in the ROR database."""
    try:
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

        results = data.get("items", [])
        if results:
            return {"status": "success", "data": results, "message": None}

        return {
            "status": "error",
            "data": None,
            "message": "No results returned from ROR API"
        }

    except requests.exceptions.Timeout:
        return {"status": "error", "data": None, "message": "Request to ROR API timed out"}
    except requests.exceptions.RequestException as e:
        return {"status": "error", "data": None, "message": f"Failed to contact ROR API: {str(e)}"}
    except Exception as e:
        return {"status": "error", "data": None, "message": f"Unexpected error: {str(e)}"}


def extract_domains_from_institution(institution: Dict) -> List[str]:
    """Extract all domains associated with a ROR institution."""
    domains = []

    if "links" in institution:
        for link in institution.get("links", []):
            if link.get("type") == "website":
                url = link.get("value", "")
                if url:
                    domain = urlparse(url).netloc.lower()
                    if domain.startswith("www."):
                        domain = domain[4:]
                    if domain:
                        domains.append(domain)

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

    return list(set(domains))


def check_email_domain_match(email: str, institution_data: List[Dict]) -> Tuple[str, float, List[Dict]]:
    """
    Check if email domain matches any domain in the institution data.

    Returns:
        Tuple of (status: str, confidence: float, evidence: List[Dict])
    """
    email_domain = extract_email_domain(email)

    if not email_domain:
        return "fail", 0.0, [{"type": "error", "message": "Invalid email format"}]

    evidence = [{"type": "email_domain", "value": email_domain, "description": "Extracted domain from email"}]
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

        for domain in institution_domains:
            if email_domain == domain:
                matched_institutions.append({"name": inst_name, "ror_id": inst_id, "matched_domain": domain})

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
