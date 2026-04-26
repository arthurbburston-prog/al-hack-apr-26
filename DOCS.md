# KYC AIO — Project Documentation

## Project Overview

KYC AIO ("Know Your Customer, All-In-One") is a Streamlit app that bundles multiple identity and credential verification checks into a single tool. It's designed for sellers of high-risk materials who need to validate a buyer's identity, institutional affiliation, payment legitimacy, and professional background before completing a transaction.

---

## Tech Stack

| Layer | Technology |
|---|---|
| Language | Python 3.10+ |
| Package manager | [uv](https://docs.astral.sh/uv/) |
| UI | [Streamlit](https://streamlit.io/) |
| LLM (optional fallback) | GPT-4o-mini via [OpenRouter](https://openrouter.ai/) (OpenAI-compatible API) |
| Address verification | [Smarty US Street Address API](https://www.smarty.com/) |
| Card/BIN lookup | [binlist.net](https://binlist.net/) (free, no key required) |
| Researcher lookup | [OpenAlex](https://openalex.org/), [ORCID](https://orcid.org/), [PubMed E-utilities](https://www.ncbi.nlm.nih.gov/books/NBK25501/) |
| Institution registry | [ROR API](https://ror.org/) |
| Company lookup | [OpenCorporates API](https://opencorporates.com/) (optional, key required) |
| Scholar search | Google Custom Search API (optional) |
| Email delivery | Gmail SMTP (app password) |

---

## How to Run

**Prerequisites:** Install [uv](https://docs.astral.sh/uv/), then clone the repo.

```bash
# Install dependencies and run the app
uv run streamlit run main.py
```

Create `.streamlit/secrets.toml` with your credentials (see Environment Variables below) before starting.

---

## File Breakdown

| File | Purpose |
|---|---|
| `main.py` | Streamlit entry point — home page with navigation to all checks |
| `pages/address_type_check.py` | Verifies a US address via Smarty: residential vs. commercial, CMRA flag, vacancy status |
| `pages/email_otp.py` | Sends a 6-digit OTP to an email address via Gmail SMTP and verifies it |
| `pages/payment_identity_check.py` | BIN lookup (detects prepaid/gift cards) + AVS/CVV/name consistency checker for payment processor responses |
| `pages/professional_footprint.py` | Multi-source professional background check against OpenAlex, PubMed, ORCID, and OpenCorporates; falls back to GPT-4o-mini via OpenRouter when API confidence is low |
| `pages/ror_check.py` | Checks whether a researcher's email domain matches their claimed institution in the ROR database |
| `pages/ror_utils.py` | Helper functions for ROR API queries and email domain matching (used by `ror_check.py` and `rors_email_combined.py`) |
| `pages/rors_email_combined.py` | Two-step flow: ROR domain check first, then email OTP only if the domain check passes |
| `pages/voucher_reference.py` | Looks up a buyer in a local CSV of voucher/vouchee relationships |
| `data/vouchers.csv` | Flat-file database of who vouches for whom (voucher name → vouchee name + email) |
| `conftest.py` | Pytest fixture that mocks Streamlit so page modules can be imported in tests |
| `test_professional_footprint.py` | Integration tests for the professional footprint check (makes real HTTP calls to OpenAlex and PubMed) |

---

## Environment Variables

All secrets go in `.streamlit/secrets.toml`:

```toml
[email]
address = "your-gmail-address@gmail.com"
password = "your-gmail-app-password"    # Generate at myaccount.google.com/apppasswords

[smarty]
auth_id    = "your-smarty-auth-id"
auth_token = "your-smarty-auth-token"  # Register at smarty.com (free tier: 250 lookups/month)

# Optional — enables LLM fallback in the professional footprint check
OPENAI_API_KEY = "your-openrouter-api-key"   # From openrouter.ai

# Optional — enables company verification in professional footprint check
OPENCORPORATES_API_KEY = "your-opencorporates-key"

# Optional — enables Google Scholar search in professional footprint check
GOOGLE_CUSTOM_SEARCH_KEY = "your-google-cse-key"
GOOGLE_CUSTOM_SEARCH_CX  = "your-search-engine-id"
```

The app runs with only `[email]` and `[smarty]` configured; the optional keys unlock additional checks.

---

## Known Limitations

- **Voucher debug panel:** `voucher_reference.py` has a "Browse all vouchers" expander that exposes the full referral list — remove before a real demo.
- **LinkedIn not queried:** The professional footprint form collects a LinkedIn URL but doesn't call any LinkedIn API (no public API available).
- **`cost_usd` is always 0.0:** The cost field in footprint results is a placeholder and not calculated.
- **binlist.net rate limit:** ~10 requests/hour on the free tier with no API key.
- **Google Scholar fallback:** Without a Google Custom Search key, Scholar search returns nothing silently.
- **`anthropic` package unused:** Listed as a dependency in `pyproject.toml` but no page imports it; all LLM calls go through OpenRouter using the OpenAI SDK.
- **OTP over plain SMTP:** The OTP flow uses Gmail SMTP with `starttls` — acceptable for a hackathon, but not production-grade.
