#!/usr/bin/env python3
"""
update_pkgdb.py — دانلود و ذخیره دیتابیس پکیج‌های ترموکس به صورت لوکال
اجرا: python update_pkgdb.py
"""

import urllib.request
import json
import os
import sys
import time

SOURCE_URL = "https://termux-packages.ajam.dev/pkgs.json"
OUT_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "static", "pkgdb.json")


def download():
    os.makedirs(os.path.dirname(OUT_FILE), exist_ok=True)

    print(f"[*] downloading from:\n    {SOURCE_URL}\n")
    start = time.time()

    req = urllib.request.Request(SOURCE_URL, headers={"User-Agent": "termux-panel/1.0"})

    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            raw = resp.read()
    except Exception as e:
        print(f"[!] download failed: {e}")
        sys.exit(1)

    elapsed = round(time.time() - start, 2)
    size_kb = round(len(raw) / 1024, 1)
    print(f"[+] downloaded {size_kb} KB in {elapsed}s")

    try:
        data = json.loads(raw)
    except json.JSONDecodeError as e:
        print(f"[!] invalid JSON: {e}")
        sys.exit(1)

    # ساختار واقعی: آرایه‌ای از {Package, Version, Description, Homepage}
    if isinstance(data, list):
        pkgs = data
    elif isinstance(data, dict):
        pkgs = list(data.values())
    else:
        print("[!] unexpected JSON structure")
        sys.exit(1)

    print(f"[*] raw entries: {len(pkgs)}")

    # debug: نمایش اولین آیتم برای بررسی کلیدها
    if pkgs:
        first = pkgs[0]
        print(f"[*] sample keys: {list(first.keys()) if isinstance(first, dict) else type(first)}")

    cleaned = []
    for p in pkgs:
        if not isinstance(p, dict):
            continue

        # کلیدها ممکنه Capital باشن یا lowercase — هر دو رو چک میکنیم
        name = (
            p.get("Package") or p.get("package") or
            p.get("Name") or p.get("name") or
            p.get("pkg") or ""
        ).strip()

        if not name:
            continue

        version = (
            p.get("Version") or p.get("version") or ""
        ).strip()

        description = (
            p.get("Description") or p.get("description") or
            p.get("desc") or ""
        ).strip()

        homepage = (
            p.get("Homepage") or p.get("homepage") or
            p.get("url") or ""
        ).strip()

        cleaned.append({
            "name":        name,
            "version":     version,
            "description": description,
            "homepage":    homepage,
        })

    cleaned.sort(key=lambda x: x["name"].lower())

    output = {
        "updated_at": int(time.time()),
        "count":      len(cleaned),
        "packages":   cleaned,
    }

    with open(OUT_FILE, "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, separators=(",", ":"))

    final_kb = round(os.path.getsize(OUT_FILE) / 1024, 1)
    print(f"[+] saved {len(cleaned)} packages → {OUT_FILE} ({final_kb} KB)")
    print(f"\n[✓] done. run 'python app.py' to start the panel.")


if __name__ == "__main__":
    download()
