# 🌏 Jora Australia Job Scraper

A powerful web scraper for collecting job data from Jora Australia with AI-powered sponsorship analysis. Supports multiple scraping modes, full job description extraction, and exports to Excel format.

## ✨ Features

- **🔍 Multiple Scraping Modes**:
  - Interactive Search (single custom search)
  - Batch Search (multiple predefined searches)
  - Continuous Scraping (scheduled automatic runs)
  - Quick Test (fast testing mode)
  - AI-Powered Search (with visa sponsorship analysis)

- **🤖 AI-Powered Analysis** (Optional):
  - Visa sponsorship signal detection
  - Confidence scoring
  - Detailed reasoning
  - Contact information extraction

- **📝 Complete Data Extraction**:
  - Full job descriptions (no truncation)
  - Company details
  - Salary information
  - Application URLs
  - Contact information

- **💾 Excel Export**: Automatic export with timestamps
- **🔄 Duplicate Handling**: Smart duplicate removal
- **📊 Comprehensive Logging**: Detailed logs for monitoring

---

## 📊 Data Fields Collected

### Regular Scraping (Modes 1-4) - 15 Fields:
- Job Title
- Company Name
- Contact Name
- Phone Number
- Company Email
- Location
- State
- Salary Range
- Job Type
- **Full Job Description** (complete, no truncation)
- Posted Date
- Application URL
- Apply Form
- Source
- Scraped Date/Time

### AI-Powered Scraping (Mode 5) - 18 Fields:
All regular fields **PLUS**:
- Sponsorship Signal (yes/maybe/unknown)
- Sponsorship Confidence (0.0-1.0)
- Sponsorship Reasoning

---

## 🚀 Quick Start Guide

### Step 1: Prerequisites

**Required:**
- ✅ Python 3.12 or 3.13 (Recommended) ([Download Python](https://www.python.org/downloads/))
  - *Note: Python 3.14+ may lack pre-built wheels for some libraries.*
- ✅ Google Chrome browser ([Download Chrome](https://www.google.com/chrome/))
- ✅ Git (optional, for cloning) ([Download Git](https://git-scm.com/downloads))

**For AI Features (Optional):**
- 🤖 Google Gemini API Key ([Get Free API Key](https://aistudio.google.com/app/apikey))

---

### Step 2: Installation

#### Option A: Clone with Git
```bash
git clone <repository-url>
cd "Scrapping Mechine"
```

#### Option B: Download ZIP
1. Download the project as ZIP
2. Extract to your desired location
3. Open terminal/command prompt in the extracted folder

---

### Step 3: Install Dependencies (Using Virtual Environment)

It is highly recommended to use a virtual environment to avoid conflicts.

**Windows:**
```powershell
# Create virtual environment (using Python 3.12)
py -3.12 -m venv venv

# Activate virtual environment
.\venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

**Mac/Linux:**
```bash
# Create virtual environment
python3 -m venv venv

# Activate virtual environment
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### Step 4: Verify Installation
Run the built-in verification script to ensure everything is set up correctly:
```bash
python test_setup.py
```

**What gets installed:**
- `selenium` - Web automation
- `beautifulsoup4` - HTML parsing
- `pandas` - Excel export
- `openpyxl` - Excel file handling
- `google-genai` - AI analysis (optional)

---

### Step 5: Configuration (Optional)

#### For Regular Scraping (No AI):
No configuration needed! Just run the scraper.

#### For AI-Powered Scraping:
1. **Get a free Google Gemini API key**:
   - Visit: https://aistudio.google.com/app/apikey
   - Click "Create API Key"
   - Copy your API key

2. **Create `.env` file**:
   ```bash
   # Windows
   copy .env.example .env
   
   # Mac/Linux
   cp .env.example .env
   ```

3. **Edit `.env` file** and add your API key:
   ```env
   # AI Analysis Settings (for Mode 5 only)
   USE_AI_ANALYSIS=True
   GEMINI_API_KEY_1=your_api_key_here
   GEMINI_MODEL=gemini-2.5-flash
   ```

---

### Step 6: Run the Scraper

```bash
python main.py
```

**You'll see a menu:**
```
Select mode:
1. Interactive Search (Single search) - Regular scraping
2. Batch Search (Multiple predefined searches) - Regular scraping
3. Continuous Scraping (Scheduled runs) - Regular scraping
4. Quick Test (IT jobs in Sydney, 2 pages) - Regular scraping
5. AI-Powered Search (With sponsorship analysis) 🤖

Enter mode (1-5):
```

---

## 📖 Usage Guide

### Mode 1: Interactive Search (Recommended for Beginners)

**Best for:** Custom one-time searches

**Steps:**
1. Select mode `1`
2. Enter job keyword (e.g., "Registered Nurse")
3. Choose location (e.g., "Western Australia")
4. Set number of pages (e.g., `5`)

**Example:**
```
Enter mode (1-5): 1
Enter job title or keyword: nursing
Enter state number: 4  (Western Australia)
Maximum number of pages: 5
```

**Output:** Excel file in `data/output/` folder

---

### Mode 2: Batch Search

**Best for:** Scraping multiple job types or locations at once

**How to use:**
1. Edit `main.py` (around line 200)
2. Customize the search list:
   ```python
   searches = [
       ("Registered Nurse", "Queensland", 5),
       ("Software Engineer", "New South Wales", 5),
       ("Electrician", "Victoria", 5),
   ]
   ```
3. Run and select mode `2`

---

### Mode 3: Continuous Scraping

**Best for:** Monitoring job market over time

**Features:**
- Runs automatically at set intervals
- Appends new jobs to existing file
- Removes duplicates automatically

**Intervals:**
- Every hour
- Every 6 hours
- Every 12 hours
- Daily
- Custom interval

---

### Mode 4: Quick Test

**Best for:** Testing if the scraper works

**What it does:**
- Scrapes "IT" jobs in "Sydney"
- Only 2 pages
- Fast test run

---

### Mode 5: AI-Powered Search 🤖

**Best for:** Finding visa sponsorship opportunities

**Requirements:**
- Google Gemini API key (free)
- `.env` file configured

**What it analyzes:**
- ✅ Explicit sponsorship mentions
- ✅ Government employers
- ✅ High-demand occupations
- ✅ Confidence scoring
- ✅ Detailed reasoning

**Example output:**
```
Sponsorship Signal: maybe
Confidence: 0.85
Reasoning: "State government health employer (NSW Health) hiring for 
           high-demand occupation (Registered Nurse). Government health 
           departments commonly sponsor skilled healthcare workers."
```

---

## 📁 Project Structure

```
Scrapping Mechine/
├── src/
│   ├── scraper.py          # Main scraper logic
│   ├── ai_analyzer.py      # AI sponsorship analysis
│   ├── config.py           # Configuration settings
│   └── utils.py            # Utility functions
├── data/
│   └── output/             # Excel output files (created automatically)
├── logs/                   # Log files (created automatically)
├── drivers/                # Chrome driver (auto-downloaded)
├── documentation/          # Detailed documentation
├── main.py                 # Main entry point - RUN THIS
├── requirements.txt        # Python dependencies
├── .env.example           # Environment template
└── README.md              # This file
```

---

## ⚙️ Configuration Options

### Basic Settings (`.env` file)

```env
# Browser Settings
HEADLESS_MODE=True              # False = show browser window
PAGE_LOAD_TIMEOUT=60            # Seconds to wait for pages

# Scraping Settings
MAX_PAGES_PER_SEARCH=50         # Maximum pages per search
DELAY_BETWEEN_REQUESTS=2        # Delay between requests (seconds)
FETCH_FULL_DESCRIPTION=True     # Get complete job descriptions

# AI Settings (for Mode 5 only)
USE_AI_ANALYSIS=True            # Enable AI features
GEMINI_API_KEY_1=your_key_here  # Your Gemini API key
GEMINI_MODEL=gemini-2.5-flash   # AI model to use
AI_RATE_LIMIT_RPM=15            # Requests per minute (free tier)
```

---

## 📊 Output Format

### File Location
`data/output/jora_[keyword]_[location]_YYYYMMDD_HHMMSS.xlsx`

### Example Filenames
- `jora_nursing_western_australia_20260107_114026.xlsx`
- `jora_software_engineer_sydney_20260107_150000.xlsx`

### Excel Columns

**Regular Mode (15 columns):**
| Column | Example |
|--------|---------|
| job_title | "Registered Nurse" |
| company_name | "NSW Health" |
| location | "Sydney, NSW" |
| salary | "$80,000 - $95,000" |
| description | "Full job description..." (COMPLETE) |
| ... | ... |

**AI-Powered Mode (18 columns):**
All regular columns PLUS:
| Column | Example |
|--------|---------|
| sponsorship_signal | "maybe" |
| sponsorship_confidence | 0.85 |
| sponsorship_reasoning | "Government employer..." |

---

## 🔧 Troubleshooting

### ❌ "No jobs found"

**Possible causes:**
- Website structure changed
- Internet connection issue
- Page took too long to load

**Solutions:**
1. Check your internet connection
2. Try again (sometimes pages load slowly)
3. Increase `PAGE_LOAD_TIMEOUT` in `.env`:
   ```env
   PAGE_LOAD_TIMEOUT=90
   ```
4. Run in visible mode to see what's happening:
   ```env
   HEADLESS_MODE=False
   ```

---

### ❌ "Chrome driver error"

**Solutions:**
1. **Update Google Chrome** to the latest version
2. **Delete the `drivers` folder** and run again (auto-downloads correct driver)
3. **Check internet connection** (driver downloads automatically)

---

### ❌ "Timeout error"

**Solutions:**
1. Increase timeout in `.env`:
   ```env
   PAGE_LOAD_TIMEOUT=90
   ```
2. Check internet speed
3. Try scraping fewer pages at once

---

### ❌ "AI analysis not working"

**Solutions:**
1. **Check API key** in `.env` file
2. **Verify API key is active**: https://aistudio.google.com/app/apikey
3. **Check rate limits**: Free tier = 15 requests/minute
4. **Review logs**: Check `logs/scraper.log` for errors

---

### ❌ "Descriptions are short/truncated"

**This is FIXED!** If you still see short descriptions:
1. **Make sure you're using the latest code**
2. **Check logs** for "Fetched full description (XXXX chars)"
3. **If logs show large numbers but Excel has short text:**
   - This was a bug that's been fixed
   - Re-download the latest version

---

### ❌ "Excel file won't open"

**Solutions:**
1. Close Excel if it's already open
2. Check if file is being used by another program
3. Try opening with Google Sheets or LibreOffice

---

## � Tips & Best Practices

### For Best Results:

1. **Start Small**: Test with 1-2 pages first
2. **Use Headless Mode**: Faster and more stable
   ```env
   HEADLESS_MODE=True
   ```
3. **Respect Rate Limits**: Don't scrape too aggressively
   ```env
   DELAY_BETWEEN_REQUESTS=3  # Increase if needed
   ```
4. **Monitor Logs**: Check `logs/scraper.log` for issues
5. **Regular Backups**: Save your Excel files regularly

### For AI-Powered Search:

1. **Free Tier Limits**: 15 requests/minute
2. **Best for**: Targeted searches (not bulk scraping)
3. **Use Regular Mode First**: Get all jobs, then analyze subset with AI
4. **Multiple API Keys**: Add more keys for higher limits:
   ```env
   GEMINI_API_KEY_1=key1_here
   GEMINI_API_KEY_2=key2_here
   GEMINI_API_KEY_3=key3_here
   ```

---

## � Additional Documentation

Detailed documentation available in the `documentation/` folder:

- **SCRAPING_MODES_SEPARATION.md** - Detailed mode explanations
- **QUICK_MODE_REFERENCE.md** - Quick reference guide
- **FLOW_DIAGRAMS.md** - Visual flow diagrams
- **CRITICAL_DESCRIPTION_FIX.md** - Technical bug fixes
- **AI_FEATURE_DOCUMENTATION.md** - AI features guide

---

## 🆘 Getting Help

### Check These First:
1. **Logs**: `logs/scraper.log` - Shows what's happening
2. **This README**: Most common issues covered above
3. **Documentation folder**: Detailed technical docs

### Common Issues Checklist:
- [ ] Python 3.12 or 3.13 installed?
- [ ] Chrome browser installed?
- [ ] Virtual environment created and activated?
- [ ] Dependencies installed? (`pip install -r requirements.txt`)
- [ ] Internet connection working?
- [ ] For AI: API key configured in `.env`?

---

## 🎯 Example Workflows

### Workflow 1: Find Nursing Jobs in Western Australia
```bash
python main.py
# Select: 1 (Interactive Search)
# Keyword: nursing
# Location: 4 (Western Australia)
# Pages: 5
```

### Workflow 2: Monitor IT Jobs Daily
```bash
python main.py
# Select: 3 (Continuous Scraping)
# Interval: Daily
# Keyword: software developer
# Location: Sydney
# Pages: 10
```

### Workflow 3: Find Sponsorship Opportunities
```bash
python main.py
# Select: 5 (AI-Powered Search)
# Keyword: registered nurse
# Location: Queensland
# Pages: 5
```

---

## 📄 License & Legal

**Educational & Research Use**

This scraper is for:
- ✅ Educational purposes
- ✅ Personal research
- ✅ Job market analysis

**Please:**
- ⚠️ Respect Jora's Terms of Service
- ⚠️ Don't overload their servers
- ⚠️ Use reasonable delays between requests
- ⚠️ Don't use for commercial purposes without permission

---

## 🔄 Updates & Maintenance

### If Jora Changes Their Website:

The scraper may stop working if Jora updates their HTML structure. To fix:

1. **Run in visible mode**:
   ```env
   HEADLESS_MODE=False
   ```

2. **Inspect the page**:
   - Right-click on job cards
   - Select "Inspect"
   - Find new CSS selectors

3. **Update `src/config.py`**:
   ```python
   SELECTORS = {
       'job_card': '.new-selector-here',
       'job_title': '.new-title-selector',
       # ... update as needed
   }
   ```

---

## 🎉 You're Ready!

### Quick Start Checklist:
- [x] Python installed
- [x] Chrome installed
- [x] Dependencies installed (`pip install -r requirements.txt`)
- [x] (Optional) API key configured for AI features

### Run Your First Scrape:
```bash
python main.py
```

**Happy Scraping! 🚀**

---

## � Support

For technical issues:
1. Check `logs/scraper.log`
2. Review troubleshooting section above
3. Check documentation folder for detailed guides

---

**Made with ❤️ for job seekers and researchers**
