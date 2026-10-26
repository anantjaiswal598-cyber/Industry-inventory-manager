from flask import Flask, request, jsonify
import json
import os
from datetime import datetime

app = Flask(__name__)

DATA_FILE = "/tmp/crusher_data.json"

USERS = {
    "admin": {"password": "admin123", "role": "admin"},
    "staff": {"password": "staff123", "role": "staff"}
}

def load_data():
    if not os.path.exists(DATA_FILE):
        return {"purchases": [], "usage": [], "suppliers": []}
    try:
        with open(DATA_FILE, "r") as f:
            data = json.load(f)
            if "suppliers" not in data:
                data["suppliers"] = []
            return data
    except Exception:
        return {"purchases": [], "usage": [], "suppliers": []}

def save_data(data):
    with open(DATA_FILE, "w") as f:
        json.dump(data, f, indent=2)

@app.route('/api/login', methods=['POST'])
def login():
    req = request.json
    username = req.get("username", "").lower()
    password = req.get("password", "")
    
    user = USERS.get(username)
    if user and user["password"] == password:
        return jsonify({"success": True, "role": user["role"]})
    return jsonify({"success": False, "message": "Invalid credentials"}), 401

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
    
    stock_list = []
    for k, v in stock.items():
        status = "Normal"
        if v < 50:
            status = "Low Stock"
        if v <= 0:
            status = "Out of Stock"
            
        stock_list.append({
            "item": k, 
            "remaining": v, 
            "unit": units.get(k, ""),
            "status": status
        })
    return jsonify(stock_list)

@app.route('/api/purchase', methods=['POST'])
def add_purchase():
    data = load_data()
    req = request.json
    supplier_name = req.get("supplier")
    source = req.get("source", "")
    
    if supplier_name and not any(s["name"].lower() == supplier_name.lower() for s in data["suppliers"]):
        data["suppliers"].append({"name": supplier_name, "location": source})
        
    data["purchases"].append({
        "date": req.get("date") or datetime.now().strftime("%Y-%m-%d"),
        "category": req.get("category", "Uncategorized"),
        "item": req.get("item"),
        "supplier": supplier_name,
        "source": source,
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
        purpose = u.get("purpose", "Other") 
        monthly[purpose] = monthly.get(purpose, 0) + u["quantity"]
        
    labels = list(monthly.keys())
    chart_data = list(monthly.values())
    return jsonify({"labels": labels, "data": chart_data})

@app.route('/api/history', methods=['GET'])
def get_history():
    data = load_data()
    return jsonify(data["purchases"])

@app.route('/api/suppliers', methods=['GET'])
def get_suppliers():
    data = load_data()
    stats = {}
    for p in data["purchases"]:
        name = p.get("supplier", "Unknown")
        stats.setdefault(name, {"count": 0, "total": 0})
        stats[name]["count"] += 1
        stats[name]["total"] += p.get("price", 0)
        
    result = []
    for s in data["suppliers"]:
        name = s["name"]
        result.append({
            "name": name,
            "location": s.get("location", ""),
            "count": stats.get(name, {}).get("count", 0),
            "total": stats.get(name, {}).get("total", 0)
        })
    return jsonify(result)

@app.route('/api/supplier_action', methods=['POST'])
def manage_supplier():
    data = load_data()
    req = request.json
    action = req.get("action")
    name = req.get("name")
    role = req.get("role")
    
    if action == "add":
        location = req.get("location", "")
        if not any(s["name"].lower() == name.lower() for s in data["suppliers"]):
            data["suppliers"].append({"name": name, "location": location})
    elif action == "delete":
        if role != "admin":
            return jsonify({"error": "Unauthorized"}), 403
        data["suppliers"] = [s for s in data["suppliers"] if s["name"].lower() != name.lower()]
        
    save_data(data)
    return jsonify({"message": "Success"})
