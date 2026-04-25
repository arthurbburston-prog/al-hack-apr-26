"""Integration tests for professional footprint verification.

These tests make real HTTP requests to OpenAlex and PubMed.
Run with: uv run pytest test_professional_footprint.py -v
"""

from pages.professional_footprint import perform_professional_footprint_check


def test_high_confidence_academic_returns_valid_structure():
    """Well-known academic should return a structurally valid result."""
    result = perform_professional_footprint_check(
        name="Albert Einstein",
        email="einstein@princeton.edu",
        institution="Princeton University",
        use_case="I am a theoretical physicist conducting research in relativity and quantum mechanics.",
    )

    assert result["confidence"] in ("high", "low")
    assert isinstance(result["affiliation_confirmed"], bool)
    assert isinstance(result.get("flags", []), list)
    assert len(result.get("evidence", [])) > 0


def test_unknown_person_returns_valid_structure():
    """Unknown person with no online presence should not crash."""
    result = perform_professional_footprint_check(
        name="Dr. Jane Smith",
        email="jane.smith@unknown-research.edu",
        institution="Unknown Research Institute",
        use_case="I am a researcher studying advanced materials science and nanotechnology.",
    )

    assert result["confidence"] in ("high", "low")
    assert isinstance(result["affiliation_confirmed"], bool)
    assert isinstance(result.get("flags", []), list)


def test_company_executive_includes_sources_for_collision_detection():
    """Common name with company should include sources key for UI collision handling."""
    result = perform_professional_footprint_check(
        name="John Smith",
        email="john.smith@techcorp.com",
        institution="",
        company="TechCorp Inc",
        use_case="I am a senior software engineer leading development of AI-powered enterprise solutions.",
    )

    assert result["confidence"] in ("high", "low")
    assert "sources" in result


def test_result_never_has_false_role_consistent():
    """role_consistent should only ever be True or None, never False (absence != malice rule)."""
    result = perform_professional_footprint_check(
        name="Dr. Alex Chen",
        email="alex.chen@biotech.com",
        institution="BioTech Research",
        use_case="I am a bioinformatics researcher developing machine learning models for drug discovery.",
    )

    assert result.get("role_consistent") in (True, None)
