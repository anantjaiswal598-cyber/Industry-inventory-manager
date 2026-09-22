from flask import Flask, request, jsonify
import json
import os
from datetime import datetime

app = Flask(__name__)

DATA_FILE = "/tmp/crusher_data.json"

def load_data():
    if not os.path.exists(DATA_FILE):
        return {"purchases": [], "usage": [], "suppliers": []}
    with open(DATA_FILE, "r") as f:
        data = json.load(f)
        
        # Auto-migrate: If 'suppliers' list doesn't exist yet, build it from old purchases
        if "suppliers" not in data:
            unique_suppliers = {}
            for p in data.get("purchases", []):
                name = p.get("supplier")
                if name and name not in unique_suppliers:
                    unique_suppliers[name] = p.get("source", "")
            data["suppliers"] = [{"name": k, "location": v} for k, v in unique_suppliers.items()]
            
        return data

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
    supplier_name = req.get("supplier")
    source = req.get("source", "")
    
    # Auto-add supplier to master list if it's new
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
    stats = {}
    # Count purchase totals for each supplier
    for p in data["purchases"]:
        name = p.get("supplier", "Unknown")
        stats.setdefault(name, {"count": 0, "total": 0})
        stats[name]["count"] += 1
        stats[name]["total"] += p.get("price", 0)
        
    # Combine with master list
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
    
    if action == "add":
        location = req.get("location", "")
        if not any(s["name"].lower() == name.lower() for s in data["suppliers"]):
            data["suppliers"].append({"name": name, "location": location})
    elif action == "delete":
        # Removes supplier from master list (keeps old purchase records intact)
        data["suppliers"] = [s for s in data["suppliers"] if s["name"].lower() != name.lower()]
        
    save_data(data)
    return jsonify({"message": "Success"})
