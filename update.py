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

    data_rows = rows[header_idx + 1:]

    for row in data_rows:
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
                    for v in vals:
                        total *= (1 + v / 100)
                    annual[year] = round((total - 1) * 100, 2)
        else:
            if vals:
                total = 1.0
                for v in vals:
                    total *= (1 + v / 100)
                annual[year] = round((total - 1) * 100, 2)

    return monthly, annual

def update_html(monthly, annual):
    with open("index.html", "r", encoding="utf-8") as f:
        html = f.read()

    # Keys used in the current index.html
    monthly_js = json.dumps(monthly, ensure_ascii=False, separators=(",", ":"))
    annual_js  = json.dumps(annual,  ensure_ascii=False, separators=(",", ":"))

    # Update MONTHLY_REAL (current variable name in index.html)
    html = re.sub(
        r"(const MONTHLY_REAL\s*=\s*)\{[\s\S]*?\}(?=;)",
        r"\g<1>" + monthly_js,
        html, count=1
    )

    # Update ANNUAL (current variable name in index.html)
    html = re.sub(
        r"(const ANNUAL\s*=\s*)\{[\s\S]*?\}(?=;)",
        r"\g<1>" + annual_js,
        html, count=1
    )

    # Update real update date in the badge
    # Format: "16 июня 2026 г."
    months_ru = ["января","февраля","марта","апреля","мая","июня",
                 "июля","августа","сентября","октября","ноября","декабря"]
    now = datetime.utcnow()
    date_str = f"{now.day} {months_ru[now.month-1]} {now.year} г."

    # Replace the static date placeholder in the JS date calculation block
    # We inject a data attribute so JS can read the real date
    html = re.sub(
        r"(document\.getElementById\('lastUpdatedLine'\)\.textContent\s*=\s*)'Обновлено: —'",
        r"\1'Обновлено: —'",
        html, count=1
    )

    # Simpler: replace the entire lastUpdatedLine init with a hardcoded real date
    html = re.sub(
        r"document\.getElementById\('lastUpdatedLine'\)\.textContent\s*=\s*'Обновлено[^']*';",
        f"document.getElementById('lastUpdatedLine').textContent = 'Обновлено {date_str}';",
        html, count=1
    )

    with open("index.html", "w", encoding="utf-8") as f:
        f.write(html)

    last_year = max(monthly.keys())
    last_months = [m for m in monthly[last_year] if m is not None]
    print(f"Updated: {len(monthly)} years, latest {last_year} — {len(last_months)} months filled")
    print(f"Date set to: {date_str}")

if __name__ == "__main__":
    print("Fetching data from statbureau.org...")
    content = fetch_data()
    print("Parsing CSV...")
    monthly, annual = parse_csv(content)
    print("Updating index.html...")
    update_html(monthly, annual)
    print("Done.")
