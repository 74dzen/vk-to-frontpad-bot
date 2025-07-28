import os
from flask import Flask, request
import requests

app = Flask(__name__)

FRONTPAD_SECRET = os.getenv("FRONTPAD_SECRET")
VK_GROUP_ID = os.getenv("VK_GROUP_ID")
VK_SECRET = os.getenv("VK_SECRET")
VK_TOKEN = os.getenv("VK_TOKEN")


@app.route("/", methods=["POST"])
def vk_callback():
    event = request.get_json()

    # Подтверждение сервера
    if event.get("type") == "confirmation":
        return "3e2d3b00"

    # Обработка заказа из корзины
    if event.get("type") == "order_new":
        obj = event.get("object", {})
        secret = event.get("secret")

        # Проверка секрета
        if secret != VK_SECRET:
            return "access denied"

        # Извлекаем нужные данные из заказа
        order_id = obj.get("id")
        user_id = obj.get("user_id")
        items = obj.get("items", [])
        delivery = obj.get("delivery")

        # Адрес
        street = delivery.get("address", {}).get("street", "")
        home = delivery.get("address", {}).get("house", "")
        apart = delivery.get("address", {}).get("apartment", "")
        phone = delivery.get("phone", "")
        comment = obj.get("comment", "")

        # Подготовка данных для заказа во FrontPad
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
            data[f"product[{i}]"] = item["id"]      # артикул
            data[f"product_kol[{i}]"] = item["quantity"]  # количество

        # Отправка запроса в FrontPad
        response = requests.post("https://app.frontpad.ru/api/index.php?new_order", data=data)

        res_json = response.json()
        print(res_json)

        return "ok"

    return "ok"


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)
