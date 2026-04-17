import socket
import json
import math
import time

HOST = "10.1.18.216"   # your server IP
PORT = 5000

print("🚀 Starting Worker...")


def connect():
    while True:
        try:
            w = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            w.connect((HOST, PORT))
            w.send("WORKER".encode())
            print("✅ Connected to Server")
            return w
        except:
            print("🔁 Retrying connection...")
            time.sleep(2)


worker = connect()

while True:
    try:
        job = worker.recv(4096).decode()

        if not job:
            print("❌ Server disconnected")
            worker.close()
            worker = connect()
            continue

        data = json.loads(job)
        task = data["Task"]
        job_id = data["JobID"]

        print(f"⚙️ Processing {job_id}")

        # ACK
        worker.send("ACK".encode())

        try:
            if task["type"] == "factorial":
                result = math.factorial(task["number"])

            elif task["type"] == "sum":
                result = sum(task["numbers"])

            elif task["type"] == "prime":
                n = task["number"]
                result = all(n % i != 0 for i in range(2, int(n**0.5)+1))

            else:
                result = "[ERROR] Unknown task"

        except Exception as e:
            result = f"[ERROR] {str(e)}"

        print(f"✅ Done {job_id}")

        worker.send(str(result).encode())

    except Exception as e:
        print("❌ Error:", e)
        worker.close()
        time.sleep(2)
        worker = connect()