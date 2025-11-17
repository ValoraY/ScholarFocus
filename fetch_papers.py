import json
from scholarly import scholarly
import traceback
import requests
from bs4 import BeautifulSoup
import html
import os
from datetime import datetime

# -----------------------------------
# Logging Helpers
# -----------------------------------
def info(msg):    print(f"\033[94m[INFO]\033[0m {msg}")
def success(msg): print(f"\033[92m[SUCCESS]\033[0m {msg}")
def warn(msg):    print(f"\033[93m[WARN]\033[0m {msg}")
def error(msg):   print(f"\033[91m[ERROR]\033[0m {msg}")

# ================================================================
# 1. Load Minimal config.json
# ================================================================
info("Loading config.json ...")

with open("config.json", "r", encoding="utf-8") as f:
    cfg = json.load(f)

# Required fields (override by GitHub Actions if config_override.json exists)
YEAR_START = cfg.get("year_start", 2020)
YEAR_END = datetime.now().year
AUTHORS = cfg.get("authors", [])
INCREMENTAL_LIMIT = cfg.get("incremental_limit", 20)

# ================================================================
# 2. Load GitHub override (optional)
# ================================================================
if os.path.exists("config_override.json"):
    info("Loading config_override.json ...")
    with open("config_override.json", "r", encoding="utf-8") as f:
        override = json.load(f)

    YEAR_START = override.get("year_start", YEAR_START)
    YEAR_END = override.get("year_end", YEAR_END)
    AUTHORS = override.get("authors", AUTHORS)
    INCREMENTAL_LIMIT = override.get("incremental_limit", INCREMENTAL_LIMIT)

info("Final Config:")
info(f"  YEAR_START = {YEAR_START}")
info(f"  YEAR_END   = {YEAR_END}")
info(f"  AUTHORS    = {AUTHORS}")
info(f"  INCREMENTAL_LIMIT = {INCREMENTAL_LIMIT}")

# ================================================================
# 3. Hard-coded defaults (NO complex config anymore)
# ================================================================
DATA_DIR = "data/json"
AUTHOR_MD_DIR = "data/authors"
ALL_MD_FILE = "data/all_papers.md"

MAX_PAPERS_PER_AUTHOR = 200      # Hardcoded default
ENABLE_INCREMENTAL_MODE = True   # Hardcoded default
ENABLE_TRUNCATED_CHECK = True    # Hardcoded default
USE_ARXIV = True                 # Hardcoded default

# Ensure directories exist
os.makedirs("data", exist_ok=True)
os.makedirs(DATA_DIR, exist_ok=True)
os.makedirs(AUTHOR_MD_DIR, exist_ok=True)

# ================================================================
# Helper functions
# ================================================================
def is_truncated(abs_text):
    if not abs_text:
        return False
    return abs_text.strip().endswith("...") or abs_text.strip().endswith("…")

def clean_html(raw):
    if not raw:
        return raw
    clean = BeautifulSoup(raw, "html.parser").get_text()
    clean = html.unescape(clean).strip()
    return clean

def load_state(author_id, author_name):
    safe = author_name.replace(" ", "").replace("/", "_")
    path = os.path.join(DATA_DIR, f"{safe}_{author_id}.json")
    if not os.path.exists(path):
        return []
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)

def save_state(author_id, author_name, papers):
    safe = author_name.replace(" ", "").replace("/", "_")
    path = os.path.join(DATA_DIR, f"{safe}_{author_id}.json")
    papers = sorted(papers, key=lambda x: x["year"], reverse=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(papers, f, indent=2, ensure_ascii=False)

# ================================================================
# Full abstract only for arXiv
# ================================================================
def fetch_arxiv_abstract(url):
    try:
        paper_id = url.split("/")[-1]
        api = f"https://export.arxiv.org/api/query?id_list={paper_id}"
        r = requests.get(api, timeout=10)
        xml = r.text
        s = xml.find("<summary>") + len("<summary>")
        e = xml.find("</summary>")
        summary = xml[s:e].strip()
        return clean_html(summary)
    except:
        return None

def fetch_full_abstract(url, fallback_abs):
    if not ENABLE_TRUNCATED_CHECK or not is_truncated(fallback_abs):
        return fallback_abs

    info("Truncated abstract detected. Checking arXiv...")

    if USE_ARXIV and "arxiv.org" in url:
        full = fetch_arxiv_abstract(url)
        if full:
            info("Full arXiv abstract retrieved.")
            return full

    warn("Full abstract not found, using shortened version.")
    return fallback_abs

# ================================================================
# Fetch papers
# ================================================================
def fetch_author_papers(author_id, author_name):
    state = load_state(author_id, author_name)
    is_first = (len(state) == 0)

    info(f"Fetching papers for: {author_name}")

    author = scholarly.search_author_id(author_id)
    author = scholarly.fill(author, sections=["publications"])

    papers = author["publications"]
    total = len(papers)
    info(f"Total papers found: {total}")

    # Limit
    papers = papers[:MAX_PAPERS_PER_AUTHOR]

    if not is_first and ENABLE_INCREMENTAL_MODE:
        papers = papers[:INCREMENTAL_LIMIT]
        info(f"Incremental mode enabled: checking top {INCREMENTAL_LIMIT} papers")

    existing_titles = {p["title"] for p in state}
    new_results = []

    for idx, pub in enumerate(papers, 1):
        info(f" ({idx}/{len(papers)}) loading paper details...")

        try:
            pub_filled = scholarly.fill(pub)
            bib = pub_filled.get("bib", {})

            year_raw = bib.get("pub_year")
            if not year_raw:
                continue
            try:
                year = int(year_raw)
            except:
                continue

            if not (YEAR_START <= year <= YEAR_END):
                continue

            title = bib.get("title", "Unknown Title")
            info(f" → {title}")

            short_abs = bib.get("abstract", "")
            link = pub_filled.get("pub_url", "")

            if not is_first and title in existing_titles:
                info("   Already exists. Skipped.")
                continue

            abstract = fetch_full_abstract(link, short_abs)

            new_results.append({
                "year": year,
                "title": title,
                "abstract": abstract,
                "link": link
            })

        except Exception:
            warn("Failed to load paper:")
            warn(traceback.format_exc())
            continue

    merged = state + new_results

    # Deduplicate
    seen = set()
    final = []
    for p in merged:
        if p["title"] not in seen:
            final.append(p)
            seen.add(p["title"])

    save_state(author_id, author_name, final)
    success(f"Added {len(new_results)} new papers. Total stored: {len(final)}")

    return final

# ================================================================
# Markdown
# ================================================================
def generate_md(author_name, papers):
    md = f"## {author_name} Papers ({YEAR_START}-{YEAR_END})\n\n"
    md += "| Year | Title | Abstract | Link |\n"
    md += "|------|-------|----------|------|\n"

    for p in papers:
        abs_clean = p["abstract"].replace("\n", " ")
        md += f"| {p['year']} | {p['title']} | {abs_clean} | [Link]({p['link']}) |\n"

    md += "\n"
    return md

# ================================================================
# Main
# ================================================================
def main():
    info("Starting fetch_papers.py ...")
    info("README.md will NOT be touched. Output is in /data/...")

    all_md = "# All Scholars Paper Collection\n\n"

    for author in AUTHORS:
        name = author["name"]
        author_id = author["id"]

        info("="*60)
        info(f"Processing: {name}")
        info("="*60)

        papers = fetch_author_papers(author_id, name)
        papers = [p for p in papers if YEAR_START <= p["year"] <= YEAR_END]
        papers.sort(key=lambda x: x["year"], reverse=True)

        # Individual MD
        safe_name = name.replace(" ", "").replace("/", "_")
        md_path = os.path.join(AUTHOR_MD_DIR, f"{safe_name}.md")

        with open(md_path, "w", encoding="utf-8") as f:
            f.write(generate_md(name, papers))

        success(f"Saved: {md_path}")

        all_md += generate_md(name, papers)

    # Global MD
    with open(ALL_MD_FILE, "w", encoding="utf-8") as f:
        f.write(all_md)

    success(f"Saved global MD: {ALL_MD_FILE}")
    success("🎉 All done!")

if __name__ == "__main__":
    main()
