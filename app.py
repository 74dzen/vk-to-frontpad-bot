import os
import json
import logging
from flask import Flask, request
import requests
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)
logging.basicConfig(level=logging.INFO)

FRONTPAD_API_URL = "https://app.frontpad.ru/api/index.php"
FRONTPAD_SECRET = os.getenv("FRONTPAD_SECRET")
CONFIRMATION_TOKEN = os.getenv("VK_CONFIRMATION")

@app.route("/", methods=["POST"])
def vk_callback():
    data = request.json
    logging.info(f"📩 Получен callback от VK: {json.dumps(data, ensure_ascii=False)}")

    if data.get("type") == "confirmation":
        return CONFIRMATION_TOKEN

    if data.get("type") == "market_order_new":
        order = data["object"]

        customer = order.get("customer", {})
        first_name = customer.get("first_name", "")
        last_name = customer.get("last_name", "")
        phone = customer.get("phone", "")
        full_name = f"{first_name} {last_name}".strip() or "Без имени"

        address = order.get("delivery_address", "")
        note = order.get("comment", "")

        items = order.get("items", [])
        if not items:
            logging.warning("⚠️ Пустой список товаров. Пропускаем заказ.")
            return "ok"

        products = []
        for item in items:
            sku = item.get("sku", "").strip()
            quantity = int(item.get("quantity", 1))
            if sku and sku.isdigit():
                products.append({"article": sku, "quantity": quantity})
            else:
                logging.warning(f"⚠️ Пропущен товар с невалидным SKU: {sku}")

        if not products:
            logging.warning("⚠️ Не удалось собрать ни одного товара. Пропускаем заказ.")
            return "ok"

        payload = {
            "secret": FRONTPAD_SECRET,
            "action": "new_order",
            "phone": phone,
            "name": full_name,
            "delivery_address": address,
            "comment": note,
            "products": json.dumps(products, ensure_ascii=False),  # ВАЖНО: JSON-строка!
        }

        logging.info(f"📦 Отправляем заказ в FrontPad: {payload}")

        try:
            response = requests.post(FRONTPAD_API_URL, data=payload)
            response.encoding = "utf-8"
            logging.info(f"✅ Ответ от FrontPad: {response.text}")

            try:
                response_data = response.json()
            except Exception as e:
                logging.error(f"❌ Ошибка разбора JSON: {e}")
                return "ok"

            if response_data.get("result") != "success":
                logging.error(f"❌ Ошибка от FrontPad: {response_data.get('error')}")
            else:
                logging.info("🎉 Заказ успешно создан!")

        except Exception as e:
            logging.exception("❌ Ошибка при отправке заказа в FrontPad:")

    return "ok"

@app.route("/", methods=["GET"])
def index():
    return "👋 FrontPad VK интеграция активна."

if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=5000)
