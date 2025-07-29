import os
from flask import Flask, request
import requests

app = Flask(__name__)

FRONTPAD_SECRET = os.getenv("FRONTPAD_SECRET")
VK_CONFIRMATION = os.getenv("VK_CONFIRMATION")
VK_SECRET = os.getenv("VK_SECRET")

# Таблица соответствий SKU (ВКонтакте) — Артикулы (FrontPad)
sku_to_article = {
    str(i).zfill(3): str(i).zfill(3) for i in range(1, 182)
}

@app.route("/", methods=["POST"])
def vk_callback():
    event = request.get_json()

    # Подтверждение сервера ВКонтакте
    if event.get("type") == "confirmation":
        return VK_CONFIRMATION

    # Обработка события создания заказа
    if event.get("type") == "market_order_new":
        obj = event.get("object", {})
        secret = event.get("secret")

        if secret != VK_SECRET:
            return "access denied"

        order_id = obj.get("id")
        user_id = obj.get("user_id")
        items = obj.get("items", [])
        delivery = obj.get("delivery", {})

        # --- Защита от ошибки: address может быть строкой
        address_info = delivery.get("address", {})
        if isinstance(address_info, str):
            address_info = {}

        street = address_info.get("street", "")
        home = address_info.get("house", "")
        apart = address_info.get("apartment", "")
        phone = delivery.get("phone", "")
        comment = obj.get("comment", "")

        # Формируем заказ для FrontPad
        data = {
            "secret": FRONTPAD_SECRET,
            "name": f"VK заказ #{order_id}",
            "descr": f"Комментарий: {comment}",
            "phone": phone,
            "street": street,
            "home": home,
            "apart": apart,
            "channel": "ВКонтакте"
        }

        for i, item in enumerate(items):
            sku = str(item["id"]).zfill(3)
            quantity = item["quantity"]
            article = sku_to_article.get(sku)

            if not article:
                print(f"❌ Неизвестный SKU: {sku}")
                return "unknown product"

            data[f"product[{i}]"] = article
            data[f"product_kol[{i}]"] = quantity

        # Отправляем заказ в FrontPad
        response = requests.post("https://app.frontpad.ru/api/index.php?new_order", data=data)

        try:
            res = response.json()
            print(f"✅ Ответ от FrontPad: {res}")
        except Exception as e:
            print("❌ Ошибка при обработке ответа от FrontPad:", e)
            print(response.text)

        return "ok"

    return "ok"


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)
