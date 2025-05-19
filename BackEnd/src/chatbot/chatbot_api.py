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

    if not user_input:
        return jsonify({"response": "No input provided."}), 400

    response = generate_response(user_input)
    return jsonify({"response": response})


# run the app:
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))  # default to 5000
    app.run(host="0.0.0.0", port=port, debug=False)
