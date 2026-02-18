# Deploying Your Naver Blog RAG to GitHub Pages

GitHub Pages is a **static hosting service**. It cannot run Python scripts (`rag_search.py`, `scraper.py`) or databases (`ChromaDB`) dynamically when a user visits the site.

However, you can build a **"Serverless RAG"** system that runs entirely in the user's browser!

## The Architecture

1.  **Scraping & Indexing (GitHub Actions)**:
    -   A GitHub Action runs `scraper.py` every day (or manually).
    -   It runs `rag_indexer.py` to create the vector database.
    -   It **exports** the database (or a simpler JSON index + embeddings) to a static file (e.g., `index.json` or `embeddings.bin`).

2.  **Frontend (GitHub Pages)**:
    -   A simple HTML/JS website.
    -   **Search Engine**: Uses a JavaScript library (like `Voy`, `Orama`, or `Transformers.js`) to load the index into the browser's memory.
    -   **Embeddings**: `Transformers.js` runs the embedding model (e.g., `all-MiniLM-L6-v2`) **inside the browser** to convert the user's query into a vector.
    -   The vector search happens locally on the user's device. No backend server needed!

---

## Step-by-Step Implementation Guide

### Phase 1: Prepare the Data for Web
Your current `chromadb` is great for Python, but heavy for browsers. We need to export it.

1.  **Create an Exporter Script (`export_index.py`)**:
    -   Read data from ChromaDB.
    -   Save a `documents.json` containing: `[{ "id": "...", "text": "...", "embedding": [...] }]`.
    -   Commit this file to your repo (or upload as a release asset).

### Phase 2: Create the Website
Create an `index.html` in your repository.

```html
<!-- index.html -->
<!DOCTYPE html>
<html>
<head>
    <title>My Blog RAG</title>
    <!-- Load Transformers.js -->
    <script type="module">
        import { pipeline, env } from 'https://cdn.jsdelivr.net/npm/@xenova/transformers@2.6.0';

        // Disable local model checking (since we use CDN)
        env.allowLocalModels = false;

        let index = [];
        let extractor = null;

        async function loadSystem() {
            document.getElementById('status').innerText = "Loading AI Model...";
            
            // 1. Load the Embedding Model (runs in browser!)
            extractor = await pipeline('feature-extraction', 'Xenova/all-MiniLM-L6-v2');
            
            // 2. Load the Index (your scraped data)
            document.getElementById('status').innerText = "Loading Blog Index...";
            const response = await fetch('./documents.json'); // The file you exported
            index = await response.json();
            
            document.getElementById('status').innerText = "Ready!";
        }

        // Cosine Similarity Function
        function cosineSimilarity(a, b) {
            let dot = 0;
            let magA = 0;
            let magB = 0;
            for (let i = 0; i < a.length; i++) {
                dot += a[i] * b[i];
                magA += a[i] * a[i];
                magB += b[i] * b[i];
            }
            return dot / (Math.sqrt(magA) * Math.sqrt(magB));
        }

        window.search = async () => {
            const query = document.getElementById('query').value;
            document.getElementById('results').innerHTML = "Searching...";
            
            // Generate embedding for query
            const output = await extractor(query, { pooling: 'mean', normalize: true });
            const queryVector = output.data;

            // Brute-force search (fast enough for <10k posts)
            // For larger scales, use 'voy' or 'usearch' JS libraries.
            const results = index.map(doc => ({
                doc,
                score: cosineSimilarity(queryVector, doc.embedding)
            }))
            .sort((a, b) => b.score - a.score)
            .slice(0, 5); // Top 5

            // Render
            const html = results.map(r => `
                <div style="border:1px solid #ddd; padding:10px; margin:10px 0;">
                    <h3>${r.doc.metadata.title} (Score: ${r.score.toFixed(2)})</h3>
                    <p>${r.doc.page_content.substring(0, 200)}...</p>
                    <a href="https://blog.naver.com/${r.doc.metadata.blog_id}/${r.doc.metadata.log_no}" target="_blank">Read Post</a>
                </div>
            `).join('');
            
            document.getElementById('results').innerHTML = html;
        };

        loadSystem();
    </script>
</head>
<body>
    <h1>Blog Archive RAG</h1>
    <div id="status">Initializing...</div>
    <input type="text" id="query" placeholder="Ask about 'AI' or 'Money'...">
    <button onclick="search()">Search</button>
    <div id="results"></div>
</body>
</html>
```

### Phase 3: Automate with GitHub Actions
Create `.github/workflows/scrape_and_deploy.yml`:

```yaml
name: Scrape and Deploy
on:
  schedule:
    - cron: '0 0 * * *' # Daily at midnight
  workflow_dispatch:

jobs:
  build:
    runs-on: ubuntu-latest
    steps:
    - uses: actions/checkout@v3
    
    - name: Set up Python
      uses: actions/setup-python@v4
      with:
        python-version: '3.9'
        
    - name: Install Dependencies
      run: pip install requests beautifulsoup4 chromadb sentence-transformers
      
    - name: Run Scraper
      run: python scraper.py --limit 10 # Incremental update
      
    - name: Run Indexer
      run: python rag_indexer.py
      
    - name: Export for Web
      # You need to write this script to dump ChromaDB to documents.json
      run: python export_index_for_web.py 
      
    - name: Deploy to GitHub Pages
      uses: peaceiris/actions-gh-pages@v3
      with:
        github_token: ${{ secrets.GITHUB_TOKEN }}
        publish_dir: ./ # Or wherever index.html and documents.json are
```

## Summary
1.  **Python** scrapes and creates the "Brain" (embeddings).
2.  **GitHub Actions** automates this daily.
3.  **JSON** carries the brain to the web.
4.  **Transformers.js** creates the "Mind" in the browser to match user queries to the brain.

This is cost-effective (free hosting) and very fast for the user!
