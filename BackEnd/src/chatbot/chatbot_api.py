import os
import requests
import pickle
from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
from chatbot_main import generate_response

# serve react here. Path to built React files:
FRONTEND_DIST = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "../../../FrontEnd/dist")
)

app = Flask(__name__, static_folder=FRONTEND_DIST)
# still safe to allow CORS if you ever hit APIs from elsewhere:
CORS(app)

# serve React’s index.html:
@app.route("/", defaults={"path": ""})
@app.route("/<path:path>")
def serve_react(path):
    # if the requested file exists, serve it; otherwise fallback to index.html:
    target = os.path.join(FRONTEND_DIST, path)
    if path and os.path.exists(target):
        return send_from_directory(FRONTEND_DIST, path)
    return send_from_directory(FRONTEND_DIST, "index.html")


#endpoint of chatbot:
@app.route("/chatbot", methods=["GET", "POST"])
def chatbot():
    if request.method == "GET":
        return "Chatbot endpoint is live. Please send a POST request with a message."

    data = request.get_json()
    user_input = data.get("message", "").strip()
    if not user_input:
        return jsonify({"response": "No input provided."}), 400

    response = generate_response(user_input)
    return jsonify({"response": response})


# ticket lookup endpoint:
@app.route("/tickets/cheapest", methods=["GET"])
def cheapest_ticket():
    origin      = request.args.get("originStation", "").strip()
    destination = request.args.get("destinationStation", "").strip()
    travel_date = request.args.get("date", "").strip()
    api_url     = os.environ.get("RAIL_API_URL")
    api_key     = os.environ.get("RAIL_API_KEY")

    if not all([origin, destination, travel_date]):
        return jsonify({"error": "Missing originStation, destinationStation or date"}), 400
    if not api_url or not api_key:
        return jsonify({"error": "Ticket API not configured"}), 500

    try:
        resp = requests.get(api_url, params={
            "originStation":      origin,
            "destinationStation": destination,
            "date":               travel_date,
            "apikey":             api_key
        }, timeout=10)
        resp.raise_for_status()
        info = resp.json()
        return jsonify({
            "from":       origin,
            "to":         destination,
            "date":       travel_date,
            "price":      info.get("price"),
            "bookingUrl": info.get("bookingUrl"),
        })
    except Exception as e:
        app.logger.error(f"Ticket lookup failed: {e}")
        return jsonify({"error": "Failed to fetch ticket data"}), 502


# run server:
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    # debug=False in demo
    app.run(host="0.0.0.0", port=port, debug=False)
