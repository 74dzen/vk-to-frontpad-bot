import os
import json
import logging
import requests
from flask import Flask, request
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)
logging.basicConfig(level=logging.INFO)

FRONTPAD_SECRET = os.getenv("FRONTPAD_SECRET")

# Таблица соответствия SKU → артикулов
sku_to_article = {f"{i:03}": f"{i:03}" for i in range(1, 182)}

@app.route("/", methods=["POST"])
def vk_callback():
    data = request.get_json()
    logging.info(f"📥 Получены данные от ВК: {data}")

    if data.get("type") == "confirmation":
        return os.getenv("VK_CONFIRMATION_CODE", "")

    if data.get("type") != "market_order_new":
        logging.info("🔕 Необрабатываемый тип события. Пропускаем.")
        return "ok"

    order = data["object"]
    buyer = order.get("buyer", {})
    delivery = order.get("delivery_address", {})

    # Контакты
    phone = buyer.get("phone", "")
    name = f"{buyer.get('first_name', '')} {buyer.get('last_name', '')}".strip()

    # Адрес
    street = delivery.get("street", "")
    city = delivery.get("city", "")
    delivery_address = f"{city}, {street}".strip(", ")

    # Комментарий
    note = order.get("comment", "") or "Заказ из ВКонтакте"

    # Товары
    items = order.get("items", [])
    products = []

    for item in items:
        sku = item.get("sku", "").strip()
        quantity = int(item.get("quantity", 1))
        article = sku_to_article.get(sku)

        if article:
            products.append({"article": article, "quantity": quantity})
        else:
            logging.warning(f"⚠️ Неизвестный SKU: {sku} — товар пропущен")

    if not products:
        logging.warning("⚠️ Пустой список товаров. Пропускаем заказ.")
        return "ok"

    payload = {
        "secret": FRONTPAD_SECRET,
        "action": "new_order",
        "phone": phone,
        "name": name,
        "delivery_address": delivery_address,
        "comment": note,
        "products": json.dumps(products, ensure_ascii=False),
    }

    logging.info(f"📦 Отправляем заказ в FrontPad: {payload}")
    try:
        response = requests.post("https://app.frontpad.ru/api/index.php", data=payload, timeout=10)
        logging.info(f"✅ Ответ от FrontPad: {response.text}")
        response_data = response.json()

        if response_data.get("result") != "success":
            logging.error(f"❌ Ошибка от FrontPad: {response_data.get('error')}")
    except Exception as e:
        logging.exception(f"💥 Исключение при отправке заказа в FrontPad: {e}")

    return "ok"

if __name__ == "__main__":
    app.run(debug=True)
