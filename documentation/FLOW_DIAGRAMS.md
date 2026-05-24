# Scraping Flow Diagram

## Mode Selection Flow

```
┌─────────────────────────────────────────────────────────────┐
│                    JORA SCRAPER MAIN MENU                   │
└─────────────────────────────────────────────────────────────┘
                            │
                            ▼
        ┌───────────────────────────────────────┐
        │      Select Mode (1-5)                │
        └───────────────────────────────────────┘
                            │
        ┌───────────────────┴───────────────────┐
        │                                       │
        ▼                                       ▼
┌───────────────────┐                 ┌──────────────────┐
│  REGULAR MODES    │                 │  AI-POWERED MODE │
│    (1, 2, 3, 4)   │                 │       (5)        │
└───────────────────┘                 └──────────────────┘
        │                                       │
        ▼                                       ▼
┌───────────────────┐                 ┌──────────────────┐
│ use_ai = False    │                 │  use_ai = True   │
└───────────────────┘                 └──────────────────┘
        │                                       │
        ▼                                       ▼
┌───────────────────┐                 ┌──────────────────┐
│  Scrape Jobs      │                 │  Scrape Jobs     │
│  (Fast)           │                 │  (Slower)        │
└───────────────────┘                 └──────────────────┘
        │                                       │
        ▼                                       ▼
┌───────────────────┐                 ┌──────────────────┐
│  Extract Data:    │                 │  Extract Data:   │
│  • Title          │                 │  • Title         │
│  • Company        │                 │  • Company       │
│  • Location       │                 │  • Location      │
│  • Description    │                 │  • Description   │
│    (COMPLETE)     │                 │    (COMPLETE)    │
│  • Salary         │                 │  • Salary        │
│  • Job Type       │                 │  • Job Type      │
│  • etc.           │                 │  • etc.          │
│  (15 fields)      │                 │  (15 fields)     │
└───────────────────┘                 └──────────────────┘
        │                                       │
        │                                       ▼
        │                             ┌──────────────────┐
        │                             │  AI Analysis     │
        │                             │  • Sponsorship   │
        │                             │  • Confidence    │
        │                             │  • Reasoning     │
        │                             │  (+3 fields)     │
        │                             └──────────────────┘
        │                                       │
        ▼                                       ▼
┌───────────────────┐                 ┌──────────────────┐
│  Output Excel:    │                 │  Output Excel:   │
│  15 Fields        │                 │  18 Fields       │
│  ✅ Fast          │                 │  🤖 AI-Enhanced  │
└───────────────────┘                 └──────────────────┘
```

---

## Data Flow Comparison

### Regular Mode (1-4)

```
Job Listing Page
      │
      ▼
┌─────────────────┐
│  Job Card       │
│  • Title        │
│  • Company      │
│  • Location     │
│  • Abstract     │
└─────────────────┘
      │
      ▼
┌─────────────────┐
│  Job Detail     │
│  Page           │
│  • FULL DESC    │
│  • Apply URL    │
│  • Contact Info │
└─────────────────┘
      │
      ▼
┌─────────────────┐
│  Extract Data   │
│  (15 fields)    │
│  NO TRUNCATION  │
└─────────────────┘
      │
      ▼
┌─────────────────┐
│  Save to Excel  │
│  ✅ Complete    │
└─────────────────┘
```

### AI-Powered Mode (5)

```
Job Listing Page
      │
      ▼
┌─────────────────┐
│  Job Card       │
│  • Title        │
│  • Company      │
│  • Location     │
│  • Abstract     │
└─────────────────┘
      │
      ▼
┌─────────────────┐
│  Job Detail     │
│  Page           │
│  • FULL DESC    │
│  • Apply URL    │
│  • Contact Info │
└─────────────────┘
      │
      ▼
┌─────────────────┐
│  Extract Data   │
│  (15 fields)    │
│  NO TRUNCATION  │
└─────────────────┘
      │
      ▼
┌─────────────────┐
│  AI Analyzer    │
│  • Analyze up   │
│    to 50K chars │
│  • Detect       │
│    sponsorship  │
│  • Extract      │
│    contacts     │
└─────────────────┘
      │
      ▼
┌─────────────────┐
│  Merge Results  │
│  (15 + 3 fields)│
└─────────────────┘
      │
      ▼
┌─────────────────┐
│  Save to Excel  │
│  🤖 AI-Enhanced │
└─────────────────┘
```

---

## Description Handling

### Scraper (Both Modes)

```
Job Detail Page
      │
      ▼
┌──────────────────────────────────┐
│  HTML Content                    │
│  <div class="job-description">   │
│    [FULL JOB DESCRIPTION TEXT]   │
│    • Requirements                │
│    • Responsibilities            │
│    • Benefits                    │
│    • How to Apply                │
│    • Contact Information         │
│    • Sponsorship Info (if any)   │
│  </div>                          │
└──────────────────────────────────┘
      │
      ▼
┌──────────────────────────────────┐
│  BeautifulSoup Extraction        │
│  desc_elem.get_text()            │
│  → Gets ALL text                 │
│  → NO truncation                 │
│  → Complete content              │
└──────────────────────────────────┘
      │
      ▼
┌──────────────────────────────────┐
│  job_data['description']         │
│  = full_text                     │
│  → COMPLETE DESCRIPTION          │
│  → All characters preserved      │
└──────────────────────────────────┘
```

### AI Analyzer (Mode 5 Only)

```
job_data['description']
      │
      ▼
┌──────────────────────────────────┐
│  AI Prompt Builder               │
│  Description: {desc[:50000]}     │
│  → Takes first 50,000 chars      │
│  → Enough for virtually all jobs │
└──────────────────────────────────┘
      │
      ▼
┌──────────────────────────────────┐
│  Google Gemini AI                │
│  • Analyzes full context         │
│  • Detects sponsorship signals   │
│  • Extracts contact info         │
│  • Provides reasoning            │
└──────────────────────────────────┘
      │
      ▼
┌──────────────────────────────────┐
│  AI Results                      │
│  • sponsorship_signal            │
│  • sponsorship_confidence        │
│  • sponsorship_reasoning         │
└──────────────────────────────────┘
```

---

## Field Inclusion Logic

```python
# In scraper.py - _extract_job_data()

# Base fields (ALWAYS included)
job_data = {
    'job_title': 'N/A',
    'company_name': 'N/A',
    'contact_name': None,
    'phone_number': None,
    'company_email': None,
    'location': 'N/A',
    'state': 'N/A',
    'salary': 'N/A',
    'job_type': 'N/A',
    'description': 'N/A',  # ← FULL DESCRIPTION
    'posted_date': 'N/A',
    'application_url': 'N/A',
    'apply_form': 'N/A',
    'source': 'Jora Australia',
    'scraped_date': timestamp
}

# Conditional fields (ONLY if use_ai=True)
if self.use_ai:
    job_data.update({
        'sponsorship_signal': 'unknown',
        'sponsorship_confidence': 0.0,
        'sponsorship_reasoning': 'Not analyzed'
    })
```

---

## Mode Comparison Matrix

```
┌──────────────────┬─────────────┬──────────────┐
│    Feature       │ Regular     │ AI-Powered   │
│                  │ (Modes 1-4) │ (Mode 5)     │
├──────────────────┼─────────────┼──────────────┤
│ Speed            │ ⚡ Fast     │ 🐌 Slower    │
├──────────────────┼─────────────┼──────────────┤
│ Description      │ ✅ Complete │ ✅ Complete  │
│ Extraction       │ (Unlimited) │ (Unlimited)  │
├──────────────────┼─────────────┼──────────────┤
│ AI Analysis      │ ❌ No       │ ✅ Yes       │
│ Description      │             │ (50K chars)  │
├──────────────────┼─────────────┼──────────────┤
│ Sponsorship      │ ❌ No       │ ✅ Yes       │
│ Fields           │             │              │
├──────────────────┼─────────────┼──────────────┤
│ Output Fields    │ 15          │ 18           │
├──────────────────┼─────────────┼──────────────┤
│ API Calls        │ ❌ No       │ ✅ Yes       │
├──────────────────┼─────────────┼──────────────┤
│ Rate Limiting    │ ❌ No       │ ✅ Yes       │
├──────────────────┼─────────────┼──────────────┤
│ Use Case         │ Bulk        │ Targeted     │
│                  │ Scraping    │ Analysis     │
└──────────────────┴─────────────┴──────────────┘
```

---

## Summary

✅ **Clear Separation**: Two distinct processing paths
✅ **Complete Descriptions**: No truncation in either mode
✅ **Flexible Output**: 15 or 18 fields based on mode
✅ **Optimized Performance**: Fast regular, thorough AI
