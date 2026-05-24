# AI-Powered Job Scraping Feature

## Overview

The AI-powered scraping feature uses **Google Gemini AI** to enhance job data extraction with intelligent analysis. This feature adds:

1. **Contact Information Extraction** - Automatically extracts contact names, phone numbers, and email addresses from job descriptions
2. **Sponsorship Signal Detection** - Analyzes job postings to determine visa sponsorship likelihood
3. **Confidence Scoring** - Provides confidence levels and reasoning for AI decisions

## New Data Structure

Each scraped job now includes these additional fields:

```python
{
    'job_title': str,
    'company_name': str,
    'contact_name': str,              # AI extracted
    'phone_number': str,              # AI extracted  
    'company_email': str,             # AI extracted
    'location': str,
    'state': str,
    'salary': str,
    'job_type': str,
    'description': str,
    'posted_date': str,
    'application_url': str,
    'apply_form': str,
    'source': str,
    'sponsorship_signal': str,        # 'yes', 'maybe', 'unknown'
    'sponsorship_confidence': float,  # 0.0-1.0
    'sponsorship_reasoning': str,     # AI explanation
    'scraped_date': str
}
```

## Sponsorship Signal Classification

### "yes" - Explicit Sponsorship
Job explicitly mentions:
- Visa sponsorship available
- 482 visa (TSS)
- 186 visa (ENS)
- "Will sponsor" or similar phrases

### "maybe" - Potential Sponsorship
Indicators include:
- Government or public sector role
- Large multinational company
- High-demand occupations (healthcare, engineering)
- "International candidates welcome"
- "Diverse backgrounds encouraged"
- Company on official sponsor register

### "unknown" - No Information
No sponsorship information found in the job posting.

## Setup

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

This will install the new dependency: `google-generativeai`

### 2. Configure API Keys

The scraper uses **3 Gemini API keys** with automatic rotation for reliability:

**Option A: Hardcoded (Already configured)**
The keys are already set in `src/config.py`:
- scraping-mechine-1: `AIzaSyAhdu8XFz74gRfzlItUB-KndYPsYi0hZio`
- scraping-mechine-2: `AIzaSyA2lVvQ3wgPHCabFJiiPezNzIVC0TLhAZ4`
- scraping-mechine-3: `AIzaSyBhJUGEKcIA9HeP29wdCnI6xS82gn8hCMg`

**Option B: Environment Variables (Recommended for production)**
Create a `.env` file:

```bash
USE_AI_ANALYSIS=True
GEMINI_API_KEY_1=AIzaSyAhdu8XFz74gRfzlItUB-KndYPsYi0hZio
GEMINI_API_KEY_2=AIzaSyA2lVvQ3wgPHCabFJiiPezNzIVC0TLhAZ4
GEMINI_API_KEY_3=AIzaSyBhJUGEKcIA9HeP29wdCnI6xS82gn8hCMg
```

## Usage

### Method 1: Interactive Mode (Recommended)

Run the scraper and select option 5:

```bash
python main.py
```

```
Select mode:
1. Interactive Search (Single search)
2. Batch Search (Multiple predefined searches)
3. Continuous Scraping (Scheduled runs)
4. Quick Test (IT jobs in Sydney, 2 pages)
5. AI-Powered Search (With sponsorship analysis) 🤖

Enter mode (1-5): 5
```

### Method 2: Programmatic Usage

```python
from src.scraper import JoraScraper

# Initialize with AI enabled
scraper = JoraScraper(use_ai=True)

# Search for jobs
jobs = scraper.search_jobs(
    job_keyword="Registered Nurse",
    location="Sydney",
    max_pages=5
)

# Results include AI analysis
for job in jobs:
    print(f"Title: {job['job_title']}")
    print(f"Sponsorship: {job['sponsorship_signal']}")
    print(f"Confidence: {job['sponsorship_confidence']}")
    print(f"Reasoning: {job['sponsorship_reasoning']}")
    print(f"Contact: {job['contact_name']}")
    print(f"Phone: {job['phone_number']}")
    print(f"Email: {job['company_email']}")
    print("-" * 60)

scraper.close()
```

### Method 3: Enable AI for Existing Modes

Modify any scraper initialization to include `use_ai=True`:

```python
# Before
scraper = JoraScraper()

# After
scraper = JoraScraper(use_ai=True)
```

## API Key Rotation

The system automatically rotates between 3 API keys if one fails or hits rate limits:

1. **Primary Key** - Used first
2. **Secondary Key** - Fallback if primary fails
3. **Tertiary Key** - Final fallback

This ensures:
- ✅ High reliability
- ✅ Automatic failover
- ✅ Continued operation even if one key expires

## Rate Limiting

**Free Tier Limits:**
- 15 requests per minute (RPM)
- 1 million tokens per minute (TPM)
- 1,500 requests per day (RPD)

**Automatic Handling:**
- The scraper automatically pauses when approaching rate limits
- Processes ~900 jobs per hour
- Completely free for typical usage

**Example Processing Times:**
- 100 jobs: ~7 minutes
- 500 jobs: ~35 minutes
- 1000 jobs: ~70 minutes

## Output

Results are saved to Excel with all fields included:

```
data/output/jora_ai_registered_nurse_sydney_20260106_163000.xlsx
```

**Summary Statistics** are displayed after scraping:

```
✅ Successfully scraped and analyzed 150 jobs!

📊 Sponsorship Analysis:
  ✓ Explicit sponsorship: 23 jobs
  ? Potential sponsorship: 67 jobs
  - No sponsorship info: 60 jobs

📞 Contact Information Found:
  • Contact names: 45 jobs
  • Phone numbers: 38 jobs
  • Email addresses: 52 jobs
```

## Testing

### Test the AI Analyzer

```bash
cd src
python ai_analyzer.py
```

This runs a test with sample job data and displays the AI analysis result.

### Test with Real Jobs

```bash
python main.py
# Select option 5 (AI-Powered Search)
# Enter: IT jobs, Sydney, 2 pages
```

## Cost Analysis

**Gemini Flash Pricing (Free Tier):**
- ✅ **FREE** for up to 1,500 requests/day
- ✅ **FREE** for up to 1M tokens/day

**Typical Usage:**
- Average job: ~600 tokens (input + output)
- 1000 jobs/day: ~600,000 tokens
- **Cost: $0.00** (within free tier)

**If you exceed free tier:**
- Input: $0.075 per 1M tokens
- Output: $0.30 per 1M tokens
- 1000 jobs: ~$0.06

## Architecture

```
┌─────────────────┐
│  JoraScraper    │
│  (Selenium)     │
└────────┬────────┘
         │
         │ Scrapes job data
         ▼
┌─────────────────┐
│   Job Data      │
│   (Basic info)  │
└────────┬────────┘
         │
         │ If use_ai=True
         ▼
┌─────────────────┐
│ GeminiAnalyzer  │
│  (AI Analysis)  │
└────────┬────────┘
         │
         │ Enhances with:
         │ • Contact info
         │ • Sponsorship signals
         │ • Confidence scores
         ▼
┌─────────────────┐
│  Enhanced Data  │
│  (Excel output) │
└─────────────────┘
```

## Key Features

### 1. Multi-Key Rotation
- Automatic failover between 3 API keys
- Continues operation if one key fails
- Logs which key is being used

### 2. Rate Limit Handling
- Automatic pause when approaching limits
- Smart batching for efficiency
- Progress logging every 10 jobs

### 3. Regex Fallback
- Uses regex patterns for contact extraction
- Supplements AI results
- Ensures maximum data capture

### 4. Error Handling
- Graceful degradation if AI fails
- Default values for failed analysis
- Detailed error logging

## Troubleshooting

### AI Analysis Not Working

**Check API Keys:**
```python
from src.config import GEMINI_API_KEYS
print(GEMINI_API_KEYS)
```

**Test API Connection:**
```bash
cd src
python ai_analyzer.py
```

### Rate Limit Errors

If you see rate limit errors:
1. Wait 1 minute
2. The scraper will automatically resume
3. Consider reducing `AI_BATCH_SIZE` in config

### No Contact Information Found

This is normal! Many job postings don't include:
- Contact names
- Direct phone numbers
- Email addresses

The AI will return `null` for missing information.

## Advanced Configuration

Edit `src/config.py`:

```python
# Use different Gemini model
GEMINI_MODEL = 'gemini-1.5-flash'  # More stable
# or
GEMINI_MODEL = 'gemini-2.0-flash-exp'  # Latest features

# Adjust rate limiting
AI_RATE_LIMIT_RPM = 10  # More conservative

# Change batch size
AI_BATCH_SIZE = 5  # Smaller batches
```

## Future Enhancements

Potential additions:
- [ ] Sponsor register database integration
- [ ] Historical sponsorship tracking
- [ ] Salary range normalization
- [ ] Skills extraction and matching
- [ ] Job quality scoring
- [ ] Duplicate detection across sources

## Support

For issues or questions:
1. Check logs in `logs/scraper.log`
2. Review error messages
3. Test with small batches first (2-3 pages)

## License

This AI feature uses Google's Gemini API under their terms of service.
