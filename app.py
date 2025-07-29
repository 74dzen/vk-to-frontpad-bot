import os
import json
import logging
import requests
from flask import Flask, request

app = Flask(__name__)
logging.basicConfig(level=logging.INFO)

VK_CONFIRMATION = os.environ.get("VK_CONFIRMATION")
VK_SECRET = os.environ.get("VK_SECRET")
FRONTPAD_SECRET = os.environ.get("FRONTPAD_SECRET")

# Таблица соответствия SKU и артикулов FrontPad
sku_to_article = {f"{i:03}": f"{i:03}" for i in range(1, 182)}

@app.route("/", methods=["POST"])
def vk_callback():
    data = request.get_json()
    logging.info(f"📥 Получен запрос: {data}")

    if data.get("type") == "confirmation":
        return VK_CONFIRMATION

    if data.get("secret") != VK_SECRET:
        logging.warning("⚠️ Неверный секретный ключ")
        return "invalid secret"

    if data.get("type") == "market_order_new":
        order = data.get("object", {})

        customer = order.get("customer", {})
        delivery = order.get("delivery", {})
        address_data = delivery.get("address", {}) if isinstance(delivery.get("address", {}), dict) else {}
        comment = order.get("comment", "")

        name = customer.get("name", "")
        phone = customer.get("phone", "")
        city = address_data.get("city", "")
        street = address_data.get("street", "")
        house = address_data.get("house", "")
        full_address = f"{city}, {street}, {house}".strip(", ")

        items = order.get("items", [])
        products = []

        for item in items:
            sku = str(item.get("sku", "")).strip()
            quantity = item.get("quantity", 1)
            article = sku_to_article.get(sku)
            if article:
                products.append({"article": article, "quantity": quantity})
            else:
                logging.warning(f"⚠️ Не найден артикул для SKU: {sku}")

        if not products:
            logging.warning("⚠️ Пустой список товаров. Пропускаем заказ.")
            return "no products"

        payload = {
            "secret": FRONTPAD_SECRET,
            "action": "new_order",
            "phone": phone,
            "name": name,
            "delivery_address": full_address,
            "comment": comment,
            "products": json.dumps(products, ensure_ascii=False),
        }

        logging.info(f"📦 Отправляем заказ в FrontPad: {payload}")
        response = requests.post("https://app.frontpad.ru/api/index.php", data=payload)
        try:
            response_data = response.json()
        except Exception as e:
            logging.error(f"❌ Ошибка при разборе ответа FrontPad: {e}")
            response_data = None

        logging.info(f"✅ Ответ от FrontPad: {response_data}")

        if not response_data:
            logging.error("❌ FrontPad не вернул ответ.")
        elif response_data.get("result") != "success":
            logging.error(f"❌ Ошибка от FrontPad: {response_data.get('error')}")

        return "ok"

    return "unsupported"
