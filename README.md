<p align="center">
  <img src="docs/banner.png" alt="ScholarScout" width="600">
</p>

<p align="center">
  <strong>AI-powered research idea discovery for students and researchers.</strong><br>
  <em>Scan 250M+ papers. Analyze trends. Generate actionable ideas. Verify novelty.</em>
</p>

<p align="center">
  <a href="https://ko-fi.com/scholarscout">♥ Ko-fi</a> · 
  <a href="https://saweria.co/scholarscout">♥ Saweria</a> · 
  <a href="#quick-start">Quick Start</a> · 
  <a href="#features">Features</a> · 
  <a href="#bahasa-indonesia">Bahasa Indonesia</a>
</p>

<p align="center">
  <img src="docs/screenshot-welcome.png" alt="Welcome Screen" width="700"><br>
  <em>Welcome screen with guided onboarding</em>
</p>

<p align="center">
  <img src="docs/screenshot-ideas.png" alt="Generated Ideas" width="700"><br>
  <em>Generated research ideas with methodology and next steps</em>
</p>

---

## Features

### Data & Sources
- **Multi-source paper fetching** — arXiv, OpenAlex, Semantic Scholar (250M+ papers combined)
- **Parallel fetching** — 3 sources fetched simultaneously per category for speed
- **80+ research categories** — CS, Medicine, Biology, Physics, Engineering, Chemistry, Social Sciences, Earth Sciences, Agriculture
- **Smart deduplication** — Papers deduplicated across sources by title

### Intelligence
- **Trend analysis** — Identifies emerging methods, research gaps, and methodology patterns via LLM
- **Idea generation** — Produces specific, feasible ideas with methodology hints, next steps, and key papers
- **Research approach filter** — Computational/AI, Experimental/Lab, Clinical/Field, Theoretical/Review
- **Novelty checking** — Compares ideas against Semantic Scholar and arXiv to verify originality
- **Deep dive analysis** — Full research outline: methodology, datasets, timeline, tools, references

### Personalization
- **Research context** — Describe your background for tailored results
- **Onboarding flow** — First-time users guided to set approach + context before generating
- **Language support** — English or Bahasa Indonesia (including titles)
- **Difficulty levels** — Undergraduate, Master's, PhD
- **Skills system** — 9 customizable research profiles (Data Scientist, Lab Scientist, Clinical, Thesis, Grant Proposal, etc.)

### Dashboard
- **Real-time pipeline monitoring** — Watch papers being fetched and analyzed live
- **Search & filter** — Find ideas by keyword or filter by difficulty level
- **Show more popup** — Full idea detail in a clean modal
- **Per-idea PDF export** — Export any single idea as a formatted PDF
- **Bookmark system** — Save favorites to shortlist (localStorage)
- **Recent ideas** — Access results from previous pipeline runs

### LLM & Configuration
- **6 LLM providers** — Gemini (free), Groq (free), OpenRouter, OpenAI, Ollama (local), Custom endpoint
- **Settings UI** — Configure provider, API key, and model from the dashboard
- **Test connection** — Verify LLM setup with one click
- **Adaptive token budgets** — Different max_tokens per task type (saves ~48% cost)
- **`stream: false`** — Compatible with streaming endpoints

### Developer Experience
- **100 automated tests** — Python (pytest) + JavaScript (Jest)
- **Modular architecture** — Add new paper sources in 1 file
- **Skills system** — Community-extensible research profiles
- **MIT licensed** — Use, modify, distribute freely

---

## Quick Start

```bash
git clone https://github.com/neej4/ScholarScout.git
cd ScholarScout
pip install -r requirements.txt
python preview_server.py
```

Open **http://localhost:5050** in your browser.

### First Run

1. Click **Run Pipeline** — onboarding asks for your research approach and context
2. Select categories from the left panel (only check what you need)
3. Wait for papers to be fetched and analyzed
4. Browse ideas → click **Show more** for details → **Deep Dive** for full analysis → **Export PDF**

### LLM Setup

Go to **Settings** tab and choose a provider:

| Provider | Free? | Speed | Get Key |
|----------|-------|-------|---------|
| Gemini | Yes (15 req/min) | Fast | [aistudio.google.com](https://aistudio.google.com/app/apikey) |
| Groq | Yes (free tier) | Very fast | [console.groq.com](https://console.groq.com/keys) |
| Ollama | Yes (local) | Depends on GPU | [ollama.com](https://ollama.com/download) |
| OpenRouter | Pay-per-use | Varies | [openrouter.ai](https://openrouter.ai/keys) |
| OpenAI | Pay-per-use | Fast | [platform.openai.com](https://platform.openai.com/api-keys) |

Or edit `config.yaml`:

```yaml
llm:
  provider: gemini
  api_key: "your-key-here"
  model: gemini-2.0-flash
```

---

## Project Structure

```
ScholarScout/
├── src/core/                # Core pipeline logic
│   ├── orchestrator.py      # Pipeline controller (parallel multi-source)
│   ├── analyzer.py          # Trend analysis via LLM
│   ├── generator.py         # Idea generation via LLM
│   ├── deep_dive.py         # Deep dive analysis via LLM
│   ├── novelty_checker.py   # Novelty scoring (Semantic Scholar + arXiv)
│   ├── llm.py               # Multi-provider LLM client (6 providers)
│   ├── config.py            # Configuration loader
│   ├── models.py            # Data models
│   └── fetchers/            # Paper fetching modules
│       ├── arxiv_fetcher.py
│       ├── openalex_fetcher.py
│       └── semanticscholar_fetcher.py
├── src/web/                 # Dashboard UI
│   ├── templates/dashboard.html
│   └── static/
├── tests/                   # Test suite (73 Python + 27 JS = 100 tests)
├── skills/                  # Customizable research profiles (9 built-in)
├── docs/                    # Documentation and assets
├── preview_server.py        # Flask web server (entry point)
├── run_pipeline.py          # CLI entry point
└── config.yaml              # LLM and app configuration
```

---

## CLI Usage

```bash
python run_pipeline.py

# With environment variables
SCOUT_CONTEXT="NLP researcher" SCOUT_APPROACH="computational" python run_pipeline.py
SCOUT_LANGUAGE="id" SCOUT_CATEGORIES="med.cardio,med.neuro" python run_pipeline.py
```

## Testing

```bash
pytest tests/          # Python tests
npm test               # JavaScript tests
```

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines. Key areas:
- Add new paper sources (fetchers)
- Create custom skills (research profiles)
- Improve LLM prompts
- Add new categories

## License

MIT — see [LICENSE](LICENSE).

---

## Support

If ScholarScout helps your research:

- [♥ Ko-fi (International)](https://ko-fi.com/scholarscout)
- [♥ Saweria (Indonesia)](https://saweria.co/scholarscout)
- Star this repo on GitHub

---

---

# Bahasa Indonesia

<p align="center">
  <img src="docs/banner.png" alt="ScholarScout" width="600">
</p>

<p align="center">
  <strong>Platform penemuan ide riset berbasis AI untuk mahasiswa dan peneliti.</strong><br>
  <em>Scan 250 juta+ paper. Analisis tren. Generate ide actionable. Verifikasi kebaruan.</em>
</p>

---

## Fitur Lengkap

### Data & Sumber
- **Multi-sumber** — arXiv, OpenAlex, Semantic Scholar (250M+ paper)
- **Fetch paralel** — 3 sumber diambil bersamaan per kategori
- **80+ kategori** — Ilmu Komputer, Kedokteran, Biologi, Fisika, Teknik, Kimia, Ilmu Sosial, Ilmu Bumi, Pertanian
- **Deduplikasi otomatis** — Paper tidak duplikat antar sumber

### Kecerdasan
- **Analisis tren** — Identifikasi metode baru, celah riset, pola metodologi
- **Generasi ide** — Ide spesifik dengan hint metodologi, langkah awal, paper kunci
- **Filter pendekatan** — Komputasi/AI, Eksperimental/Lab, Klinis/Lapangan, Teoritis/Review
- **Cek kebaruan** — Bandingkan ide dengan paper yang sudah ada
- **Deep dive** — Outline riset lengkap: metodologi, dataset, timeline, tools, referensi

### Personalisasi
- **Konteks riset** — Deskripsikan latar belakang untuk hasil yang relevan
- **Onboarding** — User baru dipandu pilih approach + konteks sebelum generate
- **Bahasa** — English atau Bahasa Indonesia (termasuk judul)
- **Level** — Undergraduate, Master's, PhD
- **Skills** — 9 profil riset yang bisa di-customize

### Dashboard
- **Monitoring real-time** — Lihat paper di-fetch dan dianalisis secara live
- **Search & filter** — Cari ide by keyword atau filter by level
- **Popup detail** — Full detail ide dalam modal yang bersih
- **Export PDF per ide** — Export satu ide sebagai PDF terformat
- **Bookmark** — Simpan favorit ke shortlist
- **Recent ideas** — Akses hasil pipeline sebelumnya

### LLM & Konfigurasi
- **6 provider LLM** — Gemini (gratis), Groq (gratis), OpenRouter, OpenAI, Ollama (lokal), Custom
- **Settings UI** — Konfigurasi dari dashboard tanpa edit file
- **Test connection** — Verifikasi setup dengan 1 klik
- **Token budget adaptif** — Hemat ~48% biaya token

---

## Cara Memulai

```bash
git clone https://github.com/neej4/ScholarScout.git
cd ScholarScout
pip install -r requirements.txt
python preview_server.py
```

Buka **http://localhost:5050** di browser.

### Setup LLM

Buka tab **Settings** → pilih provider → paste API key → **Test Connection** → **Save**.

Provider gratis: **Gemini** ([dapatkan key](https://aistudio.google.com/app/apikey)) atau **Groq** ([dapatkan key](https://console.groq.com/keys)).

---

## Kontribusi

Lihat [CONTRIBUTING.md](CONTRIBUTING.md). Area kontribusi:
- Tambah sumber paper baru (fetcher)
- Buat custom skills (profil riset)
- Perbaiki prompt LLM
- Tambah kategori baru

## Lisensi

MIT — lihat [LICENSE](LICENSE).

## Dukung Proyek Ini

- [♥ Ko-fi (International)](https://ko-fi.com/scholarscout)
- [♥ Saweria (Indonesia)](https://saweria.co/scholarscout)
- Beri bintang di GitHub

