# Quick Reference: AI-Powered Scraping

## 🚀 Run AI-Powered Scraping

```bash
python main.py
# Select: 5
```

## 📝 Data Fields (New)

| Field | Type | Source | Description |
|-------|------|--------|-------------|
| `contact_name` | str | AI | Contact person name |
| `phone_number` | str | AI + Regex | Phone number |
| `company_email` | str | AI + Regex | Email address |
| `sponsorship_signal` | str | AI | 'yes', 'maybe', 'unknown' |
| `sponsorship_confidence` | float | AI | 0.0 - 1.0 |
| `sponsorship_reasoning` | str | AI | Explanation |

## 🔑 API Keys (Already Configured)

```python
# In src/config.py
GEMINI_API_KEYS = [
    'AIzaSyAhdu8XFz74gRfzlItUB-KndYPsYi0hZio',  # Key 1
    'AIzaSyA2lVvQ3wgPHCabFJiiPezNzIVC0TLhAZ4',  # Key 2
    'AIzaSyBhJUGEKcIA9HeP29wdCnI6xS82gn8hCMg',  # Key 3
]
```

## ⚡ Quick Commands

```bash
# Install dependencies
pip install -r requirements.txt

# Test AI analyzer
python src/ai_analyzer.py

# Run scraper (interactive)
python main.py

# Run with AI (programmatic)
python -c "from src.scraper import JoraScraper; s=JoraScraper(use_ai=True); jobs=s.search_jobs('Nurse','Sydney',2); s.close()"
```

## 🎯 Sponsorship Signals

| Signal | Meaning | Examples |
|--------|---------|----------|
| **yes** | Explicit mention | "Visa sponsorship available", "482 visa", "Will sponsor" |
| **maybe** | Potential indicators | Government job, Large company, Healthcare role |
| **unknown** | No information | No sponsorship mentions |

## ⚙️ Configuration Options

```python
# src/config.py

USE_AI_ANALYSIS = True          # Enable/disable AI
GEMINI_MODEL = 'gemini-1.5-flash'  # Model to use
AI_RATE_LIMIT_RPM = 15          # Requests per minute
AI_BATCH_SIZE = 10              # Jobs per batch
```

## 📊 Performance

| Jobs | Time | Cost |
|------|------|------|
| 100 | ~7 min | FREE |
| 500 | ~35 min | FREE |
| 1000 | ~70 min | FREE |

**Free Tier:** 1,500 requests/day

## 🔧 Troubleshooting

| Issue | Solution |
|-------|----------|
| Quota exceeded | Wait 1 minute or use next key |
| No AI results | Check logs, verify API keys |
| Slow processing | Normal (rate limiting) |
| Import errors | Run `pip install -r requirements.txt` |

## 📁 Output Location

```
data/output/jora_ai_[keyword]_[location]_[timestamp].xlsx
```

## 🎨 Example Output

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

## 💡 Pro Tips

1. **Start small** - Test with 2-3 pages first
2. **Check logs** - `logs/scraper.log` for details
3. **Monitor quota** - https://ai.dev/usage
4. **Batch processing** - More efficient than one-by-one
5. **Key rotation** - Automatic, no action needed

## 📚 Documentation

- Full docs: `AI_FEATURE_DOCUMENTATION.md`
- Summary: `IMPLEMENTATION_SUMMARY.md`
- This guide: `QUICK_REFERENCE.md`

---

**Ready to go! Run `python main.py` and select option 5** 🚀
