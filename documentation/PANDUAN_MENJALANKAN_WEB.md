# 📖 Panduan Menjalankan Job Scraper Dashboard

> Dokumentasi ini menjelaskan cara menyiapkan dan menjalankan aplikasi web **Job Scraper Dashboard** dari awal hingga siap digunakan.

---

## 📋 Daftar Isi

1. [Gambaran Umum Sistem](#1-gambaran-umum-sistem)
2. [Persyaratan](#2-persyaratan)
3. [Instalasi](#3-instalasi)
4. [Menjalankan Aplikasi](#4-menjalankan-aplikasi)
5. [Menggunakan Dashboard](#5-menggunakan-dashboard)
6. [Struktur Folder](#6-struktur-folder)
7. [API Endpoints](#7-api-endpoints)
8. [Pemecahan Masalah](#8-pemecahan-masalah)

---

## 1. Gambaran Umum Sistem

Aplikasi ini terdiri dari **dua bagian** yang harus dijalankan secara bersamaan:

```
┌─────────────────────────────────────────────────────────┐
│                                                         │
│   FRONTEND (React + Vite)          BACKEND (FastAPI)    │
│   Port: 5173                       Port: 8000           │
│                                                         │
│   Browser ──────────────────────────► API               │
│   http://localhost:5173             http://localhost:8000│
│                                                         │
└─────────────────────────────────────────────────────────┘
```

| Komponen | Teknologi | Port |
|---|---|---|
| Frontend (UI) | React 18 + Vite | `localhost:5173` |
| Backend (API) | Python FastAPI + Uvicorn | `localhost:8000` |
| Database | SQLite (`backend/scraper_jobs.db`) | - |
| Output Data | CSV (`data/output/`) | - |

---

## 2. Persyaratan

### Software yang Harus Terinstal

| Software | Versi Minimum | Link Download |
|---|---|---|
| **Python** | 3.10+ | https://www.python.org/downloads/ |
| **Node.js** | 18+ | https://nodejs.org/ |
| **Google Chrome** | Versi terbaru | https://www.google.com/chrome/ |
| **Git** | (opsional) | https://git-scm.com/ |

### Cek Instalasi

Buka terminal dan jalankan:

```bash
python --version     # Harus 3.10 atau lebih
node --version       # Harus v18 atau lebih
npm --version        # Harus 8 atau lebih
```

---

## 3. Instalasi

### Langkah 3.1 — Clone / Buka Project

Jika menggunakan Git:
```bash
git clone <url-repository>
cd Scrapping-Mechine-Job-Australia
```

Atau langsung buka folder project jika sudah ada.

---

### Langkah 3.2 — Setup Virtual Environment Python

Buat dan aktifkan virtual environment:

```bash
# Buat venv
python -m venv venv

# Aktifkan (Windows)
venv\Scripts\activate

# Aktifkan (Linux/Mac)
source venv/bin/activate
```

> ✅ Tanda berhasil: nama `(venv)` muncul di awal baris terminal.

---

### Langkah 3.3 — Install Dependensi Python

```bash
pip install -r requirements.txt
```

Dependensi yang akan diinstal:
- `fastapi` — framework backend API
- `uvicorn` — server ASGI untuk menjalankan FastAPI
- `selenium` — otomasi browser untuk scraping
- `webdriver-manager` — manajemen ChromeDriver otomatis
- `beautifulsoup4` — parsing HTML
- `pandas` — manipulasi data & output CSV

---

### Langkah 3.4 — Install Dependensi Frontend

```bash
cd frontend
npm install
cd ..
```

---

### Langkah 3.5 — Buat File `.env` (jika belum ada)

Di root folder project, buat file `.env`:

```env
# Kosongkan jika tidak menggunakan Gemini AI
GEMINI_API_KEY=your_api_key_here
```

> ℹ️ File `.env` sudah ada di project. Cek isinya sebelum menjalankan.

---

## 4. Menjalankan Aplikasi

> ⚠️ **Backend dan Frontend harus dijalankan di dua terminal terpisah secara bersamaan.**

---

### Terminal 1 — Jalankan Backend (API)

```bash
# Pastikan berada di root folder project
# Pastikan virtual environment aktif (ada tulisan (venv))

uvicorn backend.main:app --reload --port 8000
```

**Output yang diharapkan:**
```
INFO:     Uvicorn running on http://127.0.0.1:8000 (Press CTRL+C to quit)
INFO:     Started reloader process [xxxx]
INFO:     Application startup complete.
```

✅ Backend siap jika ada pesan `Application startup complete.`

---

### Terminal 2 — Jalankan Frontend (UI)

```bash
# Masuk ke folder frontend
cd frontend

# Jalankan dev server
npm run dev
```

**Output yang diharapkan:**
```
  VITE v5.x.x  ready in xxx ms

  ➜  Local:   http://localhost:5173/
  ➜  Network: use --host to expose
```

✅ Frontend siap jika muncul URL `http://localhost:5173/`

---

### Langkah 4.3 — Buka di Browser

Buka browser dan akses:

```
http://localhost:5173
```

Dashboard akan muncul dengan tampilan berikut:

```
┌──────────────────────────────────────────────────────┐
│ [Icon] Job Scraper Dashboard     Dashboard | History  │
├──────────────────────────────────────────────────────┤
│ Scrape Configuration                                  │
│  Keyword: [________________]                          │
│  Platform: [ Jora ] [ Seek ] [ Indeed ]               │
│  States: [ NSW ] [ VIC ] [ QLD ] ...                  │
│  Pages: [2]                                           │
│  [▶ Start Scraping]                                   │
├──────────────────────────────────────────────────────┤
│ Logs              │ Results                           │
│ ...               │ ...                               │
└──────────────────────────────────────────────────────┘
```

---

## 5. Menggunakan Dashboard

### 5.1 Halaman Dashboard — Mulai Scraping

1. **Isi Keyword** — Kata kunci pekerjaan yang dicari (contoh: `web developer`, `data analyst`)
2. **Pilih Platform** — Pilih salah satu: `Jora`, `Seek`, atau `Indeed`
3. **Pilih State** — Pilih satu atau beberapa state Australia (NSW, VIC, QLD, dst.)
4. **Atur Jumlah Halaman** — Berapa banyak halaman hasil scraping per state (default: 2)
5. **Klik "Start Scraping"** — Proses dimulai

### 5.2 Memantau Progress

- Tab **Logs** — menampilkan log real-time proses scraping
- Tab **Results** — menampilkan data pekerjaan yang berhasil diambil
- **Status badge** di tab menampilkan jumlah job yang ditemukan

### 5.3 Download Hasil

Setelah scraping selesai, klik tombol **"Download CSV"** untuk mengunduh data dalam format CSV.

File CSV disimpan di folder: `data/output/`

### 5.4 Halaman History

Klik tab **"History"** di pojok kanan atas untuk melihat riwayat semua scraping yang pernah dilakukan, termasuk:
- Waktu mulai dan selesai
- Platform dan keyword
- Jumlah job ditemukan
- Link download CSV

---

## 6. Struktur Folder

```
Scrapping-Mechine-Job-Australia/
│
├── backend/                    # ← API FastAPI (Python)
│   ├── main.py                 #   Entry point API server
│   ├── database.py             #   Koneksi & query SQLite
│   ├── models.py               #   Pydantic models (request/response)
│   ├── routes/
│   │   └── scrape.py           #   Endpoint: /api/scrape, /api/status, dll.
│   └── services/
│       ├── jora_service.py     #   Logika scraping Jora
│       ├── seek_service.py     #   Logika scraping Seek
│       └── indeed_service.py   #   Logika scraping Indeed
│
├── src/                        # ← Core scraper (Python)
│   ├── scraper.py              #   Kelas JoraScraper
│   ├── utils.py                #   Fungsi utilitas & parsing
│   └── seek_scraper/
│       ├── scraper.py          #   Kelas SeekScraper
│       ├── utils.py            #   Utilitas Seek
│       └── config.py           #   Konfigurasi Seek
│
├── frontend/                   # ← UI React (JavaScript)
│   ├── index.html              #   Entry HTML
│   ├── src/
│   │   ├── App.jsx             #   Komponen utama
│   │   ├── index.css           #   Styling global (dark/light mode)
│   │   ├── api.js              #   Fungsi pemanggil API
│   │   ├── components/         #   Komponen UI reusable
│   │   └── pages/
│   │       └── HistoryPage.jsx #   Halaman riwayat
│   └── package.json
│
├── data/
│   └── output/                 # ← File CSV hasil scraping tersimpan di sini
│
├── documentation/              # ← Folder dokumentasi
├── drivers/                    # ← ChromeDriver (diisi otomatis)
├── requirements.txt            # ← Dependensi Python
└── .env                        # ← Konfigurasi environment
```

---

## 7. API Endpoints

Backend menyediakan REST API yang bisa diakses langsung. Dokumentasi interaktif tersedia di:

```
http://localhost:8000/docs        ← Swagger UI
http://localhost:8000/redoc       ← ReDoc
```

### Daftar Endpoint Utama

| Method | Endpoint | Deskripsi |
|---|---|---|
| `GET` | `/` | Health check API |
| `POST` | `/api/scrape` | Mulai job scraping baru |
| `GET` | `/api/status/{job_id}` | Cek status & log scraping |
| `GET` | `/api/result/{job_id}` | Ambil hasil scraping (JSON) |
| `GET` | `/api/download/{job_id}` | Download hasil scraping (CSV) |
| `GET` | `/api/jobs` | Daftar semua riwayat job |
| `DELETE` | `/api/job/{job_id}` | Hapus job dari memory |

### Contoh Request Scraping

```bash
curl -X POST http://localhost:8000/api/scrape \
  -H "Content-Type: application/json" \
  -d '{
    "platform": "seek",
    "keyword": "web developer",
    "states": ["New South Wales"],
    "pages": 2
  }'
```

---

## 8. Pemecahan Masalah

### ❌ Error: `ModuleNotFoundError`

**Penyebab:** Virtual environment tidak aktif atau dependensi belum diinstal.

**Solusi:**
```bash
# Aktifkan venv
venv\Scripts\activate   # Windows

# Install ulang dependensi
pip install -r requirements.txt
```

---

### ❌ Error: `CORS error` di browser

**Penyebab:** Backend belum berjalan atau berjalan di port yang berbeda.

**Solusi:**
- Pastikan terminal backend sudah menjalankan `uvicorn backend.main:app --reload --port 8000`
- Cek apakah `http://localhost:8000/health` bisa diakses di browser

---

### ❌ Error: `ChromeDriver` / WebDriver gagal

**Penyebab:** ChromeDriver tidak cocok dengan versi Chrome yang terinstal.

**Solusi:**
```bash
# Jalankan script fix chrome driver bawaan project
python fix_chrome_driver.py
```

Atau update Chrome ke versi terbaru, lalu jalankan ulang scraper (ChromeDriver akan diunduh otomatis oleh `webdriver-manager`).

---

### ❌ Frontend tidak bisa connect ke Backend

**Penyebab:** Backend belum jalan atau port salah.

**Cek:**
1. Buka `http://localhost:8000` di browser — harus muncul `{"status": "ok"}`
2. Pastikan port 5173 dan 8000 tidak diblokir firewall

---

### ❌ Scraping menghasilkan 0 job

**Penyebab:** Seek/Jora mendeteksi bot dan memblokir request.

**Solusi:**
- Kurangi jumlah halaman (coba `pages: 1` dulu)
- Tunggu beberapa menit sebelum mencoba lagi
- Scraping berjalan dalam mode headless — pastikan Chrome terinstal dengan benar

---

## 📝 Catatan Penting

> **Jangan jalankan scraping terlalu sering** dalam waktu singkat. Website Seek dan Jora dapat mendeteksi aktivitas bot dan memblokir IP sementara.

> **File CSV** hasil scraping tersimpan di `data/output/` dan tidak terhapus otomatis. Lakukan pembersihan manual jika diperlukan.

> **Database** (`backend/scraper_jobs.db`) menyimpan riwayat semua job yang pernah dijalankan. File ini aman untuk dihapus jika ingin reset riwayat.

---

*Dokumentasi ini dibuat untuk versi aplikasi yang berjalan dengan backend FastAPI (port 8000) dan frontend React/Vite (port 5173).*
