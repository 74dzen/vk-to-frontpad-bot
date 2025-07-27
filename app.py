from flask import Flask, request
import requests
import os
import json

app = Flask(__name__)

# 🔐 Значения из настроек
CONFIRMATION_TOKEN = "f4256a8f"  # VK требует вернуть это при подтверждении
VK_SECRET = os.getenv("VK_SECRET")
FRONTPAD_API_KEY = os.getenv("FRONTPAD_API_KEY")

if not FRONTPAD_API_KEY:
    raise ValueError("FRONTPAD_API_KEY is not set")
if not VK_SECRET:
    raise ValueError("VK_SECRET is not set")

@app.route("/", methods=["POST"])
def vk_callback():
    data = request.get_json()
    print("📥 Получен запрос от VK:\n", json.dumps(data, ensure_ascii=False, indent=2))

    # ✅ Подтверждение сервера VK
    if data.get("type") == "confirmation":
        print("✅ Подтверждение сервера VK")
        return CONFIRMATION_TOKEN

    # ⛔ Проверка секрета
    if data.get("secret") != VK_SECRET:
        print("❌ Неверный VK_SECRET!")
        return "access denied", 403

    # 📦 Обработка заказа
    if data.get("type") == "order_edit":
        order = data["object"]
        phone = order.get("phone", "")
        name = order.get("user_name", "Клиент из VK")
        items = order.get("items", [])

        payload = {
            "request": "add_order",
            "key": FRONTPAD_API_KEY,
            "phone": phone,
            "name": name,
            "source": "VK"
        }

        # Обрабатываем только товар с item_id = 123
        for idx, item in enumerate(items):
            if str(item["item_id"]) == "123":
                payload[f"items[{idx}][id]"] = "123"
                payload[f"items[{idx}][quantity]"] = item.get("quantity", 1)

        print("➡️ Отправляем заказ в FrontPad:\n", payload)
        response = requests.post("https://app.frontpad.ru/api/index.php", data=payload)
        print("🟢 Ответ от FrontPad:", response.text)

        return "ok"

    # 🚫 Обработка остальных типов
    print("⚠️ Неизвестный тип события:", data.get("type"))
    return "unsupported"
