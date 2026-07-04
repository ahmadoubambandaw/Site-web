#!/usr/bin/env python3
"""
ViralCut - interface web.

Lance le serveur puis ouvre http://localhost:5000 :
    python3 app.py

Tu deposes ta video, tu choisis ton accroche, et tu recuperes le montage
TikTok pret a poster.
"""

import os
import threading
import time
import uuid

from flask import (Flask, jsonify, render_template, request, send_file,
                   url_for)
from werkzeug.utils import secure_filename

import viralcut

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
JOBS_DIR = os.path.join(BASE_DIR, "jobs")
os.makedirs(JOBS_DIR, exist_ok=True)

ALLOWED_EXT = {".mp4", ".mov", ".mkv", ".avi", ".webm", ".m4v"}
MUSIC_EXT = {".mp3", ".m4a", ".aac", ".wav", ".ogg", ".flac"}

app = Flask(__name__)
app.config["MAX_CONTENT_LENGTH"] = 2 * 1024 * 1024 * 1024  # 2 Go

jobs = {}
jobs_lock = threading.Lock()


def set_status(job_id, **fields):
    with jobs_lock:
        jobs[job_id].update(fields)


def run_job(job_id, src, out, opts):
    def progress(msg):
        set_status(job_id, message=str(msg))

    try:
        viralcut.make_viral(
            src, out,
            target_duration=opts["duration"],
            hook=opts["hook"],
            handle=opts["handle"],
            music=opts["music"],
            punch_zoom=opts["punch_zoom"],
            progress=progress,
        )
        set_status(job_id, state="done",
                   message="Montage termine ! Ta video est prete.")
    except Exception as exc:  # montre l'erreur a l'utilisateur
        set_status(job_id, state="error", message=f"Erreur : {exc}")
    finally:
        if os.path.exists(src):
            os.remove(src)
        music = opts["music"]
        if music and os.path.exists(music):
            os.remove(music)


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/upload", methods=["POST"])
def upload():
    video = request.files.get("video")
    if not video or not video.filename:
        return jsonify(error="Aucune video recue."), 400
    ext = os.path.splitext(video.filename)[1].lower()
    if ext not in ALLOWED_EXT:
        return jsonify(error=f"Format non supporte ({ext}). "
                             "Utilise mp4, mov, mkv, avi ou webm."), 400

    job_id = uuid.uuid4().hex[:12]
    job_dir = os.path.join(JOBS_DIR, job_id)
    os.makedirs(job_dir, exist_ok=True)
    src = os.path.join(job_dir, "source" + ext)
    video.save(src)

    music_path = None
    music = request.files.get("music")
    if music and music.filename:
        mext = os.path.splitext(music.filename)[1].lower()
        if mext in MUSIC_EXT:
            music_path = os.path.join(job_dir, "music" + mext)
            music.save(music_path)

    try:
        duration = min(120.0, max(10.0, float(request.form.get("duration", 30))))
    except ValueError:
        duration = 30.0

    opts = {
        "duration": duration,
        "hook": request.form.get("hook", "").strip()[:120].replace("|", "\n"),
        "handle": request.form.get("handle", "").strip()[:40],
        "music": music_path,
        "punch_zoom": request.form.get("zoom", "on") == "on",
    }
    out = os.path.join(job_dir, "viral.mp4")

    with jobs_lock:
        jobs[job_id] = {"state": "processing",
                        "message": "Video recue, analyse en cours...",
                        "output": out, "created": time.time(),
                        "name": secure_filename(video.filename)}

    threading.Thread(target=run_job, args=(job_id, src, out, opts),
                     daemon=True).start()
    return jsonify(job=job_id)


@app.route("/status/<job_id>")
def status(job_id):
    with jobs_lock:
        job = jobs.get(job_id)
    if not job:
        return jsonify(error="Job inconnu."), 404
    payload = {"state": job["state"], "message": job["message"]}
    if job["state"] == "done":
        payload["download"] = url_for("download", job_id=job_id)
    return jsonify(payload)


@app.route("/download/<job_id>")
def download(job_id):
    with jobs_lock:
        job = jobs.get(job_id)
    if not job or job["state"] != "done":
        return jsonify(error="Video pas encore prete."), 404
    return send_file(job["output"], as_attachment=True,
                     download_name="viralcut_tiktok.mp4")


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    print(f"ViralCut demarre sur http://localhost:{port}")
    app.run(host="0.0.0.0", port=port, debug=False)
