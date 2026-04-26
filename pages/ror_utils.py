def extract_email_domain(email):
    """
    Extracts the domain from an email address.
    
    Args:
        email (str): The email address to extract the domain from.
    
    Returns:
        str: The domain of the email address.
    """
    return email.split('@')[1] if '@' in email else None


def search_ror_institution(query):
    """
    Searches for a ROR institution by query.
    
    Args:
        query (str): The search query.
    
    Returns:
        dict: The retrieved institution information if found, else None.
    """
    # Placeholder for actual search logic
    return {"name": "Example Institution", "ror_id": "https://ror.org/01asdf"} if query else None


def extract_domains_from_institution(institution):
    """
    Extracts domains from a ROR institution.
    
    Args:
        institution (dict): The institution information.
    
    Returns:
        list: A list of extracted domains.
    """
    # Placeholder for extracting domains logic
    return ["example.edu", "example.org"] if institution else []


def check_email_domain_match(email, institution):
    """
    Checks if the email domain matches any of the ROR institution domains.
    
    Args:
        email (str): The email address.
        institution (dict): The institution information with domains.
    
    Returns:
        bool: True if there is a match, else False.
    """
    email_domain = extract_email_domain(email)
    if not email_domain or not institution:
        return False
    return email_domain in extract_domains_from_institution(institution)
