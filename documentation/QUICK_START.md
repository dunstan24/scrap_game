# 🚀 QUICK START GUIDE - Jora Australia Job Scraper

## ✅ Installation Complete!

All dependencies have been installed and directories created. You're ready to start scraping!

---

## 📋 What You Have

### Project Structure:
```
Scrapping Mechine/
├── src/
│   ├── scraper.py       ✅ Main scraper engine
│   ├── config.py        ✅ Settings & configuration
│   └── utils.py         ✅ Helper functions
├── data/
│   ├── raw/             ✅ Created
│   ├── processed/       ✅ Created
│   └── output/          ✅ Excel files will be saved here
├── logs/                ✅ Created (scraper.log will be here)
├── main.py              ✅ Interactive scraper
├── example_usage.py     ✅ Code examples
└── requirements.txt     ✅ Dependencies installed
```

---

## 🎯 How to Use

### Option 1: Interactive Mode (Easiest)

Run the main script and follow the prompts:

```bash
python main.py
```

You'll see a menu:
1. **Interactive Search** - Custom single search
2. **Batch Search** - Multiple predefined searches
3. **Continuous Scraping** - Scheduled automatic runs
4. **Quick Test** - Test with IT jobs in Sydney

**Recommended for first time**: Choose option 4 (Quick Test)

---

### Option 2: Run Examples

Try pre-built examples:

```bash
python example_usage.py
```

Examples included:
1. IT Jobs in Sydney
2. Nurses in Queensland
3. Electricians across 3 states
4. All Jobs in Melbourne
5. Multiple Tech Jobs

---

### Option 3: Write Your Own Script

Create a custom script:

```python
from src.scraper import JoraScraper
from src.utils import save_to_excel

# Initialize scraper
scraper = JoraScraper(headless=True)  # False to see browser

try:
    # Search for jobs
    jobs = scraper.search_jobs(
        job_keyword="Software Engineer",
        location="Melbourne",
        max_pages=5
    )
    
    # Save to Excel
    if jobs:
        save_to_excel(jobs, "my_search")
        print(f"Found {len(jobs)} jobs!")
        
finally:
    scraper.close()
```

---

## 🎬 Step-by-Step First Run

### 1. Test the Scraper

```bash
python main.py
```

- Select option **4** (Quick Test)
- This will scrape 2 pages of IT jobs in Sydney
- Browser will open (you can watch it work)
- Excel file will be saved to `data/output/`

### 2. Try Interactive Search

```bash
python main.py
```

- Select option **1** (Interactive Search)
- Enter job keyword: `Registered Nurse`
- Select state: `3` (Queensland)
- Max pages: `5`
- Wait for scraping to complete
- Check `data/output/` for Excel file

### 3. Setup Continuous Scraping

```bash
python main.py
```

- Select option **3** (Continuous Scraping)
- Choose interval (e.g., every 6 hours)
- Define search parameters
- Let it run in background
- Press Ctrl+C to stop

---

## 📊 Understanding the Output

### Excel File Structure

Your Excel files will contain these columns:

| Column | Description | Example |
|--------|-------------|---------|
| job_title | Job position | "Software Engineer" |
| company_name | Employer | "Google Australia" |
| location | Job location | "Sydney NSW" |
| state | Australian state | "New South Wales" |
| salary | Salary range | "$80,000 - $120,000" |
| job_type | Employment type | "Full-time" |
| description | Job description | "We are looking for..." |
| skills | Required skills | "Python, AWS, Docker" |
| posted_date | When posted | "2 days ago" |
| application_url | Link to apply | "https://au.jora.com/..." |
| source | Data source | "Jora Australia" |
| scraped_date | When scraped | "2026-01-06 14:30:00" |

### File Naming

Files are automatically named with timestamps:
- `jora_software_engineer_sydney_20260106_143000.xlsx`
- Format: `jora_[keyword]_[location]_[YYYYMMDD]_[HHMMSS].xlsx`

---

## ⚙️ Configuration

### Change Settings

Edit `.env` file to customize:

```env
# Run browser in background (True) or visible (False)
HEADLESS_MODE=True

# How long to wait for page elements (seconds)
IMPLICIT_WAIT=10

# Maximum pages to scrape per search
MAX_PAGES_PER_SEARCH=50

# Delay between page requests (seconds)
DELAY_BETWEEN_REQUESTS=2
```

### Common Adjustments

**See the browser working:**
```env
HEADLESS_MODE=False
```

**Scrape more pages:**
```env
MAX_PAGES_PER_SEARCH=100
```

**Faster scraping (not recommended):**
```env
DELAY_BETWEEN_REQUESTS=1
```

---

## 🔍 Search Tips

### By Location

**Specific cities:**
- `Sydney`
- `Melbourne`
- `Brisbane`
- `Perth`
- `Adelaide`

**By state:**
- `New South Wales`
- `Victoria`
- `Queensland`
- `Western Australia`
- `South Australia`
- `Tasmania`
- `Australian Capital Territory`
- `Northern Territory`

**All Australia:**
- Leave location blank or use `All Australia`

### By Job Type

**Specific titles:**
- `Software Engineer`
- `Registered Nurse`
- `Electrician`
- `Accountant`
- `Data Analyst`

**Broad categories:**
- `Information Technology`
- `Healthcare`
- `Construction`
- `Finance`

**Leave blank for all jobs in a location**

---

## 🛠️ Troubleshooting

### Problem: "No jobs found"

**Solution:**
1. Run with `HEADLESS_MODE=False` to see what's happening
2. Check if Jora website structure changed
3. Update CSS selectors in `src/config.py`

### Problem: Chrome driver error

**Solution:**
- The script auto-downloads the driver
- Make sure Chrome browser is installed
- Check internet connection

### Problem: Scraping is slow

**Solution:**
- This is normal and intentional (to be respectful)
- Reduce `MAX_PAGES_PER_SEARCH` for faster results
- Don't decrease `DELAY_BETWEEN_REQUESTS` too much

### Problem: Duplicate data

**Solution:**
- The script automatically removes duplicates
- Duplicates are based on: job_title + company_name + location

---

## 📈 Best Practices

### 1. Start Small
- Test with 2-3 pages first
- Verify data quality
- Then scale up

### 2. Use Continuous Mode Wisely
- Don't set intervals too short
- Recommended: Every 6-12 hours
- Monitor the logs

### 3. Respect the Website
- Don't scrape too aggressively
- Keep delays reasonable (2+ seconds)
- Follow Jora's Terms of Service

### 4. Monitor Logs
- Check `logs/scraper.log` for issues
- Logs show what's happening
- Helpful for debugging

### 5. Backup Your Data
- Excel files are in `data/output/`
- Copy important files elsewhere
- Git doesn't track these (in .gitignore)

---

## 🎯 Common Use Cases

### Use Case 1: Job Market Research
```python
# Search multiple job types in one location
jobs = [
    ("Software Engineer", "Sydney", 10),
    ("Data Scientist", "Sydney", 10),
    ("DevOps Engineer", "Sydney", 10),
]
```

### Use Case 2: Geographic Comparison
```python
# Same job across different states
states = ["NSW", "VIC", "QLD", "WA"]
for state in states:
    scraper.search_jobs("Electrician", state, 5)
```

### Use Case 3: Continuous Monitoring
- Use mode 3 in main.py
- Set to run every 12 hours
- Track new job postings over time

---

## 📞 Need Help?

### Check These First:
1. **README.md** - Full documentation
2. **logs/scraper.log** - Error messages
3. **example_usage.py** - Working examples

### Common Issues:
- Website structure changed → Update selectors in `config.py`
- No Chrome → Install Google Chrome browser
- Slow internet → Increase timeouts in `.env`

---

## 🚀 Next Steps

1. ✅ **Run Quick Test**: `python main.py` → Option 4
2. ✅ **Try Examples**: `python example_usage.py`
3. ✅ **Custom Search**: Use Interactive Mode
4. ✅ **Setup Continuous**: For ongoing monitoring
5. ✅ **Analyze Data**: Open Excel files in `data/output/`

---

## 🎉 You're Ready!

Everything is set up and ready to go. Start with the Quick Test to make sure everything works, then move on to your specific scraping needs.

**Happy Scraping! 🌏**

---

*Last Updated: 2026-01-06*
