# 🎮 PCGamingWiki Scraper

A robust, full-stack web scraper designed specifically for extracting PC game system requirements directly from [PCGamingWiki](https://www.pcgamingwiki.com/). Equipped with an advanced Cloudflare bypass mechanism, a FastAPI backend, and a React frontend, this tool allows you to easily harvest and export game specifications into CSV formats.

---

## ✨ Key Features

- **🛡️ Cloudflare Bypass**: Integrates Playwright with `camoufox` to automatically handle and bypass Cloudflare bot protection smoothly.
- **🖥️ Full-Stack Interface**: 
  - **React Frontend**: A clean UI to configure scraping parameters, view live progress, and manage jobs.
  - **FastAPI Backend**: A robust REST API to handle long-running scraping tasks asynchronously.
- **🗂️ Accurate System Specs**: Extracts both **Minimum** and **Recommended** system requirements including:
  - Operating System (OS)
  - Processor (CPU)
  - Memory (RAM)
  - Graphics (GPU)
  - Storage Space
- **💾 CSV Export**: Automatically saves extracted data into structured, Excel-compatible CSV files (`utf-8-sig`).
- **🔤 Alphabetical & Full Modes**: Scrape all games, or target specific starting letters/numbers (e.g., games starting with "A", "B", "0-9").
- **⏩ Smart Skipping**: Automatically skips games that have already been scraped in previous sessions to save time.

---

## 🛠️ Tech Stack

- **Backend**: Python 3.12+, FastAPI, SQLite (for job tracking), Playwright, BeautifulSoup4.
- **Frontend**: React (Vite), Tailwind CSS.
- **Browser Automation**: `camoufox` (Anti-detect browser for Playwright).

---

## 🚀 Quick Start Guide

### 1. Prerequisites
- **Python 3.12+**
- **Node.js 18+** (For running the frontend)
- Git

### 2. Installation

Clone the repository and enter the project folder:
```bash
git clone https://github.com/dunstan24/scrap_game.git
cd scrap_game
```

**Setup Backend (Python):**
```bash
# Create and activate virtual environment
python -m venv venv
# On Windows:
venv\Scripts\activate
# On Mac/Linux:
# source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Install Playwright browsers
playwright install
```

**Setup Frontend (Node.js):**
```bash
cd frontend
npm install
cd ..
```

---

## 💻 Running the Application

To run the application, you need to start both the backend server and the frontend development server.

### 1. Start the Backend API
Open a terminal, ensure your virtual environment is activated, and run:
```bash
uvicorn backend.main:app --reload --port 8000
```
*The API will be available at `http://localhost:8000`*

### 2. Start the Frontend UI
Open a second terminal, navigate to the `frontend` folder, and run:
```bash
cd frontend
npm run dev
```
*The UI will be available at `http://localhost:5173`*

### 3. Start Scraping
1. Open `http://localhost:5173` in your browser.
2. Select your scraping mode (Alphabet or All).
3. Configure your target alphabet and page limits.
4. Click **Start Scraping**. You can monitor the progress directly from the dashboard!

---

## 📊 Data Output

All scraped data is automatically saved in the `data/output/` directory as a `.csv` file. 
The CSV file contains the following columns:

- `Title`: Game Name
- `URL`: Link to the PCGamingWiki page
- `Scraped_At`: Timestamp of data extraction
- `OS_Minimum` / `OS_Recommended`
- `CPU_Minimum` / `CPU_Recommended`
- `RAM_Minimum` / `RAM_Recommended`
- `GPU_Minimum` / `GPU_Recommended`
- `Storage_Minimum` / `Storage_Recommended`

*Note: If the PCGamingWiki page leaves the "Recommended" table empty because it matches the minimum requirements, the scraper respects the site's layout and records it as `N/A`.*

---

## ⚙️ Configuration

If you want to tweak internal browser behaviors, you can adjust settings in `src/config.py` or modify the `camoufox` initialization in `src/playwright_helper.py`.

---

## ⚠️ Disclaimer

This tool is strictly intended for **educational purposes and personal research**. 
- Please respect the target website's Terms of Service.
- Do not overload their servers with aggressive scraping limits.
- The developers are not responsible for any misuse of this software.

---
*Built for game preservationists and data enthusiasts.*
