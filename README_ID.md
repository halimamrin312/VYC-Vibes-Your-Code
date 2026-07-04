# Platform Swarm Uji Tuntas M&A (M&A Due Diligence Swarm Platform)

Sebuah platform uji tuntas (*due diligence*) otomatis untuk aktivitas Merger & Akuisisi (M&A). Sistem ini mengoordinasikan agen-agen cerdas untuk menganalisis kesehatan keuangan, kontrak hukum, sentimen pasar, dan efisiensi operasional target perusahaan menggunakan **Google Agent Development Kit (ADK)** dan **Model Context Protocol (MCP)**.

---

## 🚀 Fitur Utama

* **Multi-Agent Orchestration (2-Wave Execution):** Mengoordinasikan eksekusi agen secara paralel (Wave 1: Keuangan & Sentimen; Wave 2: Hukum & Operasional) dengan transfer konteks otomatis antar-gelombang.
* **Human-in-the-Loop (HITL) Checkpoints:** Menghentikan sementara swarm secara otomatis dan meminta arahan strategis dari pengguna ketika mendeteksi risiko kritis (Severity 1) atau data keuangan swasta yang kurang.
* **Sandbox Eksekusi Kode Aman:** Mengeksekusi kode analisis Python yang ditulis oleh agen di dalam subprocess terisolasi dengan penyaringan impor modul berbasis AST dan proteksi *path-traversal*.
* **Semantic Legal RAG:** Mengindeks dokumen kontrak hukum PDF ke FAISS Vector Store lokal dan menjalankan 10 kueri pencarian risiko hukum spesifik (LQ-01 hingga LQ-10).
* **Model Context Protocol (MCP):** Menghubungkan agen secara terstruktur ke API regulator publik (seperti SEC EDGAR Search) menggunakan komunikasi stdio JSON-RPC.
* **Dashboard Kontrol Interaktif:** Antarmuka visual modern berbasis React/Vite dengan desain *glassmorphism* untuk memantau status agen, log streaming, grafik CSI/ESI, dan laporan memo investasi.

---

## 📂 Arsitektur Proyek

```mermaid
graph TD
    User([User / Partner Investasi]) <--> Frontend[React/Vite Dashboard]
    Frontend <--> |HTTP / SSE Streaming| Backend[FastAPI Gateway]
    Backend <--> DB[(SQLite Session DB)]
    Backend <--> Orchestrator[Orchestrator / Lead Agent]
    
    Orchestrator --> |Wave 1 - Paralel| FinAuditor[Financial Auditor Agent]
    Orchestrator --> |Wave 1 - Paralel| BrandSentiment[Brand Sentiment Agent]
    
    FinAuditor -.-> |Konteks Gelombang 1| ContextBuffer[Wave 1 Context: Pendapatan, Utang, Runway]
    ContextBuffer -.-> |Diteruskan ke Wave 2| LegalCompliance
    ContextBuffer -.-> |Diteruskan ke Wave 2| OpsEvaluator
    
    Orchestrator --> |Wave 2 - Paralel| LegalCompliance[Legal & Compliance Agent]
    Orchestrator --> |Wave 2 - Paralel| OpsEvaluator[Operations Evaluator Agent]
```

---

## 🛠️ Komponen Teknologi

* **Backend:** FastAPI (Python 3.14+), Uvicorn, Peewee ORM (SQLite).
* **Frontend:** React 18, Vite, Lucide React, CSS Glassmorphism.
* **Agent Engine:** Google Agent Development Kit (ADK), Pola Registry Kustom.
* **Keamanan:** Python AST (Abstract Syntax Trees), Subprocess Sandboxing.
* **Vector Store:** FAISS (Facebook AI Similarity Search) & SentenceTransformers.

---

## ⚡ Panduan Memulai Cepat

### Prasyarat
* Python 3.14+
* Node.js & npm

### 1. Konfigurasi Lingkungan
Buat file `.env` di direktori utama proyek:
```properties
GEMINI_API_KEY="api_key_gemini_anda"
COURTLISTENER_API_TOKEN="token_courtlistener_opsional"
GOVINFO_API_KEY="key_govinfo_opsional"
```

### 2. Jalankan Server API Backend
```bash
# Aktifkan virtual environment
source venv/bin/activate

# Jalankan server backend uvicorn
uvicorn backend.app.main:app --host 0.0.0.0 --port 8000 --reload
```

### 3. Jalankan Server Frontend Vite
Buka terminal baru di direktori utama proyek:
```bash
cd frontend
npm install
npm run dev
```
Buka alamat **[http://localhost:3000/](http://localhost:3000/)** di browser Anda.

---

## 🧪 Menguji Sistem Swarm

Memverifikasi integritas sistem, aturan keamanan, dan fungsi multi-agent:

* **Jalankan Pengujian Unit Otomatis:**
  ```bash
  venv/bin/pytest -v
  ```
* **Skenario Pengujian pada Dashboard:**
  * **Alur Publik (Otomatis):** Set nama perusahaan target ke **`TSLA`** atau **`AAPL`** dan klik *Dispatch*. Sistem akan menarik laporan keuangan secara otomatis dari SEC/yfinance.
  * **Alur Swasta (HITL):** Set nama perusahaan target ke **`Acme Corp`** dan klik *Dispatch*. Swarm akan dijeda otomatis dan meminta Anda mengunggah file keuangan sampel `.csv` di tab Data Room.
  * **Peringatan Hukum (HITL):** Set nama perusahaan target ke **`Cyberdyne Systems`** dan klik *Dispatch*. Swarm akan dijeda di Wave 2 untuk memunculkan red flag kasus hukum aktif dari CourtListener.
