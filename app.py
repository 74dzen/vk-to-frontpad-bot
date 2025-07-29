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

# Словарь соответствий SKU → Артикул
sku_to_article = {f"{i:03d}": f"{i:03d}" for i in range(1, 182)}

@app.route("/", methods=["POST"])
def vk_callback():
    data = request.json
    logging.info(f"📩 Получено событие от ВК: {data}")

    if data.get("type") == "confirmation":
        return VK_CONFIRMATION

    if data.get("type") in ["market_order_new", "market_order_edit"]:
        order_data = data.get("object", {})
        customer = order_data.get("customer", {})
        name = f"{customer.get('first_name', '')} {customer.get('last_name', '')}".strip()
        phone = customer.get("phone", "")
        address_data = order_data.get("delivery", {}).get("address", "Челябинск")
        comment = order_data.get("comment", "Заказ из ВКонтакте")

        items = order_data.get("items", [])
        logging.info(f"📦 Список товаров в заказе: {items}")

        products_list = []
        for item in items:
            sku = item.get("sku")
            quantity = item.get("quantity", 1)
            if not sku:
                logging.warning(f"⚠️ У товара нет SKU: {item}")
                continue
            article = sku_to_article.get(sku)
            if article:
                products_list.append({"article": article, "quantity": quantity})
            else:
                logging.warning(f"⚠️ Не найден артикул для SKU: {sku}")

        if not products_list:
            logging.warning("⚠️ Пустой список товаров. Пропускаем заказ.")
            return "ok"

        payload = {
            "secret": FRONTPAD_SECRET,
            "action": "new_order",
            "phone": phone,
            "name": name or "Клиент из ВК",
            "delivery_address": address_data,
            "comment": comment,
            "products": json.dumps(products_list)  # сериализуем в строку!
        }

        logging.info(f"📦 Отправляем заказ в FrontPad: {payload}")

        try:
            response = requests.post("https://app.frontpad.ru/api/index.php", json=payload)
            response_data = response.json()
        except Exception as e:
            logging.error(f"❌ Ошибка при запросе в FrontPad: {e}")
            return "ok"

        logging.info(f"✅ Ответ от FrontPad: {response_data}")

        if not response_data:
            logging.error("❌ Пустой ответ от FrontPad")
        elif response_data.get("result") != "success":
            logging.error(f"❌ Ошибка от FrontPad: {response_data.get('error')}")

    return "ok"
