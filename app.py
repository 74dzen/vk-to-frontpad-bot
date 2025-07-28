
import os
from flask import Flask, request
import requests
import logging

app = Flask(__name__)

# Настройка логирования в файл
logging.basicConfig(filename="app.log", level=logging.INFO)

FRONTPAD_SECRET = os.getenv("FRONTPAD_SECRET")
VK_GROUP_ID = os.getenv("VK_GROUP_ID")
VK_SECRET = os.getenv("VK_SECRET")
VK_TOKEN = os.getenv("VK_TOKEN")


@app.route("/", methods=["POST"])
def vk_callback():
    event = request.get_json()
    logging.info(f"Получен ивент: {event}")

    # Подтверждение сервера
    if event.get("type") == "confirmation":
        logging.info("Отправка confirmation-кода")
        return "3e2d3b00"

    # Обработка нового заказа
    if event.get("type") == "order_new":
        secret = event.get("secret")
        if secret != VK_SECRET:
            logging.warning(f"Секрет не совпал: {secret} != {VK_SECRET}")
            return "access denied"

        order = event.get("object", {}).get("order", {})
        delivery = event.get("object", {}).get("delivery", {})

        order_id = order.get("id")
        user_id = order.get("user_id")
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
            data[f"product[{i}]"] = item.get("id")  # артикул
            data[f"product_kol[{i}]"] = item.get("quantity", 1)  # количество

        # Отправка запроса
        try:
            response = requests.post("https://app.frontpad.ru/api/index.php?new_order", data=data)
            logging.info(f"Ответ от FrontPad: {response.text}")
        except Exception as e:
            logging.error(f"Ошибка при отправке заказа: {e}")

        return "ok"

    logging.info("Необработанный тип события")
    return "ok"


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)
