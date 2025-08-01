import os
import logging
from flask import Flask, request
from dotenv import load_dotenv
import requests

load_dotenv()

app = Flask(__name__)
logging.basicConfig(level=logging.INFO)

FRONTPAD_SECRET = os.getenv("FRONTPAD_SECRET")
VK_SECRET = os.getenv("VK_SECRET")

@app.route("/", methods=["POST"])
def vk_callback():
    data = request.get_json()
    logging.info("📥 Получен запрос от ВКонтакте: %s", data)

    if data.get("type") == "market_order_new" and data.get("secret") == VK_SECRET:
        order = data.get("object", {})
        recipient = order.get("recipient", {})
        delivery = order.get("delivery", {})
        comment = order.get("comment", "")
        items = order.get("preview_order_items", [])

        payload = {
            "secret": FRONTPAD_SECRET,
            "phone": recipient.get("phone", "не указан"),
            "name": recipient.get("name", "не указано"),
            "delivery_address": delivery.get("address", "не указан"),
            "comment": comment
        }

        for i, item in enumerate(items):
            sku = item.get("item", {}).get("sku")
            qty = item.get("quantity", 1)
            if sku and qty:
                payload[f"product[{i}]"] = sku
                payload[f"product_kol[{i}]"] = qty
                logging.info(f"➕ Товар: {sku} x{qty}")
            else:
                logging.warning(f"⚠️ Пропущен товар: {item}")

        logging.info("📦 Отправляем заказ в FrontPad: %s", payload)

        try:
            response = requests.post("https://app.frontpad.ru/api/index.php?new_order", data=payload)
            logging.info("📤 Статус ответа от FrontPad: %s", response.status_code)
            logging.info("📤 Тело ответа от FrontPad (text): %s", response.text)
            return "ok"
        except Exception as e:
            logging.exception("❌ Ошибка при отправке заказа в FrontPad:")
            return "error"

    return "ok"
