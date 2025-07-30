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
        order = data.get("object", {})

        customer = order.get("customer", {})
        full_name = f"{customer.get('first_name', '')} {customer.get('last_name', '')}".strip() or "Без имени"
        phone = customer.get("phone", "")
        address = order.get("delivery_address", "")
        comment = order.get("comment", "")

        items = order.get("items", [])
        products = []
        for item in items:
            sku = item.get("sku")
            quantity = int(item.get("quantity", 1))
            if sku and sku.isdigit():
                products.append({"article": sku, "quantity": quantity})
            else:
                logging.warning(f"⚠️ Пропущен товар с невалидным SKU: {sku}")

        if not products:
            logging.warning("⚠️ Пустой список товаров. Пропускаем заказ.")
            return "ok"

        payload = {
            "secret": FRONTPAD_SECRET,
            "action": "new_order",
            "phone": phone,
            "name": full_name,
            "delivery_address": address,
            "comment": comment,
            "products": json.dumps(products, ensure_ascii=False),  # обязательно JSON-строка!
        }

        logging.info(f"📦 Отправляем заказ в FrontPad: {payload}")

        try:
            response = requests.post(FRONTPAD_API_URL, data=payload)
            response.encoding = "utf-8"
            logging.info(f"✅ Ответ от FrontPad: {response.text}")

            if response.text:
                try:
                    response_data = response.json()
                    if response_data.get("result") != "success":
                        logging.error(f"❌ Ошибка от FrontPad: {response_data.get('error')}")
                    else:
                        logging.info("🎉 Заказ успешно создан!")
                except Exception as e:
                    logging.error(f"❌ Ошибка при разборе JSON-ответа: {e}")
            else:
                logging.error("❌ FrontPad вернул пустой ответ (null).")

        except Exception as e:
            logging.exception("❌ Ошибка при запросе к FrontPad")

    return "ok"


@app.route("/", methods=["GET"])
def index():
    return "👋 Сервер работает!"


if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=5000)
