import os
import logging
from flask import Flask, request
import requests
from dotenv import load_dotenv

load_dotenv()
logging.basicConfig(level=logging.INFO)

app = Flask(__name__)

FRONTPAD_SECRET = os.getenv("FRONTPAD_SECRET")

# Сопоставление SKU <-> артикул (SKU = артикул)
ARTICLE_MAP = {f"{i:03}": f"{i:03}" for i in range(1, 182)}

@app.route("/", methods=["POST"])
def vk_callback():
    data = request.get_json()
    logging.info(f"📥 Получен запрос от ВКонтакте: {data}")

    if data.get("type") == "market_order_new":
        order = data["object"]
        recipient = order.get("recipient", {})
        delivery = order.get("delivery", {})
        items = order.get("preview_order_items", [])

        name = recipient.get("name", "")
        phone = recipient.get("phone", "")
        address = delivery.get("address", "")
        comment = order.get("comment", "")

        products = []
        for item in items:
            sku = item.get("item", {}).get("sku")
            quantity = item.get("quantity", 1)
            if not sku:
                logging.warning(f"❌ Нет SKU у товара: {item}")
                continue
            article = ARTICLE_MAP.get(sku)
            if not article:
                logging.warning(f"❌ SKU {sku} не найден в таблице!")
                continue
            products.append((article, quantity))

        if not products:
            logging.warning("⚠️ Пустой список товаров. Пропускаем заказ.")
            return "ok"

        # Формирование data-полей, как требует FrontPad
        payload = {
            "secret": FRONTPAD_SECRET,
            "action": "new_order",
            "phone": phone,
            "name": name,
            "delivery_address": address,
            "comment": comment
        }

        for i, (article, qty) in enumerate(products):
            payload[f"product[{i}]"] = article
            payload[f"product_kol[{i}]"] = qty

        logging.info(f"📦 Отправляем заказ в FrontPad: {payload}")

        try:
            response = requests.post("https://app.frontpad.ru/api/index.php", data=payload)
            logging.info(f"📤 Статус ответа от FrontPad: {response.status_code}")
            logging.info(f"📤 Тело ответа от FrontPad (text): {response.text}")
            try:
                json_resp = response.json()
                logging.info(f"✅ Ответ от FrontPad (json): {json_resp}")
            except Exception:
                logging.warning("⚠️ Ответ не в JSON формате")
        except Exception as e:
            logging.exception(f"🚨 Ошибка при отправке запроса в FrontPad: {e}")

    return "ok"
