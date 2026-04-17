import socket
import threading
import json
import time
from flask import Flask, request, jsonify
from flask_cors import CORS

SOCKET_HOST = "0.0.0.0"
SOCKET_PORT = 5000

API_HOST = "0.0.0.0"
API_PORT = 8000

free_workers = []
worker_info = {}
worker_status = {}
clients = set()
logs = []
job_queue = []

LOCK = threading.Lock()

app = Flask(__name__)
CORS(app)

server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
server.bind((SOCKET_HOST, SOCKET_PORT))
server.listen(10)


def log(msg):
    print(msg)
    logs.append(msg)
    if len(logs) > 50:
        logs.pop(0)


def get_worker():
    while True:
        with LOCK:
            if free_workers:
                return free_workers.pop(0)
        time.sleep(0.2)


def handle_worker(conn, addr, worker_id):
    log(f"🤖 Worker {worker_id} connected")

    with LOCK:
        free_workers.append(conn)
        worker_info[conn] = worker_id
        worker_status[worker_id] = "Idle"

    try:
        while True:
            try:
                # 🔥 Send heartbeat
                conn.settimeout(5)
                conn.send(b"PING")

                # 🔥 Wait for response
                response = conn.recv(1024).decode()

                if response != "PONG":
                    raise Exception("Invalid heartbeat")

                time.sleep(3)

            except:
                raise Exception("Worker not responding")

    except:
        log(f"❌ Worker {worker_id} disconnected")

        with LOCK:
            if conn in free_workers:
                free_workers.remove(conn)
            if conn in worker_info:
                del worker_info[conn]

        worker_status[worker_id] = "Dead"

        try:
            conn.close()
        except:
            pass


def accept_connections():
    while True:
        conn, addr = server.accept()
        role = conn.recv(1024).decode()

        if role.startswith("WORKER"):
            worker_id = role.split(":")[1]
            threading.Thread(target=handle_worker, args=(conn, addr, worker_id), daemon=True).start()


@app.route("/submit", methods=["POST"])
def submit():
    data = request.json
    job_id = data["JobID"]
    client_id = data["ClientID"]

    clients.add(client_id)

    with LOCK:
        job_queue.append(job_id)

    log(f"📩 {client_id} submitted {job_id}")

    while True:   # 🔥 retry loop for reassignment
        worker = get_worker()

        if worker not in worker_info:
            continue

        worker_id = worker_info[worker]
        worker_status[worker_id] = "Busy"

        log(f"⚡ {job_id} → {worker_id}")

        try:
            worker.settimeout(10)
            worker.send(json.dumps(data).encode())

            # ACK
            ack = worker.recv(1024).decode()
            log(f"ACK from {worker_id}: {ack}")

            time.sleep(0.1)

            # RESULT
            result = worker.recv(4096).decode()
            log(f"RESULT from {worker_id}: {result}")

            worker_status[worker_id] = "Idle"

            with LOCK:
                free_workers.append(worker)
                if job_id in job_queue:
                    job_queue.remove(job_id)

            log(f"✅ Completed {job_id}")

            return jsonify({"status": "success", "result": result})

        except:
            log(f"❌ Worker {worker_id} FAILED while processing {job_id}")
            worker_status[worker_id] = "Dead"
            with LOCK:
                if worker in free_workers:
                    free_workers.remove(worker)
        if worker in worker_info:
            del worker_info[worker]
            log(f"🔁 Reassigning job {job_id} to another worker...")

            # 🔥 DO NOT remove job → loop retries automatically


@app.route("/")
def dashboard():
    return f"""
    <body style="background:#0f172a;color:white;font-family:Arial;">
    <h1>⚡ SERVER DASHBOARD</h1>

    <h2>Clients</h2>
    {"<br>".join(clients)}

    <h2>Workers</h2>
    {"<br>".join([f"{wid} → {status}" for wid, status in worker_status.items()])}

    <h2>Job Queue</h2>
    {"<br>".join(job_queue)}

    <h2>Logs</h2>
    {"<br>".join(logs)}

    <meta http-equiv="refresh" content="2">
    </body>
    """


if __name__ == "__main__":
    threading.Thread(target=accept_connections, daemon=True).start()
    print(f"🌐 Server UI: http://localhost:{API_PORT}")
    app.run(host=API_HOST, port=API_PORT)