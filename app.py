import os
import logging
from flask import Flask, request
from dotenv import load_dotenv
import requests
import json

load_dotenv()

app = Flask(__name__)
logging.basicConfig(level=logging.INFO)

FRONTPAD_SECRET = os.getenv("FRONTPAD_SECRET")
VK_SECRET = os.getenv("VK_SECRET")

@app.route("/", methods=["POST"])
def vk_callback():
    data = request.get_json()
    logging.info("📥 Получен запрос от ВКонтакте: %s", json.dumps(data, ensure_ascii=False, indent=2))

    if data.get("type") in ["market_order_new", "market_order_edit"] and data.get("secret") == VK_SECRET:
        order = data.get("object", {})
        recipient = order.get("recipient", {})
        delivery = order.get("delivery", {})
        comment = order.get("comment", "")

        # Берем только preview_order_items
        items = order.get("preview_order_items", [])
        logging.info(f"🔢 Фактическое количество товаров: {len(items)}")

        phone = recipient.get("phone", "").strip()
        name = recipient.get("name", "").strip()
        address = delivery.get("address", "").strip()

        if not phone or not name or not address:
            logging.error("❌ Ошибка: отсутствует имя, телефон или адрес")
            return "error"

        payload = {
            "secret": FRONTPAD_SECRET,
            "phone": phone,
            "name": name,
            "delivery_address": address,
            "comment": comment
        }

        for i, item in enumerate(items):
            logging.info(f"\n🧩 Товар #{i} полный: {json.dumps(item, ensure_ascii=False)}")

            if not isinstance(item, dict):
                logging.warning(f"⚠️ Неверный формат товара #{i}: {item}")
                continue

            item_data = item.get("item", item)  # поддержка структуры {item: {sku:...}} и просто {sku:...}
            sku = str(item_data.get("sku", "")).strip()
            qty = int(item.get("quantity", 1))

            logging.info(f"🔍 Обработан товар #{i}: sku='{sku}', qty={qty}")

            if not sku:
                logging.warning(f"⛔️ Пропущен товар #{i} — пустой или отсутствует SKU")
                continue

            payload[f"product[{i}]"] = sku
            payload[f"product_kol[{i}]"] = qty
            logging.info(f"📦 Добавлен в заказ: {sku} x{qty}")

        logging.info("\n📤 Полный payload для FrontPad:")
        for key, value in payload.items():
            logging.info(f"    {key}: {value}")

        logging.info("📡 Отправляем заказ в FrontPad...")

        try:
            response = requests.post("https://app.frontpad.ru/api/index.php?new_order", data=payload)
            logging.info("📤 Статус ответа: %s", response.status_code)
            logging.info("📤 Тело ответа: %s", response.text)

            if response.status_code == 200 and response.text != "null":
                logging.info("✅ Заказ успешно создан во FrontPad.")
            else:
                logging.error("❌ Ошибка: FrontPad вернул null. Проверь артикулы, настройки и API-ключ.")

            return "ok"
        except Exception as e:
            logging.exception("❌ Ошибка при отправке запроса в FrontPad:")
            return "error"

    return "ok"
