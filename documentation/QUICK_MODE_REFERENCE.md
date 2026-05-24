# Quick Reference: Regular vs AI-Powered Scraping

## Choose Your Mode

### 🏃 Fast Regular Scraping (Modes 1-4)
**When to use:**
- Need quick results
- Don't need sponsorship analysis
- Want complete job descriptions
- Avoid AI costs/limits

**Command:**
```bash
python main.py
# Select: 1, 2, 3, or 4
```

**Output:** 15 fields (no sponsorship data)

---

### 🤖 AI-Powered Scraping (Mode 5)
**When to use:**
- Need sponsorship analysis
- Want AI-extracted contacts
- Need confidence scores
- Identify government employers

**Command:**
```bash
python main.py
# Select: 5
```

**Output:** 18 fields (includes sponsorship data)

---

## Key Differences

| Feature | Regular (1-4) | AI-Powered (5) |
|---------|---------------|----------------|
| **Speed** | ⚡ Fast | 🐌 Slower |
| **Description** | ✅ Complete | ✅ Complete |
| **Sponsorship Analysis** | ❌ No | ✅ Yes |
| **AI API Calls** | ❌ No | ✅ Yes |
| **Output Fields** | 15 | 18 |
| **Cost** | Free | API usage |

---

## Description Handling

### ✅ Both modes get COMPLETE descriptions

**Regular Mode:**
- Scrapes full description from job page
- No character limit
- No truncation

**AI-Powered Mode:**
- Scrapes full description from job page
- Analyzes up to 50,000 characters
- Virtually no practical limit

---

## Quick Start Examples

### Example 1: Quick Job Search (No AI)
```bash
python main.py
# Select: 1 (Interactive Search)
# Keyword: Nurse
# Location: Western Australia
# Pages: 3
```
**Result:** Fast scraping, complete descriptions, no sponsorship analysis

---

### Example 2: Sponsorship Analysis (With AI)
```bash
python main.py
# Select: 5 (AI-Powered Search)
# Keyword: Registered Nurse
# Location: Western Australia
# Pages: 3
```
**Result:** Slower scraping, complete descriptions, WITH sponsorship analysis

---

### Example 3: Batch Scraping (No AI)
```bash
python main.py
# Select: 2 (Batch Search)
# Confirm: y
```
**Result:** Multiple searches, fast, no AI overhead

---

## Output Field Comparison

### Regular Mode Output (15 fields):
```
✅ job_title
✅ company_name
✅ contact_name
✅ phone_number
✅ company_email
✅ location
✅ state
✅ salary
✅ job_type
✅ description (COMPLETE)
✅ posted_date
✅ application_url
✅ apply_form
✅ source
✅ scraped_date
```

### AI-Powered Mode Output (18 fields):
```
✅ All 15 regular fields PLUS:
✅ sponsorship_signal
✅ sponsorship_confidence
✅ sponsorship_reasoning
```

---

## Tips

### 💡 Use Regular Mode When:
- Scraping large volumes of jobs
- Building a job database
- Need fast results
- Don't care about sponsorship

### 💡 Use AI-Powered Mode When:
- Looking for visa sponsorship opportunities
- Need to identify government employers
- Want AI-powered contact extraction
- Need confidence scores for decision making

### 💡 Hybrid Approach:
1. Use Regular Mode to scrape 1000s of jobs quickly
2. Filter interesting jobs manually
3. Use AI-Powered Mode on filtered subset for detailed analysis

---

## Remember

✅ **Both modes get COMPLETE descriptions** - no truncation!

✅ **Choose based on your needs:**
- Speed → Regular Mode
- Analysis → AI-Powered Mode

✅ **You can always switch modes** - they're independent!

---

**Let's GO! 🚀**
