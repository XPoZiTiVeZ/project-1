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
owners = ['1349175494', '5264927635']
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

def check_user(userid, username):
    userInfo = db.getInfoByUserid(userid)
    if userid not in db.getUsers():
        db.addUser(userid, username, datetime.now().strftime("%d.%m.%Y"))
    elif username != userInfo[0]:
        db.updateUser(userid, username, userInfo[1], userInfo[2], userInfo[3], userInfo[4])


def add(message, addtype, call, callback):
    print(callback)
    if addtype == "course":
        db.addCourse(message.text)
    elif addtype == "topic":
        db.addTopic(callback.split("-")[1], message.text)
    elif addtype == "task":
        db.addTask(callback.split("-")[1], callback.split("-")[2], message.text)
    elif addtype == "explanation":
        db.addExplanation(callback.split("-")[1], callback.split("-")[2], callback.split("-")[3], message.text)
    elif addtype == "solution":
        db.addSolution(callback.split("-")[1], callback.split("-")[2], callback.split("-")[3], message.text)
    bot.send_message(call.message.json['chat']['id'], "Успешно добавлено")
    call.data = callback
    bot.process_new_callback_query((call,))


def edit(message, addtype, call, callback):
    print(callback)
    if addtype == "course":
        db.updateCourse(call.data.split("-")[1], message.text)
    elif addtype == "topic":
        db.updateTopic(call.data.split("-")[1], call.data.split("-")[2], message.text)
    elif addtype == "task":
        db.updateTask(call.data.split("-")[1], call.data.split("-")[2], call.data.split("-")[3], message.text)
    elif addtype == "explanation":
        db.updateExplanation(call.data.split("-")[1], call.data.split("-")[2], call.data.split("-")[3], message.text)
    elif addtype == "solution":
        db.updateSolution(call.data.split("-")[1], call.data.split("-")[2], call.data.split("-")[3], message.text)
    bot.send_message(call.message.json['chat']['id'], "Успешно изменено")
    call.data = callback
    bot.process_new_callback_query((call,))


bot = telebot.TeleBot(tg_token)
print('bot is online!')


@bot.message_handler(commands=['start'])
def message(message):
    id = str(message.chat.id)
    username = str(message.from_user.username)
    check_user(id, username)
    markup_reply = ReplyKeyboardMarkup(row_width=1).add("Инфа", "Меню")
    markup_inline = InlineKeyboardMarkup(row_width=1).add(InlineKeyboardButton("Инфа", callback_data="info"),
                          InlineKeyboardButton("Меню", callback_data="menu"))
    if id in db.getAdmins() or id in owners:
        markup_reply.add("Админпанель")
        markup_inline.add(InlineKeyboardButton("Админпанель", callback_data="admin"))
    elif id in db.getStaffs():
        markup_inline.add(InlineKeyboardButton("Добавить", callback_data="add"))

    bot.send_message(id, "Здравствуйте, вас приветствует бот помощник по программированию.",
                     reply_markup=markup_reply)
    bot.send_message(id, "Этот бот предоставляет более подробное и понятное объяснение тем по спецкурсу и программированию, а также предоставляет ответы к задачам.",
                     reply_markup=markup_inline)


@bot.message_handler(commands=['info'])
def message(message):
    id = str(message.chat.id)
    username = str(message.from_user.username)
    check_user(id, username)
    client = db.getSubsByUserid(str(message.chat.id))
    if client[0] == 0:
        bot.send_message(id, "У вас нет подписки")
    else:
        bot.send_message(id,
                         f"У вас подписка {client[0]} уровня до {client[1]}, \n{'Вы являетесь админом' if client[2] else ''} \n{'Вы являетесь работником' if client[3] else ''}")

@bot.message_handler(commands=['add_admin'])
def message(message):
    id = str(message.chat.id)
    username = str(message.from_user.username)
    check_user(id, username)
    if id in db.getAdmins() or id in owners:
        userInfo = db.getInfoByUserid(id)
        db.updateUser(db.getUseridByUsername(message.text.split()[1]), userInfo[0], userInfo[1], userInfo[2], 1, userInfo[4])
        bot.send_message(id, "Добавлен")

@bot.message_handler(commands=['add_staff'])
def message(message):
    id = str(message.chat.id)
    username = str(message.from_user.username)
    check_user(id, username)
    if id in db.getAdmins() or id in owners:
        userInfo = db.getInfoByUserid(id)
        db.updateUser(db.getUseridByUsername(message.text.split()[1]), userInfo[0], userInfo[1], userInfo[2], userInfo[3], 1)
        bot.send_message(id, "Добавлен")


@bot.message_handler(content_types=['text'])
def message(message):
    # log.update({str(message.text.split()[0]): int(message.text.split()[1])})
    # bot.send_message(message.chat.id, "Добавлено")
    id = str(message.chat.id)
    username = str(message.from_user.username)
    check_user(id, username)
    markup = InlineKeyboardMarkup(row_width=1)
    if message.text == "Инфа":
        markup.add(InlineKeyboardButton("Назад", callback_data=f"mainmenu"))
        info = db.getInfoByUserid(id)
        if info[1] == 0:
            bot.send_message(id,
                             f"У вас нет подписки. \n{'Вы являетесь админом' if info[3] else ''} \n{'Вы являетесь работником' if info[4] else ''}", reply_markup=markup)
        else:
            bot.send_message(id,
                             f"У вас подписка {info[1]} уровня до {info[2]}. \n{'Вы являетесь админом' if info[3] else ''} \n{'Вы являетесь работником' if info[4] else ''}", reply_markup=markup)

    if message.text == "Меню":
        for courseid, course in db.getCourses():
            markup.add(InlineKeyboardButton(course, callback_data=f"menu-{courseid}"))

        if id in db.getStaffs() or id in db.getAdmins() or id in owners:
            foradmin = [InlineKeyboardButton("Добавить курс", callback_data=f"menu-add"), ]
            if len(db.getCourses()):
                foradmin.append(InlineKeyboardButton("Изменить курс", callback_data=f"menu-edit"))
                foradmin.append(InlineKeyboardButton("Удалить курс", callback_data=f"menu-delete"))

            markup.add(*foradmin)

        markup.add(InlineKeyboardButton("Назад", callback_data=f"mainmenu"))
        bot.send_message(id, "Выберите курс:", reply_markup=markup)


@bot.callback_query_handler(lambda call: True)
def callback(call):
    id = str(call.message.json['chat']['id'])
    username = str(call.from_user.username)
    check_user(id, username)
    markup = InlineKeyboardMarkup()
    if call.data == "mainmenu":
        markup.add(InlineKeyboardButton("Инфа", callback_data="info"),
                          InlineKeyboardButton("Меню", callback_data="menu"))
        if id in db.getAdmins() or id in owners:
            markup.add(InlineKeyboardButton("Админпанель", callback_data="admin"))

        bot.send_message(id, "Этот бот предоставляет более подробное и понятное объяснение тем по спецкурсу и программированию, а также предоставляет ответы к задачам.",
                         reply_markup=markup)

    elif call.data == "info":
        markup.add(InlineKeyboardButton("Назад", callback_data=f"mainmenu"))
        info = db.getInfoByUserid(id)
        if info[1] == 0:
            bot.send_message(id,
                             f"У вас нет подписки. \n{'Вы являетесь админом' if info[3] else ''} \n{'Вы являетесь работником' if info[4] else ''}", reply_markup=markup)
        else:
            bot.send_message(id,
                             f"У вас подписка {info[1]} уровня до {info[2]}. \n{'Вы являетесь админом' if info[3] else ''} \n{'Вы являетесь работником' if info[4] else ''}", reply_markup=markup)

    elif call.data == "admin":
        markup.add(InlineKeyboardButton("Назад", callback_data=f"mainmenu"))
        bot.send_message(id, "Это админпанель", reply_markup=markup)

    elif call.data.startswith("menu"):
        print(call.data)
        if "cancel" in call.data:
            bot.clear_step_handler_by_chat_id(int(id))
            call.data = call.data[:-7]

        elif "accept" in call.data:
            if "fordelete" in call.data:
                if id in db.getStaffs() or id in db.getAdmins() or id in owners:
                    if len(call.data.split("-")) == 4:
                        courseid = call.data.split("-")[1]
                        db.deleteCourse(courseid)
                        bot.send_message(id, "Успешно удалено")
                        call.data = "menu"

                    if len(call.data.split("-")) == 5:
                        courseid = call.data.split("-")[1]
                        topicid = call.data.split("-")[2]
                        db.deleteTopic(topicid)
                        bot.send_message(id, "Успешно удалено")
                        call.data = f"menu-{courseid}"

                    if len(call.data.split("-")) == 6:
                        courseid = call.data.split("-")[1]
                        topicid = call.data.split("-")[2]
                        taskid = call.data.split("-")[3]
                        db.deleteTask(taskid)
                        bot.send_message(id, "Успешно удалено")
                        call.data = f"menu-{courseid}-{topicid}"

                    if len(call.data.split("-")) == 7:
                        courseid = call.data.split("-")[1]
                        topicid = call.data.split("-")[2]
                        taskid = call.data.split("-")[3]
                        action = call.data.split("-")[4]
                        if action == "0":
                            db.updateExplanation(courseid, topicid, taskid, "")

                        else:
                            db.updateSolution(courseid, topicid, taskid, "")

                        bot.send_message(id, "Успешно удалено")
                        call.data = f"menu-{courseid}-{topicid}-{taskid}"

        if len(call.data.split("-")) == 1:
            for courseid, course in db.getCourses():
                markup.add(InlineKeyboardButton(course, callback_data=f"menu-{courseid}"))

            if id in db.getStaffs() or id in db.getAdmins() or id in owners:
                foradmin = [InlineKeyboardButton("Добавить курс", callback_data=f"menu-add"), ]
                if len(db.getCourses()):
                    foradmin.append(InlineKeyboardButton("Изменить курс", callback_data=f"menu-edit"))
                    foradmin.append(InlineKeyboardButton("Удалить курс", callback_data=f"menu-delete"))

                markup.add(*foradmin)

            markup.add(InlineKeyboardButton("Назад", callback_data=f"mainmenu"))
            bot.send_message(id, "Выберите курс:", reply_markup=markup)

        elif len(call.data.split("-")) == 2:
            courseid = call.data.split("-")[1]
            if call.data.endswith('add') and (id in db.getStaffs() or id in db.getAdmins() or id in owners):
                text = "Пришлите название курса:"
                if id in db.getStaffs() or id in db.getAdmins() or id in owners:
                    markup.add(InlineKeyboardButton("Отмена", callback_data=f"menu-cancel"))
                    bot.register_next_step_handler_by_chat_id(int(id), add, "course", call, "menu")

            elif call.data.endswith('edit') and (id in db.getStaffs() or id in db.getAdmins() or id in owners):
                text = "Выберите курс:"
                for courseid, course in db.getCourses():
                    markup.add(InlineKeyboardButton("✏ " + str(course), callback_data=f"menu-{courseid}-foredit"))

                markup.add(InlineKeyboardButton("Назад", callback_data=f"menu"))

            elif call.data.endswith('delete') and (id in db.getStaffs() or id in db.getAdmins() or id in owners):
                text = "Выберите курс:"
                for courseid, course in db.getCourses():
                    markup.add(InlineKeyboardButton("🗑️ " + str(course), callback_data=f"menu-{courseid}-fordelete"))

                markup.add(InlineKeyboardButton("Назад", callback_data=f"menu"))

            else:
                text = "Выберите тему:"
                for topicid, topic in db.getTopics(courseid):
                    markup.add(InlineKeyboardButton(topic, callback_data=f"menu-{courseid}-{topicid}"))

                if id in db.getStaffs() or id in db.getAdmins() or id in owners:
                    foradmin = [InlineKeyboardButton("Добавить тему", callback_data=f"menu-{courseid}-add"), ]
                    if len(db.getTopics(courseid)) != 0:
                        foradmin.append(InlineKeyboardButton("Изменить тему", callback_data=f"menu-{courseid}-edit"))
                        foradmin.append(InlineKeyboardButton("Удалить тему", callback_data=f"menu-{courseid}-delete"))

                    markup.add(*foradmin)

                markup.add(InlineKeyboardButton("Назад", callback_data=f"menu"))

            bot.send_message(id, f"{text}", reply_markup=markup)

        elif len(call.data.split("-")) == 3:
            courseid = call.data.split("-")[1]
            topicid = call.data.split("-")[2]
            if call.data.endswith('add') and (id in db.getStaffs() or id in db.getAdmins() or id in owners):
                text = "Пришлите название темы:"
                if id in db.getStaffs() or id in db.getAdmins() or id in owners:
                    markup.add(InlineKeyboardButton("Отмена", callback_data=f"menu-{courseid}-cancel"))
                    bot.register_next_step_handler_by_chat_id(int(id), add, "topic", call, f"menu-{courseid}")

            elif call.data.endswith('foredit') and (id in db.getStaffs() or id in db.getAdmins() or id in owners):
                text = "Пришлите новое название курса:"
                markup.add(InlineKeyboardButton("Отмена", callback_data=f"menu-cancel"))
                bot.register_next_step_handler_by_chat_id(int(id), edit, "course", call, f"menu")

            elif call.data.endswith('edit') and (id in db.getStaffs() or id in db.getAdmins() or id in owners):
                text = "Выберите тему:"
                for topicid, topic in db.getTopics(courseid):
                    markup.add(InlineKeyboardButton("✏ " + str(topic), callback_data=f"menu-{courseid}-{topicid}-foredit"))

                markup.add(InlineKeyboardButton("Назад", callback_data=f"menu-{courseid}"))

            elif call.data.endswith('fordelete') and (id in db.getStaffs() or id in db.getAdmins() or id in owners):
                text = "Вы уверены, что хотите удалить курс " + str(db.getCourse(courseid)) + "?"
                markup.add(InlineKeyboardButton("Да", callback_data=f"menu-{courseid}-fordelete-accept"))
                markup.add(InlineKeyboardButton("Отмена", callback_data=f"menu"))

            elif call.data.endswith('delete') and (id in db.getStaffs() or id in db.getAdmins() or id in owners):
                text = "Выберите тему"
                for topicid, topic in db.getTopics(courseid):
                    markup.add(InlineKeyboardButton("🗑 " + str(topic), callback_data=f"menu-{courseid}-{topicid}-fordelete"))

                markup.add(InlineKeyboardButton("Назад", callback_data=f"menu-{courseid}"))

            else:
                text = "Выберите задание:"
                courseid = call.data.split("-")[1]
                topicid = call.data.split("-")[2]
                for taskid, task in db.getTasks(courseid, topicid):
                    markup.add(InlineKeyboardButton(task, callback_data=f"menu-{courseid}-{topicid}-{taskid}"))

                if id in db.getStaffs() or id in db.getAdmins() or id in owners:
                    foradmin = [InlineKeyboardButton("Добавить задание", callback_data=f"menu-{courseid}-{topicid}-add"), ]
                    if len(db.getTasks(courseid, topicid)) != 0:
                        foradmin.append(InlineKeyboardButton("Изменить задание", callback_data=f"menu-{courseid}-{topicid}-edit"))
                        foradmin.append(InlineKeyboardButton("Удалить задание", callback_data=f"menu-{courseid}-{topicid}-delete"))

                    markup.add(*foradmin)

                markup.add(InlineKeyboardButton("Назад", callback_data=f"menu-{courseid}"))

            bot.send_message(id, f"{text}", reply_markup=markup)

        elif len(call.data.split("-")) == 4:
            courseid = call.data.split("-")[1]
            topicid = call.data.split("-")[2]
            taskid = call.data.split("-")[3]
            if call.data.endswith('add') and (id in db.getStaffs() or id in db.getAdmins() or id in owners):
                text = "Пришлите название задания:"
                markup.add(InlineKeyboardButton("Отмена", callback_data=f"menu-{courseid}-{topicid}-cancel"))
                bot.register_next_step_handler_by_chat_id(int(id), add, "task", call, f"menu-{courseid}-{topicid}")

            elif call.data.endswith('foredit') and (id in db.getStaffs() or id in db.getAdmins() or id in owners):
                text = "Пришлите новое название темы:"
                markup.add(InlineKeyboardButton("Отмена", callback_data=f"menu-{courseid}-cancel"))
                bot.register_next_step_handler_by_chat_id(int(id), edit, "topic", call, f"menu-{courseid}")

            elif call.data.endswith('edit') and (id in db.getStaffs() or id in db.getAdmins() or id in owners):
                text = "Выберите задание:"
                for taskid, task in db.getTasks(courseid, topicid):
                    markup.add(InlineKeyboardButton("✏ " + str(task), callback_data=f"menu-{courseid}-{topicid}-{taskid}-foredit"))

                markup.add(InlineKeyboardButton("Назад", callback_data=f"menu-{courseid}-{topicid}"))

            elif call.data.endswith('fordelete') and (id in db.getStaffs() or id in db.getAdmins() or id in owners):
                text = "Вы уверены, что хотите удалить тему " + str(db.getTopic(topicid)) + "?"
                markup.add(InlineKeyboardButton("Да", callback_data=f"menu-{courseid}-{topicid}-fordelete-accept"))
                markup.add(InlineKeyboardButton("Отмена", callback_data=f"menu-{courseid}-cancel"))

            elif call.data.endswith('delete') and (id in db.getStaffs() or id in db.getAdmins() or id in owners):
                text = "Выберите задание:"
                for taskid, task in db.getTasks(courseid, topicid):
                    markup.add(InlineKeyboardButton("🗑 " + str(task), callback_data=f"menu-{courseid}-{topicid}-{taskid}-fordelete"))

                markup.add(InlineKeyboardButton("Назад", callback_data=f"menu-{courseid}-{topicid}"))

            else:
                text = "Выберите объяснение или решение:"
                if db.getExplanation(courseid, topicid, taskid) is not None and db.getExplanation(courseid, topicid, taskid) != "":
                    markup.add(InlineKeyboardButton("Объяснение", callback_data=f"menu-{courseid}-{topicid}-{taskid}-0"))

                else:
                    if id in db.getStaffs() or id in db.getAdmins() or id in owners:
                        markup.add(InlineKeyboardButton("Добавить объяснение", callback_data=f"menu-{courseid}-{topicid}-{taskid}-0-add"))

                    else:
                        markup.add(InlineKeyboardButton("Нет объяснения", callback_data=f"none"))

                if db.getSolution(courseid, topicid, taskid) is not None and db.getSolution(courseid, topicid, taskid) != "":
                    markup.add(InlineKeyboardButton("Решение", callback_data=f"menu-{courseid}-{topicid}-{taskid}-1"))

                else:
                    if id in db.getStaffs() or id in db.getAdmins() or id in owners:
                        markup.add(InlineKeyboardButton("Добавить решение", callback_data=f"menu-{courseid}-{topicid}-{taskid}-1-add"))

                    else:
                        markup.add(InlineKeyboardButton("Нет решения", callback_data=f"none"))

                markup.add(InlineKeyboardButton("Назад", callback_data=f"menu-{courseid}-{topicid}"))

            bot.send_message(id, f"{text}", reply_markup=markup)

        elif len(call.data.split("-")) == 5:
            courseid = call.data.split("-")[1]
            topicid = call.data.split("-")[2]
            taskid = call.data.split("-")[3]
            action = call.data.split("-")[4]
            if call.data.endswith('foredit'):
                text = "Пришлите новое название задание:"
                markup.add(InlineKeyboardButton("Отмена", callback_data=f"menu-{courseid}-{topicid}-cancel"))
                bot.register_next_step_handler_by_chat_id(int(id), edit, "task", call, f"menu-{courseid}-{topicid}")

            elif call.data.endswith('edit'):
                text = "Выберите:"
                if db.getExplanation(courseid, topicid, taskid) is not None and db.getExplanation(courseid, topicid, taskid) != "":
                    markup.add(InlineKeyboardButton("✏ Объяснение", callback_data=f"menu-{courseid}-{topicid}-{taskid}-0-foredit"))
                if db.getSolution(courseid, topicid, taskid) is not None  and db.getSolution(courseid, topicid, taskid) != "":
                    markup.add(InlineKeyboardButton("✏ Решение", callback_data=f"menu-{courseid}-{topicid}-{taskid}-1-foredit"))
                markup.add(InlineKeyboardButton("Назад", callback_data=f"menu-{courseid}-{topicid}-{taskid}"))

            elif call.data.endswith('fordelete'):
                text = "Вы уверены, что хотите удалить задание " + str(db.getTask(taskid)) + "?"
                markup.add(InlineKeyboardButton("Да", callback_data=f"menu-{courseid}-{topicid}-{taskid}-fordelete-accept"))
                markup.add(InlineKeyboardButton("Отмена", callback_data=f"menu-{courseid}-{topicid}-{taskid}-cancel"))

            elif call.data.endswith('delete'):
                text = "Выберите:"
                if db.getExplanation(courseid, topicid, taskid) is not None and db.getExplanation(courseid, topicid, taskid) != "":
                    markup.add(InlineKeyboardButton("✏ Объяснение", callback_data=f"menu-{courseid}-{topicid}-{taskid}-0-fordelete"))
                if db.getSolution(courseid, topicid, taskid) is not None  and db.getSolution(courseid, topicid, taskid) != "":
                    markup.add(InlineKeyboardButton("✏ Решение", callback_data=f"menu-{courseid}-{topicid}-{taskid}-1-fordelete"))
                markup.add(InlineKeyboardButton("Назад", callback_data=f"menu-{courseid}-{topicid}"))

            else:
                if action == "0":
                    text = db.getExplanation(courseid, topicid, taskid) if db.getExplanation(courseid, topicid, taskid) is not None and db.getExplanation(courseid, topicid, taskid) != "" else "Нет"
                    markup.add(InlineKeyboardButton("Назад", callback_data=f"menu-{courseid}-{topicid}-{taskid}"))
                else:
                    if id in db.getSubs() or db in db.getStaffs() or id in db.getAdmins() or id in owners:
                        text = db.getSolution(courseid, topicid, taskid) if db.getSolution(courseid, topicid, taskid) is not None and db.getSolution(courseid, topicid, taskid) != "" else "Нет"
                        markup.add(InlineKeyboardButton("Назад", callback_data=f"menu-{courseid}-{topicid}-{taskid}"))

                    elif id in db.getUsers():
                        text = "Чтобы просмотреть решения вам нужна подписка, вы можете приобрести её по кнопке ниже."
                        markup.add(InlineKeyboardButton("Купить подписку", callback_data="buy"))
                        markup.add(InlineKeyboardButton("Назад", callback_data=f"menu-{courseid}-{topicid}-{taskid}"))

            bot.send_message(id, f"{text}", reply_markup=markup)

        elif len(call.data.split("-")) == 6:
            courseid = call.data.split("-")[1]
            topicid = call.data.split("-")[2]
            taskid = call.data.split("-")[3]
            action = call.data.split("-")[4]
            if call.data.endswith("add"):
                if action == "0":
                    if id in db.getStaffs() or id in db.getAdmins() or id in owners:
                        text = "Пришлите объяснение"
                        markup.add(InlineKeyboardButton("Отмена", callback_data=f"menu-{courseid}-{topicid}-{taskid}-cancel"))
                        bot.register_next_step_handler_by_chat_id(int(id), add, "explanation", call, f"menu-{courseid}-{topicid}-{taskid}")

                else:
                    if id in db.getStaffs() or id in db.getAdmins() or id in owners:
                        text = "Пришлите решение"
                        markup.add(InlineKeyboardButton("Отмена", callback_data=f"menu-{courseid}-{topicid}-{taskid}-cancel"))
                        bot.register_next_step_handler_by_chat_id(int(id), add, "solution", call, f"menu-{courseid}-{topicid}-{taskid}")

            elif call.data.endswith('foredit'):
                text = f"Пришлите новое {'объяснение' if action == 0 else 'решение'}"
                markup.add(InlineKeyboardButton("Отмена", callback_data=f"menu-{courseid}-{topicid}-{taskid}-cancel"))
                bot.register_next_step_handler_by_chat_id(int(id), edit, "task", call, f"menu-{courseid}-{topicid}-{taskid}")

            elif call.data.endswith('fordelete'):
                text = f"Вы уверены, что хотите удалить {'объяснение' if action == 0 else 'решение'} к заданию " + str(db.getTask(taskid)) + "?"
                markup.add(InlineKeyboardButton("Да", callback_data=f"menu-{courseid}-{topicid}-{taskid}-{action}-fordelete-accept"))
                markup.add(InlineKeyboardButton("Отмена", callback_data=f"menu-{courseid}-{topicid}-{taskid}-{action}-cancel"))

            bot.send_message(id, f"{text}:", reply_markup=markup)


    #
    # elif call.data.startswith("add"):
    #     markup = InlineKeyboardMarkup(row_width=1)
    #     if "cancel" in call.data:
    #         bot.clear_step_handler()
    #
    #     elif call.data.endswith("course"):
    #         markup.add(InlineKeyboardButton("Назад", callback_data="add-cancel"))
    #         message = bot.send_message(id, "Пришлите название курса", reply_markup=markup)
    #         bot.register_next_step_handler_by_chat_id(message, add, call, "add")
    #
    #     elif call.data.endswith("topic"):
    #         courseid = call.data.split("-")[1]
    #         markup.add(InlineKeyboardButton("Назад", callback_data="add-cancel"))
    #         message = bot.send_message(id, "Пришлите название темы", reply_markup=markup)
    #         bot.register_next_step_handler_by_chat_id(message, add, call, f"add-{courseid}")
    #
    #     elif len(call.data.split("-")) == 1:
    #         for courseid, course in db.getCourses():
    #             markup.add(InlineKeyboardButton(course, callback_data=f"add-{courseid}"))
    #         markup.add(InlineKeyboardButton("Добавить курс", callback_data=f"add-course"))
    #         markup.add(InlineKeyboardButton("Назад", callback_data=f"mainmenu"))
    #         bot.send_message(id, "Выберите курс:", reply_markup=markup)
    #
    #     elif len(call.data.split("-")) == 2:
    #         courseid = call.data.split("-")[1]
    #         for topicid, topic in db.getTopics(courseid):
    #             markup.add(InlineKeyboardButton(topic, callback_data=f"add-{courseid}-{topicid}"))
    #         markup.add(InlineKeyboardButton("Добавить тему", callback_data=f"add-{courseid}-topic"))
    #         markup.add(InlineKeyboardButton("Назад", callback_data=f"add"))
    #         bot.send_message(id, "Выберите тему:", reply_markup=markup)
    #
    #     elif len(call.data.split("-")) == 3:
    #         courseid = call.data.split("-")[1]
    #         topicid = call.data.split("-")[2]
    #         for taskid, task in db.getTasks(courseid, topicid):
    #             markup.add(InlineKeyboardButton(task, callback_data=f"add-{courseid}-{topicid}-{taskid}"))
    #         markup.add(InlineKeyboardButton("Добавить тему", callback_data=f"add-{courseid}-{topicid}-task"))
    #         markup.add(InlineKeyboardButton("Назад", callback_data=f"add-{courseid}"))
    #         bot.send_message(id, "Выберите задание:", reply_markup=markup)
    #
    #     elif len(call.data.split("-")) == 4:
    #         courseid = call.data.split("-")[1]
    #         topicid = call.data.split("-")[2]
    #         taskid = call.data.split("-")[3]
    #         if db.getExplanation(courseid, topicid, taskid) is not None:
    #             markup.add(InlineKeyboardButton("Объяснение", callback_data=f"add-{courseid}-{topicid}-{taskid}-0"))
    #         else:
    #             markup.add(InlineKeyboardButton("Добавить тему", callback_data=f"add-{courseid}-topic"))
    #         markup.add(InlineKeyboardButton("Решение", callback_data=f"add-{courseid}-{topicid}-{taskid}-1"))
    #         markup.add(InlineKeyboardButton("Назад", callback_data=f"add-{courseid}-{topicid}"))
    #         bot.send_message(id, "Выберите нужное:", reply_markup=markup)
    #
    #     elif len(call.data.split("-")) == 5:
    #         courseid = call.data.split("-")[1]
    #         topicid = call.data.split("-")[2]
    #         taskid = call.data.split("-")[3]
    #         action = call.data.split("-")[4]
    #         if action == "0":
    #             markup.add(InlineKeyboardButton("Назад", callback_data=f"add-{courseid}-{topicid}-{taskid}"))
    #             bot.send_message(id, db.getExplanation(courseid, topicid, taskid), reply_markup=markup)
    #
    #         else:
    #             if id in db.getSubs() or db in db.getStaffs() or id in db.getAdmins() or id in owners:
    #                 markup.add(InlineKeyboardButton("Назад", callback_data=f"add-{courseid}-{topicid}-{taskid}"))
    #                 bot.send_message(id, db.getSolution(courseid, topicid, taskid), reply_markup=markup)
    #
    #             elif id in db.getUsers():
    #                 markup.add(InlineKeyboardButton("Купить подписку", callback_data="buy"))
    #                 markup.add(InlineKeyboardButton("Назад", callback_data=f"add-{courseid}-{topicid}-{taskid}"))
    #                 bot.send_message(id, "Чтобы просмотреть решения вам нужна подписка, вы можете приобрести её по кнопке ниже.", reply_markup=markup)

    elif call.data == "buy":
        client = db.getSubs()
        if client is None:
            db.addUser(id, username, datetime.now().strftime("%d.%m.%Y"))
            bot.send_message(call.message.json['chat']['id'], "Добавлен")
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
