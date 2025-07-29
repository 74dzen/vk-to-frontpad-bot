import os
import json
import logging
import requests
from flask import Flask, request
from dotenv import load_dotenv

load_dotenv()
app = Flask(__name__)
logging.basicConfig(level=logging.INFO)

VK_CONFIRMATION = os.getenv("VK_CONFIRMATION")
FRONTPAD_SECRET = os.getenv("FRONTPAD_SECRET")

# Таблица соответствий SKU → артикул (просто один в один от 001 до 181)
sku_to_article = {f"{i:03}": f"{i:03}" for i in range(1, 182)}

@app.route("/", methods=["POST"])
def vk_callback():
    data = request.get_json()
    logging.info(f"📩 Получены данные от VK: {json.dumps(data, ensure_ascii=False)}")

    if not data or "type" not in data:
        return "invalid"

    if data["type"] == "confirmation":
        return VK_CONFIRMATION

    if data["type"] == "market_order_new":
        try:
            order = data.get("object", {}).get("order", {})
            items = order.get("items", [])
            if not items:
                logging.warning("⚠️ Пустой список товаров. Пропускаем заказ.")
                return "no_items"

            # Правильное формирование списка товаров
            products = []
            for item in items:
                item_data = item.get("item", {})
                sku = str(item_data.get("sku", "")).zfill(3)
                article = sku_to_article.get(sku)
                if article:
                    products.append({
                        "article": article,
                        "quantity": item.get("quantity", 1)
                    })
                else:
                    logging.warning(f"⚠️ Неизвестный артикул (SKU): {sku}. Пропускаем.")

            if not products:
                logging.warning("⚠️ Все товары оказались без артикула. Пропускаем заказ.")
                return "no_valid_products"

            address_data = order.get("address", {})
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
                "phone": order.get("phone", ""),
                "name": order.get("display_user_name", ""),
                "delivery_address": address,
                "comment": order.get("comment", ""),
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
                logging.error(f"❌ Ошибка разбора ответа от FrontPad: {e}")
                logging.error(f"↩️ Ответ: {response.text}")

        except Exception:
            logging.exception("💥 Ошибка при обработке заказа")

    return "ok"

if __name__ == "__main__":
    app.run()
