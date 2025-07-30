import os
import json
import logging
from flask import Flask, request
import requests

app = Flask(__name__)
logging.basicConfig(level=logging.INFO)

FRONTPAD_SECRET = os.getenv("FRONTPAD_SECRET")
FRONTPAD_URL = "https://app.frontpad.ru/api/index.php"

# Таблица соответствия SKU -> артикул (одинаковы от "001" до "181")
sku_to_article = {f"{i:03}": f"{i:03}" for i in range(1, 182)}

@app.route("/", methods=["POST"])
def vk_callback():
    data = request.json
    logging.info(f"\ud83d\udce2 Получен заказ от VK: {json.dumps(data, ensure_ascii=False)}")

    if data.get("type") == "confirmation":
        return os.getenv("VK_CONFIRMATION_TOKEN")

    if data.get("type") != "market_order_new":
        return "ok"

    order = data.get("object", {})
    customer = order.get("customer", {})
    delivery = order.get("delivery", {})
    items = order.get("items", [])

    if not items:
        logging.warning("⚠️ Пустой список товаров. Пропускаем заказ.")
        return "ok"

    products = []
    for item in items:
        sku = str(item.get("item", {}).get("sku"))
        quantity = int(item.get("quantity", 1))
        article = sku_to_article.get(sku)
        if article:
            products.append({"article": article, "quantity": quantity})
        else:
            logging.warning(f"⚠️ Неизвестный SKU: {sku}, товар пропущен")

    if not products:
        logging.warning("⚠️ Ни один товар не подошёл под таблицу. Пропускаем заказ.")
        return "ok"

    # Составление данных заказа
    payload = {
        "secret": FRONTPAD_SECRET,
        "action": "new_order",
        "phone": customer.get("phone", ""),
        "name": customer.get("name", ""),
        "delivery_address": delivery.get("address", {}).get("street", "") or delivery.get("address", ""),
        "comment": order.get("comment", "Заказ из ВКонтакте"),
        "products": json.dumps(products, ensure_ascii=False)
    }

    logging.info(f"\ud83d\udce6 Отправляем заказ в FrontPad: {payload}")

    try:
        response = requests.post(FRONTPAD_URL, data=payload, timeout=10)
        response_text = response.text.strip()
        logging.info(f"✅ Ответ от FrontPad: {response_text}")

        try:
            response_data = json.loads(response_text)
            if response_data.get("result") != "success":
                logging.error(f"❌ Ошибка от FrontPad: {response_data.get('error')}")
        except json.JSONDecodeError:
            logging.error("❌ Ответ от FrontPad не является JSON")

    except requests.RequestException as e:
        logging.exception("❌ Ошибка при отправке запроса в FrontPad")

    return "ok"

if __name__ == "__main__":
    app.run(debug=True)
