import json
from pathlib import Path

import requests
from bs4 import BeautifulSoup


URL = "https://rulebook.sama.gov.sa/en/banking-sector-0"


def fetch_page(url: str) -> str:
  """Download HTML of the SAMA Banking Sector page."""
  response = requests.get(
    url,
    timeout=15,
    headers={"User-Agent": "IOTA-RegTechAI-Test-Script/1.0"},
  )
  response.raise_for_status()
  return response.text


def extract_banking_sections(html: str) -> list[str]:
  """Parse the HTML and extract the list of Banking Sector subsections."""
  soup = BeautifulSoup(html, "html.parser")

  # Find the <li> that contains the current "Banking Sector" navigation item
  nav_li = soup.select_one(
    "li.menu-item.menu-item--expanded.menu-item--active-trail"
  )
  if nav_li is None:
    raise RuntimeError("Could not find Banking Sector navigation <li> on the page.")

  # Inside that <li>, there is a nested <ul class=\"menu\"> with all subsection links
  ul = nav_li.find("ul", class_="menu")
  if ul is None:
    raise RuntimeError("Could not find nested <ul class='menu'> with Banking Sector sections.")

  sections: list[str] = []
  for a in ul.find_all("a", href=True):
    text = a.get_text(strip=True)
    if not text:
      continue
    # Skip the parent "Banking Sector" link if it ever appears here
    if text == "Banking Sector":
      continue
    # Clean any trailing "›" characters if present
    cleaned = text.rstrip("›").strip()
    sections.append(cleaned)

  # Deduplicate while preserving order
  seen: set[str] = set()
  unique_sections: list[str] = []
  for section in sections:
    if section not in seen:
      seen.add(section)
      unique_sections.append(section)

  return unique_sections


def generate_questions(sections: list[str]) -> list[dict]:
  """Turn the extracted section titles into simple QA pairs."""
  questions: list[dict] = []

  if sections:
    questions.append(
      {
        "id": "sama-banking-1",
        "source_url": URL,
        "question": "What are the main categories under the Banking Sector in the SAMA Rulebook?",
        "answer": "; ".join(sections),
      }
    )

  for index, name in enumerate(sections, start=2):
    base_id = f"sama-banking-{index}"

    questions.append(
      {
        "id": f"{base_id}-which-section",
        "source_url": URL,
        "question": f"Which SAMA Rulebook Banking Sector category covers {name}?",
        "answer": f"The '{name}' category under the Banking Sector in the SAMA Rulebook.",
      }
    )

    questions.append(
      {
        "id": f"{base_id}-list-with-highlight",
        "source_url": URL,
        "question": "List the Banking Sector categories in the SAMA Rulebook and include the one related to "
        f"{name}.",
        "answer": "The Banking Sector categories are: " + "; ".join(sections),
      }
    )

  return questions


def main() -> None:
  html = fetch_page(URL)
  sections = extract_banking_sections(html)
  print(f"Extracted sections ({len(sections)}): {sections}")

  questions = generate_questions(sections)
  print(f"Generated {len(questions)} questions.")

  # Save alongside other datasets
  datasets_dir = Path(__file__).resolve().parents[1] / "datasets"
  datasets_dir.mkdir(parents=True, exist_ok=True)
  out_path = datasets_dir / "sama_banking_questions.json"

  with out_path.open("w", encoding="utf-8") as file:
    json.dump(questions, file, ensure_ascii=False, indent=2)

  print(f"Saved questions to {out_path}")


if __name__ == "__main__":
  main()

