from flask import Flask, request, jsonify
from flask_cors import CORS
import pandas as pd
import requests
from twilio.rest import Client
import logging
import os

app = Flask(__name__)
CORS(app)

# Helper function to load environment variables
def get_env_variable(var_name, default=None):
    value = os.getenv(var_name, default)
    if value is None:
        logging.error(f"Missing environment variable: {var_name}")
        raise EnvironmentError(f"Required environment variable {var_name} is not set.")
    return value

# Load environment variables
TWILIO_ACCOUNT_SID = get_env_variable("TWILIO_ACCOUNT_SID")
TWILIO_AUTH_TOKEN = get_env_variable("TWILIO_AUTH_TOKEN")
TWILIO_WHATSAPP_NUMBER = get_env_variable("TWILIO_WHATSAPP_NUMBER")
LLAMA_API_URL = get_env_variable("LLAMA_API_URL")
LLAMA_API_KEY = get_env_variable("LLAMA_API_KEY")
CSV_FILE = "Bargain Bot Product List - Sheet1.csv"

# Initialize Twilio Client
twilio_client = Client(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)

# Load and preprocess product data
try:
    product_data = pd.read_csv(CSV_FILE, usecols=[
        "Serial Number", "Product Name", "Category", "MRP", "Minimum Retail Price",
        "Units Available", "Product Description Summary", "Product Image",
        "Product Video", "Product Specifications", "Shipping details", "Policy"
    ])
    product_data['Search Index'] = product_data['Product Name'].str.lower()
except FileNotFoundError:
    logging.error(f"CSV file not found: {CSV_FILE}")
    product_data = pd.DataFrame()

# Helper function to search for products
def search_product(query):
    """Search for products matching the query using a case-insensitive search."""
    if product_data.empty:
        return None

    query = query.lower()
    matches = product_data[product_data['Search Index'].str.contains(query, na=False)]
    return matches.to_dict(orient='records') if not matches.empty else None

# Helper function to generate a witty response from Llama
def generate_llama_response(context):
    """Get a witty response from the Llama model API."""
    headers = {"Authorization": f"Bearer {LLAMA_API_KEY}", "Content-Type": "application/json"}
    payload = {
        "messages": [
            {
                "role": "system",
                "content": (
                    "You are a witty, fun chatbot designed to help customers make decisions. "
                    "Use humor and persuasive language to help the customer decide on a product. "
                    "Do not overwhelm them with all the details at once, and keep the tone friendly and engaging."
                )
            },
            {"role": "user", "content": context}
        ]
    }

    try:
        response = requests.post(LLAMA_API_URL, headers=headers, json=payload, timeout=10)
        response.raise_for_status()
        result = response.json()
        return result.get("choices", [])[0].get("message", {}).get("content", "Couldn't generate a witty response.")
    except requests.RequestException as e:
        logging.error(f"Llama API error: {e}")
        return "Oops! My witty side is taking a nap right now. Try again later!"

# Twilio webhook route
@app.route('/api/messages', methods=['POST'])
def twilio_webhook():
    """Handle incoming messages from Twilio."""
    data = request.form
    phone_number = data.get('From')
    user_query = data.get('Body')

    # Search for products dynamically
    products = search_product(user_query)
    message_parts = []

    if products:
        message_parts.append(f"Hey there! I found some awesome products matching '{user_query}'! Let me tell you about them:")

        # Generate responses for top 3 products
        for i, product in enumerate(products[:3], 1):
            context = (
                f"Product Name: {product['Product Name']}\n"
                f"Category: {product['Category']}\n"
                f"MRP: ₹{product['MRP']}\n"
                f"Minimum Price: ₹{product['Minimum Retail Price']}\n"
                f"Units Available: {product['Units Available']}\n"
                f"Description: {product['Product Description Summary']}\n"
                "Generate a witty response to convince the customer to buy this product."
            )
            witty_response = generate_llama_response(context)
            message_parts.append(f"**Product {i}: {product['Product Name']}**\n{witty_response}\nWant more details? Just say the word!")

        message_parts.append("So, what do you think? Ready to grab one of these amazing deals?")
    else:
        message_parts.append(f"Oops! I couldn't find anything matching '{user_query}'. How about trying a different search term?")

    # Send response via Twilio
    chatbot_reply = "\n\n".join(message_parts)
    try:
        twilio_client.messages.create(
            body=chatbot_reply,
            from_=TWILIO_WHATSAPP_NUMBER,
            to=phone_number
        )
    except Exception as e:
        logging.error(f"Failed to send message via Twilio: {e}")
        return jsonify({"status": "Failed", "error": str(e)}), 500

    return jsonify({"status": "Message sent to user."})

# Health check route
@app.route('/')
def index():
    """Health check endpoint."""
    return "Welcome to Bargain Bot! The API is running."

# Logging configuration
logging.basicConfig(level=logging.INFO)

# Main entrypoint
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    app.run(host="0.0.0.0", port=port)
