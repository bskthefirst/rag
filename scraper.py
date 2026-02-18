
import os
import requests
from bs4 import BeautifulSoup
import markdownify
import easyocr
from PIL import Image
from io import BytesIO
import time
import re
import json
import html
import argparse
from datetime import datetime
from urllib.parse import urlparse, parse_qs, urlencode, urlunparse
import ssl

try:
    _create_unverified_https_context = ssl._create_unverified_context
except AttributeError:
    pass
else:
    ssl._create_default_https_context = _create_unverified_https_context

# Configuration
BLOG_ID = "xpfkwh56"
BASE_URL = "https://blog.naver.com"
POST_LIST_URL = f"{BASE_URL}/PostList.naver"
POST_VIEW_URL = f"{BASE_URL}/PostView.naver"
OUTPUT_DIR = "posts"
IMAGE_DIR = "images"
STATE_FILE = "state.json"

# Initialize OCR reader (will download model on first run)
print("Initializing OCR (this may take a while first time)...")
try:
    reader = easyocr.Reader(['ko', 'en'], gpu=False) # GPU False for compatibility
except Exception as e:
    print(f"Warning: OCR initialization failed: {e}")
    reader = None

def ensure_dirs():
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    os.makedirs(IMAGE_DIR, exist_ok=True)

def get_with_retry(url, headers=None, timeout=20, retries=3, backoff=1.5):
    last_err = None
    for attempt in range(retries):
        try:
            resp = requests.get(url, headers=headers, timeout=timeout)
            resp.raise_for_status()
            return resp
        except requests.RequestException as e:
            last_err = e
            if attempt < retries - 1:
                time.sleep(backoff * (attempt + 1))
    raise last_err

def get_post_list(page=1):
    """Fetches list of posts from PostList.naver"""
    # Use categoryNo=0 (View All) and from=postList
    # Even if listCount is ignored by server (defaults to 5/10), pagination works.
    url = f"{POST_LIST_URL}?blogId={BLOG_ID}&currentPage={page}&categoryNo=0&from=postList"
    headers = {
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.114 Safari/537.36',
        'Referer': f"{BASE_URL}/{BLOG_ID}"
    }
    response = get_with_retry(url, headers=headers, timeout=20, retries=3)
    # Debug
    # print(f"DEBUG Page {page} fetched. Len: {len(response.text)}")
    return response.text

def extract_links_from_list_page(html):
    # Bruteforce Regex extraction because the HTML is messy/dynamic
    # We just need the logNos. The specific title can be fetched from the post view itself.
    
    links = []
    
    # Pattern 1: logNo=123456789 (Common in hrefs)
    # Pattern 2: /blogId/123456789 (Common in clean URLs)
    # Pattern 3: data-cid="blogId_123456789" (Common in like buttons/scripts)
    # Pattern 4: logNo: "123456789" (Common in JS objects)
    
    # Find all sequences of digits that look like logNos (usually 11-12 digits)
    # Naver logNos are typically long integers.
    # Let's simple look for the explicitly labelled ones first.
    
    details_found = {} # logNo -> title map
    
    # 1. Regex for logNo=...
    matches_param = re.findall(r'logNo=(\d+)', html)
    for log_no in matches_param:
        details_found[log_no] = "Found via Regex"

    # 2. Regex for /blogId/logNo
    matches_path = re.findall(f"/{BLOG_ID}/(\\d+)", html)
    for log_no in matches_path:
        details_found[log_no] = "Found via Regex"
        
    # 3. Regex for data-cid or similar (data-cid="blogId_logNo")
    matches_cid = re.findall(f'{BLOG_ID}_(\\d+)', html)
    for log_no in matches_cid:
        details_found[log_no] = "Found via Regex"
    
    # 4. Try to find titles if possible (HTML parsing)
    soup = BeautifulSoup(html, 'html.parser')
    for a in soup.find_all('a'):
        href = a.get('href', '')
        txt = a.get_text(strip=True)
        if not txt: continue
        
        # Check if this <a> contains a logNo we found
        for log_no in details_found.keys():
            if log_no in href and txt not in ['목록열기', '글쓰기', '전체글 보기', '공감']:
                 details_found[log_no] = txt
    
    # Construct final list
    for log_no, title in details_found.items():
        links.append({
            'url': f"https://blog.naver.com/{BLOG_ID}/{log_no}",
            'logNo': str(log_no),
            'title': title
        })
            
    # Naver often puts the "current" post (from the redirect) in the HTML too.
    # This might result in scraping the "latest" post repeatedly if every page redirects to it.
    # But unique check in `process_posts` handles that.
    
    return links

def fetch_post_content_html(log_no):
    url = f"{POST_VIEW_URL}?blogId={BLOG_ID}&logNo={log_no}"
    headers = {
         'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.114 Safari/537.36'
    }
    response = get_with_retry(url, headers=headers, timeout=20, retries=3)
    return response.text

def choose_best_image_url(img):
    # Naver's `src` is often a tiny `w80_blur` thumbnail.
    # Prefer lazy/full image candidates first.
    for key in ['data-lazy-src', 'data-src', 'src']:
        val = img.get(key)
        if val and 'blank.gif' not in val:
            return val
    return None

def normalize_naver_image_url(url):
    # Force a high-resolution variant for postfiles CDN.
    # `type=w2000` returns the highest practical size in most cases.
    parsed = urlparse(url)
    if not parsed.scheme:
        if url.startswith('//'):
            url = f"https:{url}"
        else:
            url = f"https://{url.lstrip('/')}"
        parsed = urlparse(url)

    query = parse_qs(parsed.query, keep_blank_values=True)
    query['type'] = ['w2000']
    new_query = urlencode(query, doseq=True)
    return urlunparse(parsed._replace(query=new_query))

def should_redownload_image(img_abs_path):
    if not os.path.exists(img_abs_path):
        return True
    try:
        with Image.open(img_abs_path) as im:
            w, h = im.size
        size = os.path.getsize(img_abs_path)
        # Existing archives were mostly 80px thumbnails.
        return w <= 120 or h <= 120 or size < 12_000
    except Exception:
        return True

def process_images_and_ocr(soup, post_id, perform_ocr=True):
    ocr_texts = []
    
    # Try different selectors for images
    imgs = soup.select('img.se-image-resource, .se-module-image img, #postViewArea img')
    
    for i, img in enumerate(imgs):
        src = choose_best_image_url(img)
            
        if src:
            try:
                src = normalize_naver_image_url(src)
                # Basic filename
                ext = 'jpg'
                path_lower = urlparse(src).path.lower()
                if path_lower.endswith('.png'):
                    ext = 'png'
                elif path_lower.endswith('.gif'):
                    ext = 'gif'
                elif path_lower.endswith('.webp'):
                    ext = 'webp'
                
                img_name = f"{post_id}_{i}.{ext}"
                img_rel_path = os.path.join(IMAGE_DIR, img_name)
                img_abs_path = os.path.abspath(img_rel_path)
                
                # Download (or replace low-res legacy thumbnail files)
                if should_redownload_image(img_abs_path):
                    # Download
                    content = get_with_retry(src, headers={
                        'User-Agent': 'Mozilla/5.0',
                        'Referer': f"{BASE_URL}/{BLOG_ID}"
                    }, timeout=20, retries=3).content
                    with open(img_abs_path, 'wb') as f:
                        f.write(content)
                
                # Update src in HTML for markdown conversion
                # We use relative path for markdown
                img['src'] = os.path.join("..", IMAGE_DIR, img_name)
                
                # Perform OCR
                if perform_ocr and reader:
                    # check file size/type validity for OCR
                    if os.path.getsize(img_abs_path) > 100:
                        try:
                            # print(f"OCR processing {img_name}...")
                            result = reader.readtext(img_abs_path, detail=0)
                            if result:
                                text_content = " ".join(result)
                                if len(text_content.strip()) > 1: # Filter empty
                                    ocr_texts.append(f"Image {i+1} Text: {text_content}")
                                    # Add caption to HTML 
                                    caption_div = soup.new_tag("blockquote")
                                    caption_div.string = f"**OCR Detected Text:** {text_content}"
                                    img.insert_after(caption_div)
                        except Exception as e:
                            print(f"    OCR Error on {img_name}: {e}")
                            
            except Exception as e:
                print(f"    Failed to process image {src}: {e}")
                
    return "\n\n".join(ocr_texts)

def clean_filename(s):
    # Remove invalid chars
    s = re.sub(r'[\\/*?:"<>|]', "", s)
    return s[:100].strip()

def save_post(post_data):
    md_text = markdownify.markdownify(str(post_data['content_soup']), heading_style="ATX")
    
    # Format: YYYY-MM-DD_Title.md
    safe_title = clean_filename(post_data['title'])
    
    # Date normalization
    date_str = post_data['date']
    try:
        # Expected: "2025. 5. 18. 5:29" or similar
        # Regex to find YYYY. M. D.
        match = re.search(r'(\d{4})\.\s*(\d{1,2})\.\s*(\d{1,2})', date_str)
        if match:
            y, m, d = match.groups()
            date_str = f"{y}-{int(m):02d}-{int(d):02d}"
        else:
             # Fallback cleanup
             date_str = re.sub(r'[^\w-]', '', date_str)
    except Exception as e:
        print(f"    Date parsing warning ({date_str}): {e}")
        date_str = re.sub(r'[^\w-]', '', date_str)

    filename = f"{date_str}_{safe_title}.md"
    filepath = os.path.join(OUTPUT_DIR, filename)
    
    header = f"# {post_data['title']}\n"
    header += f"**Date:** {post_data['date']}\n"
    header += f"**Category:** {post_data.get('category', 'Uncategorized')}\n"
    header += f"**Original URL:** {BASE_URL}/{BLOG_ID}/{post_data['logNo']}\n"
    header += "---\n\n"
    
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(header + md_text)
        
    print(f"  Saved: {filepath}")

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--limit', type=int, default=None)
    parser.add_argument('--incremental', action='store_true')
    parser.add_argument('--no-ocr', action='store_true')
    args = parser.parse_args()
    
    ensure_dirs()
    
    # Load state
    last_log_no = None
    if os.path.exists(STATE_FILE):
        try:
            with open(STATE_FILE, 'r') as f:
                state = json.load(f)
                last_log_no = state.get('last_log_no')
        except:
            pass
            
    print(f"Starting scrape. Incremental: {args.incremental}, Last LogNo: {last_log_no}")
    
    all_links = []
    seen_lognos = set() # Global set to avoid duplicates (like pinned notices appearing on every page)
    
    page = 1
    stop_scraping = False
    consecutive_empty_pages = 0
    
    # 1. Collect all valid links first (up to limit or known post)
    while not stop_scraping:
        print(f"Scanning list page {page}...")
        html = get_post_list(page)
        links = extract_links_from_list_page(html)
        
        if not links:
            print("  No more links found on this page.")
            # If page 1 gives nothing, something is wrong.
            if page == 1:
                print("  Warning: No links found on page 1. Check selector or URL.")
            break
            
        new_links_found = 0
        for link in links:
            if args.incremental and str(link['logNo']) == str(last_log_no):
                print(f"  Reached known post {link['logNo']}. Stopping list scan.")
                stop_scraping = True
                break
            
            if link['logNo'] in seen_lognos:
                continue
                
            seen_lognos.add(link['logNo'])
            all_links.append(link)
            new_links_found += 1
            
            if args.limit and len(all_links) >= args.limit:
                stop_scraping = True
                break
        
        if new_links_found == 0:
            print(f"  No new unique links on page {page}. (Duplicates/Notices only)")
            consecutive_empty_pages += 1
            if len(links) > 0 and consecutive_empty_pages >= 3:
                print("  3 consecutive pages with only duplicate links. Likely end of unique posts. Stopping.")
                break
            elif len(links) == 0:
                 # Should have been caught by 'if not links' above, but just in case
                 break
        else:
            consecutive_empty_pages = 0
        
        page += 1
        if page > 1000: # safety limit increased
            break
            
    print(f"Found {len(all_links)} posts to process.")
    
    if not all_links:
        return

    
    # Let's reverse found_posts to process oldest first? 
    # No, automation usually wants newest.
    # We just need to save the logNo of the newest post (index 0) to state.
    
    newest_log_no = all_links[0]['logNo']
    
    for post_meta in all_links:
        log_no = post_meta['logNo']
        print(f"Processing {log_no}: {post_meta['title']}")
        
        try:
            raw_html = fetch_post_content_html(log_no)
            soup = BeautifulSoup(raw_html, 'html.parser')
            
            # Extract meta
            # Main container
            main_container = soup.select_one('.se-main-container') or soup.select_one('#postViewArea')
            
            if not main_container:
                print("  Skipping: Content container not found (hidden or protected post?)")
                continue
                
            # Date
            date_elem = soup.select_one('.se_publishDate') or soup.select_one('.date')
            date_text = date_elem.get_text(strip=True) if date_elem else "Unknown Date"
            
            # Title (re-verify from post content to be sure)
            title_elem = soup.select_one('.se-title-text') or soup.select_one('.htitle') or soup.select_one('.itemSubject')
            title_text = title_elem.get_text(strip=True) if title_elem else post_meta['title']
            
            # Category extraction
            # Browser debug found '.blog2_series a.pcol2'
            cate_elem = (soup.select_one('.blog2_series a') or 
                         soup.select_one('.blog2_series') or 
                         soup.select_one('.blog2_category') or 
                         soup.select_one('.category') or 
                         soup.select_one('.cate'))
            category_text = cate_elem.get_text(strip=True) if cate_elem else "Uncategorized"
            
            # Process Images & OCR
            # Modifies soup in-place
            process_images_and_ocr(main_container, log_no, perform_ocr=not args.no_ocr)
            
            post_data = {
                'logNo': log_no,
                'title': title_text,
                'date': date_text,
                'category': category_text,
                'content_soup': main_container
            }
            
            save_post(post_data)
            time.sleep(1) # Be nice
            
        except Exception as e:
            print(f"  Error processing {log_no}: {e}")
            import traceback
            traceback.print_exc()

    # Update state
    with open(STATE_FILE, 'w') as f:
        json.dump({'last_log_no': newest_log_no}, f)
    print("State updated.")

if __name__ == "__main__":
    main()
