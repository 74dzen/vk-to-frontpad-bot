import os
from flask import Flask, request
import requests

app = Flask(__name__)

FRONTPAD_SECRET = os.getenv("FRONTPAD_SECRET")
VK_GROUP_ID = os.getenv("VK_GROUP_ID")
VK_SECRET = os.getenv("VK_SECRET")
VK_TOKEN = os.getenv("VK_TOKEN")
VK_CONFIRMATION = os.getenv("VK_CONFIRMATION")


@app.route("/", methods=["POST"])
def vk_callback():
    event = request.get_json()
    print("VK Event:", event)

    if event.get("type") == "confirmation":
        print("VK confirmation requested")
        return VK_CONFIRMATION

    if event.get("type") == "market_order_new":
        secret = event.get("secret")
        if secret != VK_SECRET:
            print("❌ Invalid secret:", secret)
            return "access denied"

        obj = event.get("object", {})
        order_id = obj.get("id")
        comment = obj.get("comment", "")
        recipient = obj.get("recipient", {})
        phone = recipient.get("phone", "")
        name = recipient.get("name", "")
        delivery_address = obj.get("delivery", {}).get("address", "")

        # Товары
        items = obj.get("preview_order_items", [])

        data = {
            "secret": FRONTPAD_SECRET,
            "name": name,
            "phone": phone,
            "street": delivery_address,
            "descr": f"Комментарий: {comment}\nИсточник: ВК Маркет",
            "channel": "ВКонтакте"
        }

        for i, item in enumerate(items):
            sku = item.get("item", {}).get("sku") or "123"
            qty = item.get("quantity", 1)
            data[f"product[{i}]"] = sku
            data[f"product_kol[{i}]"] = qty
            print(f"➕ Товар: {sku} x{qty}")

        # Отправка заказа в FrontPad
        try:
            response = requests.post("https://app.frontpad.ru/api/index.php?new_order", data=data)
            print("✅ Ответ от FrontPad:", response.text)
        except Exception as e:
            print("❌ Ошибка при отправке в FrontPad:", e)

        return "ok"

    return "ok"


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)
