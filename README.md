# NeuroPredict — Alzheimer's Risk Assessment Platform

A modern, responsive, non-technical web application for evaluating Alzheimer's cognitive risk factors using an automated 5-factor clinical assessment engine.

---

## Architecture Overview

```text
┌──────────────────────────────────────────┐
│             Public User                  │
└────────────────────┬─────────────────────┘
                     │ HTTPS
                     ▼
┌──────────────────────────────────────────┐
│      GitHub Pages Static Frontend        │
│   (HTML5, CSS3, JavaScript, Chart.js)    │
└────────────────────┬─────────────────────┘
                     │ REST API / JSON (CORS)
                     ▼
┌──────────────────────────────────────────┐
│        FastAPI Python Backend            │
│  (main.py, report_generator.py, ReportLab)│
└────────────────────┬─────────────────────┘
                     │ Pipeline Inference
                     ▼
┌──────────────────────────────────────────┐
│       Assessment Model Engine            │
│      (final_catboost_top5.pkl)           │
└──────────────────────────────────────────┘
```

---

## Key Features

- **4-Step Progressive Workflow**:
  1. **Your Details**: Clinical input form with range validation and real-time bounds checking.
  2. **Assessment**: Smooth progress indicator during evaluation.
  3. **Results**: Visual probability donut chart, key factor relevance breakdown, score meters, and status cards.
  4. **Report & Guidance**: Comprehensive summary, actionable lifestyle suggestions, and on-demand 4-page A4 PDF report generation.
- **Zero Technical Jargon**: Wording is tailored for patients and families—no raw algorithm names or internal jargon visible in the user interface.
- **Live Service Status Indicator**: Dynamic connection monitoring (`● Assessment Service Online` / `○ Assessment Service Offline`) with interactive backend URL configuration.
- **Automated 4-Page PDF Reports**: Professional clinical-style PDF generation using ReportLab, vector charts, and numbered pages ("Page X of 4").
- **100% Free Hosting Architecture**: Frontend hosted on GitHub Pages; Backend ready for free-tier deployment on Render or Hugging Face Spaces.

---

## The 5 Clinical Assessment Indicators

The assessment engine evaluates exactly five validated indicators:

| Factor | Range / Options | Plain-Language Description |
| :--- | :---: | :--- |
| **Functional Assessment Score** | `0.0 – 10.0` | Measures how independently a person manages everyday activities. |
| **MMSE Score** | `0 – 30` | Mini-Mental State Examination evaluating memory, attention, and orientation. |
| **ADL Score** | `0.0 – 10.0` | Activities of Daily Living evaluating autonomous self-care capacity. |
| **Memory Complaints** | `No / Yes` | Subjective or reported persistent memory difficulties and forgetfulness. |
| **Behavioral Problems** | `No / Yes` | Observed changes in mood, agitation, apathy, or personality. |

---

## Project Structure

```text
neuro-predict/
│
├── frontend/                               # GitHub Pages Static Site
│   ├── index.html                          # 4-step progressive user interface
│   ├── style.css                           # Healthcare design system & responsive CSS
│   ├── script.js                           # State manager, validation, Chart.js, API client
│   ├── chart.umd.min.js                    # Local Chart.js bundle (with CDN fallback)
│   └── assets/                             # Icons and static imagery
│
├── backend/                                # FastAPI Python Backend
│   ├── main.py                             # API endpoints (/health, /predict, /download-report)
│   ├── report_generator.py                 # 4-page A4 PDF generation via ReportLab
│   ├── test_suite.py                       # Automated test suite (6 validation & inference tests)
│   ├── final_catboost_top5.pkl             # Trained 5-factor assessment engine
│   ├── requirements.txt                    # Production Python dependencies
│   ├── Procfile                            # Process file for PaaS deployments (Render / Heroku)
│   └── Dockerfile                          # Containerized deployment configuration
│
├── .github/
│   └── workflows/
│       └── deploy-pages.yml                # Automated GitHub Actions Pages deployment
│
├── .gitignore                              # Excludes venv, cache, datasets, and reports
├── README.md                               # Project documentation
└── LICENSE                                 # MIT License
```

---

## Local Development Setup

### 1. Backend Setup

```bash
cd backend

# Create and activate virtual environment
python -m venv venv
# Windows:
venv\Scripts\activate
# macOS/Linux:
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Run automated tests
python test_suite.py

# Start local backend server
uvicorn main:app --reload --host 127.0.0.1 --port 8000
```

Verify backend health at: [http://127.0.0.1:8000/health](http://127.0.0.1:8000/health)

### 2. Frontend Setup

In a new terminal window:

```bash
cd frontend

# Run any lightweight static file server:
python -m http.server 5500
```

Open [http://localhost:5500](http://localhost:5500) in your web browser. The frontend will automatically detect localhost and connect to `http://127.0.0.1:8000`.

---

## Free Backend Deployment Options

Deploy the `backend/` directory to any free cloud service:

### Option A: Render (Recommended — Quickest)

1. Create a free account at [render.com](https://render.com).
2. Click **New +** → **Web Service**.
3. Connect your GitHub repository (`neuro-predict`).
4. Configure the service settings:
   - **Name**: `neuro-predict-api` (or any unique name)
   - **Region**: Choose the closest region (e.g., Oregon, Frankfurt)
   - **Branch**: `main`
   - **Root Directory**: `backend`
   - **Runtime**: `Python 3`
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `uvicorn main:app --host 0.0.0.0 --port $PORT`
   - **Instance Type**: `Free`
5. Click **Create Web Service**.
6. Once deployed, copy your live backend URL:
   `https://neuro-predict-api.onrender.com`

---

### Option B: Hugging Face Spaces (100% Free Docker Tier)

1. Create a free account at [huggingface.co](https://huggingface.co).
2. Click **New Space** → Name: `neuro-predict-api`.
3. Select **Docker** as the SDK (Blank) → **Free CPU tier**.
4. Push the files inside `backend/` to your Space repository. The included `Dockerfile` will automatically build and run the FastAPI server on port 7860.

---

## Connecting Frontend to Your Live Backend

Once your backend is deployed:

1. Open `frontend/script.js`.
2. Update line 12:
   ```javascript
   const BACKEND_URL = "https://your-backend-api.onrender.com";
   ```
3. Commit and push to `main`.
4. *Alternative (No code edit needed)*: On your live GitHub Pages site, click the **Service Status pill** in the top-right header and paste your backend URL. It will instantly connect and save to your browser's storage!

---

## GitHub Pages Frontend Deployment

This repository includes an automated GitHub Actions deployment workflow (`.github/workflows/deploy-pages.yml`).

### Enable GitHub Pages in your Repository:

1. Navigate to your repository on GitHub: `https://github.com/<USERNAME>/neuro-predict`.
2. Click **Settings** (top navigation tab).
3. In the left sidebar, click **Pages**.
4. Under **Build and deployment** → **Source**, select **GitHub Actions**.
5. Push to the `main` branch. GitHub Actions will automatically deploy your frontend.
6. Your live site will be accessible at:
   `https://<USERNAME>.github.io/neuro-predict/`

---

## Verification & Testing

Run the automated backend test suite anytime:

```bash
cd backend
python test_suite.py
```

Tests verify:
- Model unpickling and pipeline compatibility
- Feature importance weight extraction
- Low-risk scenario inference (`prob < 15%`)
- High-risk scenario inference (`prob > 85%`)
- Input validation boundaries and error reporting
- ReportLab 4-page PDF generation and table formatting

---

## Medical Disclaimer

> **IMPORTANT NOTICE**: This application provides an automated risk assessment based solely on the five entered clinical indicators. It is designed strictly for **educational and research purposes** and does **not constitute a medical diagnosis or clinical evaluation**. Users experiencing memory or cognitive changes should consult a qualified healthcare professional or neurologist.

---

## License

This project is licensed under the [MIT License](LICENSE).

