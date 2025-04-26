from flask import Flask, request, jsonify
from chatbot_main import generate_response
from flask_cors import CORS

app = Flask(__name__)
CORS(app)  # Enable Cross-Origin Resource Sharing for frontend requests


@app.route("/chatbot", methods=["POST"])
def chatbot():
    data = request.get_json()
    user_input = data.get("message", "")

    if not user_input:
        return jsonify({"response": "No input provided."}), 400

    response = generate_response(user_input)
    return jsonify({"response": response})


if __name__ == "__main__":
    app.run(port=5000)
