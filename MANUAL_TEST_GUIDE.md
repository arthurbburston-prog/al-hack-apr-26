# Professional Footprint Verification - Manual Test Guide

## Manual Test 4: UI Integration and User Experience Test

### Objective
Test the complete user experience including UI interaction, collision handling, and LLM enhancement feedback.

### Prerequisites
- Streamlit app running: `uv run streamlit run main.py`
- OpenRouter API key configured in `.streamlit/secrets.toml`
- Browser access to the local Streamlit app

### Test Steps

#### Step 1: Basic Functionality Test
1. **Navigate** to the Professional Footprint page
2. **Enter test data**:
   - Name: `Dr. Sarah Johnson`
   - Email: `sarah.johnson@stanford.edu`
   - Institution: `Stanford University`
   - Use Case: `I am a medical researcher studying cancer immunotherapy and personalized medicine approaches.`
3. **Click** "Run Footprint Check"
4. **Verify**:
   - ✅ Results display within 30 seconds
   - ✅ Confidence level shown (HIGH expected)
   - ✅ Evidence sources listed
   - ✅ No LLM enhancement message (should be high confidence from APIs)

#### Step 2: LLM Enhancement Test
1. **Enter test data for low confidence case**:
   - Name: `Dr. Alex Chen`
   - Email: `alex.chen@newbiotech.com`
   - Institution: `NewBioTech Research`
   - Use Case: `I am a bioinformatics researcher developing machine learning models for drug discovery and genomic analysis.`
2. **Click** "Run Footprint Check"
3. **Verify**:
   - ✅ "API confidence is low - calling LLM agent" message appears
   - ✅ Progress indicator or loading state
   - ✅ Results show "LLM Enhanced: True"
   - ✅ Enhanced evidence or analysis in results

#### Step 3: Name Collision Handling Test
1. **Enter ambiguous name**:
   - Name: `John Smith`
   - Email: `john.smith@university.edu`
   - Institution: `State University`
   - Use Case: `I am a computer science professor teaching algorithms and data structures.`
2. **Click** "Run Footprint Check"
3. **Verify collision handling**:
   - ✅ Multiple candidates detected
   - ✅ User prompted to select specific candidate
   - ✅ Results update after selection
   - ✅ Selected candidate data used in final analysis

#### Step 4: Error Handling Test
1. **Test with invalid email**:
   - Name: `Test User`
   - Email: `invalid-email`
   - Institution: `Test University`
   - Use Case: `Testing error handling`
2. **Click** "Run Footprint Check"
3. **Verify**:
   - ✅ Graceful error handling
   - ✅ No crashes or unhandled exceptions
   - ✅ Clear error messages to user

#### Step 5: API Key Missing Test
1. **Temporarily remove** OpenRouter API key from `secrets.toml`
2. **Restart** Streamlit app
3. **Run a low confidence check**
4. **Verify**:
   - ✅ System works without LLM (falls back gracefully)
   - ✅ Clear message about missing API key
   - ✅ API-only results still functional

### Expected Results

#### ✅ PASS Criteria
- [ ] All form inputs accept data correctly
- [ ] Loading states provide user feedback
- [ ] Results display clearly with proper formatting
- [ ] LLM enhancement triggers appropriately
- [ ] Name collision UI works smoothly
- [ ] Error states are user-friendly
- [ ] No crashes or hangs during testing

#### ❌ FAIL Criteria
- [ ] App crashes or hangs
- [ ] Results don't display
- [ ] LLM enhancement doesn't trigger when expected
- [ ] UI is confusing or non-functional
- [ ] Error messages are unclear

### Test Environment
- **Browser**: Chrome/Firefox/Safari
- **Screen Size**: Desktop (1920x1080)
- **Network**: Stable internet connection
- **API Keys**: OpenRouter configured

### Notes
- Document any unexpected behavior
- Note response times for each test
- Capture screenshots of key UI states
- Test on different browsers if possible

### Completion
Mark test as **PASSED** if all steps complete successfully and meet PASS criteria.