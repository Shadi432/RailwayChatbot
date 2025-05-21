# import necessary libraries:
from flask import Flask, request, jsonify
from chatbot_main import generate_response
from flask_cors import CORS
import os

# initialize flask app:
app = Flask(__name__)
CORS(app)  # allow cross-origin requests from frontend

# define chatbot endpoint:
@app.route("/chatbot", methods=["GET", "POST"])
def chatbot():
    if request.method == "GET":
        return "Chatbot endpoint is live. Please send a POST request with a message."

    data = request.get_json()
    user_input = data.get("message", "")
    session_id = data.get("session_id")  # Support session_id

    if not user_input:
        return jsonify({"response": "No input provided."}), 400

    response, session_id = generate_response(user_input, session_id)
    return jsonify({"response": response, "session_id": session_id})

@app.route("/chat", methods=["POST"])
def chat():
    data = request.json
    user_input = data.get("message")
    session_id = data.get("session_id")
    response, session_id = generate_response(user_input, session_id)
    return jsonify({"response": response, "session_id": session_id})


# run the app:
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))  # default to 5000
    app.run(host="0.0.0.0", port=port, debug=False)
