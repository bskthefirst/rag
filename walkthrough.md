# Naver Blog Scraper Walkthrough

This guide explains how to use the Naver Blog Scraper for [xpfkwh56](https://blog.naver.com/xpfkwh56).

## Features
- **Scrapes all posts**: Starting from the "View All" list.
- **OCR Integration**: Extracts Korean text from images using `EasyOCR`.
- **Incremental Updates**: Tracks the last scraped post to only fetch new content on subsequent runs.
- **Markdown Output**: Saves posts as `YYYY-MM-DD_Title.md` with downloaded images.

## Prerequisite
Ensure dependencies are installed:
```bash
python3 -m pip install -r requirements.txt
```
*(Note: On first run, EasyOCR will download detection models which might take a few minutes)*

## Manual Execution

### Run Full Scrape (or First Run)
To start scraping:
```bash
python3 scraper.py
```

### Run with Limit
To test with just the latest 5 posts:
```bash
python3 scraper.py --limit 5
```

## Daily Automation

A shell script `run_daily.sh` is provided for automation. It runs the scraper in `--incremental` mode.

### 1. Test the script
```bash
./run_daily.sh
```

### 2. Schedule with Cron (Mac/Linux)
Open your crontab:
```bash
crontab -e
```
Add the following line to run daily at 9:00 AM (replace `/path/to/...` with your actual path):
```cron
0 9 * * * /Users/suhyun/.gemini/antigravity/brain/558fbe7a-dd4d-4a21-b204-2d47dcf92244/run_daily.sh >> /tmp/naver_scraper.log 2>&1
```

## RAG System (Search)

You can search through your scraped posts using the built-in RAG system.

### 1. Install RAG Dependencies
If you haven't already:
```bash
python3 -m pip install -r requirements.txt
```

### 2. Build the Index
Run this command whenever you scrape new posts to update the search index:
```bash
python3 rag_indexer.py
```
*Creates a local vector database in `chroma_db/`.*

### 3. Search
Query your blog archive:
```bash
python3 rag_search.py "your search query"
```

**Options:**
- `--k 5`: Return top 5 results (default 3).
- `--category "Category Name"`: Filter results by category.
  - Example: `python3 rag_search.py "study tips" --category "갓생추구"`

## Output Structure
- `posts/`: Contains Markdown files.
- `images/`: Contains downloaded images.
- `state.json`: Track the last scraped post ID.
- `chroma_db/`: Vector database for RAG.

## 4. Static RAG Deployment (GitHub Pages)

We have implemented a **Serverless RAG** system that runs entirely in the browser using `Transformers.js`.

### Key Components:
-   **`export_for_web.py`**: Converts the local ChromaDB index into a lightweight `documents.json` suitable for web use.
-   **`index.html`**: A simple frontend that loads `documents.json` and runs the embedding model (`all-MiniLM-L6-v2`) in the user's browser to perform semantic search.
-   **`.github/workflows/deploy.yml`**: Automates the entire process. It scrapes new posts, updates the index, exports it, and deploys the static site to GitHub Pages daily.

### How to Deploy:
1.  Push the code to your repository: `git push origin main`.
2.  Go to **GitHub Settings > Pages** and set source to `gh-pages` branch (once the Action runs).
3.  Visit your new RAG-powered blog archive!
