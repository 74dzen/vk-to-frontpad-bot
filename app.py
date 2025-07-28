import os
import json
import requests
from flask import Flask, request

app = Flask(__name__)

FRONTPAD_SECRET = os.getenv("FRONTPAD_SECRET")
FRONTPAD_URL = "https://app.frontpad.ru/api/index.php"

VK_SECRET = os.getenv("VK_SECRET", "3223")  # на всякий случай
TARGET_SKU = "123"

@app.route("/", methods=["POST"])
def handle_vk_callback():
    data = request.get_json()
    print("🔔 Входящий webhook от VK:")
    print(json.dumps(data, ensure_ascii=False, indent=2))

    # Проверка секрета
    if data.get("secret") != VK_SECRET:
        print("⛔ Неверный секрет.")
        return "access denied", 403

    # Ответ для подтверждения сервера
    if data.get("type") == "confirmation":
        return os.getenv("VK_CONFIRMATION", "no_confirmation_code")

    # Обработка нового заказа
    if data.get("type") == "market_order_new":
        order = data.get("object", {})

        recipient = order.get("recipient", {})
        phone = recipient.get("phone", "")
        name = recipient.get("name", "")
        comment = order.get("comment", "")

        delivery_address = order.get("delivery", {}).get("address", "")

        items = order.get("preview_order_items", [])
        order_items = []
        for item in items:
            sku = item.get("item", {}).get("sku", "")
            if sku != TARGET_SKU:
                print(f"⚠️ Пропущен товар с SKU: {sku}")
                continue
            quantity = item.get("quantity", 1)
            order_items.append(f"{sku}:{quantity}")

        if not order_items:
            print("❌ Нет подходящих товаров для отправки во FrontPad.")
            return "ok"

        payload = {
            "secret": FRONTPAD_SECRET,
            "phone": phone,
            "name": name,
            "address": delivery_address,
            "comment": comment,
            "products": ";".join(order_items),
            "client_time": str(order.get("date", "")),
            "action": "new_order"
        }

        print("📦 Отправка заказа во FrontPad:")
        print(payload)

        try:
            response = requests.post(FRONTPAD_URL, data=payload, timeout=10)
            print("✅ Ответ от FrontPad:", response.text)
        except Exception as e:
            print("🔥 Ошибка при отправке запроса в FrontPad:", str(e))

    return "ok"
