import os
import json
import logging
from flask import Flask, request
import requests
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)
logging.basicConfig(level=logging.INFO)

VK_CONFIRMATION = os.getenv("VK_CONFIRMATION")
FRONTPAD_SECRET = os.getenv("FRONTPAD_SECRET")

# Словарь соответствий SKU → артикул
sku_to_article = {f"{i:03d}": f"{i:03d}" for i in range(1, 182)}

@app.route("/", methods=["POST"])
def vk_callback():
    data = request.get_json()
    logging.info(f"📩 Получен запрос: {data}")

    if data.get("type") == "confirmation":
        return VK_CONFIRMATION

    if data.get("type") == "market_order_new":
        order = data["object"]
        items = order.get("items", [])
        if not items:
            logging.warning("⚠️ Пустой список товаров. Пропускаем заказ.")
            return "ok"

        products = []
        for item in items:
            sku = str(item.get("item", {}).get("sku", "")).strip()
            quantity = item.get("quantity", 1)
            article = sku_to_article.get(sku)

            if article:
                products.append({
                    "article": article,
                    "quantity": quantity
                })
            else:
                logging.warning(f"❗ SKU {sku} не найден в таблице соответствия.")

        if not products:
            logging.warning("⚠️ Ни одного подходящего товара. Пропускаем заказ.")
            return "ok"

        # Адрес
        address_data = order.get("recipient", {}).get("address", {})
        address_str = ""
        if isinstance(address_data, str):
            address_str = address_data
        elif isinstance(address_data, dict):
            address_str = f"{address_data.get('city', '')}, {address_data.get('street', '')}, {address_data.get('house', '')}"

        payload = {
            "secret": FRONTPAD_SECRET,
            "action": "new_order",
            "phone": order.get("recipient", {}).get("phone", ""),
            "name": order.get("recipient", {}).get("name", ""),
            "delivery_address": address_str.strip(", "),
            "comment": order.get("comment", ""),
            "products": json.dumps(products, ensure_ascii=False)
        }

        logging.info(f"📦 Отправляем заказ в FrontPad: {payload}")
        try:
            response = requests.post("https://app.frontpad.ru/api/index.php", data=payload)
            logging.info(f"✅ Ответ от FrontPad: {response.text}")
        except Exception as e:
            logging.exception(f"❌ Ошибка при запросе в FrontPad: {e}")

    return "ok"
