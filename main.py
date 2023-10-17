import telebot
from telebot.types import ReplyKeyboardMarkup, InlineKeyboardMarkup, InlineKeyboardButton
from random import randint
from threading import Thread
from datetime import datetime
from dateutil.relativedelta import relativedelta
from dotenv import load_dotenv
from db import Connection
from keep_alive import keep_alive
import socketio
import json
import time
import os

load_dotenv()
da_token = os.environ['da_token']
tg_token = os.environ['tg_token']
db = Connection()
code = {}
log = {}
checking_codes = []
price = 1

sio = socketio.Client()


@sio.on('connect')
def on_connect():
    sio.emit('add-user', {"token": da_token, "type": "alert_widget"})


@sio.on('donation')
def on_message(data):
    y = json.loads(data)
    log.update({y['message']: y['amount']})


sio.connect('wss://socket.donationalerts.ru:443', transports='websocket')


def check():
    while True:
        for i, data in enumerate(checking_codes):
            if data[1] in list(log.keys()):
                bot.send_message(data[0].message.json['chat']['id'], "Код пришёл!")
                if log.get(code.get(str(data[0].message.json['chat']['id']), "")) < data[2]:
                    bot.send_message(data[0].message.json['chat']['id'],
                                     f"Код пришёл, но вы отправили меньше {data[2]} рублей, попробуйте ещё раз!")
                else:
                    bot.send_message(data[0].message.json['chat']['id'], "Код пришёл, ваша подписка оплачена.")
                    db.updateUser(data[0].message.json['chat']['id'], data[0].from_user.username, 1,
                                  (datetime.now() + relativedelta(months=1)).strftime("%d.%m.%Y"), 0, 0)
                checking_codes.pop(i)
                code.pop(str(data[0].message.json['chat']['id']))
                log.pop(data[1])

        time.sleep(1)



bot = telebot.TeleBot(tg_token)
print('bot is online!')


@bot.message_handler(commands=['start'])
def message(message):
    id = str(message.chat.id)
    username = str(message.from_user.username)
    markup_reply = ReplyKeyboardMarkup(row_width=1).add("Инфа", "Меню")
    markup_inline = InlineKeyboardMarkup(row_width=1).add(InlineKeyboardButton("Инфа", callback_data="info"),
                          InlineKeyboardButton("Меню", callback_data="menu"))
    if id in db.getAdmins():
        markup_reply.add("Добавить", "Админпанель")
        markup_inline.add(InlineKeyboardButton("Добавить", callback_data="add"),
                          InlineKeyboardButton("Админпанель", callback_data="admin"))
    elif id in db.getStaffs():
        markup_reply.add("Добавить")
        markup_inline.add(InlineKeyboardButton("Добавить", callback_data="add"))
    elif id not in db.getUsers():
        db.addUser(id, username, datetime.now().strftime("%d.%m.%Y"))

    bot.send_message(id, "Здравствуйте, вас приветствует бот помощник по программированию.",
                     reply_markup=markup_reply)
    bot.send_message(id, "Этот бот предоставляет более подробное и понятное объяснение тем по спецкурсу и программированию, а также предоставляет ответы к задачам.",
                     reply_markup=markup_inline)


@bot.message_handler(commands=['info'])
def message(message):
    id = str(message.chat.id)
    username = str(message.from_user.username)
    client = db.getSubsByUserid(str(message.chat.id))
    if client is None:
        db.addUser(id, username, datetime.now().strftime("%d.%m.%Y"))
        bot.send_message(message.chat.id, "Добавлен")
        client = db.getSubsByUserid(str(message.chat.id))

    if client[0] == 0:
        bot.send_message(id, "У вас нет подписки")
    else:
        bot.send_message(id,
                         f"У вас подписка {client[0]} уровня до {client[1]}, \n{'Вы являетесь админом' if client[2] else ''} \n{'Вы являетесь работником' if client[3] else ''}")


# @bot.message_handler(content_types=['text'])
# def message(message):
#     log.update({str(message.text.split()[0]): int(message.text.split()[1])})
#     bot.send_message(message.chat.id, "Добавлено")


@bot.callback_query_handler(lambda call: True)
def callback(call):
    id = str(call.message.json['chat']['id'])
    username = str(call.from_user.username)

    if call.data == "info":
        info = db.getInfoByUserid(id)
        if info is None:
            db.addUser(id, username, datetime.now().strftime("%d.%m.%Y"))
            info = db.getInfoByUserid(id)

        if info[0] == 0:
            bot.send_message(id,
                             f"У вас нет подписки. \n{'Вы являетесь админом' if info[2] else ''} \n{'Вы являетесь работником' if info[3] else ''}")
        else:
            bot.send_message(id,
                             f"У вас подписка {info[0]} уровня до {info[1]}. \n{'Вы являетесь админом' if info[2] else ''} \n{'Вы являетесь работником' if info[3] else ''}")

    elif call.data.startswith("menu"):
        markup = InlineKeyboardMarkup(row_width=1)
        if len(call.data.split("-")) == 1:
            for courseid, course in db.getCourses():
                markup.add(InlineKeyboardButton(course, callback_data=f"menu-{courseid}"))
            markup.add(InlineKeyboardButton("Назад", callback_data=f"mainmenu"))
            bot.send_message(id, "Выберите курс:", reply_markup=markup)
        elif len(call.data.split("-")) == 2:
            courseid = call.data.split("-")[1]
            for topicid, topic in db.getTopics(courseid):
                markup.add(InlineKeyboardButton(topic, callback_data=f"menu-{courseid}-{topicid}"))
            markup.add(InlineKeyboardButton("Назад", callback_data=f"menu"))
            bot.send_message(id, "Выберите тему:", reply_markup=markup)
        elif len(call.data.split("-")) == 3:
            courseid = call.data.split("-")[1]
            topicid = call.data.split("-")[2]
            for taskid, task in db.getTasks(courseid, topicid):
                markup.add(InlineKeyboardButton(task, callback_data=f"menu-{courseid}-{topicid}-{taskid}"))
            markup.add(InlineKeyboardButton("Назад", callback_data=f"menu-{courseid}"))
            bot.send_message(id, "Выберите задание:", reply_markup=markup)
        elif len(call.data.split("-")) == 4:
            courseid = call.data.split("-")[1]
            topicid = call.data.split("-")[2]
            taskid = call.data.split("-")[3]
            markup.add(InlineKeyboardButton("Объяснение", callback_data=f"menu-{courseid}-{topicid}-{taskid}-0"))
            markup.add(InlineKeyboardButton("Решение", callback_data=f"menu-{courseid}-{topicid}-{taskid}-1"))
            markup.add(InlineKeyboardButton("Назад", callback_data=f"menu-{courseid}-{topicid}"))
            bot.send_message(id, "Выберите нужное:", reply_markup=markup)
        elif len(call.data.split("-")) == 5:
            courseid = call.data.split("-")[1]
            topicid = call.data.split("-")[2]
            taskid = call.data.split("-")[3]
            action = call.data.split("-")[4]
            if action == "0":
                markup.add(InlineKeyboardButton("Назад", callback_data=f"menu-{courseid}-{topicid}-{taskid}"))
                bot.send_message(id, db.getExplanation(courseid, topicid, taskid), reply_markup=markup)
            else:
                if id in db.getSubs() or db in db.getStaffs() or id in db.getAdmins():
                    markup.add(InlineKeyboardButton("Назад", callback_data=f"menu-{courseid}-{topicid}-{taskid}"))
                    bot.send_message(id, db.getSolution(courseid, topicid, taskid), reply_markup=markup)
                elif id in db.getUsers():
                    markup.add(InlineKeyboardButton("Купить подписку", callback_data="buy"))
                    markup.add(InlineKeyboardButton("Назад", callback_data=f"menu-{courseid}-{topicid}-{taskid}"))
                    bot.send_message(id, "Чтобы просмотреть решения вам нужна подписка, вы можете приобрести её по кнопке ниже.", reply_markup=markup)

    # def add(message, call, callback):
    #     bot.send_message(message.chat.id, "Успешно добавлено")
    #
    # elif call.data.startswith("add"):
    #     markup = InlineKeyboardMarkup(row_width=1)
    #     if "cancel" in call.data:
    #         bot.clear_step_handler()
    #     if call.data.endswith("course"):
    #         markup.add(InlineKeyboardButton("Назад", callback_data="add-cancel"))
    #         message = bot.send_message(id, "Пришлите название курса", reply_markup=markup)
    #         bot.register_next_step_handler(message, add, call, "")
    #     if len(call.data.split("-")) == 1:
    #         for courseid, course in db.getCourses():
    #             markup.add(InlineKeyboardButton(course, callback_data=f"add-{courseid}"))
    #         markup.add(InlineKeyboardButton("Добавить курс", callback_data=f"add-course"))
    #         markup.add(InlineKeyboardButton("Назад", callback_data=f"mainmenu"))
    #         bot.send_message(id, "Выберите курс:", reply_markup=markup)
    #     elif len(call.data.split("-")) == 2:
    #         courseid = call.data.split("-")[1]
    #         for topicid, topic in db.getTopics(courseid):
    #             markup.add(InlineKeyboardButton(topic, callback_data=f"add-{courseid}-{topicid}"))
    #         markup.add(InlineKeyboardButton("Назад", callback_data=f"add"))
    #         bot.send_message(id, "Выберите тему:", reply_markup=markup)
    #     elif len(call.data.split("-")) == 3:
    #         courseid = call.data.split("-")[1]
    #         topicid = call.data.split("-")[2]
    #         for taskid, task in db.getTasks(courseid, topicid):
    #             markup.add(InlineKeyboardButton(task, callback_data=f"add-{courseid}-{topicid}-{taskid}"))
    #         markup.add(InlineKeyboardButton("Назад", callback_data=f"add-{courseid}"))
    #         bot.send_message(id, "Выберите задание:", reply_markup=markup)
    #     elif len(call.data.split("-")) == 4:
    #         courseid = call.data.split("-")[1]
    #         topicid = call.data.split("-")[2]
    #         taskid = call.data.split("-")[3]
    #         markup.add(InlineKeyboardButton("Объяснение", callback_data=f"add-{courseid}-{topicid}-{taskid}-0"))
    #         markup.add(InlineKeyboardButton("Решение", callback_data=f"add-{courseid}-{topicid}-{taskid}-1"))
    #         markup.add(InlineKeyboardButton("Назад", callback_data=f"add-{courseid}-{topicid}"))
    #         bot.send_message(id, "Выберите нужное:", reply_markup=markup)
    #     elif len(call.data.split("-")) == 5:
    #         courseid = call.data.split("-")[1]
    #         topicid = call.data.split("-")[2]
    #         taskid = call.data.split("-")[3]
    #         action = call.data.split("-")[4]
    #         if action == "0":
    #             markup.add(InlineKeyboardButton("Назад", callback_data=f"add-{courseid}-{topicid}-{taskid}"))
    #             bot.send_message(id, db.getExplanation(courseid, topicid, taskid), reply_markup=markup)
    #         else:
    #             if id in db.getSubs() or db in db.getStaffs() or id in db.getAdmins():
    #                 markup.add(InlineKeyboardButton("Назад", callback_data=f"add-{courseid}-{topicid}-{taskid}"))
    #                 bot.send_message(id, db.getSolution(courseid, topicid, taskid), reply_markup=markup)
    #             elif id in db.getUsers():
    #                 markup.add(InlineKeyboardButton("Купить подписку", callback_data="buy"))
    #                 markup.add(InlineKeyboardButton("Назад", callback_data=f"add-{courseid}-{topicid}-{taskid}"))
    #                 bot.send_message(id, "Чтобы просмотреть решения вам нужна подписка, вы можете приобрести её по кнопке ниже.", reply_markup=markup)

    elif call.data == "buy":
        client = db.getSubs()
        if client is None:
            db.addUser(id, username, datetime.now().strftime("%d.%m.%Y"))
            bot.send_message(message.chat.id, "Добавлен")
            client = db.getSubs()

        if str(call.message.json['chat']['id']) not in client:
            markup = InlineKeyboardMarkup(row_width=1).add(
                InlineKeyboardButton("Оплатить", url="https://www.donationalerts.com/r/xpozitivez"),
                InlineKeyboardButton("Отменить оплату", callback_data="cancel"),
                InlineKeyboardButton("Проверить состояние", callback_data="check"))
            if str(call.message.json['chat']['id']) not in list(code.keys()):
                code[str(call.message.json['chat']['id'])] = str(randint(100000000, 999999999))
                bot.send_message(call.message.json['chat']['id'],
                                 f"Стоимость подписки {price} рублей.\nПри покупке оставьте только этот код в сообщении - {code.get(str(call.message.json['chat']['id']), '')}",
                                 reply_markup=markup)
                checking_codes.append((call, code.get(str(call.message.json['chat']['id']), ''), price))
            else:
                bot.send_message(call.message.json['chat']['id'],
                                 f"Стоимость подписки {price} рублей.\nПри покупке оставьте только этот код в сообщении - {code.get(str(call.message.json['chat']['id']), '')}",
                                 reply_markup=markup)
        else:
            bot.send_message(call.message.json['chat']['id'], "Подписка уже приобретена")

    elif call.data == "check":
        print(code, log, checking_codes)
        if code.get(str(call.message.json['chat']['id']), "") not in list(log.keys()):
            bot.send_message(call.message.json['chat']['id'], "Оплата ещё не пришла или вы указали неверный код")

    elif call.data == "cancel":
        for i, data in enumerate(checking_codes):
            if data[1] == code.get(str(call.message.json['chat']['id']), ""):
                checking_codes.pop(i)
        if code.get(str(call.message.json['chat']['id']), ""):
            log.pop(code.get(str(call.message.json['chat']['id']), ""), "")
        code.pop(str(call.message.json['chat']['id']), "")


Thread(target=keep_alive).start()
Thread(target=check).start()
while True:
    try:
        bot.infinity_polling(skip_pending=True)
    except Exception as e:
        print(e)
        continue
