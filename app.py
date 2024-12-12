from flask import Flask, request, jsonify
from flask_cors import CORS  # Import CORS
import pandas as pd
import requests
from twilio.rest import Client
import logging

app = Flask(__name__)
CORS(app)  # Enable CORS for the entire application

# Constants and Configurations
CSV_FILE = "Bargain_Bot_Product_List.csv"  # Ensure the file name is concise and correct
LLAMA_API_URL = "https://ai-suraj0809ai813750528844.openai.azure.com/"
LLAMA_API_KEY = "1ZDucnkCOIV3HQ2X4oaAFttP4PLci2jnmsBYBXluhbC3MyLC3bUtJQQJ99AKACHYHv6XJ3w3AAAAACOG4yvd"
TWILIO_ACCOUNT_SID = "AC9692e3502917f71176187d84ae39a536"
TWILIO_AUTH_TOKEN = "eaa6a73a74cb3d2440a224ffd59088e0"
TWILIO_WHATSAPP_NUMBER = "whatsapp:+917483490469"

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
    """Get a response from the Llama model API."""
    headers = {"Authorization": f"Bearer {LLAMA_API_KEY}", "Content-Type": "application/json"}
    payload = {
        "messages": [
            {
                "role": "system",
                "content": (
                    "You are a witty price-bargaining chatbot. Help the customer fix a price on the product. "
                    "Keep the minimum retail price in mind when bargaining."
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

    # Search for products
    products = search_product(user_query)
    if products:
        product_details = "\n\n".join([
            (
                f"Product Name: {p['Product Name']}\n"
                f"Category: {p['Category']}\n"
                f"MRP: {p['MRP']}\n"
                f"Minimum Price: {p['Minimum Retail Price']}\n"
                f"Units Available: {p['Units Available']}\n"
                f"Description: {p['Product Description Summary']}\n"
                f"Specifications: {p['Product Specifications']}\n"
                f"Shipping Details: {p['Shipping details']}\n"
                f"Policy: {p['Policy']}\n"
                f"Image: {p['Product Image']}\n"
                f"Video: {p['Product Video']}\n"
            )
            for p in products
        ])
        context = (
            f"The user is asking about '{user_query}'. Here are the matching products:\n"
            f"{product_details}\n"
            "Now, engage with the user in witty price bargaining."
        )
        chatbot_reply = generate_llama_response(context)
    else:
        chatbot_reply = f"Sorry, I couldn't find any products matching '{user_query}'."

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
