from flask import Flask, jsonify, request

app = Flask(__name__)

tasks = []

@app.route("/tasks", methods=["POST"])
def create_task():
    data = request.get_json()

    task = {
        "id": len(tasks) + 1,
        "name": data["name"],
        "status": "pending"
    }

    tasks.append(task)

    return jsonify(task), 201

@app.route("/tasks", methods=["GET"])
def get_tasks():
    return jsonify(tasks)

@app.route("/health")
def health():
    return jsonify(status="healthy")


@app.route("/")
def home():
    return jsonify(message="Task API is running")


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
