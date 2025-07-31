import os
import json
import logging
import requests
from flask import Flask, request
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)
logging.basicConfig(level=logging.INFO)

# 🔐 Секреты
VK_CONFIRMATION = os.getenv("VK_CONFIRMATION")
VK_SECRET = os.getenv("VK_SECRET")
FRONTPAD_SECRET = os.getenv("FRONTPAD_SECRET")

# 🗂️ Таблица соответствия SKU (ВК) -> Артикул (FrontPad)
ARTICLES = {f"{i:03}": f"{i:03}" for i in range(1, 182)}

@app.route("/", methods=["POST"])
def vk_callback():
    try:
        data = request.get_json(force=True)
        logging.info(f"📥 JSON от ВК:\n{json.dumps(data, ensure_ascii=False, indent=2)}")

        # 📌 Подтверждение сервера
        if data.get("type") == "confirmation":
            return VK_CONFIRMATION

        # 🔐 Проверка секрета
        if data.get("secret") != VK_SECRET:
            logging.warning("❌ Неверный секрет от ВК")
            return "not ok"

        # 🛒 Новый заказ
        if data.get("type") == "market_order_new":
            order = data["object"]
            customer = order.get("recipient", {})
            items = order.get("preview_order_items", [])

            logging.info(f"🧾 Товары в заказе ВК: {json.dumps(items, ensure_ascii=False, indent=2)}")

            products = []
            for item in items:
                sku = item.get("item", {}).get("sku")
                quantity = item.get("quantity", 1)
                article = ARTICLES.get(sku)

                logging.info(f"🔍 Обрабатываем SKU: {sku}, Кол-во: {quantity}, Артикул: {article}")

                if article:
                    products.append({"article": article, "quantity": quantity})
                else:
                    logging.warning(f"❌ SKU {sku} не найден в таблице артикулов!")

            if not products:
                logging.error("⚠️ Пустой список товаров. Пропускаем заказ.")
                return "ok"

            # 📞 Клиент
            phone = customer.get("phone", "")
            name = customer.get("name", "Имя не указано")
            address = order.get("delivery", {}).get("address", "Адрес не указан")
            comment = order.get("comment", "")

            payload = {
                "secret": FRONTPAD_SECRET,
                "action": "new_order",
                "phone": phone,
                "name": name,
                "delivery_address": address,
                "comment": comment,
                "products": json.dumps(products, ensure_ascii=False)
            }

            logging.info(f"📦 Отправляем заказ в FrontPad: {payload}")

            response = requests.post("https://app.frontpad.ru/api/index.php", data=payload)
            try:
                response_data = response.json()
            except Exception:
                response_data = response.text
                logging.error(f"❌ Ошибка при разборе ответа: {response_data}")

            logging.info(f"✅ Ответ от FrontPad: {response_data}")
            return "ok"

        return "ok"

    except Exception as e:
        logging.exception(f"❌ Ошибка в обработке запроса: {e}")
        return "error"

