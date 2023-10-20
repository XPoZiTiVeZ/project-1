import telebot
from telebot.types import ReplyKeyboardMarkup, InlineKeyboardMarkup, InlineKeyboardButton
from random import choice
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
log = {}
checking_codes = {}
owners = ['hayk9685', 'lukashevda']
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

def get_key(d, value):
	for k, v in d.items():
		if v == value:
			return k
		
def check():
	while True:
		donations = list(log.items())
		for username, amount in donations:
			id = db.getUseridByUsername(username)
			info = db.getInfoByUserid(id) if id is not None else None
			if info is not None and info[1] != 0 and username in checking_codes.keys():
				checking_codes.pop(username, "")
				log.pop(username, "")
	
			elif username in checking_codes.keys() and amount >= price:
				markup = InlineKeyboardMarkup().add(InlineKeyboardButton("Назад", callback_data=f"newmainmenu"))
				bot.delete_message(chat_id=id, message_id=checking_codes.get(username))
				bot.send_message(id, "Пришёл код, ваша подписка оплачена.", reply_markup=markup)
				markup = InlineKeyboardMarkup().add(InlineKeyboardButton("Назад", callback_data=f"newmainmenu"))
				db.updateUser(id, username, 1, (datetime.now() + relativedelta(months=1)).strftime("%d.%m.%Y"), info[3])
				checking_codes.pop(username, "")
				log.pop(username, "")
	
			elif amount <= price:
				bot.delete_message(chat_id=id, message_id=checking_codes.get(username))
				markup = InlineKeyboardMarkup().add(InlineKeyboardButton("Купить подписку", callback_data="buy")).add(InlineKeyboardButton("Назад", callback_data=f"newmainmenu"))
				bot.send_message(id, "Пришёл код, но суммы платежа не хватило для оплаты подписки.", reply_markup=markup)
				checking_codes.pop(username, "")
				log.pop(username, "")

		for userid in db.getSubs():
			info = db.getInfoByUserid(userid)
			if datetime.strptime(info[2], "%d.%m.%Y") < datetime.now():
				markup = InlineKeyboardMarkup().add(InlineKeyboardButton("Купить подписку", callback_data="buy")).add(InlineKeyboardButton("Назад", callback_data=f"newmainmenu"))
				db.updateUser(userid, info[0], 0, info[2], info[3])
				bot.send_message(userid, "У вас закончилась подписка, продлите её по кнопке ниже, чтобы продолжить пользоваться решениями.", reply_markup=markup)

		time.sleep(1)
  
# def gencode(length):
# 	letters = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789012345678901234567890123456789"
# 	code = ''.join(("-" if i % 4 == 0 and i != 0 else "") + choice(letters) for i in range(length))
# 	return code

def check_user(userid, username):
	userInfo = db.getInfoByUserid(userid)
	if userid not in db.getUsers(0):
		db.addUser(userid, username, datetime.now().strftime("%d.%m.%Y"))
	elif username != userInfo[0]:
		db.updateUser(userid, username, userInfo[1], userInfo[2], userInfo[3])


def add_course(message, addtype, call, callback):
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


def edit_course(message, addtype, call, callback):
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


def update_user(message, permlevel, call, callback):
	id = str(call.message.json['chat']['id'])
	userid = db.getUseridByUsername(call.data.split("-")[1])
	if call.data.endswith("addadmins") or call.data.endswith("addstaffs") or call.data.endswith("addusers") or call.data.endswith("addblocks"):
		info = db.getInfoByUserid(db.getUseridByUsername(message.text))
		if info is not None:
			print(message.text, info[0], info[1], info[2], permlevel)
			db.updateUser(db.getUseridByUsername(message.text), info[0], info[1], info[2], permlevel)
			bot.send_message(id, "Успешно изменено")
		else:
			bot.send_message(id, "Не найдено пользователя с таким именем")

	else:
		userid = call.data.split("-")[1]
		if call.data.endswith("tosub") or call.data.endswith("tounsub"):
			info = db.getInfoByUserid(userid)
			if info is not None:
				db.updateUser(userid, info[0], permlevel, (datetime.now() + relativedelta(months=1)).strftime("%d.%m.%Y"), info[3])
				bot.send_message(id, "Успешно изменено")
		else:
			info = db.getInfoByUserid(userid)
			if info is not None:
				db.updateUser(userid, info[0], info[1], info[2], permlevel)
				bot.send_message(id, "Успешно изменено")

	call.data = callback
	bot.process_new_callback_query((call,))


bot = telebot.TeleBot(tg_token)
print('bot is online!')

def delayed_delete(chat_id, message_id, timeout):
	time.sleep(timeout)
	try:
		bot.delete_message(chat_id, message_id)
	except telebot.apihelper.ApiTelegramException:
		pass
	checking_codes.pop(db.getInfoByUserid(chat_id)[0], "")
	log.pop(db.getInfoByUserid(chat_id)[0], "")

@bot.message_handler(commands=['start'])
def message(message):
	id = str(message.chat.id)
	username = str(message.from_user.username)
	check_user(id, username)
	markup_reply = ReplyKeyboardMarkup(row_width=1).add("Инфа", "Меню")
	markup_inline = InlineKeyboardMarkup().add(InlineKeyboardButton("Инфа", callback_data="info"),
											   InlineKeyboardButton("Меню", callback_data="menu"))
	if id in db.getUsers(2) or id in [db.getUseridByUsername(username) for username in owners]:
		markup_reply.add("Админпанель")
		markup_inline.add(InlineKeyboardButton("Админпанель", callback_data="admin"))
	elif id in db.getUsers(1):
		markup_inline.add(InlineKeyboardButton("Добавить", callback_data="add"))

	bot.send_message(id, "Здравствуйте, вас приветствует бот помощник по программированию.",
					 reply_markup=markup_reply)
	bot.send_message(id,
					 "Этот бот предоставляет более подробное и понятное объяснение тем по спецкурсу и программированию, а также предоставляет ответы к задачам.",
					 reply_markup=markup_inline)


@bot.message_handler(commands=['info'])
def message(message):
	id = str(message.chat.id)
	username = str(message.from_user.username)
	check_user(id, username)
	info = db.getSubsByUserid(str(message.chat.id))
	markup = InlineKeyboardMarkup()
	if info[0] == 0 and id not in [db.getUseridByUsername(username) for username in owners]:
		markup.add(InlineKeyboardButton("Купить подписку", callback_data="buy"))
		markup.add(InlineKeyboardButton("Назад", callback_data=f"mainmenu"))
		bot.send_message(id, f"У вас нет подписки. \n{'Вы являетесь работником' if info[2] >= 2 else ''} \n{'Вы являетесь админом' if info[2] >= 1 else ''} \n{'Вы являетесь владельцем' if id in [db.getUseridByUsername(username) for username in owners] else ''}", reply_markup=markup)
	else:
		markup.add(InlineKeyboardButton("Назад", callback_data=f"mainmenu"))
		bot.send_message(id,
						 f"У вас подписка {info[0]} уровня до {info[1]}. \n{'Вы являетесь работником' if info[2] >= 2 else ''} \n{'Вы являетесь админом' if info[2] >= 1 else ''} \n{'Вы являетесь владельцем' if id in [db.getUseridByUsername(username) for username in owners] else ''}", reply_markup=markup)


# @bot.message_handler(commands=['add_admin'])
# def message(message):
# 	id = str(message.chat.id)
# 	username = str(message.from_user.username)
# 	check_user(id, username)
# 	if id in db.getUsers(2) or id in [db.getUseridByUsername(username) for username in owners]:
# 		userInfo = db.getInfoByUserid(id)
# 		db.updateUser(db.getUseridByUsername(message.text.split()[1]), userInfo[0], userInfo[1], userInfo[2], 1,
# 					  userInfo[4])
# 		bot.send_message(id, "Добавлен")


# @bot.message_handler(commands=['add_staff'])
# def message(message):
# 	id = str(message.chat.id)
# 	username = str(message.from_user.username)
# 	check_user(id, username)
# 	if id in db.getUsers(2) or id in [db.getUseridByUsername(username) for username in owners]:
# 		userInfo = db.getInfoByUserid(id)
# 		db.updateUser(db.getUseridByUsername(message.text.split()[1]), userInfo[0], userInfo[1], userInfo[2],
# 					  userInfo[3], 1)
# 		bot.send_message(id, "Добавлен")


@bot.message_handler(content_types=['text'])
def message(message):
	id = str(message.chat.id)
	username = str(message.from_user.username)
	check_user(id, username)
	markup = InlineKeyboardMarkup()
	if message.text == "Инфа":
		info = db.getInfoByUserid(id)
		if info[1] == 0 and id not in [db.getUseridByUsername(username) for username in owners]:
			markup.add(InlineKeyboardButton("Купить подписку", callback_data="buy"))
			markup.add(InlineKeyboardButton("Назад", callback_data=f"mainmenu"))
			bot.send_message(id,
							 f"У вас нет подписки. \n{'Вы являетесь работником' if info[3] >= 1 else ''} \n{'Вы являетесь админом' if info[3] >= 2 else ''} \n{'Вы являетесь владельцем' if id in [db.getUseridByUsername(username) for username in owners] else ''}",
							 reply_markup=markup)
		else:
			markup.add(InlineKeyboardButton("Назад", callback_data=f"mainmenu"))
			bot.send_message(id,
							 f"У вас подписка {info[1]} уровня до {info[2]}. \n{'Вы являетесь работником' if info[3] >= 1 else ''} \n{'Вы являетесь админом' if info[3] >= 2 else ''} \n{'Вы являетесь владельцем' if id in [db.getUseridByUsername(username) for username in owners] else ''}",
							 reply_markup=markup)

	if message.text == "Меню":
		for courseid, course in db.getCourses():
			markup.add(InlineKeyboardButton(course, callback_data=f"menu-{courseid}"))

		if id in db.getUsers(1) or id in [db.getUseridByUsername(username) for username in owners]:
			foradmin = [InlineKeyboardButton("Добавить курс", callback_data=f"menu-add"), ]
			if len(db.getCourses()):
				foradmin.append(InlineKeyboardButton("Изменить курс", callback_data=f"menu-edit"))
				foradmin.append(InlineKeyboardButton("Удалить курс", callback_data=f"menu-delete"))

			markup.add(*foradmin)

		markup.add(InlineKeyboardButton("Назад", callback_data=f"mainmenu"))
		bot.send_message(id, "Выберите курс:", reply_markup=markup)

	if message.text == "Админпанель" and (id in db.getUsers(2) or id in [db.getUseridByUsername(username) for username in owners]):
		text = "Админпанель:"
		markup.add(InlineKeyboardButton("Админы", callback_data=f"admin-admins"))
		markup.add(InlineKeyboardButton("Работники", callback_data=f"admin-staffs"))
		markup.add(InlineKeyboardButton("Подписчики", callback_data=f"admin-subs"))
		markup.add(InlineKeyboardButton("Пользователи", callback_data=f"admin-users"))
		markup.add(InlineKeyboardButton("Заблокированные", callback_data=f"admin-blocks"))
		markup.add(InlineKeyboardButton("Назад", callback_data=f"mainmenu"))
		bot.send_message(id, text, reply_markup=markup)

@bot.callback_query_handler(lambda call: True)
def callback(call):
	id = str(call.message.json['chat']['id'])
	username = str(call.from_user.username)
	check_user(id, username)
	markup = InlineKeyboardMarkup()
	if call.data == "mainmenu" or call.data == "newmainmenu":
		markup.add(InlineKeyboardButton("Инфа", callback_data="info"),
				   InlineKeyboardButton("Меню", callback_data="menu"))
		if id in db.getUsers(2) or id in [db.getUseridByUsername(username) for username in owners]:
			markup.add(InlineKeyboardButton("Админпанель", callback_data="admin"))

		if call.data.startswith("new"):
			bot.send_message(id,
							 "Этот бот предоставляет более подробное и понятное объяснение тем по спецкурсу и программированию, а также предоставляет ответы к задачам.",
							 reply_markup=markup)
		else:
			bot.edit_message_text(chat_id=id, message_id=call.message.message_id, text="Этот бот предоставляет более подробное и понятное объяснение тем по спецкурсу и программированию, а также предоставляет ответы к задачам.",
								  reply_markup=markup)

	elif call.data == "info" or  call.data == "newinfo":
		info = db.getInfoByUserid(id)
		if info[1] == 0:
			markup.add(InlineKeyboardButton("Купить подписку", callback_data="buy"))
			markup.add(InlineKeyboardButton("Назад", callback_data=f"mainmenu"))
			text = f"У вас нет подписки. \n{'Вы являетесь админом' if info[3] >= 1 else ''} \n{'Вы являетесь работником' if info[3] >= 2 else ''} \n{'Вы являетесь владельцем' if id in [db.getUseridByUsername(username) for username in owners] else ''}"

		else:
			markup.add(InlineKeyboardButton("Назад", callback_data=f"mainmenu"))
			text = f"У вас подписка {info[1]} уровня до {info[2]}. \n{'Вы являетесь работником' if info[3] >= 1 else ''} \n{'Вы являетесь Админом' if info[3] >= 2 else ''} \n{'Вы являетесь владельцем' if id in [db.getUseridByUsername(username) for username in owners] else ''}"

		if call.data.startswith("new"):
			bot.send_message(id, text, reply_markup=markup)

		else:
			bot.edit_message_text(chat_id=id, message_id=call.message.message_id, text=text, reply_markup=markup)

	elif call.data.startswith("admin") or call.data.startswith("newadmin"):
		if id in db.getUsers(2) or id in [db.getUseridByUsername(username) for username in owners]:
			print(call.data)
			if "cancel" in call.data:
				bot.clear_step_handler_by_chat_id(int(id))
				call.data = call.data[:-7]

			if call.data.endswith("admins"):
				if call.data.endswith("addadmins"):
					text = "Админпанель -> Админы -> Добавить админа\nВведите имя пользователя:"
					markup.add(InlineKeyboardButton("Отмена", callback_data=f"newadmin-admins-cancel"))
					bot.register_next_step_handler_by_chat_id(int(id), update_user, 2, call, "newadmin-admins")
				elif len(call.data.split("-")) == 3:
					userid = call.data.split("-")[1]
					text = f"Админпанель -> Админы -> {db.getInfoByUserid(userid)[0]}:"
					markup.add(InlineKeyboardButton("Понизить", callback_data=f"admin-{userid}-admins-tostaff"))
					markup.add(InlineKeyboardButton("Сбросить", callback_data=f"admin-{userid}-admins-touser"))
					markup.add(InlineKeyboardButton("Заблокировать", callback_data=f"admin-{userid}-admins-block"))
					markup.add(InlineKeyboardButton("Назад", callback_data=f"admin-admins"))
				else:
					text = "Админпанель -> Админы:"
					for userid, username in db.getUsersByPermlevel(2):
						markup.add(InlineKeyboardButton(username, callback_data=f"admin-{userid}-admins"))
					markup.add(InlineKeyboardButton("Добавить", callback_data=f"admin-addadmins"))
					markup.add(InlineKeyboardButton("Назад", callback_data=f"admin"))

			elif call.data.endswith("staffs"):
				if call.data.endswith("addstaffs"):
					text = "Админпанель -> Работники -> Добавить работника\nВведите имя пользователя:"
					markup.add(InlineKeyboardButton("Отмена", callback_data=f"newadmin-staffs-cancel"))
					bot.register_next_step_handler_by_chat_id(int(id), update_user, 1, call, "newadmin-staffs")
				elif len(call.data.split("-")) == 3:
					userid = call.data.split("-")[1]
					text = f"Админпанель -> Работники -> {db.getInfoByUserid(userid)[0]}:"
					markup.add(InlineKeyboardButton("Повысить", callback_data=f"admin-{userid}-staffs-toadmin"))
					markup.add(InlineKeyboardButton("Понизить", callback_data=f"admin-{userid}-staffs-touser"))
					markup.add(InlineKeyboardButton("Заблокировать", callback_data=f"admin-{userid}-staffs-block"))
					markup.add(InlineKeyboardButton("Назад", callback_data=f"admin-staffs"))
				else:
					text = "Админпанель -> Работники:"
					for userid, username in db.getUsersByPermlevel(1):
						markup.add(InlineKeyboardButton(username, callback_data=f"admin-{userid}-staffs"))
					markup.add(InlineKeyboardButton("Добавить", callback_data=f"admin-addstaffs"))
					markup.add(InlineKeyboardButton("Назад", callback_data=f"admin"))

			elif call.data.endswith("subs"):
				if call.data.endswith("addsubs"):
					text = "Админпанель -> Подписчики -> Добавить подписчика\nВведите имя пользователя:"
					markup.add(InlineKeyboardButton("Отмена", callback_data=f"newadmin-subs-cancel"))
					bot.register_next_step_handler_by_chat_id(int(id), update_user, 0, call, "newadmin-subs")
				elif len(call.data.split("-")) == 3:
					userid = call.data.split("-")[1]
					text = f"Админпанель -> Подписчики -> {db.getInfoByUserid(userid)[0]}:"
					markup.add(InlineKeyboardButton("Сделать админом", callback_data=f"admin-{userid}-subs-toadmin"))
					markup.add(InlineKeyboardButton("Сделать работником", callback_data=f"admin-{userid}-subs-tostaff"))
					markup.add(InlineKeyboardButton("Отменить подписку", callback_data=f"admin-{userid}-subs-tounsub"))
					markup.add(InlineKeyboardButton("Заблокировать", callback_data=f"admin-{userid}-subs-block"))
					markup.add(InlineKeyboardButton("Назад", callback_data=f"admin-subs"))
				else:
					text = "Админпанель -> Подписчики:"
					users = db.getUsersByPermlevel(0)
					subs = db.getSubs()
					for i, user in enumerate(users):
						if user[0] not in subs:
							users.pop(i)
					for userid, username in users:
						markup.add(InlineKeyboardButton(username, callback_data=f"admin-{userid}-subs"))
					markup.add(InlineKeyboardButton("Добавить", callback_data=f"admin-addsubs"))
					markup.add(InlineKeyboardButton("Назад", callback_data=f"admin"))

			elif call.data.endswith("users"):
				if call.data.endswith("addusers"):
					text = "Админпанель -> Пользователи -> Добавить пользователя\nВведите имя пользователя:"
					markup.add(InlineKeyboardButton("Отмена", callback_data=f"newadmin-users-cancel"))
					bot.register_next_step_handler_by_chat_id(int(id), update_user, 0, call, "newadmin-users")
				elif len(call.data.split("-")) == 3:
					userid = call.data.split("-")[1]
					text = f"Админпанель -> Пользователи -> {db.getInfoByUserid(userid)[0]}:"
					markup.add(InlineKeyboardButton("Сделать админом", callback_data=f"admin-{userid}-users-toadmin"))
					markup.add(InlineKeyboardButton("Сделать работником", callback_data=f"admin-{userid}-users-tostaff"))
					markup.add(InlineKeyboardButton("Добавить подписку", callback_data=f"admin-{userid}-users-tosub"))
					markup.add(InlineKeyboardButton("Заблокировать", callback_data=f"admin-{userid}-users-block"))
					markup.add(InlineKeyboardButton("Назад", callback_data=f"admin-users"))
				else:
					text = "Админпанель -> Пользователи:"
					users = db.getUsersByPermlevel(0)
					subs = db.getSubs()
					for i, user in enumerate(users):
						if user[0] in subs:
							users.pop(i)
					for userid, username in users:
						markup.add(InlineKeyboardButton(username, callback_data=f"admin-{userid}-users"))
					markup.add(InlineKeyboardButton("Добавить", callback_data=f"admin-addusers"))
					markup.add(InlineKeyboardButton("Назад", callback_data=f"admin"))

			elif call.data.endswith("blocks"):
				if call.data.endswith("addblocks"):
					text = "Админпанель -> Заблокированные -> Добавить заблокированного\nВведите имя пользователя:"
					markup.add(InlineKeyboardButton("Отмена", callback_data=f"newadmin-blocks-cancel"))
					bot.register_next_step_handler_by_chat_id(int(id), update_user, -1, call, "newadmin-users")
				elif len(call.data.split("-")) == 3:
					userid = call.data.split("-")[1]
					text = f"Админпанель -> Заблокированные -> {db.getInfoByUserid(userid)[0]}:"
					markup.add(InlineKeyboardButton("Сделать админом", callback_data=f"admin-{userid}-blocks-toadmin"))
					markup.add(InlineKeyboardButton("Сделать работником", callback_data=f"admin-{userid}-blocks-tostaff"))
					markup.add(InlineKeyboardButton("Разблокировать", callback_data=f"admin-{userid}-blocks-touser"))
					markup.add(InlineKeyboardButton("Назад", callback_data=f"admin-blocks"))
				else:
					text = "Админпанель -> Заблокированные:"
					for userid, username in db.getUsersByPermlevel(-1):
						markup.add(InlineKeyboardButton(username, callback_data=f"admin-{userid}-blocks"))
					markup.add(InlineKeyboardButton("Добавить", callback_data=f"admin-addblocks"))
					markup.add(InlineKeyboardButton("Назад", callback_data=f"admin"))

			elif call.data.endswith("toadmin"):
				tab = call.data.split("-")[2]
				update_user(call.data.split("-")[1], 2, call, "newadmin-"+tab)

			elif call.data.endswith("tostaff"):
				tab = call.data.split("-")[2]
				update_user(None, 1, call, "newadmin-"+tab)

			elif call.data.endswith("tosub"):
				tab = call.data.split("-")[2]
				update_user(None, 1, call, "newadmin-"+tab)

			elif call.data.endswith("tounsub"):
				tab = call.data.split("-")[2]
				update_user(None, 0, call, "newadmin-"+tab)

			elif call.data.endswith("touser"):
				tab = call.data.split("-")[2]
				update_user(None, 0, call, "newadmin-"+tab)

			elif call.data.endswith("block"):
				tab = call.data.split("-")[2]
				update_user(None, -1, call, "newadmin-"+tab)

			else:
				text = "Админпанель:"
				markup.add(InlineKeyboardButton("Админы", callback_data=f"admin-admins"))
				markup.add(InlineKeyboardButton("Работники", callback_data=f"admin-staffs"))
				markup.add(InlineKeyboardButton("Подписчики", callback_data=f"admin-subs"))
				markup.add(InlineKeyboardButton("Пользователи", callback_data=f"admin-users"))
				markup.add(InlineKeyboardButton("Заблокированные", callback_data=f"admin-blocks"))
				markup.add(InlineKeyboardButton("Назад", callback_data=f"mainmenu"))
	
			if not (call.data.endswith("toadmin") and call.data.endswith("tostaff") and call.data.endswith("tosub") and call.data.endswith("tounsub") and call.data.endswith("touser") and call.data.endswith("block")):
				try:
					if call.data.startswith("new"):
						bot.send_message(id, text, reply_markup=markup)

					else:
						bot.edit_message_text(chat_id=id, message_id=call.message.message_id, text=text, reply_markup=markup)
				except UnboundLocalError:
					pass

	elif call.data.startswith("menu") or call.data.startswith("newmenu"):
		print(call.data)
		if "cancel" in call.data:
			bot.clear_step_handler_by_chat_id(int(id))
			call.data = call.data[:-7]

		elif "accept" in call.data:
			if "fordelete" in call.data:
				if id in db.getUsers(1) or id in [db.getUseridByUsername(username) for username in owners]:
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
						call.data = f"newmenu-{courseid}-{topicid}-{taskid}"

		if len(call.data.split("-")) == 1:
			text = "Выберите курс:"
			for courseid, course in db.getCourses():
				markup.add(InlineKeyboardButton(course, callback_data=f"menu-{courseid}"))

			if id in db.getUsers(1) or id in [db.getUseridByUsername(username) for username in owners]:
				foradmin = [InlineKeyboardButton("Добавить курс", callback_data=f"menu-add"), ]
				if len(db.getCourses()):
					foradmin.append(InlineKeyboardButton("Изменить курс", callback_data=f"menu-edit"))
					foradmin.append(InlineKeyboardButton("Удалить курс", callback_data=f"menu-delete"))

				markup.add(*foradmin)

			markup.add(InlineKeyboardButton("Назад", callback_data=f"mainmenu"))

		elif len(call.data.split("-")) == 2:
			courseid = call.data.split("-")[1]
			if call.data.endswith('add') and (id in db.getUsers(1) or id in [db.getUseridByUsername(username) for username in owners]):
				text = "Пришлите название курса:"
				if id in db.getUsers(1) or id in [db.getUseridByUsername(username) for username in owners]:
					markup.add(InlineKeyboardButton("Отмена", callback_data=f"menu-cancel"))
					bot.register_next_step_handler_by_chat_id(int(id), add_course, "course", call, "newmenu")

			elif call.data.endswith('edit') and (id in db.getUsers(1) or id in [db.getUseridByUsername(username) for username in owners]):
				text = "Выберите курс:"
				for courseid, course in db.getCourses():
					markup.add(InlineKeyboardButton("✏ " + str(course), callback_data=f"menu-{courseid}-foredit"))

				markup.add(InlineKeyboardButton("Назад", callback_data=f"menu"))

			elif call.data.endswith('delete') and (id in db.getUsers(1) or id in [db.getUseridByUsername(username) for username in owners]):
				text = "Выберите курс:"
				for courseid, course in db.getCourses():
					markup.add(InlineKeyboardButton("🗑️ " + str(course), callback_data=f"menu-{courseid}-fordelete"))

				markup.add(InlineKeyboardButton("Назад", callback_data=f"menu"))

			else:
				text = "Выберите тему:"
				for topicid, topic in db.getTopics(courseid):
					markup.add(InlineKeyboardButton(topic, callback_data=f"menu-{courseid}-{topicid}"))

				if id in db.getUsers(1) or id in [db.getUseridByUsername(username) for username in owners]:
					foradmin = [InlineKeyboardButton("Добавить тему", callback_data=f"menu-{courseid}-add"), ]
					if len(db.getTopics(courseid)) != 0:
						foradmin.append(InlineKeyboardButton("Изменить тему", callback_data=f"menu-{courseid}-edit"))
						foradmin.append(InlineKeyboardButton("Удалить тему", callback_data=f"menu-{courseid}-delete"))

					markup.add(*foradmin)

				markup.add(InlineKeyboardButton("Назад", callback_data=f"menu"))

		elif len(call.data.split("-")) == 3:
			courseid = call.data.split("-")[1]
			topicid = call.data.split("-")[2]
			if call.data.endswith('add') and (id in db.getUsers(1) or id in [db.getUseridByUsername(username) for username in owners]):
				text = "Пришлите название темы:"
				if id in db.getUsers(1) or id in [db.getUseridByUsername(username) for username in owners]:
					markup.add(InlineKeyboardButton("Отмена", callback_data=f"menu-{courseid}-cancel"))
					bot.register_next_step_handler_by_chat_id(int(id), add_course, "topic", call, f"newmenu-{courseid}")

			elif call.data.endswith('foredit') and (id in db.getUsers(1) or id in [db.getUseridByUsername(username) for username in owners]):
				text = "Пришлите новое название курса:"
				markup.add(InlineKeyboardButton("Отмена", callback_data=f"menu-cancel"))
				bot.register_next_step_handler_by_chat_id(int(id), edit_course, "course", call, f"newmenu")

			elif call.data.endswith('edit') and (id in db.getUsers(1) or id in [db.getUseridByUsername(username) for username in owners]):
				text = "Выберите тему:"
				for topicid, topic in db.getTopics(courseid):
					markup.add(
						InlineKeyboardButton("✏ " + str(topic), callback_data=f"menu-{courseid}-{topicid}-foredit"))

				markup.add(InlineKeyboardButton("Назад", callback_data=f"menu-{courseid}"))

			elif call.data.endswith('fordelete') and (id in db.getUsers(1) or id in [db.getUseridByUsername(username) for username in owners]):
				text = "Вы уверены, что хотите удалить курс " + str(db.getCourse(courseid)) + "?"
				markup.add(InlineKeyboardButton("Да", callback_data=f"menu-{courseid}-fordelete-accept"))
				markup.add(InlineKeyboardButton("Отмена", callback_data=f"menu"))

			elif call.data.endswith('delete') and (id in db.getUsers(1) or id in [db.getUseridByUsername(username) for username in owners]):
				text = "Выберите тему"
				for topicid, topic in db.getTopics(courseid):
					markup.add(
						InlineKeyboardButton("🗑 " + str(topic), callback_data=f"menu-{courseid}-{topicid}-fordelete"))

				markup.add(InlineKeyboardButton("Назад", callback_data=f"menu-{courseid}"))

			else:
				text = "Выберите задание:"
				courseid = call.data.split("-")[1]
				topicid = call.data.split("-")[2]
				for taskid, task in db.getTasks(courseid, topicid):
					markup.add(InlineKeyboardButton(task, callback_data=f"menu-{courseid}-{topicid}-{taskid}"))

				if id in db.getUsers(1) or id in [db.getUseridByUsername(username) for username in owners]:
					foradmin = [InlineKeyboardButton("Добавить задание", callback_data=f"menu-{courseid}-{topicid}-add"), ]
					if len(db.getTasks(courseid, topicid)) != 0:
						foradmin.append(
							InlineKeyboardButton("Изменить задание", callback_data=f"menu-{courseid}-{topicid}-edit"))
						foradmin.append(
							InlineKeyboardButton("Удалить задание", callback_data=f"menu-{courseid}-{topicid}-delete"))

					markup.add(*foradmin)

				markup.add(InlineKeyboardButton("Назад", callback_data=f"menu-{courseid}"))


		elif len(call.data.split("-")) == 4:
			courseid = call.data.split("-")[1]
			topicid = call.data.split("-")[2]
			taskid = call.data.split("-")[3]
			if call.data.endswith('add') and (id in db.getUsers(1) or id in [db.getUseridByUsername(username) for username in owners]):
				text = "Пришлите название задания:"
				markup.add(InlineKeyboardButton("Отмена", callback_data=f"menu-{courseid}-{topicid}-cancel"))
				bot.register_next_step_handler_by_chat_id(int(id), add_course, "task", call, f"newmenu-{courseid}-{topicid}")

			elif call.data.endswith('foredit') and (id in db.getUsers(1) or id in [db.getUseridByUsername(username) for username in owners]):
				text = "Пришлите новое название темы:"
				markup.add(InlineKeyboardButton("Отмена", callback_data=f"menu-{courseid}-cancel"))
				bot.register_next_step_handler_by_chat_id(int(id), edit_course, "topic", call, f"newmenu-{courseid}")

			elif call.data.endswith('edit') and (id in db.getUsers(1) or id in [db.getUseridByUsername(username) for username in owners]):
				text = "Выберите задание:"
				for taskid, task in db.getTasks(courseid, topicid):
					markup.add(InlineKeyboardButton("✏ " + str(task),
													callback_data=f"menu-{courseid}-{topicid}-{taskid}-foredit"))

				markup.add(InlineKeyboardButton("Назад", callback_data=f"menu-{courseid}-{topicid}"))

			elif call.data.endswith('fordelete') and (id in db.getUsers(1) or id in [db.getUseridByUsername(username) for username in owners]):
				text = "Вы уверены, что хотите удалить тему " + str(db.getTopic(topicid)) + "?"
				markup.add(InlineKeyboardButton("Да", callback_data=f"menu-{courseid}-{topicid}-fordelete-accept"))
				markup.add(InlineKeyboardButton("Отмена", callback_data=f"menu-{courseid}-cancel"))

			elif call.data.endswith('delete') and (id in db.getUsers(1) or id in [db.getUseridByUsername(username) for username in owners]):
				text = "Выберите задание:"
				for taskid, task in db.getTasks(courseid, topicid):
					markup.add(InlineKeyboardButton("🗑 " + str(task),
													callback_data=f"menu-{courseid}-{topicid}-{taskid}-fordelete"))

				markup.add(InlineKeyboardButton("Назад", callback_data=f"menu-{courseid}-{topicid}"))
# Здесь нет решение, пошел быстро в объяснение!

			else:
				text = "Выберите объяснение или решение:"
				foradmin = []
				if db.getExplanation(courseid, topicid, taskid) is not None and db.getExplanation(courseid, topicid, taskid) != "":
					markup.add(InlineKeyboardButton("Объяснение", callback_data=f"menu-{courseid}-{topicid}-{taskid}-0"))

				else:
					if id in db.getUsers(1) or id in [db.getUseridByUsername(username) for username in owners]:
						foradmin.append(InlineKeyboardButton("Добавить объяснение", callback_data=f"menu-{courseid}-{topicid}-{taskid}-0-add"))

					# else:
					# 	markup.add(InlineKeyboardButton("Нет объяснения", callback_data=f"none"))

				if db.getSolution(courseid, topicid, taskid) is not None and db.getSolution(courseid, topicid, taskid) != "":
					markup.add(InlineKeyboardButton("Решение", callback_data=f"menu-{courseid}-{topicid}-{taskid}-1"))

				else:
					if id in db.getUsers(1) or id in [db.getUseridByUsername(username) for username in owners]:
						foradmin.append(InlineKeyboardButton("Добавить решение", callback_data=f"menu-{courseid}-{topicid}-{taskid}-1-add"))

					# else:
					# 	markup.add(InlineKeyboardButton("Нет решения", callback_data=f"none"))
				if id in db.getUsers(1) and [db.getUseridByUsername(username) for username in owners]:
					foradmin.append(
						InlineKeyboardButton("Изменить", callback_data=f"menu-{courseid}-{topicid}-{taskid}-edit"))
					foradmin.append(
						InlineKeyboardButton("Удалить", callback_data=f"menu-{courseid}-{topicid}-{taskid}-delete"))
					markup.add(*foradmin)
				markup.add(InlineKeyboardButton("Назад", callback_data=f"menu-{courseid}-{topicid}"))

		elif len(call.data.split("-")) == 5:
			courseid = call.data.split("-")[1]
			topicid = call.data.split("-")[2]
			taskid = call.data.split("-")[3]
			action = call.data.split("-")[4]
			if call.data.endswith('foredit'):
				text = "Пришлите новое название задание:"
				markup.add(InlineKeyboardButton("Отмена", callback_data=f"menu-{courseid}-{topicid}-cancel"))
				bot.register_next_step_handler_by_chat_id(int(id), edit_course, "task", call, f"newmenu-{courseid}-{topicid}")

			elif call.data.endswith('edit'):
				text = "Выберите:"
				if db.getExplanation(courseid, topicid, taskid) is not None and db.getExplanation(courseid, topicid,
																								  taskid) != "":
					markup.add(InlineKeyboardButton("✏ Объяснение",
													callback_data=f"menu-{courseid}-{topicid}-{taskid}-0-foredit"))
				if db.getSolution(courseid, topicid, taskid) is not None and db.getSolution(courseid, topicid,
																							taskid) != "":
					markup.add(InlineKeyboardButton("✏ Решение",
													callback_data=f"menu-{courseid}-{topicid}-{taskid}-1-foredit"))
				markup.add(InlineKeyboardButton("Назад", callback_data=f"menu-{courseid}-{topicid}-{taskid}"))

			elif call.data.endswith('fordelete'):
				text = "Вы уверены, что хотите удалить задание " + str(db.getTask(taskid)) + "?"
				markup.add(
					InlineKeyboardButton("Да", callback_data=f"menu-{courseid}-{topicid}-{taskid}-fordelete-accept"))
				markup.add(InlineKeyboardButton("Отмена", callback_data=f"menu-{courseid}-{topicid}-{taskid}-cancel"))

			elif call.data.endswith('delete'):
				text = "Выберите:"
				if db.getExplanation(courseid, topicid, taskid) is not None and db.getExplanation(courseid, topicid,
																								  taskid) != "":
					markup.add(InlineKeyboardButton("🗑 Объяснение",
													callback_data=f"menu-{courseid}-{topicid}-{taskid}-0-fordelete"))
				if db.getSolution(courseid, topicid, taskid) is not None and db.getSolution(courseid, topicid,
																							taskid) != "":
					markup.add(InlineKeyboardButton("🗑 Решение",
													callback_data=f"menu-{courseid}-{topicid}-{taskid}-1-fordelete"))
				markup.add(InlineKeyboardButton("Назад", callback_data=f"menu-{courseid}-{topicid}"))

			else:
				if action == "0":
					text = db.getExplanation(courseid, topicid, taskid) if db.getExplanation(courseid, topicid,
																							 taskid) is not None and db.getExplanation(
						courseid, topicid, taskid) != "" else "Нет"
					markup.add(InlineKeyboardButton("Назад", callback_data=f"menu-{courseid}-{topicid}-{taskid}"))
				else:
					if id in db.getSubs() or id in db.getUsers(1) or id in [db.getUseridByUsername(username) for username in owners]:
						text = db.getSolution(courseid, topicid, taskid) if db.getSolution(courseid, topicid,
																						   taskid) is not None and db.getSolution(
							courseid, topicid, taskid) != "" else "Нет"
						markup.add(InlineKeyboardButton("Назад", callback_data=f"menu-{courseid}-{topicid}-{taskid}"))

					elif id in db.getUsers(0):
						text = "Чтобы просмотреть решения вам нужна подписка, вы можете приобрести её по кнопке ниже."
						markup.add(InlineKeyboardButton("Купить подписку", callback_data="buy"))
						markup.add(InlineKeyboardButton("Назад", callback_data=f"menu-{courseid}-{topicid}-{taskid}"))


		elif len(call.data.split("-")) == 6:
			courseid = call.data.split("-")[1]
			topicid = call.data.split("-")[2]
			taskid = call.data.split("-")[3]
			action = call.data.split("-")[4]
			if call.data.endswith("add"):
				if action == "0":
					if id in db.getUsers(1) or id in [db.getUseridByUsername(username) for username in owners]:
						text = "Пришлите объяснение"
						markup.add(
							InlineKeyboardButton("Отмена", callback_data=f"menu-{courseid}-{topicid}-{taskid}-cancel"))
						bot.register_next_step_handler_by_chat_id(int(id), add_course, "explanation", call,
																  f"newmenu-{courseid}-{topicid}-{taskid}")

				else:
					if id in db.getUsers(1) or id in [db.getUseridByUsername(username) for username in owners]:
						text = "Пришлите решение"
						markup.add(
							InlineKeyboardButton("Отмена", callback_data=f"menu-{courseid}-{topicid}-{taskid}-cancel"))
						bot.register_next_step_handler_by_chat_id(int(id), add_course, "solution", call,
																  f"newmenu-{courseid}-{topicid}-{taskid}")

			elif call.data.endswith('foredit'):
				text = f"Пришлите новое {'объяснение' if action == '0' else 'решение'}"
				markup.add(InlineKeyboardButton("Отмена", callback_data=f"menu-{courseid}-{topicid}-{taskid}-cancel"))
				bot.register_next_step_handler_by_chat_id(int(id), edit_course, f"{'explanation' if action == '0' else 'solution'}", call,
														  f"newmenu-{courseid}-{topicid}-{taskid}-{action}")

			elif call.data.endswith('fordelete'):
				text = f"Вы уверены, что хотите удалить {'объяснение' if action == '0' else 'решение'} к заданию " + str(
					db.getTask(taskid)) + "?"
				markup.add(InlineKeyboardButton("Да",
												callback_data=f"menu-{courseid}-{topicid}-{taskid}-{action}-fordelete-accept"))
				markup.add(
					InlineKeyboardButton("Отмена", callback_data=f"menu-{courseid}-{topicid}-{taskid}-{action}-cancel"))
		if call.data.startswith("new"):
			bot.send_message(id, f"{text}", reply_markup=markup)
		else:
			bot.edit_message_text(chat_id=id, message_id=call.message.message_id, text=f"{text}", reply_markup=markup)

	elif call.data == "buy":
		id = str(call.message.json['chat']['id'])
		if id not in db.getSubs():
			markup = InlineKeyboardMarkup(row_width=1).add(
				InlineKeyboardButton("Оплатить", url="https://www.donationalerts.com/r/xpozitivez"),
				InlineKeyboardButton("Отменить оплату", callback_data="cancel"),
				InlineKeyboardButton("Проверить состояние", callback_data="check"))
			if db.getInfoByUserid(id)[0] not in checking_codes:
				message = bot.send_message(id,
								 f"Стоимость подписки {price} рублей.\nПри покупке оставьте только этот код в сообщении - {db.getInfoByUserid(id)[0]}",
								 reply_markup=markup)
			else:
				message = bot.send_message(id,
								 f"Стоимость подписки {price} рублей.\nПри покупке оставьте только этот код в сообщении - {db.getInfoByUserid(id)[0]}",
								 reply_markup=markup)
			checking_codes[db.getInfoByUserid(id)[0]] = message.message_id
			Thread(target=delayed_delete, args=(id, message.message_id, 86400)).start()
			
		else:
			bot.send_message(id, "Подписка уже приобретена")

	elif call.data == "check":
		print(log, checking_codes)
		if db.getInfoByUserid(id)[0] not in list(log.keys()):
			bot.send_message(call.message.json['chat']['id'], "Оплата ещё не пришла или вы указали неверный код")

	elif call.data == "cancel":
		bot.delete_message(chat_id=id, message_id=checking_codes.get(db.getInfoByUserid(id)[0], ""))
		checking_codes.pop(db.getInfoByUserid(id)[0], "")
		log.pop(db.getInfoByUserid(id)[0], "")
		call.data = "newmainmenu"
		bot.process_new_callback_query((call,))


Thread(target=keep_alive).start()
Thread(target=check).start()
while True:
	try:
		bot.infinity_polling(skip_pending=True)
	except Exception as e:
		print(e)
		continue
