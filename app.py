import os
import json
import logging
from flask import Flask, request
from dotenv import load_dotenv
import requests

load_dotenv()

app = Flask(__name__)
logging.basicConfig(level=logging.INFO)

# Константы из .env
VK_CONFIRMATION = os.getenv("VK_CONFIRMATION")
FRONTPAD_SECRET = os.getenv("FRONTPAD_SECRET")

# Таблица соответствий SKU (VK) → артикул (FrontPad)
sku_to_article = {f"{i:03}": f"{i:03}" for i in range(1, 182)}

@app.route("/", methods=["POST"])
def vk_callback():
    data = request.get_json()
    logging.info(f"📩 Получены данные от VK: {json.dumps(data, ensure_ascii=False)}")

    if "type" not in data:
        return "no_type"

    if data["type"] == "confirmation":
        return VK_CONFIRMATION

    elif data["type"] == "market_order_new":
        try:
            order_data = data.get("object", {}).get("order", {})
            if not order_data:
                logging.warning("⚠️ Нет данных заказа в object.order.")
                return "no_order"

            # Извлекаем информацию о товарах
            items = order_data.get("items", [])
            if not items:
                logging.warning("⚠️ Пустой список товаров. Пропускаем заказ.")
                return "no_items"

            # Преобразуем товары
            products = []
            for item in items:
                sku = str(item.get("item", {}).get("sku", "")).zfill(3)
                article = sku_to_article.get(sku)
                if not article:
                    logging.warning(f"⚠️ Неизвестный SKU: {sku}. Пропускаем товар.")
                    continue
                quantity = item.get("quantity", 1)
                products.append({
                    "article": article,
                    "quantity": quantity
                })

            if not products:
                logging.warning("⚠️ Все товары были пропущены из-за отсутствия соответствий.")
                return "no_valid_products"

            # Адрес
            address_data = order_data.get("address", {})
            address = ", ".join(filter(None, [
                address_data.get("country"),
                address_data.get("city"),
                address_data.get("street"),
                address_data.get("house"),
                address_data.get("block"),
                address_data.get("flat")
            ])) or "Адрес не указан"

            payload = {
                "secret": FRONTPAD_SECRET,
                "action": "new_order",
                "phone": order_data.get("phone", ""),
                "name": order_data.get("display_user_name", ""),
                "delivery_address": address,
                "comment": order_data.get("comment", ""),
                "products": json.dumps(products, ensure_ascii=False)
            }

            logging.info(f"📦 Отправляем заказ в FrontPad: {payload}")
            response = requests.post("https://app.frontpad.ru/api/index.php", data=payload)
            try:
                response_data = response.json()
                logging.info(f"✅ Ответ от FrontPad: {response_data}")
                if response_data.get("result") != "success":
                    logging.error(f"❌ Ошибка от FrontPad: {response_data.get('error')}")
            except Exception as e:
                logging.error(f"❌ Ошибка при разборе ответа от FrontPad: {e}")
                logging.error(f"↩️ Ответ от сервера: {response.text}")

        except Exception as e:
            logging.exception("💥 Ошибка при обработке заказа.")

    return "ok"

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
