from flask import Flask, request, jsonify
from flask_cors import CORS  # Import CORS
import pandas as pd
import requests
from twilio.rest import Client
import logging
import os

app = Flask(__name__)
CORS(app)  # Enable CORS for the entire application

# Load sensitive information from environment variables
TWILIO_ACCOUNT_SID = os.getenv("TWILIO_ACCOUNT_SID")
TWILIO_AUTH_TOKEN = os.getenv("TWILIO_AUTH_TOKEN")
TWILIO_WHATSAPP_NUMBER = os.getenv("TWILIO_WHATSAPP_NUMBER")
LLAMA_API_URL = os.getenv("LLAMA_API_URL")
LLAMA_API_KEY = os.getenv("LLAMA_API_KEY")

# Initialize Twilio Client
twilio_client = Client(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)

# Load product data with error handling
try:
    product_data = pd.read_csv(CSV_FILE, usecols=[
        "Serial Number", "Product Name", "Category", "MRP", "Minimum Retail Price",
        "Units Available", "Product Description Summary", "Product Image",
        "Product Video", "Product Specifications", "Shipping details", "Policy"
    ])
except FileNotFoundError:
    logging.error(f"CSV file not found: {CSV_FILE}")
    product_data = pd.DataFrame()

# Helper Function to Search for Products
def search_product(query):
    """Search for products matching the query."""
    if product_data.empty:
        return None

    matches = product_data[
        product_data['Product Name'].str.contains(query, case=False, na=False)
    ]
    return matches.to_dict(orient='records') if not matches.empty else None

# Helper Function for Llama Response
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

    response = requests.post(LLAMA_API_URL, headers=headers, json=payload)
    if response.ok:
        return response.json().get("choices", [])[0].get("message", {}).get("content", "Sorry, I couldn't come up with a reply.")
    return f"Error communicating with the Llama API: {response.text}"

# Twilio Webhook Route
@app.route('/api/messages', methods=['POST'])
def twilio_webhook():
    """Handle incoming messages from Twilio."""
    data = request.form
    phone_number = data.get('From')
    user_query = data.get('Body')

    # Search for products dynamically
    products = search_product(user_query)
    if products:
        # Start the conversation with Llama
        chatbot_reply = f"Hey there! 👋 I found some awesome products matching '{user_query}'! Let me tell you about them, one at a time!"

        # Loop over the top 3 products and generate witty responses for each
        for i, product in enumerate(products[:3], 1):
            # Pass product details to Llama to generate a witty response
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

            # Append the witty response to chatbot reply
            chatbot_reply += f"\n\n✨ **Product {i}: {product['Product Name']}** ✨"
            chatbot_reply += f"\n{witty_response}"

            # Add suspense and keep the conversation going
            chatbot_reply += "\n\nWant more details? Just say the word! 😉"

        # After all details are shared, end with a call to action
        chatbot_reply += "\n\nSo, what do you think? Ready to grab one of these amazing deals? 😎"

    else:
        # If no product is found, provide a helpful message
        chatbot_reply = f"Oops! I couldn't find anything matching '{user_query}'. How about trying a different search term?"

    # Send response via Twilio
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

# Health Check Route
@app.route('/')
def index():
    """Health check endpoint."""
    return "Welcome to Bargain Bot! The API is running."

# Logging Configuration
logging.basicConfig(level=logging.INFO)

# Main Entrypoint
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    app.run(host="0.0.0.0", port=port)
