#!/bin/bash

# Navigate to script directory
cd "$(dirname "$0")"

# Activate virtual environment if it exists (standard convention)
# Assuming user might have created one, or we just rely on system python if that's what we used.
# Since we used `python3 -m pip install`, we should use `python3`.

echo "Starting daily scrape at $(date)"

# Run scraper in incremental mode
python3 scraper.py --incremental

echo "Scrape completed at $(date)"
