from flask import Flask, request, jsonify
import pandas as pd
import requests

app = Flask(__name__)

# Load product data from CSV
CSV_FILE = "Bargain Bot Product List - Sheet1.csv"
product_data = pd.read_csv(CSV_FILE)

# Llama Model API Configuration
LLAMA_API_URL = "https://llama-api-endpoint.com/v1/chat"  # Replace with your Llama API endpoint
LLAMA_API_KEY = "your-llama-api-key"  # Replace with your API key


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
            {"role": "system", "content": "You are a witty price-bargaining chatbot."},
            {"role": "user", "content": context}
        ]
    }

    response = requests.post(LLAMA_API_URL, headers=headers, json=payload)
    if response.status_code == 200:
        return response.json().get("choices", [])[0].get("message", {}).get("content", "Sorry, I couldn't come up with a reply.")
    else:
        return "Error communicating with the Llama API."


@app.route('/webhook', methods=['POST'])
def webhook():
    data = request.json
    if data.get('messages'):
        for message in data['messages']:
            phone_number = message['from']
            user_query = message['text']['body']

            # Step 1: Search for the product
            products = search_product(user_query)

            if products:
                # Step 2: Dynamically construct product context
                product_details = "\n".join([
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

            # Respond back
            return jsonify({
                "to": phone_number,
                "type": "text",
                "message": chatbot_reply
            })
    return jsonify({"status": "No messages received."})


if __name__ == "__main__":
    app.run(port=5000, debug=True)
