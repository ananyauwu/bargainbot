from flask import Flask, request, jsonify
import pandas as pd
import requests
from twilio.rest import Client

app = Flask(__name__)

# Load product data from CSV
CSV_FILE = "/mnt/data/Bargain Bot Product List - Sheet1.csv"
product_data = pd.read_csv(CSV_FILE)

# Llama Model API Configuration
LLAMA_API_URL = "https://ai-suraj0809ai813750528844.openai.azure.com/"
LLAMA_API_KEY = "1ZDucnkCOIV3HQ2X4oaAFttP4PLci2jnmsBYBXluhbC3MyLC3bUtJQQJ99AKACHYHv6XJ3w3AAAAACOG4yvd"

# Twilio Configuration
TWILIO_ACCOUNT_SID = "AC9692e3502917f71176187d84ae39a536"
TWILIO_AUTH_TOKEN = "eaa6a73a74cb3d2440a224ffd59088e0"
TWILIO_WHATSAPP_NUMBER = "whatsapp:+14155238886"  # Twilio sandbox number for WhatsApp

twilio_client = Client(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)


def search_product(query):
    matches = product_data[product_data['Product Name'].str.contains(query, case=False, na=False)]
    if not matches.empty:
        response = []
        for _, row in matches.iterrows():
            response.append({
                "Serial Number": row['Serial Number'],
                "Product Name": row['Product Name'],
                "Category": row['Catogory'],
                "MRP": row['MRP'],
                "Minimum Retail Price": row['Minimum Retail Price'],
                "Units Available": row['Units Available'],
                "Description": row['Product Discription Summary'],
                "Image": row['Product Image'],
                "Video": row['Prodcut Video'],
                "Specifications": row['Product Specifications'],
                "Shipping Details": row['Shipping deatils'],
                "Policy": row['Policy']
            })
        return response
    else:
        return None


def generate_llama_response(context):
    headers = {"Authorization": f"Bearer {LLAMA_API_KEY}", "Content-Type": "application/json"}
    payload = {
        "messages": [
            {"role": "system", "content": "You are a witty price-bargaining chatbot designed to engage users in an entertaining and helpful manner and to help the customer fix a price on the product. Keep the minimum retail price in mind when bargaining."},
            {"role": "user", "content": context}
        ]
    }

    response = requests.post(LLAMA_API_URL, headers=headers, json=payload)
    if response.status_code == 200:
        return response.json().get("choices", [])[0].get("message", {}).get("content", "Sorry, I couldn't come up with a reply.")
    else:
        return "Error communicating with the Llama API."


@app.route('/api/messages', methods=['POST'])
def twilio_webhook():
    data = request.form
    phone_number = data.get('From')
    user_query = data.get('Body')

    # Step 1: Search for the product
    products = search_product(user_query)

    if products:
        # Step 2: Dynamically construct product context
        product_details = "\n\n".join([
            (
                f"Product Name: {p['Product Name']}\n"
                f"Category: {p['Category']}\n"
                f"MRP: {p['MRP']}\n"
                f"Minimum Price: {p['Minimum Retail Price']}\n"
                f"Units Available: {p['Units Available']}\n"
                f"Description: {p['Description']}\n"
                f"Specifications: {p['Specifications']}\n"
                f"Shipping Details: {p['Shipping Details']}\n"
                f"Policy: {p['Policy']}\n"
                f"Image: {p['Image']}\n"
                f"Video: {p['Video']}\n"
            )
            for p in products
        ])
        context = (
            f"The user is asking about '{user_query}'. Here are the matching products:\n"
            f"{product_details}\n"
            f"Now, engage with the user in witty price bargaining."
        )

        # Step 3: Get Llama response
        chatbot_reply = generate_llama_response(context)
    else:
        chatbot_reply = f"Sorry, I couldn't find any products matching '{user_query}'."

    # Respond back via Twilio
    twilio_client.messages.create(
        body=chatbot_reply,
        from_=TWILIO_WHATSAPP_NUMBER,
        to=phone_number
    )
    return jsonify({"status": "Message sent to user."})


@app.route('/status', methods=['GET'])
def status():
    return jsonify({"status": "The bot is running!"})

import logging

logging.basicConfig(level=logging.DEBUG)

@app.route('/twilio/webhook', methods=['POST'])
def twilio_webhook():
    logging.debug("Incoming webhook triggered.")
    data = request.form
    logging.debug(f"Webhook data: {data}")

if __name__ == "__main__":
    app.run(port=5000, debug=True)
