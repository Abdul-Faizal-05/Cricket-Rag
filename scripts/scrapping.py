import requests
from bs4 import BeautifulSoup
import re

url = "https://en.wikipedia.org/wiki/2025_Indian_Premier_League"
headers = {"User-Agent": "Mozilla/5.0"}

response = requests.get(url, headers=headers)
soup = BeautifulSoup(response.text, "html.parser")

# ── Remove all unwanted tags ──────────────────────────────────────────────────
UNWANTED_TAGS = [
    "script", "style",       # code / CSS
    "sup",                   # footnote numbers like [1], [2]
    "table",                 # raw data tables
    "figure", "figcaption",  # images and captions
    "nav", "footer",         # site navigation
    "aside",                 # sidebar boxes
    ".mw-editsection",       # [edit] links
    ".navbox",               # Wikipedia navboxes at the bottom
    ".reflist", ".references",  # References section
    ".hatnote",              # "For other uses, see …" notes
    ".mw-references-wrap",
]

for selector in UNWANTED_TAGS:
    if selector.startswith("."):
        for tag in soup.select(selector):
            tag.decompose()
    else:
        for tag in soup.find_all(selector):
            tag.decompose()

# ── Extract only the article body ─────────────────────────────────────────────
content_div = soup.find("div", {"id": "mw-content-text"})
text = content_div.get_text(separator="\n") if content_div else soup.get_text(separator="\n")

# ── Clean the extracted text ──────────────────────────────────────────────────
lines = []
for line in text.splitlines():
    line = line.strip()

    if not line:                              # skip blank lines
        continue
    if re.fullmatch(r"\[\d+\]", line):        # skip lone citation markers [1]
        continue
    if re.fullmatch(r"[|\-\s]+", line):      # skip table-border artifacts
        continue
    if len(line) < 3:                         # skip stray single characters
        continue
    if re.match(r"^\^", line):               # skip reference back-links (^)
        continue
    if re.match(r"^Retrieved from", line):   # skip "Retrieved from …" footer line
        continue
    if re.match(r"^https:",line):
        continue

    # Remove inline citation clusters like [1][2][3]
    line = re.sub(r"(\[\d+\])+", "", line).strip()

    if line:
        lines.append(line)

# Join lines, adding a blank line after each one (one space between paragraphs)
clean_text = "\n\n".join(lines)
# Collapse any accidental 3+ newlines down to exactly two
clean_text = re.sub(r"\n{3,}", "\n\n", clean_text)

# ── Save ──────────────────────────────────────────────────────────────────────
output_path = "ipl_2025.txt"
with open(output_path, "w", encoding="utf-8") as f:
    f.write(clean_text)

print(f"Saved as {output_path}  ({len(lines)} lines, {len(clean_text):,} characters)")

# Preview first 30 lines
print("\n── Preview (first 30 lines) ──")
print("\n".join(lines[:30]))
