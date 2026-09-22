from flask import Flask, request, jsonify
import json
import os
from datetime import datetime

app = Flask(__name__)

DATA_FILE = "/tmp/crusher_data.json"

def load_data():
    """Load saved data from the JSON file."""
    if not os.path.exists(DATA_FILE):
        return {"purchases": [], "usage": []}
    with open(DATA_FILE, "r") as f:
        return json.load(f)

def save_data(data):
    """Write all data back to the JSON file."""
    with open(DATA_FILE, "w") as f:
        json.dump(data, f, indent=2)

@app.route('/api/stock', methods=['GET'])
def get_stock():
    data = load_data()
    stock = {}
    units = {}

    for p in data["purchases"]:
        stock[p["item"]] = stock.get(p["item"], 0) + p["quantity"]
        units[p["item"]] = p["unit"]

    for u in data["usage"]:
        if u["item"] in stock:
            stock[u["item"]] -= u["quantity"]

    stock_list = [{"item": k, "remaining": v, "unit": units.get(k, "")} for k, v in stock.items()]
    return jsonify(stock_list)

@app.route('/api/purchase', methods=['POST'])
def add_purchase():
    data = load_data()
    req = request.json
    
    data["purchases"].append({
        "date": req.get("date") or datetime.now().strftime("%Y-%m-%d"),
        "category": req.get("category", "Uncategorized"),  # NEW FIELD
        "item": req.get("item"),
        "supplier": req.get("supplier"),
        "source": req.get("source"),
        "quantity": float(req.get("quantity", 0)),
        "unit": req.get("unit"),
        "price": float(req.get("price", 0)),
    })
    save_data(data)
    return jsonify({"message": "Purchase saved successfully."})

@app.route('/api/usage', methods=['POST'])
def add_usage():
    data = load_data()
    req = request.json
    
    data["usage"].append({
        "date": req.get("date") or datetime.now().strftime("%Y-%m-%d"),
        "item": req.get("item"),
        "quantity": float(req.get("quantity", 0)),
        "purpose": req.get("purpose"),
    })
    save_data(data)
    return jsonify({"message": "Usage saved successfully."})

@app.route('/api/monthly_usage', methods=['GET'])
def get_monthly_usage():
    """Aggregates all usage quantities grouped by YYYY-MM for the chart."""
    data = load_data()
    monthly = {}
    
    for u in data["usage"]:
        month = u["date"][:7]  # Extracts just "YYYY-MM" from "YYYY-MM-DD"
        monthly[month] = monthly.get(month, 0) + u["quantity"]
        
    # Sort the months chronologically
    labels = sorted(monthly.keys())
    chart_data = [monthly[m] for m in labels]
    
    return jsonify({"labels": labels, "data": chart_data})

@app.route('/api/history', methods=['GET'])
def get_history():
    data = load_data()
    return jsonify(data["purchases"])
