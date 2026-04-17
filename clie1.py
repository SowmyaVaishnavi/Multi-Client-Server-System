from flask import Flask, request, session
import requests
import random

app = Flask(__name__)
app.secret_key = "secret123"

SERVER_API = "http://192.168.0.154:8000/submit"

history = {}


@app.route("/", methods=["GET", "POST"])
def home():
    if "client_id" not in session:
        session["client_id"] = f"C{random.randint(100,999)}"

    client_id = session["client_id"]

    if client_id not in history:
        history[client_id] = []

    result = ""

    if request.method == "POST":
        job_id = request.form["job"]
        task_type = request.form["type"]
        input_data = request.form["input"]

        try:
            if task_type == "factorial":
                task = {"type": "factorial", "number": int(input_data)}
            elif task_type == "sum":
                task = {"type": "sum", "numbers": list(map(int, input_data.split()))}
            else:
                task = {"type": "prime", "number": int(input_data)}

            res = requests.post(SERVER_API, json={
                "JobID": job_id,
                "ClientID": client_id,
                "Task": task
            }).json()

            result = res.get("result", "Error")

        except:
            result = "❌ Invalid Input"

        history[client_id].append(f"{job_id} → {result}")

    return f"""
    <body style="background:#0f172a;color:white;font-family:Arial;">
    <h1>🧑‍💻 CLIENT {client_id}</h1>

    <form method="post">
    Job ID: <input name="job"><br><br>

    Task:
    <select name="type">
        <option value="factorial">Factorial</option>
        <option value="sum">Sum</option>
        <option value="prime">Prime</option>
    </select><br><br>

    Input: <input name="input"><br><br>

    <button type="submit">Send Task</button>
    </form>

    <h2>Result: {result}</h2>

    <h3>History</h3>
    {"<br>".join(history[client_id])}

    </body>
    """


if __name__ == "__main__":
    print("🌐 Client UI: http://localhost:5500")
    app.run(host="0.0.0.0", port=5500)