from flask import Flask, render_template, request, send_file
import uuid
from process import convert_article
import threading

app = Flask(__name__)

jobs = {}


@app.route("/")
def home():
    return render_template("index.html")


def run_job(job_id, url):
    jobs[job_id] = {"status": "running", "progress": 0}

    def update_progress(completed, total, total_chunks):
        jobs[job_id] = {
            "status": "running",
            "progress": completed * 100 // total,
            "processed_chunks": total,
            "total_chunks": total_chunks,
        }

    try:
        convert_article(url, job_id, on_progress=update_progress)
        jobs[job_id].update(status="done", progress=100)
    except Exception:
        app.logger.exception("Error generating audio")
        jobs[job_id]["status"] = "error"


@app.route("/jobs", methods=["POST"])
def submit_job():
    url = request.form.get("url")
    job_id = uuid.uuid4().hex
    jobs[job_id] = {"status": "queued", "progress": 0}
    threading.Thread(target=run_job, args=(job_id, url), daemon=True).start()
    return render_template("jobs.html", job_id=job_id)


@app.route("/jobs/<job_id>")
def job_status(job_id):
    return jobs.get(job_id, {"status": "unknown", "progress": 0})


@app.route("/jobs/<job_id>/download")
def download_job(job_id):
    return send_file(
        f"{job_id}.wav",
        as_attachment=True,
    )


if __name__ == "__main__":
    app.run(debug=True, port=8080)
