import os
import json
import logging
from flask import Flask, request
from dotenv import load_dotenv
import requests

load_dotenv()

app = Flask(__name__)
logging.basicConfig(level=logging.INFO)

VK_CONFIRMATION = os.getenv("VK_CONFIRMATION")
FRONTPAD_SECRET = os.getenv("FRONTPAD_SECRET")

# Таблица соответствий SKU -> Артикул (001–181)
sku_to_article = {f"{i:03}": f"{i:03}" for i in range(1, 182)}

@app.route("/", methods=["POST"])
def vk_callback():
    data = request.json

    if data.get("type") == "confirmation":
        return VK_CONFIRMATION

    if data.get("type") != "market_order_new":
        return "ok"

    order = data.get("object", {})

    phone = order.get("phone", "")
    name = order.get("display_user_name", "")
    comment = order.get("comment", "")
    address_data = order.get("address", {})

    if isinstance(address_data, dict):
        city = address_data.get("city", "")
        street = address_data.get("street", "")
        address_str = f"{city}, {street}".strip(", ")
    else:
        address_str = ""

    items = order.get("items", [])
    if not items:
        logging.warning("⚠️ Пустой список товаров. Пропускаем заказ.")
        return "ok"

    products = []
    for item in items:
        sku = str(item.get("sku", "")).strip()
        quantity = int(item.get("quantity", 1))

        article = sku_to_article.get(sku)
        if article:
            products.append({
                "article": article,
                "quantity": quantity
            })

    if not products:
        logging.warning("⚠️ Не найдено ни одного соответствующего артикула. Пропускаем заказ.")
        return "ok"

    payload = {
        "secret": FRONTPAD_SECRET,
        "action": "new_order",
        "phone": phone,
        "name": name,
        "delivery_address": address_str,
        "comment": comment,
        "products": json.dumps(products, ensure_ascii=False)
    }

    logging.info(f"📦 Отправляем заказ в FrontPad: {payload}")
    try:
        response = requests.post("https://app.frontpad.ru/api/index.php", data=payload)
        response_data = response.json()
        logging.info(f"✅ Ответ от FrontPad: {response_data}")
        if response_data.get("result") != "success":
            logging.error(f"❌ Ошибка от FrontPad: {response_data.get('error')}")
    except Exception as e:
        logging.exception("❌ Ошибка при отправке заказа в FrontPad")

    return "ok"
