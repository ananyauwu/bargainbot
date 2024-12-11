from flask import Flask, request, jsonify
from flask_cors import CORS
import pandas as pd
import requests
from twilio.rest import Client
import logging

# Flask app setup
app = Flask(__name__)
CORS(app)

# Twilio and Llama API Configurations
TWILIO_ACCOUNT_SID = "AC9692e3502917f71176187d84ae39a536"
TWILIO_AUTH_TOKEN = "eaa6a73a74cb3d2440a224ffd59088e0"
TWILIO_WHATSAPP_NUMBER = "whatsapp:+917483490469"
LLAMA_API_URL = "https://ai-suraj0809ai813750528844.openai.azure.com/"
LLAMA_API_KEY = "1ZDucnkCOIV3HQ2X4oaAFttP4PLci2jnmsBYBXluhbC3MyLC3bUtJQQJ99AKACHYHv6XJ3w3AAAAACOG4yvd"

# Initialize Twilio client
twilio_client = Client(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)

# Load product data
CSV_FILE = "Bargain Bot Product List - Sheet1.csv"
try:
    product_data = pd.read_csv(CSV_FILE)
except FileNotFoundError:
    logging.error(f"CSV file {CSV_FILE} not found.")
    product_data = pd.DataFrame()

def search_product(query):
    """Search for products containing the query in the 'Product Name'."""
    matches = product_data[product_data['Product Name'].str.contains(query, case=False, na=False)]
    return matches.to_dict(orient="records") if not matches.empty else None

def generate_llama_response(context):
    """Generate a response from the Llama API."""
    headers = {
        "Authorization": f"Bearer {LLAMA_API_KEY}",
        "Content-Type": "application/json"
    }
    payload = {
        "messages": [
            {"role": "system", "content": "You are a witty price-bargaining chatbot. Help users negotiate prices effectively."},
            {"role": "user", "content": context}
        ]
    }

    try:
        response = requests.post(LLAMA_API_URL, headers=headers, json=payload)
        if response.status_code == 200:
            return response.json().get("choices", [])[0].get("message", {}).get("content", "I'm unable to respond right now.")
        else:
            logging.error(f"Llama API Error: {response.status_code}, {response.text}")
            return "Sorry, I couldn't generate a reply."
    except Exception as e:
        logging.error(f"Error communicating with Llama API: {e}")
        return "Error communicating with the chatbot service."

@app.route('/api/messages', methods=['POST'])
def handle_message():
    """Handle incoming WhatsApp messages."""
    data = request.form
    phone_number = data.get('From')
    user_query = data.get('Body')

    # Step 1: Search for matching products
    products = search_product(user_query)
    if products:
        # Step 2: Construct product context
        product_details = "\n\n".join([
            (
                f"Product Name: {p['Product Name']}\n"
                f"Category: {p['Catogory']}\n"
                f"MRP: {p['MRP']}\n"
                f"Minimum Price: {p['Minimum Retail Price']}\n"
                f"Units Available: {p['Units Available']}\n"
                f"Specifications: {p['Product Specifications']}\n"
            )
            for p in products[:3]  # Limit to top 3 products
        ])
        context = f"The user is asking about '{user_query}'. Here are the matching products:\n{product_details}"

        # Step 3: Generate chatbot reply
        chatbot_reply = generate_llama_response(context)
    else:
        chatbot_reply = f"Sorry, no products found for '{user_query}'. Let me know if I can assist further!"

    # Step 4: Respond via Twilio
    try:
        twilio_client.messages.create(
            body=chatbot_reply,
            from_=TWILIO_WHATSAPP_NUMBER,
            to=phone_number
        )
        return jsonify({"status": "Message sent", "reply": chatbot_reply})
    except Exception as e:
        logging.error(f"Error sending message via Twilio: {e}")
        return jsonify({"status": "Failed to send message", "error": str(e)})

@app.route('/')
def index():
    return "Welcome to Bargain Bot! The API is running."

# Logging setup
logging.basicConfig(level=logging.DEBUG)

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    app.run(host="0.0.0.0", port=port)
