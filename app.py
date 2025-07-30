import os
import json
import logging
from flask import Flask, request
import requests
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)
logging.basicConfig(level=logging.INFO)

FRONTPAD_SECRET = os.getenv("FRONTPAD_SECRET")

# Таблица соответствия SKU и артикулов (001–181)
sku_to_article = {f"{i:03d}": f"{i:03d}" for i in range(1, 182)}

@app.route("/", methods=["POST"])
def vk_callback():
    data = request.get_json()
    logging.info(f"📥 Получен запрос: {json.dumps(data, ensure_ascii=False)}")

    if data.get("type") == "confirmation":
        return os.getenv("VK_CONFIRMATION_CODE", "")

    if data.get("type") != "market_order_new":
        logging.info("⏭️ Событие не market_order_new, пропускаем")
        return "ok"

    order = data.get("object", {})
    logging.info(f"🧾 VK заказ полностью: {json.dumps(order, ensure_ascii=False)}")

    name = order.get("display_name") or "Без имени"
    phone = order.get("phone") or "+70000000000"
    address_data = order.get("preview_address") or ""
    comment = order.get("comment", "")

    # Формируем строку адреса
    address_str = ""
    if isinstance(address_data, dict):
        address_str = ", ".join(filter(None, [
            address_data.get("street"),
            address_data.get("city"),
            address_data.get("country")
        ]))
    elif isinstance(address_data, str):
        address_str = address_data

    items = order.get("items", [])
    logging.info(f"📦 Товары в заказе: {items}")

    products = []
    for item in items:
        raw_sku = item.get("sku") or item.get("id") or item.get("item_id")
        sku = str(raw_sku).strip()
        quantity = int(item.get("quantity", 1))

        article = sku_to_article.get(sku)
        if article:
            products.append({"article": article, "quantity": quantity})
        else:
            logging.warning(f"⚠️ Неизвестный SKU/ID: {sku} — товар пропущен")

    if not products:
        logging.warning("⚠️ Пустой список товаров. Пропускаем заказ.")
        return "ok"

    payload = {
        "secret": FRONTPAD_SECRET,
        "action": "new_order",
        "phone": phone,
        "name": name,
        "delivery_address": address_str,
        "comment": comment,
        "products": products  # JSON-массив, НЕ строка!
    }

    logging.info(f"📦 Отправляем заказ в FrontPad: {payload}")

    try:
        response = requests.post("https://app.frontpad.ru/api/index.php", json=payload)
        logging.info(f"✅ Ответ от FrontPad: {response.text}")
        response_data = response.json()

        if response_data.get("result") != "success":
            logging.error(f"❌ Ошибка от FrontPad: {response_data.get('error')}")
        else:
            logging.info("🎉 Заказ успешно создан в FrontPad")
    except Exception as e:
        logging.exception(f"🔥 Ошибка при отправке заказа в FrontPad: {e}")

    return "ok"

if __name__ == "__main__":
    app.run()
