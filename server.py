import socket
import threading
import json
from flask import Flask, request, jsonify
from flask_cors import CORS
app = Flask(__name__)
CORS(app)

# ---------------- CONFIG ----------------
SOCKET_HOST = "0.0.0.0"
SOCKET_PORT = 5000

API_HOST = "0.0.0.0"
API_PORT = 8000

# ---------------- GLOBALS ----------------
free_workers = []
LOCK = threading.Lock()

app = Flask(__name__)

# ---------------- SOCKET SERVER ----------------
server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
server.bind((SOCKET_HOST, SOCKET_PORT))
server.listen(10)

print(f"🚀 Socket Server running on port {SOCKET_PORT}")


def get_worker():
    while True:
        with LOCK:
            if free_workers:
                return free_workers.pop(0)


def handle_worker(conn, addr):
    print(f"🤖 Worker connected: {addr}")

    with LOCK:
        free_workers.append(conn)

    while True:
        try:
            # keep connection alive
            data = conn.recv(1024)
            if not data:
                break
        except:
            break

    print(f"❌ Worker disconnected: {addr}")


def accept_connections():
    while True:
        conn, addr = server.accept()

        try:
            role = conn.recv(1024).decode().strip()

            if role == "WORKER":
                threading.Thread(target=handle_worker, args=(conn, addr), daemon=True).start()
            else:
                print(f"⚠️ Unknown role from {addr}: {role}")

        except Exception as e:
            print("Connection error:", e)


# ---------------- FLASK API ----------------
@app.route("/submit", methods=["POST"])
def submit():
    try:
        data = request.json
        job_id = data.get("JobID")

        print(f"📩 Job received: {job_id}")

        worker = get_worker()

        print(f"⚡ Assigning {job_id} → {worker.getpeername()}")

        # send job to worker
        worker.send(json.dumps(data).encode())

        # receive ACK
        worker.recv(1024)

        # receive result
        result = worker.recv(4096).decode()

        print(f"✅ Completed {job_id}")

        # return worker to pool
        with LOCK:
            free_workers.append(worker)

        return jsonify({
            "status": "success",
            "job_id": job_id,
            "result": result
        })

    except Exception as e:
        print("❌ API Error:", e)
        return jsonify({"status": "error", "message": str(e)}), 500


# ---------------- MAIN ----------------
if __name__ == "__main__":
    # Start socket server thread
    threading.Thread(target=accept_connections, daemon=True).start()

    print(f"🌐 API running on http://{API_HOST}:{API_PORT}")

    # Start Flask server
    app.run(host=API_HOST, port=API_PORT)