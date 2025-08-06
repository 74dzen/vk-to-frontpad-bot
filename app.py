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
    logging.info("\U0001F4E5 Получен запрос от ВКонтакте: %s", data)

    if data.get("type") == "market_order_new" and data.get("secret") == VK_SECRET:
        order = data.get("object", {})
        recipient = order.get("recipient", {})
        delivery = order.get("delivery", {})
        comment = order.get("comment", "")
        items = order.get("preview_order_items", [])

        phone = recipient.get("phone", "").strip()
        name = recipient.get("name", "").strip()
        address = delivery.get("address", "").strip()

        logging.info(f"\U0001F4DD Комментарий из ВК: {comment}")

        if not phone or not name or not address:
            logging.error("❌ Ошибка: отсутствует имя, телефон или адрес")
            return "error"

        payload = {
            "secret": FRONTPAD_SECRET,
            "phone": phone,
            "name": name,
            "delivery_address": address,
            "comment": comment,
            "note": comment,
            "descr": comment
        }

        for i, item in enumerate(items):
            sku = str(item.get("item", {}).get("sku", "")).strip()
            qty = int(item.get("quantity", 1))

            logging.info(f"\U0001F575️ Проверка товара #{i}: sku={sku}, qty={qty}")

            if sku and qty > 0:
                payload[f"product[{i}]"] = sku
                payload[f"product_kol[{i}]"] = qty
                logging.info(f"➕ Товар: {sku} x{qty}")
            else:
                logging.warning(f"⚠️ Пропущен товар: {item}")

        logging.info("\U0001F4E6 Отправляем заказ в FrontPad...")

        try:
            for key, value in payload.items():
                logging.info(f"\U0001F4E4 {key}: {value}")

            response = requests.post("https://app.frontpad.ru/api/index.php?new_order", data=payload)
            logging.info("\U0001F4E4 Статус ответа от FrontPad: %s", response.status_code)
            logging.info("\U0001F4E4 Тело ответа от FrontPad (text): %s", response.text)

            if response.status_code == 200 and response.text != "null":
                logging.info("✅ Заказ успешно создан во FrontPad.")
            else:
                logging.error("❌ FrontPad вернул null. Проверь артикулы, номер телефона, настройки товаров и API-ключ.")

            return "ok"
        except Exception as e:
            logging.exception("❌ Ошибка при отправке заказа в FrontPad:")
            return "error"

    return "ok"
