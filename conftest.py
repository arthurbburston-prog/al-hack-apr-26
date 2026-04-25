"""
Mock streamlit before any test module imports it.
The pages/ modules call st.warning/info/success as side effects during API calls;
these are harmless no-ops in tests. Secrets access raises KeyError so _get_api_key
returns None and the LLM agent is skipped.
"""
import sys
from unittest.mock import MagicMock

mock_st = MagicMock()
mock_st.secrets.__getitem__.side_effect = KeyError
sys.modules["streamlit"] = mock_st
