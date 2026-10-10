
import base64
import os
import sqlite3
import uuid
from datetime import datetime

from flask import Flask, jsonify, render_template, request

app = Flask(__name__)
BASE = os.path.dirname(os.path.abspath(__file__))
DB = os.path.join(BASE, "civiceye.db")
UPLOADS = os.path.join(BASE, "static", "uploads")
os.makedirs(UPLOADS, exist_ok=True)

# Problem type -> BMC department that receives the report
CATS = {
    "Pothole / damaged road": "Roads & Traffic Department",
    "Garbage not collected": "Solid Waste Management Department",
    "Water leakage / no water": "Hydraulic Engineer Department",
    "Blocked drain / waterlogging": "Storm Water Drains Department",
    "Streetlight not working": "Street Lighting (Electrical) Department",
    "Illegal hoarding / encroachment": "Licence & Encroachment Department",
    "Stray animals / dead animal": "Veterinary Health Department",
    "Public toilet problem": "Public Health Department",
}
STATUSES = ("Pending", "In progress", "Resolved")


def db():
    con = sqlite3.connect(DB)
    con.row_factory = sqlite3.Row
    return con


def init_db():
    with db() as con:
        con.execute(
            """CREATE TABLE IF NOT EXISTS reports(
                 no INTEGER PRIMARY KEY AUTOINCREMENT,
                 id TEXT, name TEXT, phone TEXT, cat TEXT, dept TEXT,
                 ward TEXT, descr TEXT, addr TEXT, coords TEXT,
                 photo TEXT, status TEXT, date TEXT)"""
        )


def row_to_dict(r):
    d = dict(r)
    d["desc"] = d.pop("descr")
    return d


@app.route("/")
def home():
    return render_template("index.html")


@app.route("/api/reports", methods=["POST"])
def create_report():
    data = request.get_json(silent=True) or {}
    cat = data.get("cat")
    photo = data.get("photo", "")
    if cat not in CATS:
        return jsonify(error="Unknown problem type."), 400
    if not all(str(data.get(k, "")).strip() for k in ("name", "phone", "desc", "addr", "ward")):
        return jsonify(error="Please fill all required fields."), 400
    if not photo.startswith("data:image/jpeg;base64,") or len(photo) > 3_000_000:
        return jsonify(error="Invalid or too large photo."), 400

    # save the photo as a file and keep only its path in the database
    filename = uuid.uuid4().hex + ".jpg"
    with open(os.path.join(UPLOADS, filename), "wb") as f:
        f.write(base64.b64decode(photo.split(",", 1)[1]))

    with db() as con:
        cur = con.execute(
            """INSERT INTO reports(name,phone,cat,dept,ward,descr,addr,coords,photo,status,date)
               VALUES(?,?,?,?,?,?,?,?,?,?,?)""",
            (data["name"].strip(), data["phone"].strip(), cat, CATS[cat], data["ward"],
             data["desc"].strip(), data["addr"].strip(), data.get("coords", ""),
             "/static/uploads/" + filename, "Pending",
             datetime.now().strftime("%d/%m/%Y, %I:%M %p")),
        )
        rid = "CE-%d" % (1000 + cur.lastrowid)
        con.execute("UPDATE reports SET id=? WHERE no=?", (rid, cur.lastrowid))
    return jsonify(id=rid, dept=CATS[cat]), 201


@app.route("/api/reports")
def list_reports():
    sql, args = "SELECT * FROM reports", []
    if request.args.get("id"):
        sql += " WHERE id=?"
        args.append(request.args["id"])
    elif request.args.get("dept"):
        sql += " WHERE dept=?"
        args.append(request.args["dept"])
    sql += " ORDER BY no DESC"
    with db() as con:
        return jsonify([row_to_dict(r) for r in con.execute(sql, args)])


@app.route("/api/reports/<rid>/status", methods=["POST"])
def set_status(rid):
    status = (request.get_json(silent=True) or {}).get("status")
    if status not in STATUSES:
        return jsonify(error="Invalid status."), 400
    with db() as con:
        con.execute("UPDATE reports SET status=? WHERE id=?", (status, rid))
    return jsonify(ok=True)


@app.route("/api/stats")
def stats():
    with db() as con:
        rows = [r["status"] for r in con.execute("SELECT status FROM reports")]
    return jsonify(total=len(rows), open=sum(s != "Resolved" for s in rows),
                   resolved=rows.count("Resolved"))


init_db()
if __name__ == "__main__":
    app.run(debug=True)
