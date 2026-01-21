import asyncio
import os
import requests
from playwright.async_api import async_playwright
from urllib.parse import urljoin, urlparse
import csv
from pathlib import Path

# PDF storage folder
PDF_STORAGE_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "downloads", "pdfs")
os.makedirs(PDF_STORAGE_DIR, exist_ok=True)

# Track PDF URLs already processed in this run
PROCESSED_PDF_URLS = set()

# Metadata CSV file
METADATA_CSV = os.path.join(os.path.dirname(os.path.dirname(__file__)), "downloads", "documents_metadata.csv")


def append_metadata_row(source_url, pdf_url, filename, page_title):
    """Append one row of PDF metadata to CSV (create with header if new)."""
    file_exists = Path(METADATA_CSV).exists()
    with open(METADATA_CSV, "a", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        if not file_exists:
            writer.writerow(["source_url", "pdf_url", "filename", "page_title"])
        writer.writerow([source_url, pdf_url, filename, page_title or ""])


def download_pdf(pdf_url, base_url):
    """Download PDF and save to local folder"""
    # Make absolute URL
    if not pdf_url.startswith("http"):
        pdf_url = urljoin(base_url, pdf_url)

    # Get filename from URL
    filename = os.path.basename(urlparse(pdf_url).path)
    if not filename.endswith(".pdf"):
        filename = f"document_{hash(pdf_url)}.pdf"

    file_path = os.path.join(PDF_STORAGE_DIR, filename)

    # Skip if already downloaded
    if os.path.exists(file_path):
        return file_path

    # Simple retry with streaming download
    headers = {"User-Agent": "Mozilla/5.0"}
    last_err = None

    for attempt in range(3):
        try:
            with requests.get(pdf_url, headers=headers, timeout=60, stream=True) as response:
                response.raise_for_status()
                with open(file_path, "wb") as f:
                    for chunk in response.iter_content(chunk_size=8192):
                        if chunk:
                            f.write(chunk)
            return file_path
        except Exception as e:
            last_err = e
            if attempt < 2:
                import time
                time.sleep(2)
            else:
                print(f"Giving up on {pdf_url}: {last_err}")
                return None


async def get_banking_sector_links(page):
    """Get all links under Banking Sector menu"""
    await page.goto("https://rulebook.sama.gov.sa/en/banking-sector-0", wait_until="networkidle")
    
    links = []
    menu_links = await page.query_selector_all('nav#book-block-menu-1363 a[href*="/en/"]')
    
    for link in menu_links:
        href = await link.get_attribute("href")
        if href and href.startswith("/en/"):
            full_url = urljoin("https://rulebook.sama.gov.sa", href)
            if full_url not in links:
                links.append(full_url)
    
    return links


async def crawl_page(page, url):
    """Crawl a single page and download PDFs, return discovered child links"""
    try:
        await page.goto(url, wait_until="networkidle", timeout=30000)

        # Get page title once for metadata
        try:
            page_title = await page.title()
        except Exception:
            page_title = ""

        # Find PDF links
        pdf_links = await page.query_selector_all('a[href*=".pdf"], a[href*="/sites/default/files/"]')

        for pdf_link in pdf_links:
            pdf_href = await pdf_link.get_attribute("href")
            if not pdf_href or not (".pdf" in pdf_href or "/sites/default/files/" in pdf_href):
                continue

            pdf_url = urljoin(url, pdf_href)

            # Skip if we've already processed this PDF URL in this run
            if pdf_url in PROCESSED_PDF_URLS:
                continue

            # Only download Rulebook PDFs hosted on rulebook.sama.gov.sa under /sites/default/files/
            from urllib.parse import urlparse
            parsed = urlparse(pdf_url)
            if parsed.netloc != "rulebook.sama.gov.sa" or not parsed.path.startswith("/sites/default/files/"):
                continue

            file_path = download_pdf(pdf_url, url)
            if not file_path:
                # download_pdf already logged the error; skip this PDF
                continue

            PROCESSED_PDF_URLS.add(pdf_url)
            filename = os.path.basename(file_path)
            print(f"✓ Downloaded: {filename}")

            # Append metadata row for this PDF
            append_metadata_row(
                source_url=url,
                pdf_url=pdf_url,
                filename=filename,
                page_title=page_title,
            )

        # Collect inner Banking Sector links on this page
        child_links = []
        try:
            link_elements = await page.query_selector_all('a[href^="/en/"]')
        except Exception as e:
            # Playwright edge case on some pages: skip child links there
            print(f"Skipping child link discovery on {url}: {e}")
            return child_links

        for el in link_elements:
            href = await el.get_attribute("href")
            if not href:
                continue
            if href.startswith("/en/"):
                full = urljoin("https://rulebook.sama.gov.sa", href)
                if full != url and full not in child_links:
                    child_links.append(full)

        return child_links

    except Exception as e:
        print(f"Error crawling {url}: {e}")
        raise


async def main():
    """Main crawling function"""
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        
        try:
            print("Finding Banking Sector pages...")
            start_links = await get_banking_sector_links(page)
            print(f"Found {len(start_links)} top-level pages\n")

            to_visit = list(start_links)
            visited = set()
            count = 0

            while to_visit:
                url = to_visit.pop(0)
                if url in visited:
                    continue
                visited.add(url)
                count += 1
                print(f"[{count}] Crawling: {url}")

                child_links = await crawl_page(page, url)

                for child in child_links:
                    if child not in visited and child not in to_visit:
                        to_visit.append(child)

            print(f"\n✓ Completed! PDFs saved to: {PDF_STORAGE_DIR}")
            
        except Exception as e:
            print(f"\n✗ Error: {e}")
            raise
        finally:
            await browser.close()


if __name__ == "__main__":
    asyncio.run(main())
