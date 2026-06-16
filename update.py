import csv
import json
import re
import urllib.request
from datetime import datetime

CSV_URL = "https://www.statbureau.org/ru/russia/inflation-tables/inflation.monthly.csv"

def fetch_data():
    req = urllib.request.Request(CSV_URL, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=15) as r:
        content = r.read().decode("utf-8-sig")
    return content

def parse_csv(content):
    monthly = {}
    annual = {}
    reader = csv.reader(content.splitlines())
    rows = list(reader)

    header_idx = None
    for i, row in enumerate(rows):
        if row and any(cell.strip().lower() in ["jan", "january", "янв", "jan."] for cell in row):
            header_idx = i
            break
        if row and len(row) >= 13:
            try:
                ints = [int(c.strip()) for c in row[1:13]]
                if ints == list(range(1, 13)):
                    header_idx = i
                    break
            except:
                pass

    if header_idx is None:
        header_idx = 0

    print(f"Header row index: {header_idx}")

    for row in rows[header_idx + 1:]:
        if not row or not row[0].strip():
            continue
        try:
            year = int(str(row[0]).strip().strip('"'))
        except:
            continue

        months = []
        for i in range(1, 13):
            if i < len(row):
                raw = row[i].strip().strip('"').replace(",", ".").replace(" ", "")
                try:
                    months.append(float(raw))
                except:
                    months.append(None)
            else:
                months.append(None)

        monthly[year] = months

        vals = [m for m in months if m is not None]
        if len(row) > 13:
            raw = row[13].strip().strip('"').replace(",", ".").replace(" ", "")
            try:
                annual[year] = float(raw)
            except:
                if vals:
                    total = 1.0
                    for v in vals: total *= (1 + v / 100)
                    annual[year] = round((total - 1) * 100, 2)
        else:
            if vals:
                total = 1.0
                for v in vals: total *= (1 + v / 100)
                annual[year] = round((total - 1) * 100, 2)

    return monthly, annual

def update_html(monthly, annual):
    with open("index.html", "r", encoding="utf-8") as f:
        html = f.read()

    print(f"index.html size: {len(html)} chars")

    monthly_js = json.dumps(monthly, ensure_ascii=False, separators=(",", ":"))
    annual_js  = json.dumps(annual,  ensure_ascii=False, separators=(",", ":"))

    # Try all possible variable name variants
    monthly_patterns = [
        r"(const MONTHLY_REAL\s*=\s*)\{[\s\S]*?\}(?=;)",
        r"(const monthlyData\s*=\s*)\{[\s\S]*?\}(?=;)",
        r"(var MONTHLY_REAL\s*=\s*)\{[\s\S]*?\}(?=;)",
        r"(var monthlyData\s*=\s*)\{[\s\S]*?\}(?=;)",
    ]
    annual_patterns = [
        r"(const ANNUAL\s*=\s*)\{[\s\S]*?\}(?=;)",
        r"(const annualData\s*=\s*)\{[\s\S]*?\}(?=;)",
        r"(var ANNUAL\s*=\s*)\{[\s\S]*?\}(?=;)",
        r"(var annualData\s*=\s*)\{[\s\S]*?\}(?=;)",
    ]

    monthly_replaced = False
    for pat in monthly_patterns:
        if re.search(pat, html):
            html = re.sub(pat, r"\g<1>" + monthly_js, html, count=1)
            print(f"Monthly data replaced using pattern: {pat[:40]}")
            monthly_replaced = True
            break

    annual_replaced = False
    for pat in annual_patterns:
        if re.search(pat, html):
            html = re.sub(pat, r"\g<1>" + annual_js, html, count=1)
            print(f"Annual data replaced using pattern: {pat[:40]}")
            annual_replaced = True
            break

    if not monthly_replaced:
        print("ERROR: Could not find monthly data variable! Searching for clues...")
        for keyword in ["MONTHLY", "monthly", "monthData", "месяц"]:
            idx = html.find(keyword)
            if idx > 0:
                print(f"  Found '{keyword}' at pos {idx}: ...{html[idx:idx+80]}...")
                break

    if not annual_replaced:
        print("ERROR: Could not find annual data variable! Searching for clues...")
        for keyword in ["ANNUAL", "annual", "annualData", "годов"]:
            idx = html.find(keyword)
            if idx > 0:
                print(f"  Found '{keyword}' at pos {idx}: ...{html[idx:idx+80]}...")
                break

    # Update date in badge — try multiple patterns
    months_ru = ["января","февраля","марта","апреля","мая","июня",
                 "июля","августа","сентября","октября","ноября","декабря"]
    now = datetime.utcnow()
    date_str = f"{now.day} {months_ru[now.month-1]} {now.year} г."

    date_patterns = [
        r"document\.getElementById\('lastUpdatedLine'\)\.textContent\s*=\s*'[^']*';",
        r'document\.getElementById\("lastUpdatedLine"\)\.textContent\s*=\s*"[^"]*";',
    ]
    date_replaced = False
    for pat in date_patterns:
        if re.search(pat, html):
            html = re.sub(pat,
                f"document.getElementById('lastUpdatedLine').textContent = 'Обновлено {date_str}';",
                html, count=1)
            print(f"Date updated to: {date_str}")
            date_replaced = True
            break

    if not date_replaced:
        print(f"WARNING: Could not update date. Will show stale date.")

    with open("index.html", "w", encoding="utf-8") as f:
        f.write(html)

    print(f"index.html saved. Monthly replaced: {monthly_replaced}, Annual replaced: {annual_replaced}")
    last_year = max(monthly.keys())
    filled = len([m for m in monthly[last_year] if m is not None])
    print(f"Latest data: {last_year}, {filled} months")

if __name__ == "__main__":
    print("=== Inflation updater starting ===")
    print(f"Time: {datetime.utcnow().isoformat()}")
    print("Fetching CSV...")
    content = fetch_data()
    print(f"CSV fetched: {len(content)} chars")
    print("Parsing...")
    monthly, annual = parse_csv(content)
    print(f"Parsed: {len(monthly)} years")
    print("Updating index.html...")
    update_html(monthly, annual)
    print("=== Done ===")
