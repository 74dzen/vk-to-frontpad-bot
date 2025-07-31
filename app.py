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

# Таблица артикулов: "001"–"181"
ARTICLES = {f"{i:03}": f"{i:03}" for i in range(1, 182)}

@app.route("/", methods=["POST"])
def vk_callback():
    data = request.get_json(force=True)
    logging.info(f"📥 Весь JSON от ВК:\n{json.dumps(data, ensure_ascii=False, indent=2)}")

    # 🔑 Подтверждение сервера
    if data.get("type") == "confirmation":
        return VK_CONFIRMATION

    # 🔐 Проверка секрета
    if data.get("secret") != VK_SECRET:
        logging.warning("❌ Неверный секрет от ВК")
        return "not ok"

    # 🛒 Обработка нового заказа
    if data.get("type") == "market_order_new":
        order = data.get("object", {})
        customer = order.get("customer", {})
        raw_items = order.get("preview_order_items") or order.get("items") or {}
        logging.info(f"🧾 raw_items:\n{json.dumps(raw_items, ensure_ascii=False, indent=2)}")
        items = list(raw_items.values()) if isinstance(raw_items, dict) else raw_items

        if not items:
            logging.warning("⚠️ Нет товаров в заказе")
            return "ok"

        product_data = {}
        product_count = 0

        for idx, item in enumerate(items):
            sku = item.get("sku")
            quantity = item.get("quantity", 1)
            article = ARTICLES.get(sku)

            if not article:
                logging.warning(f"❌ SKU {sku} не найден в таблице артикулов!")
                continue

            product_data[f"product[{product_count}]"] = article
            product_data[f"product_kol[{product_count}]"] = str(quantity)
            product_count += 1

        if product_count == 0:
            logging.warning("⚠️ Пустой список товаров. Пропускаем заказ.")
            return "ok"

        # Данные клиента
        name = f"{customer.get('first_name', '')} {customer.get('last_name', '')}".strip()
        phone = customer.get("phone", "")
        comment = order.get("comment", "")
        address_data = order.get("delivery_address", {})
        street = address_data.get("street", "")
        home = address_data.get("home", "")
        apart = address_data.get("apartment", "")
        city = address_data.get("city", "")

        # Собираем payload
        payload = {
            "secret": FRONTPAD_SECRET,
            "name": name,
            "phone": phone,
            "descr": comment,
            "street": city or "Город не указан",
            "home": home,
            "apart": apart,
            **product_data
        }

        logging.info(f"📦 Отправляем заказ в FrontPad: {payload}")

        try:
            response = requests.post("https://app.frontpad.ru/api/index.php?new_order", data=payload)
            logging.info(f"📤 Статус ответа от FrontPad: {response.status_code}")
            logging.info(f"📤 Тело ответа от FrontPad: {response.text}")

            try:
                response_json = response.json()
                logging.info(f"✅ Ответ от FrontPad (json): {response_json}")
                if response_json.get("result") != "success":
                    logging.error(f"❌ Ошибка от FrontPad: {response_json.get('error')}")
            except Exception:
                logging.error("❌ Ответ не в формате JSON")

        except Exception as e:
            logging.exception(f"❌ Ошибка при отправке запроса в FrontPad: {e}")

        return "ok"

    return "ok"
