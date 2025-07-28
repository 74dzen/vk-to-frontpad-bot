from flask import Flask, request
import requests
import os
import json

app = Flask(__name__)

# Подтверждение сервера ВКонтакте
VK_CONFIRMATION_TOKEN = '3a6a509a'

# Ключи от FrontPad
FRONTPAD_API_KEY = os.getenv("FRONTPAD_API_KEY")
FRONTPAD_SECRET = os.getenv("FRONTPAD_SECRET")

@app.route("/", methods=["POST"])
def handle_vk_event():
    data = request.get_json()
    if not data:
        print("🔴 Нет данных в запросе")
        return "no data"

    event_type = data.get("type")
    print(f"📥 Получен event: {event_type}")

    if event_type == "confirmation":
        return VK_CONFIRMATION_TOKEN

    elif event_type == "market_order_new":
        try:
            order = data["object"]
            recipient = order["recipient"]
            phone = recipient.get("phone", "")
            name = recipient.get("name", "")
            comment = order.get("comment", "")
            address = order["delivery"].get("address", "")
            order_items = order["preview_order_items"]

            print(f"🛒 Заказ от {name} ({phone}), адрес: {address}")
            print(f"📝 Комментарий: {comment}")
            print(f"📦 Товары: {json.dumps(order_items, ensure_ascii=False)}")

            payload = {
                "request": "add_order",
                "key": FRONTPAD_API_KEY,
                "secret": FRONTPAD_SECRET,
                "phone": phone,
                "name": name,
                "address": address,
                "comment": comment,
                "source": "VK"
            }

            added_products = 0
            for idx, item in enumerate(order_items):
                sku = item.get("item", {}).get("sku")
                quantity = item.get("quantity", 1)

                if sku:
                    payload[f"product[{added_products}]"] = sku
                    payload[f"count[{added_products}]"] = quantity
                    added_products += 1
                else:
                    print("⚠️ Пропущен товар без артикла:", item)

            print(f"📤 Отправка в FrontPad: {payload}")
            response = requests.post("https://app.frontpad.ru/api/index.php", data=payload)
            print("🟢 Ответ от FrontPad:", response.text)
            return "ok"

        except Exception as e:
            print("🔴 Ошибка обработки заказа:", str(e))
            return "error"

    else:
        print("⚠️ Необработанный тип события:", event_type)

    return "unsupported"

@app.route("/", methods=["GET"])
def index():
    return "VK-Fronpad connector is working!"
