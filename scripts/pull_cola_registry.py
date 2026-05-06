"""Drive agent-browser to pull TTB Public COLA Registry label images.

CC0 source per data.gov 015-TTB-54. Same-origin fetch via agent-browser
sidesteps the venv's SSL CA-bundle gap. Saves the front label image and
captures application metadata under fixtures/_corpus/cola-{ttbid}/.
"""
from __future__ import annotations

import base64
import json
import re
import subprocess
import sys
import time
from pathlib import Path

CORPUS_ROOT = Path("/home/context/olorin/projects/takehome-e8backend/fixtures/_corpus")
CORPUS_ROOT.mkdir(parents=True, exist_ok=True)

DETAIL_URL = "https://www.ttbonline.gov/colasonline/viewColaDetails.do?action=publicFormDisplay&ttbid={ttbid}"


def ab(*args: str, stdin: str | None = None, timeout: int = 60) -> str:
    proc = subprocess.run(
        ["agent-browser", *args],
        input=stdin,
        capture_output=True,
        text=True,
        timeout=timeout,
    )
    if proc.returncode != 0:
        raise RuntimeError(f"agent-browser failed: {proc.stderr}\nstdout: {proc.stdout}")
    return proc.stdout


def ab_run_js(js: str, timeout: int = 60) -> str:
    """Run agent-browser eval-subcommand and return JS return value as Python str."""
    out = ab("eval", "--stdin", stdin=js, timeout=timeout)
    lines = [ln for ln in out.splitlines() if ln.strip()]
    if not lines:
        raise RuntimeError(f"empty agent-browser output: {out!r}")
    last = lines[-1]
    if last.startswith('"') and last.endswith('"'):
        return json.loads(last)
    return last


def fetch_detail_metadata(ttbid: str) -> dict:
    ab("open", DETAIL_URL.format(ttbid=ttbid), timeout=45)
    ab("wait", "--load", "networkidle", timeout=45)
    js = r"""
(() => {
  const txt = document.body.innerText;
  // Numbered TTB form fields: "<num>. <LABEL> (notes)\n<value>".
  // If value-line itself looks like the next numbered field, the field is empty.
  const grab = (label) => {
    const re = new RegExp('\\d+[a-z]?\\.\\s*' + label.replace(/\//g, '\\/') + '[^\\n]*\\n([^\\n]+)');
    const m = txt.match(re);
    if (!m) return null;
    const v = m[1].trim();
    if (/^\d+[a-z]?\.\s+[A-Z][A-Z]/.test(v)) return null;
    return v || null;
  };
  const ctMatch = txt.match(/\bCT\b[\s\n]+(\d+)/);
  const orMatch = txt.match(/\bOR\b[\s\n]+(\d+)/);
  const imgs = Array.from(document.querySelectorAll('img'))
    .filter(i => i.src.includes('publicViewAttachment'))
    .map(i => ({src: i.src, alt: i.alt || '', w: i.naturalWidth, h: i.naturalHeight}));
  const front = imgs.find(i => /front|brand/i.test(i.alt)) || imgs[0] || null;
  return JSON.stringify({
    ttbid: location.search.match(/ttbid=(\d+)/)?.[1] || null,
    brand: grab('BRAND NAME'),
    fancyName: grab('FANCIFUL NAME'),
    classType: ctMatch?.[1] || null,
    abv: grab('ALCOHOL CONTENT'),
    netContents: grab('NET CONTENTS'),
    origin: orMatch?.[1] || null,
    permitNo: grab('PLANT REGISTRY'),
    serialNumber: grab('SERIAL NUMBER'),
    approvalDate: grab('DATE ISSUED'),
    allLabelImages: imgs,
    frontLabelImage: front
  });
})()
"""
    raw = ab_run_js(js, timeout=45)
    return json.loads(raw)


def fetch_image_bytes(image_url: str, ttbid: str) -> bytes:
    js = f"""
(async () => {{
  const r = await fetch({json.dumps(image_url)}, {{credentials: 'include'}});
  if (!r.ok) return JSON.stringify({{error: 'http ' + r.status}});
  const buf = await r.arrayBuffer();
  const bytes = new Uint8Array(buf);
  let bin = '';
  const chunk = 0x8000;
  for (let i = 0; i < bytes.length; i += chunk) bin += String.fromCharCode.apply(null, bytes.subarray(i, i + chunk));
  return btoa(bin);
}})()
"""
    out = ab_run_js(js, timeout=60)
    if out.startswith('{'):
        raise RuntimeError(f"image fetch failed for ttbid={ttbid}: {out}")
    return base64.b64decode(out)


def save_label(ttbid: str, meta: dict, image_bytes: bytes) -> Path:
    target = CORPUS_ROOT / f"cola-{ttbid}"
    target.mkdir(parents=True, exist_ok=True)
    img_path = target / "label.jpg"
    img_path.write_bytes(image_bytes)
    meta_path = target / "registry_metadata.json"
    meta_path.write_text(json.dumps(meta, indent=2, ensure_ascii=False))
    prov_path = target / "provenance.txt"
    prov_path.write_text(
        f"source: TTB Public COLA Registry (CC0; data.gov 015-TTB-54)\n"
        f"ttbid: {ttbid}\n"
        f"detail_url: {DETAIL_URL.format(ttbid=ttbid)}\n"
        f"image_url: {meta.get('frontLabelImage', {}).get('src', 'unknown')}\n"
        f"fetched_at: {time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())}\n"
    )
    return img_path


def pull_one(ttbid: str) -> dict:
    print(f"\n=== {ttbid} ===", flush=True)
    meta = fetch_detail_metadata(ttbid)
    front = meta.get("frontLabelImage")
    if not front or not front.get("src"):
        return {"ttbid": ttbid, "ok": False, "err": "no front label image"}
    img_bytes = fetch_image_bytes(front["src"], ttbid)
    img_path = save_label(ttbid, meta, img_bytes)
    rel = img_path.relative_to(CORPUS_ROOT.parent.parent)
    print(f"  saved {len(img_bytes)} bytes to {rel}", flush=True)
    print(f"  brand={meta.get('brand')!r} class={meta.get('classType')!r}", flush=True)
    return {"ttbid": ttbid, "ok": True, "bytes": len(img_bytes), "brand": meta.get("brand")}


def main(ids: list[str]) -> None:
    results = []
    for ttbid in ids:
        try:
            results.append(pull_one(ttbid))
        except Exception as e:
            results.append({"ttbid": ttbid, "ok": False, "err": str(e)})
            print(f"  ERROR: {e}", flush=True)
        time.sleep(1.5)
    print("\n=== summary ===")
    ok = sum(1 for r in results if r.get("ok"))
    print(f"{ok}/{len(results)} pulled")
    for r in results:
        if not r.get("ok"):
            print(f"  FAIL {r['ttbid']}: {r.get('err')}")


if __name__ == "__main__":
    ids = sys.argv[1:] or ["13231001000240"]
    main(ids)
