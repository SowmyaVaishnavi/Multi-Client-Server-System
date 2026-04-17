import socket
import json
import math
import time
import threading
import random
from flask import Flask
import sys

PORT_UI = int(sys.argv[1]) if len(sys.argv) > 1 else 7000

HOST = "10.1.1.225"
PORT = 5000

WORKER_ID = f"W{random.randint(100,999)}"

app = Flask(__name__)

status = "Connecting..."
current_job = "-"
result_data = "-"
job_history = []


def connect():
    global status
    while True:
        try:
            w = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            w.connect((HOST, PORT))
            w.send(f"WORKER:{WORKER_ID}".encode())
            status = "Connected"
            return w
        except:
            status = "Retrying..."
            time.sleep(2)


def worker_loop():
    global status, current_job, result_data

    worker = connect()

    while True:
        try:
            data = worker.recv(4096).decode()
            if data == "PING":
                worker.send("PONG".encode())
                continue
            job = data
            if not job:
                worker = connect()
                continue

            data = json.loads(job)
            task = data["Task"]
            job_id = data["JobID"]

            current_job = job_id
            status = "Working"

            # ACK
            worker.send("ACK".encode())

            try:
                if task["type"] == "factorial":
                    n = int(task["number"])
                    if n < 0:
                        raise ValueError
                    result = math.factorial(n)

                elif task["type"] == "sum":
                    nums = list(map(int, task["numbers"]))
                    result = sum(nums)

                else:
                    n = int(task["number"])
                    result = all(n % i != 0 for i in range(2, int(n**0.5)+1))

            except:
                result = "❌ Invalid Input"

            result_data = str(result)
            status = "Idle"

            job_history.append(f"{job_id} → {result_data}")
            if len(job_history) > 10:
                job_history.pop(0)

            time.sleep(0.1)
            worker.send(result_data.encode())

        except:
            worker = connect()


@app.route("/")
def ui():
    return f"""
    <body style="background:#0f172a;color:white;font-family:Arial;">
    <h1>🤖 WORKER {WORKER_ID}</h1>

    <div>Status: {status}</div>
    <div>Current Job: {current_job}</div>
    <div>Result: {result_data}</div>

    <h3>📜 History</h3>
    {"<br>".join(job_history)}

    <meta http-equiv="refresh" content="2">
    </body>
    """


if __name__ == "__main__":
    threading.Thread(target=worker_loop, daemon=True).start()
    print(f"🌐 Worker UI: http://localhost:{PORT_UI}")
    app.run(host="0.0.0.0", port=PORT_UI)