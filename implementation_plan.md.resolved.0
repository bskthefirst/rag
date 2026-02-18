# Naver Blog Scraper Implementation Plan

This plan outlines the development of a Python-based scraper for the Naver blog [xpfkwh56](https://blog.naver.com/xpfkwh56) with OCR capabilities and daily automation.

## User Review Required

> [!IMPORTANT]
> **OCR dependency**: I plan to use `EasyOCR` for extracting text from images. This library requires `PyTorch` and can be heavy to install. Please confirm if this is acceptable or if you prefer `Tesseract` (which requires a system-level installation of the tesseract binary). I will proceed with EasyOCR as the default Python-only solution.

> [!NOTE]
> **Execution Time**: OCR is computationally intensive. The initial scrape of all posts will take significant time. Subsequent daily updates will be faster.

## Proposed Changes

### [Scraper Implementation]
I will create a modular Python script to handle the scraping, OCR, and file saving.

#### [NEW] [requirements.txt](file:///Users/suhyun/.gemini/antigravity/brain/558fbe7a-dd4d-4a21-b204-2d47dcf92244/requirements.txt)
- `requests`: For fetching web pages.
- `beautifulsoup4`: For parsing HTML.
- `markdownify`: For converting HTML content to Markdown.
- `easyocr`: For Korean OCR.
- `Pillow`: For image processing.

#### [NEW] [scraper.py](file:///Users/suhyun/.gemini/antigravity/brain/558fbe7a-dd4d-4a21-b204-2d47dcf92244/scraper.py)
 - **`fetch_post_list(blog_id, page)`**: Recursively fetches the list of posts from `PostList.naver` until all posts are retrieved or the last scraped ID is met.
 - **`extract_post_content(url)`**: Parses the post title, date, and body.
 - **`process_images(html_content, post_id)`**: Downloads images to a local directory and replaces `src` in <img> tags with local paths.
 - **`perform_ocr(image_path)`**: Uses `EasyOCR` to detect text in images and appends the text to the markdown.
 - **`save_post(post_data)`**: Saves the content as a markdown file named `{Date}_{Title}.md`.

### [Automation]
I will create a shell script to simplify the daily execution mechanism.

#### [NEW] [run_daily.sh](file:///Users/suhyun/.gemini/antigravity/brain/558fbe7a-dd4d-4a21-b204-2d47dcf92244/run_daily.sh)
- Checks if the virtual environment is active (or activates it).
- Runs `scraper.py` with an `--incremental` flag to only fetch new posts since the last run.
- Can be added to `crontab` for daily execution.

## Verification Plan

### Automated Tests
- I will create a small test script `test_scraper.py` to:
    - Verify `fetch_post_list` returns a list of dictionaries.
    - Verify `perform_ocr` works on a sample image.

### Manual Verification
- **Run Initial Scrape**: Execute `python scraper.py --limit 1` to scrape the latest post.
- **Check Output**:
    - Verify the markdown file exists in `posts/`.
    - Verify images are downloaded in `images/`.
    - Verify OCR text is appended to the post content.
- **Run Incremental Scrape**: Run the script again and verify it detects no new posts (or correctly identifies new ones).
