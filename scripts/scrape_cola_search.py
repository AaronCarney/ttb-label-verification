"""Walk paginated TTB Public COLA Registry search results.

Submits a class-141 BOURBON search across the requested date range, then walks
"Next >" pages collecting the visible result table per page.

Output: JSONL at fixtures/_corpus/_search-{class}-{from}-{to}.jsonl
        one row per record with ttbid + brand + permit + origin + class fields.

The Basic Search caps at 1000 records per query; for >1000 results, narrow the
date range and re-run.
"""
from __future__ import annotations

import argparse
import json
import subprocess
import time
from pathlib import Path

CORPUS_ROOT = Path("/home/context/olorin/projects/takehome-e8backend/fixtures/_corpus")
SEARCH_URL = "https://www.ttbonline.gov/colasonline/publicSearchColasBasic.do"


def ab(*args: str, stdin: str | None = None, timeout: int = 60) -> str:
    proc = subprocess.run(
        ["agent-browser", *args], input=stdin, capture_output=True, text=True, timeout=timeout
    )
    if proc.returncode != 0:
        raise RuntimeError(f"agent-browser failed: {proc.stderr}\nstdout: {proc.stdout}")
    return proc.stdout


def ab_run_js(js: str, timeout: int = 60) -> str:
    out = ab("eval", "--stdin", stdin=js, timeout=timeout)
    lines = [ln for ln in out.splitlines() if ln.strip()]
    if not lines:
        raise RuntimeError(f"empty output: {out!r}")
    last = lines[-1]
    if last.startswith('"') and last.endswith('"'):
        return json.loads(last)
    return last


PAGE_PARSE_JS = r"""
(() => {
  const rows = [];
  const links = Array.from(document.querySelectorAll('a[href*="ttbid="]'));
  for (const a of links) {
    const m = a.href.match(/ttbid=(\d+)/);
    if (!m) continue;
    const ttbid = m[1];
    const tr = a.closest('tr');
    if (!tr) continue;
    const cells = Array.from(tr.querySelectorAll('td')).map(td => td.innerText.trim());
    rows.push({ttbid, cells});
  }
  const seen = new Set();
  const uniq = [];
  for (const r of rows) {
    if (seen.has(r.ttbid)) continue;
    seen.add(r.ttbid);
    uniq.push(r);
  }
  const bodyText = document.body.innerText;
  const summaryMatch = bodyText.match(/(\d+) to (\d+) of (\d+)[^(]*(?:\(Total Matching Records:\s*(\d+)\))?/);
  const summary = summaryMatch ? {
    fromIdx: +summaryMatch[1], toIdx: +summaryMatch[2],
    pageOf: +summaryMatch[3], total: summaryMatch[4] ? +summaryMatch[4] : +summaryMatch[3],
  } : null;
  const hasNext = Array.from(document.querySelectorAll('a')).some(a => /Next\s*>/i.test(a.textContent));
  return JSON.stringify({rows: uniq, summary, hasNext});
})()
"""


COL_NAMES = [
    "ttbid", "permit_no", "serial_number", "completed_date",
    "fanciful_name", "brand_name", "origin_code", "origin_desc",
    "class_type", "class_type_desc",
]


def normalize_row(raw: dict) -> dict:
    cells = raw["cells"]
    out = {"ttbid": raw["ttbid"]}
    for i, name in enumerate(COL_NAMES[1:], start=1):
        out[name] = cells[i] if i < len(cells) else ""
    return out


def submit_search(date_from: str, date_to: str, class_from: str, class_to: str) -> None:
    ab("open", SEARCH_URL, timeout=45)
    ab("wait", "--load", "networkidle", timeout=45)
    ab("fill", 'input[name="searchCriteria.dateCompletedFrom"]', date_from, timeout=20)
    ab("fill", 'input[name="searchCriteria.dateCompletedTo"]', date_to, timeout=20)
    ab("fill", 'input[name="searchCriteria.classTypeFrom"]', class_from, timeout=20)
    ab("fill", 'input[name="searchCriteria.classTypeTo"]', class_to, timeout=20)
    ab("click", 'input[type="submit"][value="Search"]', timeout=20)
    ab("wait", "--load", "networkidle", "--timeout", "60000", timeout=70)


def click_next() -> None:
    js = r"""
    (() => {
      const link = Array.from(document.querySelectorAll('a')).find(a => /Next\s*>/i.test(a.textContent));
      if (!link) return 'NO_NEXT';
      link.click();
      return 'CLICKED';
    })()
    """
    out = ab_run_js(js, timeout=20)
    if out != 'CLICKED':
        raise RuntimeError(f"next-click failed: {out}")
    ab("wait", "--load", "networkidle", "--timeout", "60000", timeout=70)


def main(date_from: str, date_to: str, class_from: str, class_to: str) -> None:
    submit_search(date_from, date_to, class_from, class_to)

    out_path = CORPUS_ROOT / f"_search-{class_from}-{date_from.replace('/', '')}-{date_to.replace('/', '')}.jsonl"
    out_path.parent.mkdir(parents=True, exist_ok=True)

    all_rows = []
    page = 0
    while True:
        page += 1
        raw = ab_run_js(PAGE_PARSE_JS, timeout=45)
        data = json.loads(raw)
        rows = [normalize_row(r) for r in data["rows"]]
        summary = data.get("summary") or {}
        has_next = data.get("hasNext")
        all_rows.extend(rows)
        print(f"page {page}: +{len(rows)} rows (cum {len(all_rows)}); summary={summary}; hasNext={has_next}", flush=True)
        if not has_next:
            print("no Next link — done", flush=True)
            break
        click_next()
        time.sleep(0.8)

    seen = set()
    unique = []
    for r in all_rows:
        if r["ttbid"] in seen:
            continue
        seen.add(r["ttbid"])
        unique.append(r)

    with out_path.open("w") as f:
        for r in unique:
            f.write(json.dumps(r) + "\n")
    print(f"\nwrote {len(unique)} unique rows to {out_path}")


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--date-from", default="01/01/2024")
    p.add_argument("--date-to", default="05/05/2026")
    p.add_argument("--class-from", default="141")
    p.add_argument("--class-to", default="141")
    args = p.parse_args()
    main(args.date_from, args.date_to, args.class_from, args.class_to)
