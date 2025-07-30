import os
import json
import logging
import requests
from flask import Flask, request
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)
logging.basicConfig(level=logging.INFO)

# 🔐 Секреты из .env
VK_CONFIRMATION = os.getenv("VK_CONFIRMATION")
VK_SECRET = os.getenv("VK_SECRET")
FRONTPAD_SECRET = os.getenv("FRONTPAD_SECRET")

# 📦 Таблица соответствия SKU (ВК) — Артикул (FrontPad)
ARTICLES = {f"{i:03}": f"{i:03}" for i in range(1, 182)}  # от "001" до "181"

@app.route("/", methods=["POST"])
def vk_callback():
    data = request.get_json(force=True)
    logging.info(f"📥 Весь JSON от ВК:\n{json.dumps(data, ensure_ascii=False, indent=2)}")

    # 🔑 Обработка подтверждения сервера
    if data.get("type") == "confirmation":
        return VK_CONFIRMATION

    # 🔐 Проверка секрета
    if data.get("secret") != VK_SECRET:
        logging.warning("❌ Неверный секрет от ВК")
        return "not ok"

    # 🛒 Обработка нового заказа
    if data.get("type") == "market_order_new":
        order = data["object"]
        customer = order.get("customer", {})
        raw_items = order.get("items", {})
        items = list(raw_items.values()) if isinstance(raw_items, dict) else raw_items

        # 🔍 Логируем входящие товары
        logging.info("🧾 Товары в заказе ВКонтакте:")
        for item in items:
            logging.info(f"🔹 SKU: {item.get('sku')} | Title: {item.get('title')} | Qty: {item.get('quantity')}")

        # ✅ Формируем список товаров для FrontPad
        products = []
        for item in items:
            sku = item.get("sku")
            if not sku:
                continue
            sku = str(sku).strip()
            quantity = item.get("quantity", 1)
            article = ARTICLES.get(sku)
            if article:
                products.append({"article": article, "quantity": quantity})
            else:
                logging.warning(f"❌ SKU {sku} не найден в таблице артикулов!")

        if not products:
            logging.warning("⚠️ Пустой список товаров. Пропускаем заказ.")
            return "ok"

        # 🧾 Информация о клиенте
        phone = customer.get("phone", "")
        name = f"{customer.get('first_name', '')} {customer.get('last_name', '')}".strip()
        address_data = order.get("delivery_address", {})
        address = address_data.get("city", "Город не указан")
        comment = order.get("comment", "")

        # 📤 Подготовка запроса в FrontPad
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

        try:
            response = requests.post("https://app.frontpad.ru/api/index.php", data=payload)
            response_data = response.json()
            logging.info(f"✅ Ответ от FrontPad: {response_data}")

            if not response_data:
                logging.error("❌ Пустой ответ от FrontPad (null)")
            elif response_data.get("result") != "success":
                logging.error(f"❌ Ошибка от FrontPad: {response_data.get('error')}")

        except Exception as e:
            logging.exception(f"❌ Ошибка при запросе в FrontPad: {e}")

        return "ok"

    return "ok"

