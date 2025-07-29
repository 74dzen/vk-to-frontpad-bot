import os
from flask import Flask, request
import requests

app = Flask(__name__)

FRONTPAD_SECRET = os.getenv("FRONTPAD_SECRET")
VK_SECRET = os.getenv("VK_SECRET")
VK_CONFIRMATION = os.getenv("VK_CONFIRMATION")

@app.route("/", methods=["POST"])
def vk_callback():
    event = request.get_json()

    # Подтверждение сервера
    if event.get("type") == "confirmation":
        return VK_CONFIRMATION

    # Обработка нового заказа
    if event.get("type") == "order_new":
        secret = event.get("secret")
        if secret != VK_SECRET:
            return "access denied"

        obj = event.get("object", {})
        order = obj.get("order", {})
        delivery = obj.get("delivery", {})

        order_id = order.get("id")
        items = order.get("items", [])
        comment = order.get("comment", "")

        phone = delivery.get("phone", "")
        address = delivery.get("address", {})
        street = address.get("street", "")
        home = address.get("house", "")
        apart = address.get("apartment", "")

        # Подготовка данных для FrontPad
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
            sku = item.get("sku")
            quantity = item.get("quantity", 1)
            if not sku:
                continue
            data[f"product[{i}]"] = sku  # SKU совпадает с артикулом
            data[f"product_kol[{i}]"] = quantity

        try:
            response = requests.post("https://app.frontpad.ru/api/index.php?new_order", data=data)
            print("➕ Товар:", ", ".join([f"{item.get('sku')} x{item.get('quantity', 1)}" for item in items]))
            print("✅ Ответ от FrontPad:", response.text)
        except Exception as e:
            print("❌ Ошибка при отправке заказа:", e)

        return "ok"

    return "ok"

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)
