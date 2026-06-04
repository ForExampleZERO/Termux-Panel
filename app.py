from flask import Flask, render_template, request, jsonify, send_from_directory
import subprocess
import re
import os
import json
import time

app = Flask(__name__)

PKGDB_PATH = os.path.join(os.path.dirname(__file__), "static", "pkgdb.json")

# ─── helpers ───────────────────────────────────────────

def run(cmd):
    return subprocess.getoutput(cmd)


def get_packages():
    """Returns sorted list of {name, version, size}"""
    raw = run("dpkg-query -W -f='${Package}\t${Version}\t${Installed-Size}\n' 2>/dev/null")
    pkgs = []
    for line in raw.splitlines():
        parts = line.split('\t')
        if len(parts) >= 3:
            name = parts[0].strip()
            version = parts[1].strip() or "unknown"
            try:
                size_kb = int(parts[2].strip())
                size = f"{size_kb // 1024} MB" if size_kb >= 1024 else f"{size_kb} KB"
            except:
                size = "?"
            pkgs.append({"name": name, "version": version, "size": size})

    # fallback اگه dpkg-query نبود
    if not pkgs:
        raw2 = run("pkg list-installed 2>/dev/null")
        for line in raw2.splitlines():
            if "/" in line:
                parts = line.split("/")
                name = parts[0].strip()
                ver = parts[1].strip().split(" ")[0] if len(parts) > 1 else "?"
                pkgs.append({"name": name, "version": ver, "size": "?"})

    return sorted(pkgs, key=lambda x: x["name"])


def system_info():
    cpu = run("nproc").strip()
    try:
        mem = run("free -m").splitlines()[1].split()
        ram_total = round(int(mem[1]) / 1024, 2)
        ram_used  = round(int(mem[2]) / 1024, 2)
        ram_pct   = int((ram_used / ram_total) * 100) if ram_total else 0
    except:
        ram_total = ram_used = ram_pct = 0

    try:
        disk = run("df -h /data").splitlines()[1].split()
        storage  = disk[1]
        used     = disk[2]
        disk_pct = int(disk[4].replace('%', ''))
    except:
        storage = used = "?"
        disk_pct = 0

    uptime = run("uptime -p").strip().replace("up ", "")

    return {
        "cpu": cpu,
        "ram_total": ram_total, "ram_used": ram_used, "ram_pct": ram_pct,
        "storage": storage, "used": used, "disk_pct": disk_pct,
        "uptime": uptime,
    }


def pkgdb_meta():
    """Returns metadata of local pkgdb (count, updated_at) or None."""
    if not os.path.exists(PKGDB_PATH):
        return None
    try:
        with open(PKGDB_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
        ts = data.get("updated_at", 0)
        updated = time.strftime("%Y-%m-%d", time.localtime(ts)) if ts else "?"
        return {"count": data.get("count", 0), "updated": updated}
    except:
        return None

# ─── routes ────────────────────────────────────────────

@app.route("/")
def home():
    return render_template(
        "index.html",
        pkgs=get_packages(),
        sys=system_info(),
        pkgdb=pkgdb_meta(),
    )


@app.route("/pkgdb.json")
def serve_pkgdb():
    """فایل pkgdb.json رو از پوشه static سرو میکنه"""
    if not os.path.exists(PKGDB_PATH):
        return jsonify({"error": "pkgdb not found. run: python update_pkgdb.py"}), 404
    return send_from_directory(
        os.path.join(os.path.dirname(__file__), "static"),
        "pkgdb.json",
        mimetype="application/json"
    )


@app.route("/remove", methods=["POST"])
def remove():
    pkg = request.json.get("pkg", "").strip()
    if not pkg or not re.match(r'^[a-zA-Z0-9_\-\+\.]+$', pkg):
        return jsonify({"ok": False, "error": "invalid package name"})
    run(f"pkg uninstall -y {pkg}")
    return jsonify({"ok": True})


@app.route("/update", methods=["POST"])
def update():
    pkg = request.json.get("pkg", "").strip()
    if not pkg or not re.match(r'^[a-zA-Z0-9_\-\+\.]+$', pkg):
        return jsonify({"ok": False, "error": "invalid package name"})
    run(f"pkg upgrade -y {pkg}")
    return jsonify({"ok": True})


@app.route("/install", methods=["POST"])
def install():
    pkg = request.json.get("pkg", "").strip()
    if not pkg or not re.match(r'^[a-zA-Z0-9_\-\+\.]+$', pkg):
        return jsonify({"ok": False, "error": "invalid package name"})
    out = run(f"pkg install -y {pkg}")
    return jsonify({"ok": True, "output": out[-300:]})


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=8080, debug=True)
