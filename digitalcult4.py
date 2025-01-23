from flask import Flask, request, jsonify
import telebot
import sqlite3
import tensorflow as tf
import requests
import os
model = tf.keras.models.load_model('my_model.h5')

Token = 'Token'
WEBHOOK_URL = "https://ef7d-88-201-190-11.ngrok-free.app"

bot = telebot.TeleBot(Token)

app = Flask(__name__)

users ={}
conn = sqlite3.connect('users1.db',check_same_thread=False)
cursor = conn.cursor()
cursor.execute('''CREATE TABLE IF NOT EXISTS users1
                  (id INTEGER PRIMARY KEY, username TEXT, password TEXT)''')
conn.commit()

def is_user_registered(username):
    try:
        cursor.execute(f'SELECT * FROM users1 WHERE username={username}')
        user = cursor.fetchone()
        return user is not None
    except sqlite3.OperationalError:
        return None
    user = cursor.fetchone()
    return user is not None

def register_user(msg):
        username = msg.chat.id
        password = msg.text
        users[username] = {'logged_in': False}
        cursor.execute('INSERT INTO users1 (username, password) VALUES (?, ?)', (username, password))
        conn.commit()

def login_user(username, password):
    cursor.execute('SELECT * FROM users1 WHERE username=? AND password=?', (username, password))
    user = cursor.fetchone()
    return user

def login_password_parse(message):
    login = message.text.split()[0]
    password = message.text.split()[1]
    register_user(login,password)
    return login

@app.route('/', methods=['POST'])
def webhook():
    if request.headers.get('content-type') == 'application/json':
        json_str = request.get_data().decode('UTF-8')
        update = telebot.types.Update.de_json(json_str)
        bot.process_new_updates([update])
        return '', 200
    else:
        return 'Invalid request', 400


@bot.message_handler(commands=['start'])
def send_welcome(message):
    users[message.chat.id] = {'logged_in': False}
    bot.reply_to(message, "Привет! Чтобы начать, воспользуйтесь командой /register для регистрации или /login для входа.")

@bot.message_handler(commands=['register'])
def register(message):
    if is_user_registered(message) == None:
        chat_id = message.chat.id
        bot.reply_to(message, "Введите пароль для регистрации:")
        # Сохраняем пароль пользователя
        bot.register_next_step_handler(message, save_password)
    else:
        bot.reply_to(message,"Вы уже зарегестрированы")

# Функция для сохранения пароля пользователя
def save_password(message):
    register_user(message)
    bot.reply_to(message, "Регистрация успешно завершена. Теперь вы можете войти с помощью /login.")


# Обработчик команды /login
@bot.message_handler(commands=['login'])
def login(message):
    chat_id = message.chat.id
    if is_user_registered(chat_id) != None and not users[chat_id]['logged_in']:
        bot.reply_to(message, "Введите пароль для входа:")
        bot.register_next_step_handler(message, check_password)
    else:
        bot.reply_to(message, "Сначала зарегистрируйтесь с помощью /register.")

# Функция для проверки пароля пользователя
def check_password(message):
    chat_id = message.chat.id
    password = message.text
    if users.get(chat_id) and login_user(chat_id, password) != None:
        users[chat_id]['logged_in'] = True
        bot.reply_to(message, "Вы успешно вошли в систему. Теперь можете использовать команду /predict")
    else:
        bot.reply_to(message, "Неверный пароль. Попробуйте еще раз или зарегистрируйтесь с помощью /register.")
# Обработчик команды /predict
@bot.message_handler(commands=['predict'])
def predict(message):
    chat_id = message.chat.id
    if is_user_registered(chat_id) != None and users[chat_id]['logged_in']:
        bot.reply_to(message, "Пожалуйста, отправьте картинку для классификации.")
    else:
        bot.reply_to(message, "Сначала войдите с помощью /login.")


# Обработчик для получения картинки и классификации
@bot.message_handler(content_types=['photo'])
def handle_photo(message):
    chat_id = message.chat.id
    if is_user_registered(chat_id) != None and users[chat_id]['logged_in']:
        file_id = message.photo[-1].file_id
        file_info = bot.get_file(file_id)
        downloaded_file = bot.download_file(file_info.file_path)
        image = 'tmp.jpg'
        with open(image, 'wb') as new_file:
            new_file.write(downloaded_file)
        img = tf.keras.preprocessing.image.load_img(image, target_size=(200, 200))
        img_array = tf.keras.preprocessing.image.img_to_array(img)
        img_array = tf.expand_dims(img_array, 0)  # Create batch axis
        predictions = model.predict(img_array)
        # Определение класса изображения
        if predictions[0] < 0.5:
            prediction_text = "Человек"
        else:
            prediction_text = "Гиена"
        bot.reply_to(message,f"Это {prediction_text}")
    else:
        bot.reply_to(message, "Сначала войдите с помощью /login.")

# Обработчик команды /logout
@bot.message_handler(commands=['logout'])
def logout(message):
    chat_id = message.chat.id
    if chat_id in users:
        users[chat_id]['logged_in'] = False
        bot.reply_to(message, "Вы успешно вышли из системы.")
    else:
        bot.reply_to(message, "Сначала войдите с помощью /login.")


url = f"https://api.telegram.org/bot{Token}/setWebhook"
data = {"url": WEBHOOK_URL}

if  __name__ == '__main__':
    app.run()
