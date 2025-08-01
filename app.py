import os
import logging
from flask import Flask, request
import requests

app = Flask(__name__)
logging.basicConfig(level=logging.INFO)

FRONTPAD_SECRET = os.getenv("FRONTPAD_SECRET")
VK_SECRET = os.getenv("VK_SECRET")
VK_CONFIRMATION = os.getenv("VK_CONFIRMATION")

@app.route("/", methods=["POST"])
def vk_callback():
    event = request.get_json()
    logging.info("📥 Получен запрос от ВКонтакте: %s", event)

    if event.get("type") == "confirmation":
        return VK_CONFIRMATION

    if event.get("type") == "market_order_new":
        secret = event.get("secret")
        if secret != VK_SECRET:
            logging.warning("❌ Неверный секрет: %s", secret)
            return "access denied"

        obj = event.get("object", {})
        recipient = obj.get("recipient", {})
        items = obj.get("preview_order_items", [])

        data = {
            "secret": FRONTPAD_SECRET,
            "action": "new_order",
            "phone": recipient.get("phone", ""),
            "name": recipient.get("name", ""),
            "delivery_address": obj.get("delivery", {}).get("address", ""),
            "comment": obj.get("comment", ""),
        }

        for i, item in enumerate(items):
            sku = item.get("item", {}).get("sku", "").strip()
            qty = item.get("quantity", 1)
            if not sku:
                logging.warning("⚠️ Пропущен товар без SKU: %s", item)
                continue
            data[f"product[{i}]"] = sku
            data[f"product_kol[{i}]"] = qty
            logging.info(f"➕ Товар: {sku} x{qty}")

        logging.info("📦 Отправляем заказ в FrontPad: %s", data)

        try:
            response = requests.post("https://app.frontpad.ru/api/index.php", data=data)
            logging.info("📤 Статус ответа от FrontPad: %s", response.status_code)
            logging.info("📤 Тело ответа от FrontPad (text): %s", response.text)
            try:
                logging.info("✅ Ответ от FrontPad (json): %s", response.json())
            except Exception:
                pass
        except Exception as e:
            logging.exception("❌ Ошибка при отправке заказа в FrontPad")

        return "ok"

    return "ok"

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)
