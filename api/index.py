from flask import Flask, request, jsonify
import json
import os
from datetime import datetime

app = Flask(__name__)

DATA_FILE = "/tmp/crusher_data.json"

def load_data():
    if not os.path.exists(DATA_FILE):
        return {"purchases": [], "usage": []}
    with open(DATA_FILE, "r") as f:
        return json.load(f)

def save_data(data):
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
        "category": req.get("category", "Uncategorized"),
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
    data = load_data()
    monthly = {}
    for u in data["usage"]:
        month = u["date"][:7] 
        monthly[month] = monthly.get(month, 0) + u["quantity"]
        
    labels = sorted(monthly.keys())
    chart_data = [monthly[m] for m in labels]
    return jsonify({"labels": labels, "data": chart_data})

@app.route('/api/history', methods=['GET'])
def get_history():
    data = load_data()
    return jsonify(data["purchases"])

@app.route('/api/suppliers', methods=['GET'])
def get_suppliers():
    data = load_data()
    suppliers = {}
    for p in data["purchases"]:
        name = p.get("supplier", "Unknown")
        suppliers.setdefault(name, {"source": p.get("source", ""), "total": 0, "count": 0})
        suppliers[name]["total"] += p.get("price", 0)
        suppliers[name]["count"] += 1
        
    supplier_list = [
        {"name": k, "source": v["source"], "count": v["count"], "total": v["total"]} 
        for k, v in suppliers.items()
    ]
    return jsonify(supplier_list)
