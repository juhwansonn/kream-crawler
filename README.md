# Kream Crawling

![Python 3.10+](https://img.shields.io/badge/Python-3.10+-3776AB?logo=python&logoColor=white)
![Selenium 4](https://img.shields.io/badge/Selenium-4.x-43B02A?logo=selenium&logoColor=white)
![Status](https://img.shields.io/badge/status-in%20development-orange)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

> Automate data collection from the KREAM resale marketplace with Selenium and export tidy spreadsheets powered by pandas + openpyxl.

---

## Table of Contents
- [Overview](#overview)
- [Key Features](#key-features)
- [Tech Stack](#tech-stack)
- [Getting Started](#getting-started)
- [Usage](#usage)
- [Project Structure](#project-structure)
- [Troubleshooting](#troubleshooting)
- [Roadmap](#roadmap)
- [Contributing](#contributing)
- [License](#license)

## Overview
Kream Crawling is a lightweight starter kit for building Selenium-based scrapers that capture product insights from [KREAM](https://kream.co.kr/). The repository currently ships with a minimal entry point (`main.py`) and a workspace (`crawler.py`) where you can design page-specific automation. Data transformation and Excel export duties are handled with pandas and openpyxl, giving you a reliable path from browser automation to shareable spreadsheets.

Even though the crawling logic is yours to implement, the repository sets expectations for dependencies, runtime flow, and output handling so you can focus on selectors, pagination, and resilience against front-end changes.

## Key Features
- Selenium-ready scaffold for authentic browser automation (Chrome, Edge, or other Chromium browsers).
- Pandas pipelines for cleaning and reshaping scraped payloads.
- Excel-friendly exports (multi-sheet, formatting, formulas) through openpyxl.
- Clear separation between orchestration (`main.py`) and page helpers/utilities (`crawler.py`).
- Virtual-environment-friendly workflow for reproducible runs and deployment.

## Tech Stack
- **Language:** Python 3.10+
- **Automation:** Selenium 4
- **Data Processing:** pandas 2
- **Spreadsheet Writer:** openpyxl 3

Exact versions live in `requirements.txt` so you can pin or upgrade as needed.

## Getting Started
1. **Clone the repository**
   ```bash
   git clone https://github.com/<your-username>/Kream-Crawling.git
   cd Kream-Crawling
   ```

2. **Create & activate a virtual environment**
   ```bash
   python -m venv .venv
   source .venv/bin/activate        # Windows: .venv\Scripts\activate
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Install a matching WebDriver**
   - Chrome: download ChromeDriver that matches your browser version and add it to `PATH`.
   - Edge / Chromium: use the official driver manager or `webdriver_manager`.

5. **Run the script**
   ```bash
   python main.py
   ```
   Extend `main.py` with CLI arguments or scheduling logic (cron, Windows Task Scheduler) as needed.

## Usage
The repository is intentionally thin so you can tailor it to your scraping targets:

1. **Design crawler helpers** inside `crawler.py`. Wrap Selenium operations in functions or classes (`fetch_listings`, `parse_listing`, etc.) that return Python dictionaries or pandas DataFrames.
2. **Coordinate execution** from `main.py`. Initialize the crawler, pass in search keywords or product URLs, and hand the resulting dataframe to an export helper.
3. **Export results** with pandas/openpyxl. Example snippet:
   ```python
   df.to_excel("kream_listings.xlsx", index=False)
   ```
4. **Harden the scraper** with smart waits, rotating user agents, or cookie hydration to survive KREAM's anti-bot measures.

### Tips
- Keep selectors in a dedicated module or dictionary so you can update them quickly.
- Leverage pandas `to_excel` kwargs (`sheet_name`, `engine`, `freeze_panes`) to deliver analyst-friendly sheets.
- Store secrets (proxies, credentials) in environment variables or a `.env` file that stays out of version control.

## Project Structure
```
Kream-Crawling/
├── crawler.py        # Place Selenium helpers, page objects, and parsing utilities here
├── main.py           # Script entry point — orchestrates crawling & exporting
├── requirements.txt  # Runtime dependencies
└── README.md         # Project documentation
```

Add a `data/` or `outputs/` folder if you want to separate generated files from source code.

## Troubleshooting
- **WebDriver not found:** Ensure the driver binary matches both your browser version and OS architecture, then confirm it is on your `PATH`.
- **Unexpected login/OTP prompts:** Authenticate manually once, export cookies, and load them before visiting product pages.
- **Layout/selectors changed:** Isolate selectors in one place and add integration tests (pytest + Selenium) to catch KREAM UI changes early.
- **Excel encoding issues:** Always call `df.to_excel(..., engine="openpyxl")` and keep column names UTF-8 friendly.

## License
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

Distributed under the MIT License. See [`LICENSE`](LICENSE) for the full text and attribution requirements.
