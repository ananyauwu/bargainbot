from flask import Flask, request, jsonify
import pandas as pd

app = Flask(__name__)

# Load product data
csv_file_path = "Bargain Bot Product List - Sheet1.csv"
product_data = pd.read_csv(csv_file_path)

def search_product(query):
    """Search for products in the CSV based on user query."""
    matches = product_data[product_data['Product Name'].str.contains(query, case=False, na=False)]
    if not matches.empty:
        response = ""
        for _, row in matches.iterrows():
            response += (
                f"Product: {row['Product Name']}\n"
                f"Category: {row['Catogory']}\n"
                f"MRP: {row['MRP']}\n"
                f"Minimum Price: {row['Minimum Retail Price']}\n"
                f"Units Available: {row['Units Available']}\n"
                f"Description: {row['Product Discription Summary']}\n"
                f"Image: {row['Product Image']}\n\n"
            )
        return response
    else:
        return "Sorry, no matching products found."

@app.route('/webhook', methods=['POST'])
def webhook():
    """Handle incoming requests from WhatsApp."""
    data = request.json
    if data.get('messages'):
        for message in data['messages']:
            phone_number = message['from']
            user_query = message['text']['body']

            response = search_product(user_query)

            return jsonify({
                "to": phone_number,
                "type": "text",
                "message": response
            })
    return jsonify({"status": "No messages received."})

if __name__ == "__main__":
    app.run(port=5000, debug=True)
