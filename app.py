from flask import Flask, request
import requests
import os

app = Flask(__name__)

FRONTPAD_SECRET = os.environ.get("FRONTPAD_SECRET")
VK_CONFIRMATION = os.environ.get("VK_CONFIRMATION")

# Таблица соответствий SKU (ВК) и артикулов (FrontPad)
sku_to_article = {f"{i:03}": f"{i:03}" for i in range(1, 182)}  # 001–181

def create_order_in_frontpad(name, phone, sku):
    article = sku_to_article.get(sku)
    if not article:
        return {"error": f"Артикул для SKU {sku} не найден."}

    payload = {
        "secret": FRONTPAD_SECRET,
        "phone": phone,
        "name": name,
        "products": [
            {
                "article": article,
                "quantity": 1
            }
        ]
    }

    response = requests.post("https://app.frontpad.ru/api/index.php?new_order", json=payload)
    try:
        return response.json()
    except Exception:
        return {"error": "Некорректный ответ от FrontPad", "raw": response.text}

@app.route('/', methods=['POST'])
def vk_webhook():
    data = request.get_json()

    if data.get("type") == "confirmation":
        return VK_CONFIRMATION

    if data.get("type") == "market_order_new":
        order = data["object"]
        user_name = f"{order.get('first_name', '')} {order.get('last_name', '')}".strip()
        phone = order.get("delivery_phone", "")
        items = order.get("items", [])

        results = []
        for item in items:
            sku = item.get("sku") or item.get("item_id") or ""
            result = create_order_in_frontpad(user_name, phone, sku)
            results.append({sku: result})

        return {"status": "ok", "results": results}

    return "ok"

if __name__ == '__main__':
    app.run()

