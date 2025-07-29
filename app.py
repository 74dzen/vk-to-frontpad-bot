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

# Таблица соответствий SKU → артикул (1:1 от 001 до 181)
sku_to_article = {f"{i:03}": f"{i:03}" for i in range(1, 182)}

@app.route("/", methods=["POST"])
def vk_callback():
    data = request.get_json()
    logging.info(f"📩 Получено событие: {json.dumps(data, ensure_ascii=False)}")

    # Подтверждение сервера
    if data.get("type") == "confirmation":
        logging.info("📡 Подтверждение сервера ВКонтакте")
        return VK_CONFIRMATION

    # Обработка нового заказа
    if data.get("type") == "market_order_new":
        order = data["object"]
        items = order.get("items", [])
        user = order.get("user", {})
        delivery = order.get("delivery", "")
        address = ""
        if isinstance(delivery, dict):
            address = delivery.get("address", {}).get("street", "")
        else:
            address = ""

        name = f"{user.get('first_name', '')} {user.get('last_name', '')}".strip()
        phone = user.get("phone", "+79999999999")
        comment = order.get("comment", "")

        # 🔍 Проверка содержимого заказа
        logging.info(f"🛒 Состав заказа из VK: {items}")

        products = []
        for item in items:
            sku = item.get("sku", "")
            quantity = item.get("quantity", 1)
            article = sku_to_article.get(sku)

            if article:
                products.append({"article": article, "quantity": quantity})
            else:
                logging.warning(f"⚠️ Не найден артикул для SKU: {sku}")

        # ❌ Если список пуст — логируем и прекращаем
        if not products:
            logging.warning("⚠️ Пустой список товаров. Пропускаем заказ.")
            return "ok"

        payload = {
            "secret": FRONTPAD_SECRET,
            "action": "new_order",
            "phone": phone,
            "name": name,
            "delivery_address": address or "Челябинск",  # запасной вариант
            "comment": comment or "Заказ из ВКонтакте",
            "products": json.dumps(products, ensure_ascii=False),
        }

        logging.info(f"📦 Отправляем заказ в FrontPad: {payload}")
        try:
            response = requests.post("https://app.frontpad.ru/api/index.php", data=payload)
            response_data = response.json()
            logging.info(f"✅ Ответ от FrontPad: {response_data}")
            if response_data.get("result") != "success":
                logging.error(f"❌ Ошибка от FrontPad: {response_data.get('error')}")
        except Exception as e:
            logging.error(f"🔥 Ошибка при запросе к FrontPad: {e}")

        return "ok"

    return "ok"
