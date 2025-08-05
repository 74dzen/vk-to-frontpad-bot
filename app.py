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

    if data.get("type") in ["market_order_new", "market_order_edit"] and data.get("secret") == VK_SECRET:
        order = data.get("object", {})
        recipient = order.get("recipient", {})
        delivery = order.get("delivery", {})
        comment = order.get("comment", "")

        # ✅ Берем preview_order_items приоритетно
        items = order.get("preview_order_items") or order.get("items", [])

        logging.info(f"🔢 Кол-во товаров в заказе: {len(items)}")
        logging.info(f"🧾 Список всех товаров: {items}")

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
            logging.info(f"🧩 Товар #{i}: {item}")

            # Универсальный доступ к SKU
            if isinstance(item, dict):
                item_data = item.get("item", item)
            else:
                logging.warning(f"⚠️ Неверный формат item: {item}")
                continue

            sku = str(item_data.get("sku", "")).strip()
            qty = int(item.get("quantity", 1))

            if not sku:
                logging.warning(f"⚠️ SKU не найден в товаре: {item}")
                continue

            logging.info(f"🕵️ Проверка товара #{i}: sku={sku}, qty={qty}")
            payload[f"product[{i}]"] = sku
            payload[f"product_kol[{i}]"] = qty

        logging.info("📦 Отправляем заказ в FrontPad...")

        try:
            for key, value in payload.items():
                logging.info(f"📤 {key}: {value}")

            response = requests.post("https://app.frontpad.ru/api/index.php?new_order", data=payload)
            logging.info("📤 Статус ответа от FrontPad: %s", response.status_code)
            logging.info("📤 Тело ответа от FrontPad (text): %s", response.text)

            if response.status_code == 200 and response.text != "null":
                logging.info("✅ Заказ успешно создан во FrontPad.")
            else:
                logging.error("❌ FrontPad вернул null. Проверь артикулы, номер телефона, настройки товаров и API-ключ.")

            return "ok"
        except Exception as e:
            logging.exception("❌ Ошибка при отправке заказа в FrontPad:")
            return "error"

    return "ok"
