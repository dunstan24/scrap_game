# State-by-State Batch Scraping Feature

## Overview
The scraper now supports **state-by-state batch scraping** where you can scrape a specific keyword across all Australian states, with each state's results saved to a separate Excel file.

## How to Use

### Option 1: Interactive Mode (Mode 1) - Regular Scraping
1. Run the scraper: `python main.py`
2. Select mode `1` (Interactive Search)
3. Enter your job keyword (e.g., "Software Engineer")
4. When prompted for state selection, enter `0` for "ALL STATES"
5. Enter the maximum number of pages to scrape per state

### Option 2: AI-Powered Mode (Mode 5) - With AI Analysis
1. Run the scraper: `python main.py`
2. Select mode `5` (AI-Powered Search)
3. Enter your job keyword (e.g., "Data Analyst")
4. When prompted for state selection, enter `0` for "ALL STATES"
5. Enter the maximum number of pages to scrape per state

## What Happens

When you select "ALL STATES" (option 0):

1. **Sequential Processing**: The scraper will process each Australian state one by one:
   - New South Wales
   - Victoria
   - Queensland
   - South Australia
   - Western Australia
   - Tasmania
   - Northern Territory
   - Australian Capital Territory

2. **Individual Excel Files**: After completing each state, the results are immediately saved to a separate Excel file:
   - Format: `jora_{keyword}_{state}_{timestamp}.xlsx`
   - Example: `jora_software_engineer_new_south_wales_20260107_222530.xlsx`

3. **Progress Tracking**: You'll see real-time progress:
   - Current state being scraped
   - Number of jobs found per state
   - Overall progress (e.g., "3/8 states completed")
   - Total jobs scraped so far

4. **Error Handling**: If one state fails, the scraper continues to the next state

5. **Final Summary**: At the end, you'll receive:
   - Total jobs scraped across all states
   - Breakdown of jobs per state
   - List of any failed states
   - Location of all saved Excel files

## Example Output

```
🌏 Starting state-by-state search for: 'Software Engineer'
📄 Pages per state: 5
🤖 AI Analysis: Disabled

============================================================

🏙️  STATE 1/8: New South Wales
============================================================

[Scraping progress...]

✅ New South Wales: Scraped 87 jobs
   📁 Saved to: data/output/jora_software_engineer_new_south_wales_20260107_222530.xlsx

📊 Progress: 1/8 states completed
   Total jobs scraped so far: 87

============================================================

🏙️  STATE 2/8: Victoria
============================================================

[And so on for each state...]

============================================================
🎉 STATE-BY-STATE SEARCH COMPLETED!
============================================================

📊 Summary for 'Software Engineer':
   Total jobs scraped: 542
   States processed: 8/8

✅ Successful states:
   • New South Wales: 87 jobs
   • Victoria: 76 jobs
   • Queensland: 54 jobs
   • South Australia: 32 jobs
   • Western Australia: 45 jobs
   • Tasmania: 12 jobs
   • Northern Territory: 8 jobs
   • Australian Capital Territory: 28 jobs

📁 All files saved to: data/output/
============================================================
```

## Benefits

1. **Organized Data**: Each state's data is in its own file, making it easy to analyze regional job markets
2. **Incremental Saving**: If the scraper crashes or is interrupted, you don't lose all your data - completed states are already saved
3. **Flexible Analysis**: You can compare job markets across different states
4. **Resume Capability**: If interrupted, you can manually skip completed states and continue
5. **AI Support**: Works with both regular scraping and AI-powered sponsorship analysis

## File Naming Convention

- **Regular Mode**: `jora_{keyword}_{state}_{timestamp}.xlsx`
- **AI Mode**: `jora_{keyword}_{state}_{timestamp}.xlsx` (same format, but with AI analysis columns)

All files are saved to: `data/output/`

## Tips

- Start with fewer pages (e.g., 2-3) to test the feature
- For comprehensive searches, use 10+ pages per state
- AI mode will take longer but provides sponsorship analysis
- Monitor the console for progress updates
- Check the `data/output/` folder to see files being created in real-time
