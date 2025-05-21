# # import necessary libraries:
# from flask import Flask, request, jsonify
# from chatbot_main import generate_response
# from flask_cors import CORS
# import os
#
# # initialize flask app:
# app = Flask(__name__)
# # allow cross-origin requests from frontend:
# CORS(app)
#
# # define chatbot endpoint:
# @app.route("/chatbot", methods=["GET", "POST"])
# def chatbot():
#     if request.method == "GET":
#         return "Chatbot endpoint is live. Please send a POST request with a message."
#
#     data = request.get_json()
#     user_input = data.get("message", "")
#
#     if not user_input:
#         return jsonify({"response": "No input provided."}), 400
#
#     response = generate_response(user_input)
#     return jsonify({"response": response})
#
#
# # run the app:
# if __name__ == "__main__":
#     # default to 5000:
#     port = int(os.environ.get("PORT", 5000))
#     app.run(host="0.0.0.0", port=port, debug=False)

# import necessary libraries:
import os
import requests
from flask import Flask, request, jsonify
from flask_cors import CORS

# import chatbot logic:
from chatbot_main import generate_response

# initialize flask app:
app = Flask(__name__)
# allow cross-origin requests from frontend:
CORS(app)

# ---
# define chatbot endpoint:
# GET: sanity check
# POST: expect JSON {"message": "..."} → run through your ML model
@app.route("/chatbot", methods=["GET", "POST"])
def chatbot():
    if request.method == "GET":
        return "Chatbot endpoint is live. Please send a POST request with a message."

    data = request.get_json()
    user_input = data.get("message", "").strip()

    if not user_input:
        return jsonify({"response": "No input provided."}), 400

    # generate reply (delay-prediction, greetings, etc.)
    response = generate_response(user_input)
    return jsonify({"response": response})


# ---
# define cheapest-ticket lookup endpoint:
# GET /tickets/cheapest?from=<orig>&to=<dest>&date=<YYYY-MM-DD>&type=<ticketType>
@app.route("/tickets/cheapest", methods=["GET"])
def cheapest_ticket():
    # extract query parameters:
    origin      = request.args.get("from", "").upper().strip()
    destination = request.args.get("to",   "").upper().strip()
    travel_date = request.args.get("date", "").strip()
    ticket_type = request.args.get("type", "Any").strip()

    # basic validation:
    if not all([origin, destination, travel_date]):
        return jsonify({
            "error": "Missing required parameter(s). "
                     "Please provide 'from', 'to' and 'date'."
        }), 400

    # build API request to external train-feed:
    api_url = os.environ.get("RAIL_API_URL")
    api_key = os.environ.get("RAIL_API_KEY")

    # ensure API settings exist:
    if not api_url or not api_key:
        return jsonify({
            "error": "Ticket API not configured. "
                     "Set RAIL_API_URL and RAIL_API_KEY."
        }), 500

    try:
        # call the third-party service:
        resp = requests.get(
            api_url,
            params={
                "from":      origin,
                "to":        destination,
                "date":      travel_date,
                "ticketType": ticket_type,
                "apikey":     api_key
            },
            timeout=10
        )
        resp.raise_for_status()
        ticket_data = resp.json()

        # normalize and return just what the frontend/ui needs:
        return jsonify({
            "from":         origin,
            "to":           destination,
            "date":         travel_date,
            "ticketType":   ticket_type,
            "price":        ticket_data.get("price"),
            "bookingUrl":   ticket_data.get("bookingUrl")
        })

    except requests.exceptions.RequestException as e:
        # log to console for debugging
        app.logger.error(f"Ticket lookup failed: {e}")
        return jsonify({"error": "Failed to fetch ticket data."}), 502


# ---
# run the app:
if __name__ == "__main__":
    # default to port 5000:
    port = int(os.environ.get("PORT", 5000))
    # for debug only(turn off during demo)
    app.run(host="0.0.0.0", port=port, debug=False)
