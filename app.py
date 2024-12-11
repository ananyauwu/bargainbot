from flask import Flask, request, jsonify
from flask_cors import CORS
import pandas as pd
import requests
from twilio.rest import Client
import os
import logging

app = Flask(__name__)
CORS(app)

# Constants and Configurations
CSV_FILE = "Bargain Bot Product List - Sheet1.csv"
LLAMA_API_URL = os.getenv("LLAMA_API_URL")
LLAMA_API_KEY = os.getenv("LLAMA_API_KEY")
TWILIO_ACCOUNT_SID = os.getenv("TWILIO_ACCOUNT_SID")
TWILIO_AUTH_TOKEN = os.getenv("TWILIO_AUTH_TOKEN")
TWILIO_WHATSAPP_NUMBER = os.getenv("TWILIO_WHATSAPP_NUMBER")

# Initialize Twilio client
twilio_client = Client(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)

# Load product data
try:
    product_data = pd.read_csv(CSV_FILE)
except FileNotFoundError:
    logging.error(f"CSV file not found: {CSV_FILE}")
    product_data = pd.DataFrame()

# Function to search for products
def search_product(query):
    """Search for products matching the query in any column."""
    if product_data.empty:
        return None

    matches = product_data[product_data.apply(
        lambda row: query.lower() in row.astype(str).str.lower().str.cat(sep=" "), axis=1
    )]

    if matches.empty:
        return None

    return matches.to_dict(orient='records')

# Function to extract relevant details from a query
def extract_relevant_details(query, product):
    """Determine what details to include based on the query."""
    keywords = {
        "price": ["price", "cost", "mrp", "minimum price"],
        "availability": ["available", "stock", "units"],
        "specifications": ["specifications", "features", "details"],
        "shipping": ["shipping", "delivery"],
        "policy": ["policy", "warranty", "return"]
    }

    # Identify relevant keywords in the query
    relevant_keys = set()
    for key, words in keywords.items():
        if any(word in query.lower() for word in words):
            relevant_keys.add(key)

    # Map keys to product details
    details_map = {
        "price": f"MRP: {product.get('MRP', 'N/A')}, Minimum Price: {product.get('Minimum Retail Price', 'N/A')}",
        "availability": f"Units Available: {product.get('Units Available', 'N/A')}",
        "specifications": f"Specifications: {product.get('Product Specifications', 'N/A')}",
        "shipping": f"Shipping Details: {product.get('Shipping deatils', 'N/A')}",
        "policy": f"Policy: {product.get('Policy', 'N/A')}"
    }

    # Construct the response with relevant details
    response = [details_map[key] for key in relevant_keys if key in details_map]
    return "\n".join(response) if response else "Let me know what specific details you need!"

@app.route('/api/messages', methods=['POST'])
def twilio_webhook():
    """Handle incoming messages from Twilio."""
    data = request.form
    phone_number = data.get('From')
    user_query = data.get('Body')

    # Search for products
    products = search_product(user_query)

    if products:
        # Respond with details relevant to the user's query
        responses = []
        for product in products:
            product_name = product.get("Product Name", "Unknown Product")
            relevant_details = extract_relevant_details(user_query, product)
            responses.append(f"**{product_name}**\n{relevant_details}")

        chatbot_reply = "\n\n".join(responses)
    else:
        chatbot_reply = f"Sorry, I couldn't find any products matching '{user_query}'."

    # Send reply via Twilio
    try:
        twilio_client.messages.create(
            body=chatbot_reply,
            from_=TWILIO_WHATSAPP_NUMBER,
            to=phone_number
        )
        return jsonify({"status": "Message sent to user.", "reply": chatbot_reply})
    except Exception as e:
        logging.error(f"Failed to send message via Twilio: {e}")
        return jsonify({"status": "Failed to send message", "error": str(e)})

@app.route('/status', methods=['POST'])
def status():
    """Handle Twilio status updates."""
    status_update = request.form
    message_sid = status_update.get('MessageSid')
    message_status = status_update.get('MessageStatus')
    logging.info(f"Status update received: {message_sid} - {message_status}")
    return '', 200  # Respond with HTTP 200 OK to acknowledge receipt

@app.route('/')
def index():
    """Health check endpoint."""
    return "Welcome to Bargain Bot! The API is running."

# Configure logging
logging.basicConfig(level=logging.INFO)

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    app.run(host="0.0.0.0", port=port)
