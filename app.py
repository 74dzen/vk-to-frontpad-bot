import os
from flask import Flask, request
import requests

app = Flask(__name__)

FRONTPAD_SECRET = os.getenv("FRONTPAD_SECRET")
VK_GROUP_ID = os.getenv("VK_GROUP_ID")
VK_SECRET = os.getenv("VK_SECRET")  # используется для проверки подписи
VK_TOKEN = os.getenv("VK_TOKEN")

# Обработка запросов от ВКонтакте
@app.route("/", methods=["POST"])
def vk_callback():
    event = request.get_json()

    # 1. Подтверждение сервера
    if event.get("type") == "confirmation":
        return "3e2d3b00"  # Именно эту строку ждёт VK

    # 2. Обработка входящего нового сообщения
    if event.get("type") == "message_new":
        object_data = event.get("object", {})
        secret = event.get("secret")

        # Проверка секрета от ВК
        if secret != VK_SECRET:
            return "access denied"

        user_id = object_data["message"]["from_id"]
        message_text = object_data["message"]["text"].strip().lower()

        # Проверка команды
        if message_text == "аляска":
            # Отправка заказа в FrontPad
            response = requests.post(
                "https://app.frontpad.ru/api/index.php?new_order",
                data={
                    "secret": FRONTPAD_SECRET,
                    "product[0]": "123",        # Артикул ролла Аляска
                    "product_kol[0]": "1",       # Кол-во 1
                    "name": "Заказ из ВК",
                    "descr": f"от пользователя VK {user_id}",
                    "channel": "ВКонтакте"
                }
            )
            res_json = response.json()

            if res_json.get("result") == "success":
                send_message(user_id, "Спасибо! Ваш заказ принят 🎉")
            else:
                send_message(user_id, "Произошла ошибка при оформлении заказа 😞")

        else:
            send_message(user_id, "Чтобы сделать заказ, напишите: Аляска")

    return "ok"

# Функция отправки сообщения пользователю
def send_message(user_id, text):
    requests.post(
        "https://api.vk.com/method/messages.send",
        params={
            "user_id": user_id,
            "random_id": 0,
            "message": text,
            "access_token": VK_TOKEN,
            "v": "5.199"
        }
    )

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)
