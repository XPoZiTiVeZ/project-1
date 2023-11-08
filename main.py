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
import payment

load_dotenv()
tg_token = os.environ['tg_token']
db = Connection()
owners = ['hayk9685', 'lukashevda']
banned = []
price = 200


bot = telebot.TeleBot(tg_token)
print('bot is online!')


def check():
	while True:
		try:
			donations = db.getReceivedCodes(get='Username, Amount')
			for username, amount in donations:
				userid, sublevel = db.getUsers(username=username, get='UserId, SubscribeLevel')
				if sublevel != 0 and username in db.getCodes(get='Username'):
					db.deleteCodes(username)
				elif username in db.getCodes(get='Username') and username in db.getReceivedCodes(get='Username') and amount >= db.getCodes(username=username, get='Amount'):
					promocode = db.getCodes(username=username, get='Promocode')
					if promocode != '':
						db.updatePromocode(promocode=promocode, LimitUse=db.getPromocodes(promocode=promocode, get='LimitUse')-1)
					bot.delete_message(userid, db.getCodes(username=username, get='Message_id'))
					markup = InlineKeyboardMarkup().add(InlineKeyboardButton("Назад", callback_data=f"newmainmenu"))
					bot.send_message(userid, "Пришёл код, ваша подписка оплачена.", reply_markup=markup)
					db.updateUser(userid=userid, SubscribeLevel=1, SubscribeExpiration=(datetime.now() + relativedelta(months=1)).strftime("%d.%m.%Y"))
					db.deleteCodes(username)
				elif amount < db.getCodes(username=username, get='Amount'):
					bot.delete_message(userid, db.getCodes(username=username, get='Message_id'))
					markup = InlineKeyboardMarkup().add(InlineKeyboardButton("Купить подписку", callback_data="buy")).add(InlineKeyboardButton("Назад", callback_data=f"newmainmenu"))
					bot.send_message(userid, "Пришёл код, но суммы платежа не хватило для оплаты подписки. Попробуйте ещё раз. Обязательно нажмите кнопку \"Купить подписку\"", reply_markup=markup)
					db.deleteCodes(username)
			for userid in db.getUsers(sublevel=1, get='UserId'):
				subexpire = db.getUsers(userid=userid, get='SubscribeExpiration')
				if datetime.strptime(subexpire, "%d.%m.%Y") < datetime.now():
					markup = InlineKeyboardMarkup().add(InlineKeyboardButton("Купить подписку", callback_data="buy")).add(InlineKeyboardButton("Назад", callback_data=f"newmainmenu"))
					db.updateUser(userid, SubscribeLevel=0)
					bot.send_message(userid, "У вас закончилась подписка, продлите её по кнопке ниже, чтобы продолжить пользоваться решениями.", reply_markup=markup)
			time.sleep(30)
		except Exception as e:
			pass


def gencode(length):
	letters = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789012345678901234567890123456789"
	code = ''.join(("-" if i % 4 == 0 and i != 0 else "") + choice(letters) for i in range(length))
	return code


def check_user(userid, username):
	if userid not in db.getUsers(get='UserId'):
		db.addUser(userid, username)
		print(f"Пользователь {username} добавлен в базу данных.")
	elif userid in db.getUsers() and username not in db.getUsers(userid=userid, get='Username'):
		db.updateUsers(userid=userid, username=username)
		print(f"Имя пользователя {username} обновлено.")


def add_course(message, addtype, call, callback):
	if addtype == 'course':
		db.addCourse(course=message.text)
	elif addtype == 'topic':
		courseid = call.data.split("-")[1]
		db.addTopic(courseid, message.text)
	elif addtype == 'task':
		courseid = call.data.split("-")[1]
		topicid = call.data.split("-")[2]
		db.addTask(courseid, topicid, message.text)
	elif addtype == 'description':
		taskid = call.data.split("-")[3]
		db.updateTask(taskid, description=message.text)
	elif addtype == 'explanation':
		taskid = call.data.split("-")[3]
		db.updateTask(taskid, explanation=message.text)
	elif addtype == 'solution':
		taskid = call.data.split("-")[3]
		db.updateTask(taskid, solution="`"+message.text+"`")
	elif addtype == "despage":
		if "|new|" not in message.text:
			taskid = call.data.split("-")[3]
			text = db.getTasks(taskid=taskid, get="Description").split("|new|") + [message.text]
			db.updateTask(taskid, description="|new|".join(text))
		else:
			markup = InlineKeyboardMarkup().add(InlineKeyboardButton('Назад', callback_data=call.data))
			bot.edit_message_text('Текст содержит строку |new|, которая запрещена для ввода', call.message.json['chat']['id'], call.message.message_id, reply_markup=markup)
			return
	elif addtype == "exppage":
		if "|new|" not in message.text:
			taskid = call.data.split("-")[3]
			text = db.getTasks(taskid=taskid, get="Explanation").split("|new|") + [message.text]
			db.updateTask(taskid, explanation="|new|".join(text))
		else:
			markup = InlineKeyboardMarkup().add(InlineKeyboardButton('Назад', callback_data=call.data))
			bot.edit_message_text('Текст содержит строку |new|, которая запрещена для ввода', call.message.json['chat']['id'], call.message.message_id, reply_markup=markup)
			return
	elif addtype == "solpage":
		if "|new|" not in message.text:
			taskid = call.data.split("-")[3]
			text = db.getTasks(taskid=taskid, get="Solution").split("|new|") + ["`"+message.text+"`"]
			db.updateTask(taskid, solution="|new|".join(text))
		else:
			markup = InlineKeyboardMarkup().add(InlineKeyboardButton('Назад', callback_data=call.data))
			bot.edit_message_text('Текст содержит строку |new|, которая запрещена для ввода', call.message.json['chat']['id'], call.message.message_id, reply_markup=markup)
			return

	call.data = callback
	bot.process_new_callback_query((call, ))


def edit_course(message, edittype, call, callback):
	if edittype == 'course':
		courseid = call.data.split("-")[1]
		db.updateCourse(courseid, message.text)
	elif edittype == 'topic':
		topicid = call.data.split("-")[2]
		db.updateTopic(topicid, message.text)
	elif edittype == 'task':
		taskid = call.data.split("-")[3]
		db.updateTask(taskid, message.text)
	elif edittype == 'description':
		taskid = call.data.split("-")[3]
		db.updateTask(taskid, description=message.text)
	elif edittype == 'explanation':
		taskid = call.data.split("-")[3]
		db.updateTask(taskid, explanation=message.text)
	elif edittype == 'solution':
		taskid = call.data.split("-")[3]
		db.updateTask(taskid, solution=message.text)
	elif edittype == "despage":
		if "|new|" not in message.text:
			taskid = call.data.split("-")[3]
			page = call.data.split("-")[5]
			text = db.getTasks(taskid=taskid, get="Description").split("|new|")
			text[int(page)] = message.text
			db.updateTask(taskid, description="|new|".join(text))
		else:
			markup = InlineKeyboardMarkup().add(InlineKeyboardButton('Назад', callback_data=call.data))
			bot.edit_message_text('Текст содержит строку |new|, которая запрещена для ввода', call.message.json['chat']['id'], call.message.message_id, reply_markup=markup)
			return
	elif edittype == "exppage":
		if "|new|" not in message.text:
			taskid = call.data.split("-")[3]
			page = call.data.split("-")[5]
			text = db.getTasks(taskid=taskid, get="Explanation").split("|new|")
			text[int(page)] = message.text
			db.updateTask(taskid, explanation="|new|".join(text))
		else:
			markup = InlineKeyboardMarkup().add(InlineKeyboardButton('Назад', callback_data=call.data))
			bot.edit_message_text('Текст содержит строку |new|, которая запрещена для ввода', call.message.json['chat']['id'], call.message.message_id, reply_markup=markup)
			return
	elif edittype == "solpage":
		if "|new|" not in message.text:
			taskid = call.data.split("-")[3]
			page = call.data.split("-")[5]
			text = db.getTasks(taskid=taskid, get="Solution").split("|new|")
			text[int(page)] = "`"+message.text+"`"
			db.updateTask(taskid, solution="|new|".join(text))
		else:
			markup = InlineKeyboardMarkup().add(InlineKeyboardButton('Назад', callback_data=call.data))
			bot.edit_message_text('Текст содержит строку |new|, которая запрещена для ввода', call.message.json['chat']['id'], call.message.message_id, reply_markup=markup)
			return
	

	call.data = callback
	bot.process_new_callback_query((call, ))

def delete_course(message, deletetype, call, callback):
	if message.text.lower() == "да":
		if deletetype == "despage":
			taskid = call.data.split("-")[3]
			page = call.data.split("-")[5]
			text = db.getTasks(taskid=taskid, get="Description").split("|new|")
			text.pop(int(page))
			db.updateTask(taskid, description="|new|".join(text))
		elif deletetype == "exppage":
			taskid = call.data.split("-")[3]
			page = call.data.split("-")[5]
			text = db.getTasks(taskid=taskid, get="Explanation").split("|new|")
			text.pop(int(page))
			db.updateTask(taskid, explanation="|new|".join(text))
		elif deletetype == "solpage":
			taskid = call.data.split("-")[3]
			page = call.data.split("-")[5]
			text = db.getTasks(taskid=taskid, get="Solution").split("|new|")
			text.pop(int(page))
			db.updateTask(taskid, solution="|new|".join(text))

	call.data = callback
	bot.process_new_callback_query((call, ))


def update_user(message, call, callback, chatid=False, **kwargs):
	if not chatid:
		db.updateUser(db.getUsers(username=message.text, get='UserId'), **kwargs)
	else:
		db.updateUser(message, **kwargs)

	call.data = callback
	bot.process_new_callback_query((call, ))


def update_promocode(message, call, callback, arg=False, **kwargs):
	if arg and kwargs:
		args = dict()
		args[arg] = message.text
		db.updatePromocode(promocodeid=call.data.split("-")[1], **args, **kwargs)
	elif arg:
		args = dict()
		args[arg] = message.text
		db.updatePromocode(promocodeid=call.data.split("-")[1], **args)
	elif kwargs:
		db.updatePromocode(promocodeid=call.data.split("-")[1], **kwargs)
	
	call.data = callback
	bot.process_new_callback_query((call, ))


def add_promocode(message, call, callback, promocode=None):
	amount, limit = message.text.split()
	db.addPromocode(promocode, amount=amount, limit=limit)
	
	call.data = callback
	bot.process_new_callback_query((call, ))


def delayed_delete(chat_id, message_id, timeout):
	time.sleep(timeout)
	try:
		bot.delete_message(chat_id, message_id)
	except telebot.apihelper.ApiTelegramException:
		pass
	db.deleteCodes(db.getUsers(userid=chat_id, get='Username'))


@bot.message_handler(commands=['start'])
def startMessage(message):
	userid = message.chat.id
	username = message.from_user.username
	check_user(userid, username)
	if userid in db.getUsers(permlevel=0, get='UserId') and username not in banned:
		markup_reply = ReplyKeyboardMarkup(row_width=1).add("Инфа", "Меню")
		markup_inline = InlineKeyboardMarkup().add(InlineKeyboardButton("Инфа", callback_data="info"),
												InlineKeyboardButton("Меню", callback_data="menu"))
		if userid in db.getUsers(permlevel=2, get='UserId') or username in owners:
			markup_reply.add("Админпанель")
			markup_inline.add(InlineKeyboardButton("Админпанель", callback_data="admin"))

		bot.send_message(userid, "Здравствуйте, вас приветствует бот помощник по программированию.",
						reply_markup=markup_reply)
		bot.send_message(userid,
						"Этот бот предоставляет более подробное и понятное объяснение тем по спецкурсу и программированию, а также предоставляет ответы к задачам.",
						reply_markup=markup_inline)


@bot.message_handler(commands=['info'])
def infoMessage(message):
	userid = message.chat.id
	username = message.from_user.username
	check_user(userid, username)
	if userid in db.getUsers(permlevel=0, get='UserId') and username not in banned:
		info = db.getUsers(userid=userid, get='PermissionLevel, SubscribeLevel, SubscribeExpiration')
		markup = InlineKeyboardMarkup()
		nl = '\n'
		if info[1] == 0:
			markup.add(InlineKeyboardButton("Купить подписку", callback_data="buy"))
			text = f"У вас нет подписки.{nl+'Вы являетесь работником' if info[0] >= 2 else ''}{nl+'Вы являетесь админом' if info[0] >= 1 else ''}{nl+'Вы являетесь владельцем' if username in owners else ''}"
		else:
			text = f"У вас подписка {info[1]} уровня до {info[2]}.{nl+'Вы являетесь работником' if info[0] >= 2 else ''}{nl+'Вы являетесь админом' if info[0] >= 1 else ''}{nl+'Вы являетесь владельцем' if username in owners else ''}"
		markup.add(InlineKeyboardButton("Назад", callback_data=f"mainmenu"))
		bot.send_message(userid, text, reply_markup=markup)


@bot.message_handler(content_types=['text'])
def textMessage(message):
	userid = message.chat.id
	username = message.from_user.username
	check_user(userid, username)
	if userid in db.getUsers(permlevel=0, get='UserId') and username not in banned or username in owners:
		markup = InlineKeyboardMarkup()
		if message.text == "Инфа":
			info = db.getUsers(userid=userid, get='PermissionLevel, SubscribeLevel, SubscribeExpiration')
			markup = InlineKeyboardMarkup()
			nl = '\n'
			if info[1] == 0:
				markup.add(InlineKeyboardButton("Купить подписку", callback_data="buy"))
				text = f"У вас нет подписки.{nl+'Вы являетесь работником' if info[0] >= 2 else ''}{nl+'Вы являетесь админом' if info[0] >= 1 else ''}{nl+'Вы являетесь владельцем' if username in owners else ''}"
			else:
				text = f"У вас подписка {info[1]} уровня до {info[2]}.{nl+'Вы являетесь работником' if info[0] >= 2 else ''}{nl+'Вы являетесь админом' if info[0] >= 1 else ''}{nl+'Вы являетесь владельцем' if username in owners else ''}"
			markup.add(InlineKeyboardButton("Назад", callback_data=f"mainmenu"))
			bot.send_message(userid, text, reply_markup=markup)

		elif message.text == "Меню":
			for courseid, course in db.getCourses():
				markup.add(InlineKeyboardButton(course, callback_data=f"menu-{courseid}"))

			if userid in db.getUsers(permlevel=1, get='UserId') or username in owners:
				foradmin = [InlineKeyboardButton("Добавить курс", callback_data=f"menu-add"), ]
				if len(db.getCourses()):
					foradmin.append(InlineKeyboardButton("Изменить курс", callback_data=f"menu-edit"))
					foradmin.append(InlineKeyboardButton("Удалить курс", callback_data=f"menu-delete"))
				markup.add(*foradmin)
			
			markup.add(InlineKeyboardButton("Назад", callback_data=f"mainmenu"))
			bot.send_message(userid, "Выберите курс:", reply_markup=markup)

		elif message.text == "Админпанель" and (userid in db.getUsers(permlevel=2, get='UserId') or username in owners):
			text = "Админпанель:"
			markup.add(InlineKeyboardButton("Админы", callback_data=f"admin-admins"))
			markup.add(InlineKeyboardButton("Работники", callback_data=f"admin-staffs"))
			markup.add(InlineKeyboardButton("Подписчики", callback_data=f"admin-subs"))
			markup.add(InlineKeyboardButton("Пользователи", callback_data=f"admin-users"))
			markup.add(InlineKeyboardButton("Заблокированные", callback_data=f"admin-blocks"))
			markup.add(InlineKeyboardButton("Промокоды", callback_data=f"admin-promocodes"))
			markup.add(InlineKeyboardButton("Назад", callback_data=f"mainmenu"))
			bot.send_message(userid, text, reply_markup=markup, protect_content=True)
		
		elif len(message.text) == 19:
			if db.getCodes(username=message.from_user.username) is not None and db.getPromocodes(promocode=message.text, get='Promocode') is not None and db.getPromocodes(promocode=message.text, get='LimitUse') != 0:
				amount, promocode = db.getPromocodes(promocode=message.text, get='Amount, Promocode')
				messageid = db.getCodes(username, get='Message_id')
				markup = InlineKeyboardMarkup(row_width=1).add(
					InlineKeyboardButton("Оплатить", url="https://www.donationalerts.com/r/xpozitivez"),
					InlineKeyboardButton("Отменить оплату", callback_data="buy-cancel"),
					InlineKeyboardButton("Проверить состояние", callback_data="check"))
				try:
					bot.delete_message(userid, messageid)
				except:
					pass
				newmessage = bot.send_message(userid, f"3Стоимость подписки {amount} рублей {'по промокоду '+promocode if promocode is not None else ''}.\nПри покупке оставьте только этот код в сообщении - {username}", reply_markup=markup)
				db.updateCode(username=message.from_user.username, amount=amount, promocode=message.text, message_id=newmessage.message_id)

@bot.callback_query_handler(lambda call: True)
def callback(call):
	print(call.data)
	userid = call.message.json['chat']['id']
	username = call.from_user.username
	check_user(userid, username)
	try:
		if userid in db.getUsers(permlevel=0, get='UserId') and username not in banned or username in owners:
			markup = InlineKeyboardMarkup()
			if call.data == "mainmenu" or call.data == "newmainmenu":
				markup.add(InlineKeyboardButton("Инфа", callback_data="info"), InlineKeyboardButton("Меню", callback_data="menu"))
				if userid in db.getUsers(permlevel=2, get='UserId') or username in owners:
					markup.add(InlineKeyboardButton("Админпанель", callback_data="admin"))
				if call.data.startswith("new"):
					bot.send_message(userid, "Этот бот предоставляет более подробное и понятное объяснение тем по спецкурсу и программированию, а также предоставляет ответы к задачам.", reply_markup=markup)
				else:
					bot.edit_message_text("Этот бот предоставляет более подробное и понятное объяснение тем по спецкурсу и программированию, а также предоставляет ответы к задачам.", userid, call.message.message_id, reply_markup=markup)

			elif call.data == "info" or  call.data == "newinfo":
				info = db.getUsers(userid=userid, get='PermissionLevel, SubscribeLevel, SubscribeExpiration')
				markup = InlineKeyboardMarkup()
				nl = '\n'
				if info[1] == 0:
					markup.add(InlineKeyboardButton("Купить подписку", callback_data="buy"))
					text = f"У вас нет подписки.{nl+'Вы являетесь работником' if info[0] >= 2 else ''}{nl+'Вы являетесь админом' if info[0] >= 1 else ''}{nl+'Вы являетесь владельцем' if username in owners else ''}"
				else:
					text = f"У вас подписка {info[1]} уровня до {info[2]}.{nl+'Вы являетесь работником' if info[0] >= 2 else ''}{nl+'Вы являетесь админом' if info[0] >= 1 else ''}{nl+'Вы являетесь владельцем' if username in owners else ''}"
				markup.add(InlineKeyboardButton("Назад", callback_data=f"mainmenu"))
				if call.data.startswith("new"):
					bot.send_message(userid, text, reply_markup=markup)
				else:
					bot.edit_message_text(text, userid, call.message.message_id, reply_markup=markup)

			elif call.data.startswith("admin") or call.data.startswith("newadmin"):
				if userid in db.getUsers(permlevel=2, get='UserId') or username in owners:
					if "cancel" in call.data:
						bot.clear_step_handler_by_chat_id(userid)
						call.data = call.data[:-7]

					if call.data.endswith("admins"):
						if call.data.endswith("addadmins"):
							text = "Главное меню -> Админпанель -> Админы -> Добавить админа\nВведите имя пользователя:"
							markup.add(InlineKeyboardButton("Отмена", callback_data=f"admin-admins-cancel"))
							bot.register_next_step_handler_by_chat_id(userid, update_user, call, "newadmin-admins", PermissionLevel=2)
						elif len(call.data.split("-")) == 3:
							userid = call.data.split("-")[1]
							text = f"Главное меню -> Админпанель -> Админы -> {db.getUsers(userid=userid, get='Username')}:"
							markup.add(InlineKeyboardButton("Понизить", callback_data=f"admin-{userid}-admins-tostaff"))
							markup.add(InlineKeyboardButton("Сбросить", callback_data=f"admin-{userid}-admins-touser"))
							if int(userid) in db.getUsers(sublevel=1, get='UserId'):
								markup.add(InlineKeyboardButton("Отменить подписку", callback_data=f"admin-{userid}-admins-tounsub"))
							else:
								markup.add(InlineKeyboardButton("Добавить подписку", callback_data=f"admin-{userid}-admins-tosub"))
							markup.add(InlineKeyboardButton("Заблокировать", callback_data=f"admin-{userid}-admins-block"))
							markup.add(InlineKeyboardButton("Назад", callback_data=f"admin-admins"))
						else:
							text = "Главное меню -> Админпанель -> Админы:"
							for userid, username in db.getUsers(bypermlevel=2, get='UserId, Username'):
								markup.add(InlineKeyboardButton(username, callback_data=f"admin-{userid}-admins"))
							markup.add(InlineKeyboardButton("Добавить", callback_data=f"admin-addadmins"))
							markup.add(InlineKeyboardButton("Назад", callback_data=f"admin"))

					elif call.data.endswith("staffs"):
						if call.data.endswith("addstaffs"):
							text = "Главное меню -> Админпанель -> Работники -> Добавить работника\nВведите имя пользователя:"
							markup.add(InlineKeyboardButton("Отмена", callback_data=f"newadmin-staffs-cancel"))
							bot.register_next_step_handler_by_chat_id(userid, update_user, call, "newadmin-staffs", PermissionLevel=1)
						elif len(call.data.split("-")) == 3:
							userid = call.data.split("-")[1]
							text = f"Главное меню -> Админпанель -> Работники -> {db.getUsers(userid=userid, get='Username')}:"
							markup.add(InlineKeyboardButton("Повысить", callback_data=f"admin-{userid}-staffs-toadmin"))
							markup.add(InlineKeyboardButton("Понизить", callback_data=f"admin-{userid}-staffs-touser"))
							if int(userid) in db.getUsers(sublevel=1, get='UserId'):
								markup.add(InlineKeyboardButton("Отменить подписку", callback_data=f"admin-{userid}-staffs-tounsub"))
							else:
								markup.add(InlineKeyboardButton("Добавить подписку", callback_data=f"admin-{userid}-staffs-tosub"))
							markup.add(InlineKeyboardButton("Заблокировать", callback_data=f"admin-{userid}-staffs-block"))
							markup.add(InlineKeyboardButton("Назад", callback_data=f"admin-staffs"))
						else:
							text = "Главное меню -> Админпанель -> Работники:"
							for userid, username in db.getUsers(bypermlevel=1, get='UseriD, Username'):
								markup.add(InlineKeyboardButton(username, callback_data=f"admin-{userid}-staffs"))
							markup.add(InlineKeyboardButton("Добавить", callback_data=f"admin-addstaffs"))
							markup.add(InlineKeyboardButton("Назад", callback_data=f"admin"))

					elif call.data.endswith("subs"):
						if call.data.endswith("addsubs"):
							text = "Главное меню -> Админпанель -> Подписчики -> Добавить подписчика\nВведите имя пользователя:"
							markup.add(InlineKeyboardButton("Отмена", callback_data=f"newadmin-subs-cancel"))
							bot.register_next_step_handler_by_chat_id(userid, update_user, call, "newadmin-subs", SubscribeLevel=1)
						elif len(call.data.split("-")) == 3:
							userid = call.data.split("-")[1]
							text = f"Главное меню -> Админпанель -> Подписчики -> {db.getUsers(userid=userid, get='Username')}:"
							markup.add(InlineKeyboardButton("Сделать админом", callback_data=f"admin-{userid}-subs-toadmin"))
							markup.add(InlineKeyboardButton("Сделать работником", callback_data=f"admin-{userid}-subs-tostaff"))
							markup.add(InlineKeyboardButton("Отменить подписку", callback_data=f"admin-{userid}-subs-tounsub"))
							markup.add(InlineKeyboardButton("Заблокировать", callback_data=f"admin-{userid}-subs-block"))
							markup.add(InlineKeyboardButton("Назад", callback_data=f"admin-subs"))
						else:
							text = "Главное меню -> Админпанель -> Подписчики:"
							users = db.getUsers(sublevel=1, get='UserId, Username')
							for userid, username in users:
								markup.add(InlineKeyboardButton(username, callback_data=f"admin-{userid}-subs"))
							markup.add(InlineKeyboardButton("Добавить", callback_data=f"admin-addsubs"))
							markup.add(InlineKeyboardButton("Назад", callback_data=f"admin"))

					elif call.data.endswith("users"):
						if call.data.endswith("addusers"):
							text = "Главное меню -> Админпанель -> Пользователи -> Добавить пользователя\nВведите имя пользователя:"
							markup.add(InlineKeyboardButton("Отмена", callback_data=f"newadmin-users-cancel"))
							bot.register_next_step_handler_by_chat_id(userid, update_user, call, "newadmin-users", permlevel=0, sublevel=0)
						elif len(call.data.split("-")) == 3:
							userid = call.data.split("-")[1]
							text = f"Главное меню -> Админпанель -> Пользователи -> {db.getUsers(userid=userid, get='Username')}:"
							markup.add(InlineKeyboardButton("Сделать админом", callback_data=f"admin-{userid}-users-toadmin"))
							markup.add(InlineKeyboardButton("Сделать работником", callback_data=f"admin-{userid}-users-tostaffб"))
							markup.add(InlineKeyboardButton("Добавить подписку", callback_data=f"admin-{userid}-users-tosub"))
							markup.add(InlineKeyboardButton("Заблокировать", callback_data=f"admin-{userid}-users-block"))
							markup.add(InlineKeyboardButton("Назад", callback_data=f"admin-users"))
						else:
							text = "Главное меню -> Админпанель -> Пользователи:"
							users = db.getUsers(bypermlevel=0, get='UserId, Username')
							subs = db.getUsers(sublevel=0, get='UserId, Username')
							for i, user in enumerate(users):
								if user[0] in subs:
									users.pop(i)
							for userid, username in users:
								markup.add(InlineKeyboardButton(username, callback_data=f"admin-{userid}-users"))
							markup.add(InlineKeyboardButton("Добавить", callback_data=f"admin-addusers"))
							markup.add(InlineKeyboardButton("Назад", callback_data=f"admin"))

					elif call.data.endswith("blocks"):
						if call.data.endswith("addblocks"):
							text = "Главное меню -> Админпанель -> Заблокированные -> Добавить заблокированного\nВведите имя пользователя:"
							markup.add(InlineKeyboardButton("Отмена", callback_data=f"newadmin-blocks-cancel"))
							bot.register_next_step_handler_by_chat_id(userid, update_user, call, "newadmin-blocks", PermissionLevel=-1)
						elif len(call.data.split("-")) == 3:
							userid = call.data.split("-")[1]
							text = f"Главное меню -> Админпанель -> Заблокированные -> {db.getUsers(userid=userid, get='Username')}:"
							markup.add(InlineKeyboardButton("Сделать админом", callback_data=f"admin-{userid}-blocks-toadmin"))
							markup.add(InlineKeyboardButton("Сделать работником", callback_data=f"admin-{userid}-blocks-tostaff"))
							markup.add(InlineKeyboardButton("Разблокировать", callback_data=f"admin-{userid}-blocks-touser"))
							markup.add(InlineKeyboardButton("Назад", callback_data=f"admin-blocks"))
						else:
							text = "Главное меню -> Админпанель -> Заблокированные:"
							for userid, username in db.getUsers(bypermlevel=-1, get='UserId, Username'):
								markup.add(InlineKeyboardButton(username, callback_data=f"admin-{userid}-blocks"))
							markup.add(InlineKeyboardButton("Добавить", callback_data=f"admin-addblocks"))
							markup.add(InlineKeyboardButton("Назад", callback_data=f"admin"))

					elif call.data.endswith("toadmin"):
						tab = call.data.split("-")[2]
						update_user(call.data.split("-")[1], call, "admin-"+tab, chatid=True, PermissionLevel=2)

					elif call.data.endswith("tostaff"):
						tab = call.data.split("-")[2]
						update_user(call.data.split("-")[1], call, "admin-"+tab, chatid=True, PermissionLevel=1)

					elif call.data.endswith("tosub"):
						tab = call.data.split("-")[2]
						update_user(call.data.split("-")[1], call, "admin-"+tab, chatid=True, SubscribeLevel=1)

					elif call.data.endswith("tounsub"):
						tab = call.data.split("-")[2]
						update_user(call.data.split("-")[1], call, "admin-"+tab, chatid=True, SubscribeLevel=0)

					elif call.data.endswith("touser"):
						tab = call.data.split("-")[2]
						update_user(call.data.split("-")[1], call, "admin-"+tab, chatid=True, PermissionLevel=0, SubscribeLevel=0)

					elif call.data.endswith("block"):
						tab = call.data.split("-")[2]
						update_user(call.data.split("-")[1], call, "admin-"+tab, chatid=True, PermissionLevel=-1, SubscribeLevel=0)

					elif call.data.endswith("promocodes"):
						if len(call.data.split("-")) == 3:
							if call.data.endswith("editamountpromocodes"):
								text = "Введите сумму для промокода:"
								markup.add(InlineKeyboardButton("Отмена", callback_data=f"admin-promocodes-cancel"))
								bot.register_next_step_handler_by_chat_id(userid, update_promocode, call, "newadmin-promocodes", arg="Amount")
							elif call.data.endswith("editqusepromocodes"):
								text = "Введите количество использований для промокода:"
								markup.add(InlineKeyboardButton("Отмена", callback_data=f"admin-promocodes-cancel"))
								bot.register_next_step_handler_by_chat_id(userid, update_promocode, call, "newadmin-promocodes", arg="LimitUse")
							elif call.data.endswith("deletepromocodes"):
								text = "Успешно удалено"
								markup.add(InlineKeyboardButton("Назад", callback_data=f"admin-promocodes"))
								db.deletePromocode(promocodeid=call.data.split("-")[1])
								call.data = "admin-promocodes"
								bot.process_new_callback_query((call, ))
							else:
								text = "Главное меню -> Админпанель -> Промокоды -> " + db.getPromocodes(promocodeid=call.data.split('-')[1], get='Promocode')
								markup.add(InlineKeyboardButton("Изменить сумму", callback_data=f"admin-{call.data.split('-')[1]}-editamountpromocodes"))
								markup.add(InlineKeyboardButton("Изменить кол-во использований", callback_data=f"admin-{call.data.split('-')[1]}-editqusepromocodes"))
								markup.add(InlineKeyboardButton("Удалить", callback_data=f"admin-{call.data.split('-')[1]}-deletepromocodes"))
								markup.add(InlineKeyboardButton("Назад", callback_data=f"admin-promocodes"))
						elif call.data.endswith("addpromocodes"):
							text = "Введите сумму и кол-во использований для промокода через пробел:"
							markup.add(InlineKeyboardButton("Отмена", callback_data=f"admin-promocodes-cancel"))
							bot.register_next_step_handler_by_chat_id(userid, add_promocode, call, "newadmin-promocodes", promocode = gencode(16))
						else:
							text = "Главное меню -> Админпанель -> Промокоды"
							for promocodeid, promocode, amount, limit in db.getPromocodes():
								markup.add(InlineKeyboardButton(f"{promocode} - {amount} - {limit}", callback_data=f"admin-{promocodeid}-promocodes"))
							markup.add(InlineKeyboardButton("Добавить", callback_data=f"admin-addpromocodes"))
							markup.add(InlineKeyboardButton("Назад", callback_data=f"admin"))

					else:
						text = "Главное меню -> Админпанель:"
						markup.add(InlineKeyboardButton("Админы", callback_data=f"admin-admins"))
						markup.add(InlineKeyboardButton("Работники", callback_data=f"admin-staffs"))
						markup.add(InlineKeyboardButton("Подписчики", callback_data=f"admin-subs"))
						markup.add(InlineKeyboardButton("Пользователи", callback_data=f"admin-users"))
						markup.add(InlineKeyboardButton("Заблокированные", callback_data=f"admin-blocks"))
						markup.add(InlineKeyboardButton("Промокоды", callback_data=f"admin-promocodes"))
						markup.add(InlineKeyboardButton("Назад", callback_data=f"mainmenu"))
			
					if not (call.data.endswith("toadmin") and call.data.endswith("tostaff") and call.data.endswith("tosub") and call.data.endswith("tounsub") and call.data.endswith("touser") and call.data.endswith("block")):
						userid = call.message.json['chat']['id']
						try:
							if call.data.startswith("new"):
								bot.send_message(userid, text, reply_markup=markup)
							else:
								bot.edit_message_text(text, userid, call.message.message_id, reply_markup=markup)
						except UnboundLocalError:
								pass

			elif call.data.startswith("menu") or call.data.startswith("newmenu"):
				staff = username in db.getUsers(permlevel=1, get='username') or username in owners
				if "cancel" in call.data:
					bot.clear_step_handler_by_chat_id(userid)
					call.data = call.data[:-7]
				elif "accept" in call.data and staff:
					if "fordelete" in call.data:
						if staff:
							if len(call.data.split("-")) == 4:
								courseid = call.data.split("-")[1]
								db.deleteCourses(courseid=courseid)
								bot.send_message(userid, "Успешно удалено")
								call.data = "menu"
							elif len(call.data.split("-")) == 5:
								courseid = call.data.split("-")[1]
								topicid = call.data.split("-")[2]
								db.deleteTopics(topicid)
								bot.send_message(userid, "Успешно удалено")
								call.data = f"menu-{courseid}"
							elif len(call.data.split("-")) == 6:
								courseid = call.data.split("-")[1]
								topicid = call.data.split("-")[2]
								taskid = call.data.split("-")[3]
								db.deleteTasks(taskid)
								bot.send_message(userid, "Успешно удалено")
								call.data = f"menu-{courseid}-{topicid}"
							elif len(call.data.split("-")) == 7:
								courseid = call.data.split("-")[1]
								topicid = call.data.split("-")[2]
								taskid = call.data.split("-")[3]
								action = call.data.split("-")[4]
								if action == "des":
									db.updateTask(taskid, description="")
								elif action == "exp":
									db.updateTask(taskid, explanaton="")
								elif action == "sol":
									db.updateTask(taskid, solution="")
								bot.send_message(userid, "Успешно удалено")
								call.data = f"newmenu-{courseid}-{topicid}-{taskid}"
				if len(call.data.split("-")) == 1:
					text = "Выберите курс:"
					for courseid, course in db.getCourses(get='courseid, course'):
						markup.add(InlineKeyboardButton(course, callback_data=f"menu-{courseid}"))
					if staff:
						foradmin = [InlineKeyboardButton("Добавить курс", callback_data=f"menu-add"), ]
						if len(db.getCourses()):
							foradmin.append(InlineKeyboardButton("Изменить курс", callback_data=f"menu-edit"))
							foradmin.append(InlineKeyboardButton("Удалить курс", callback_data=f"menu-delete"))
						markup.add(*foradmin)
					markup.add(InlineKeyboardButton("Назад", callback_data=f"mainmenu"))
				elif len(call.data.split("-")) == 2:
					courseid = call.data.split("-")[1]
					if call.data.endswith('add') and staff:
						text = "Пришлите название курса:"
						markup.add(InlineKeyboardButton("Отмена", callback_data=f"menu-cancel"))
						bot.register_next_step_handler_by_chat_id(userid, add_course, "course", call, "newmenu")
					elif call.data.endswith('edit') and staff:
						text = "Выберите курс:"
						for courseid, course in db.getCourses(get='courseid, course'):
							markup.add(InlineKeyboardButton("✏ "+course, callback_data=f"menu-{courseid}-foredit"))
						markup.add(InlineKeyboardButton("Назад", callback_data=f"menu"))
					elif call.data.endswith('delete') and staff:
						text = "Выберите курс:"
						for courseid, course in db.getCourses(get='courseid, course'):
							markup.add(InlineKeyboardButton("🗑️ "+course, callback_data=f"menu-{courseid}-fordelete"))
						markup.add(InlineKeyboardButton("Назад", callback_data=f"menu"))
					else:
						text = "Выберите тему:"
						for topicid, topic in db.getTopics(courseid=courseid, get='topicid, topic'):
							markup.add(InlineKeyboardButton(topic, callback_data=f"menu-{courseid}-{topicid}"))
						if staff:
							foradmin = [InlineKeyboardButton("Добавить тему", callback_data=f"menu-{courseid}-add"), ]
							if len(db.getTopics(courseid=courseid)) != 0:
								foradmin.append(InlineKeyboardButton("Изменить тему", callback_data=f"menu-{courseid}-edit"))
								foradmin.append(InlineKeyboardButton("Удалить тему", callback_data=f"menu-{courseid}-delete"))
							markup.add(*foradmin)
						markup.add(InlineKeyboardButton("Назад", callback_data=f"menu"))
				elif len(call.data.split("-")) == 3:
					courseid = call.data.split("-")[1]
					topicid = call.data.split("-")[2]
					if call.data.endswith('add') and staff:
						text = "Пришлите название темы:"
						markup.add(InlineKeyboardButton("Отмена", callback_data=f"menu-{courseid}-cancel"))
						bot.register_next_step_handler_by_chat_id(userid, add_course, "topic", call, f"newmenu-{courseid}")
					elif call.data.endswith('foredit') and staff:
						text = "Пришлите новое название курса:"
						markup.add(InlineKeyboardButton("Отмена", callback_data=f"menu-cancel"))
						bot.register_next_step_handler_by_chat_id(userid, edit_course, "course", call, f"newmenu")
					elif call.data.endswith('edit') and staff:
						text = "Выберите тему:"
						for topicid, topic in db.getTopics(courseid=courseid, get='topicid, topic'):
							markup.add(InlineKeyboardButton("✏ " +topic, callback_data=f"menu-{courseid}-{topicid}-foredit"))
						markup.add(InlineKeyboardButton("Назад", callback_data=f"menu-{courseid}"))
					elif call.data.endswith('fordelete') and staff:
						text = "Вы уверены, что хотите удалить курс "+db.getCourses(courseid=courseid, get='course')+"?"
						markup.add(InlineKeyboardButton("Да", callback_data=f"menu-{courseid}-fordelete-accept"))
						markup.add(InlineKeyboardButton("Отмена", callback_data=f"menu"))
					elif call.data.endswith('delete') and staff:
						text = "Выберите тему"
						for topicid, topic in db.getTopics(courseid=courseid, get='topicid, topic'):
							markup.add(InlineKeyboardButton("🗑 "+topic, callback_data=f"menu-{courseid}-{topicid}-fordelete"))
						markup.add(InlineKeyboardButton("Назад", callback_data=f"menu-{courseid}"))
					else:
						text = "Выберите задание:"
						courseid = call.data.split("-")[1]
						topicid = call.data.split("-")[2]
						for taskid, task in db.getTasks(topicid=topicid, get='taskid, task'):
							markup.add(InlineKeyboardButton(task, callback_data=f"menu-{courseid}-{topicid}-{taskid}"))
						if staff:
							foradmin = [InlineKeyboardButton("Добавить задание", callback_data=f"menu-{courseid}-{topicid}-add")]
							if len(db.getTasks(topicid=topicid)) != 0:
								foradmin.append(InlineKeyboardButton("Изменить задание", callback_data=f"menu-{courseid}-{topicid}-edit"))
								foradmin.append(InlineKeyboardButton("Удалить задание", callback_data=f"menu-{courseid}-{topicid}-delete"))
							markup.add(*foradmin)
						markup.add(InlineKeyboardButton("Назад", callback_data=f"menu-{courseid}"))
				elif len(call.data.split("-")) == 4:
					courseid = call.data.split("-")[1]
					topicid = call.data.split("-")[2]
					taskid = call.data.split("-")[3]
					if call.data.endswith('add') and staff:
						text = "Пришлите название задания:"
						markup.add(InlineKeyboardButton("Отмена", callback_data=f"menu-{courseid}-{topicid}-cancel"))
						bot.register_next_step_handler_by_chat_id(userid, add_course, "task", call, f"newmenu-{courseid}-{topicid}")
					elif call.data.endswith('foredit') and staff:
						text = "Пришлите новое название темы:"
						markup.add(InlineKeyboardButton("Отмена", callback_data=f"menu-{courseid}-cancel"))
						bot.register_next_step_handler_by_chat_id(userid, edit_course, "topic", call, f"newmenu-{courseid}")
					elif call.data.endswith('edit') and staff:
						text = "Выберите задание:"
						for taskid, task in db.getTasks(topicid=topicid, get='taskid, task'):
							markup.add(InlineKeyboardButton("✏ "+task, callback_data=f"menu-{courseid}-{topicid}-{taskid}-foredit"))
						markup.add(InlineKeyboardButton("Назад", callback_data=f"menu-{courseid}-{topicid}"))
					elif call.data.endswith('fordelete') and staff:
						text = "Вы уверены, что хотите удалить тему "+db.getTopics(topicid=topicid, get='topic') + "?"
						markup.add(InlineKeyboardButton("Да", callback_data=f"menu-{courseid}-{topicid}-fordelete-accept"))
						markup.add(InlineKeyboardButton("Отмена", callback_data=f"menu-{courseid}-cancel"))
					elif call.data.endswith('delete') and staff:
						text = "Выберите задание:"
						for taskid, task in db.getTasks(topicid=topicid, get='taskid, task'):
							markup.add(InlineKeyboardButton("🗑 "+task, callback_data=f"menu-{courseid}-{topicid}-{taskid}-fordelete"))
						markup.add(InlineKeyboardButton("Назад", callback_data=f"menu-{courseid}-{topicid}"))
					else:
						text = "Выберите условие/объяснение/решение:"
						foradmin = []
						foradmin1 = []
						if db.getTasks(taskid=taskid, get='Description') is not None and db.getTasks(taskid=taskid, get='Description') != "":
							markup.add(InlineKeyboardButton("Условие", callback_data=f"menu-{courseid}-{topicid}-{taskid}-des-0"))
						else:
							if staff:
								foradmin.append(InlineKeyboardButton("Добавить условие", callback_data=f"menu-{courseid}-{topicid}-{taskid}-des-add"))
						if db.getTasks(taskid=taskid, get='Explanation') is not None and db.getTasks(taskid=taskid, get='Explanation') != "":
							markup.add(InlineKeyboardButton("Объяснение", callback_data=f"menu-{courseid}-{topicid}-{taskid}-exp-0"))
						else:
							if staff:
								foradmin.append(InlineKeyboardButton("Добавить объяснение", callback_data=f"menu-{courseid}-{topicid}-{taskid}-exp-add"))
						if db.getTasks(taskid=taskid, get='Solution') is not None and db.getTasks(taskid=taskid, get='Solution') != "":
							markup.add(InlineKeyboardButton("Решение", callback_data=f"menu-{courseid}-{topicid}-{taskid}-sol-0"))
						else:
							if staff:
								foradmin.append(InlineKeyboardButton("Добавить решение", callback_data=f"menu-{courseid}-{topicid}-{taskid}-sol-add"))
						if staff:
							if db.getTasks(taskid=taskid, get='Description') is not None and db.getTasks(taskid=taskid, get='Description') != "" or db.getTasks(taskid=taskid, get='Explanation') is not None and db.getTasks(taskid=taskid, get='Explanation') != "" or db.getTasks(taskid=taskid, get='Solution') is not None and db.getTasks(taskid=taskid, get='Solution') != "":
								foradmin1.append(InlineKeyboardButton("Изменить", callback_data=f"menu-{courseid}-{topicid}-{taskid}-edit"))
								foradmin1.append(InlineKeyboardButton("Удалить", callback_data=f"menu-{courseid}-{topicid}-{taskid}-delete"))
							markup.add(*foradmin)
							markup.add(*foradmin1)
						markup.add(InlineKeyboardButton("Назад", callback_data=f"menu-{courseid}-{topicid}"))
				elif len(call.data.split("-")) == 5:
					courseid = call.data.split("-")[1]
					topicid = call.data.split("-")[2]
					taskid = call.data.split("-")[3]
					action = call.data.split("-")[4]
					if call.data.endswith('foredit') and staff:
						text = "Пришлите новое название задание:"
						markup.add(InlineKeyboardButton("Отмена", callback_data=f"menu-{courseid}-{topicid}-cancel"))
						bot.register_next_step_handler_by_chat_id(userid, edit_course, "task", call, f"newmenu-{courseid}-{topicid}")
					elif call.data.endswith('edit') and staff:
						text = "Выберите:"
						if db.getTasks(taskid=taskid, get='Description') is not None and db.getTasks(taskid=taskid, get='Description') != "":
							markup.add(InlineKeyboardButton("✏ Условие", callback_data=f"menu-{courseid}-{topicid}-{taskid}-des-foredit"))
						if db.getTasks(taskid=taskid, get='Explanation') is not None and db.getTasks(taskid=taskid, get='Explanation') != "":
							markup.add(InlineKeyboardButton("✏ Объяснение", callback_data=f"menu-{courseid}-{topicid}-{taskid}-exp-foredit"))
						if db.getTasks(taskid=taskid, get='Solution') is not None and db.getTasks(taskid=taskid, get='Solution') != "":
							markup.add(InlineKeyboardButton("✏ Решение", callback_data=f"menu-{courseid}-{topicid}-{taskid}-sol-foredit"))
						markup.add(InlineKeyboardButton("Назад", callback_data=f"menu-{courseid}-{topicid}-{taskid}"))
					elif call.data.endswith('fordelete') and staff:
						text = "Вы уверены, что хотите удалить задание " + str(db.getTasks(taskid=taskid, get='task')) + "?"
						markup.add(
							InlineKeyboardButton("Да", callback_data=f"menu-{courseid}-{topicid}-{taskid}-fordelete-accept"))
						markup.add(InlineKeyboardButton("Отмена", callback_data=f"menu-{courseid}-{topicid}-{taskid}-cancel"))
					elif call.data.endswith('delete') and staff:
						text = "Выберите:"
						if db.getTasks(taskid=taskid, get='Description') is not None and db.getTasks(taskid=taskid, get='Description') != "":
							markup.add(InlineKeyboardButton("🗑 Условие", callback_data=f"menu-{courseid}-{topicid}-{taskid}-des-fordelete"))
						if db.getTasks(taskid=taskid, get='Explanation') is not None and db.getTasks(taskid=taskid, get='Explanation') != "":
							markup.add(InlineKeyboardButton("🗑 Объяснение", callback_data=f"menu-{courseid}-{topicid}-{taskid}-exp-fordelete"))
						if db.getTasks(taskid=taskid, get='Solution') is not None and db.getTasks(taskid=taskid, get='Solution') != "":
							markup.add(InlineKeyboardButton("🗑 Решение", callback_data=f"menu-{courseid}-{topicid}-{taskid}-sol-fordelete"))
						markup.add(InlineKeyboardButton("Назад", callback_data=f"menu-{courseid}-{topicid}"))
					else:
						if action == "des":
							text = db.getTasks(taskid=taskid, get='Description') if db.getTasks(taskid=taskid, get='Description') is not None and db.getTasks(taskid=taskid, get='Description') != "" else "Нет"
							markup.add(InlineKeyboardButton("Назад", callback_data=f"menu-{courseid}-{topicid}-{taskid}"))
						elif action == "exp":
							text = db.getTasks(taskid=taskid, get='Explanation') if db.getTasks(taskid=taskid, get='Explanation') is not None and db.getTasks(taskid=taskid, get='Explanation') != "" else "Нет"
							markup.add(InlineKeyboardButton("Назад", callback_data=f"menu-{courseid}-{topicid}-{taskid}"))
						elif action == "sol":
							if username in db.getUsers(sublevel=1, get='username') or staff:
								text = db.getTasks(taskid=taskid, get='Solution') if db.getTasks(taskid=taskid, get='Solution') is not None and db.getTasks(taskid=taskid, get='Solution') != "" else "Нет"
								markup.add(InlineKeyboardButton("Назад", callback_data=f"menu-{courseid}-{topicid}-{taskid}"))
							elif username in db.getUsers(sublevel=0) and username not in banned:
								text = "Чтобы просмотреть решения вам нужна подписка, вы можете приобрести её по кнопке ниже."
								markup.add(InlineKeyboardButton("Купить подписку", callback_data="buy"))
								markup.add(InlineKeyboardButton("Назад", callback_data=f"menu-{courseid}-{topicid}-{taskid}"))
				elif len(call.data.split("-")) == 6:
					courseid = call.data.split("-")[1]
					topicid = call.data.split("-")[2]
					taskid = call.data.split("-")[3]
					action = call.data.split("-")[4]
					page = call.data.split("-")[5]
					if call.data.endswith("add"):
						if action == "des":
							if staff:
								text = "Пришлите условие"
								markup.add(InlineKeyboardButton("Отмена", callback_data=f"menu-{courseid}-{topicid}-{taskid}-cancel"))
								bot.register_next_step_handler_by_chat_id(userid, add_course, "description", call, f"newmenu-{courseid}-{topicid}-{taskid}-des-0")
						if action == "exp":
							if staff:
								text = "Пришлите объяснение"
								markup.add(InlineKeyboardButton("Отмена", callback_data=f"menu-{courseid}-{topicid}-{taskid}-cancel"))
								bot.register_next_step_handler_by_chat_id(userid, add_course, "explanation", call, f"newmenu-{courseid}-{topicid}-{taskid}-exp-0")
						elif action == "sol":
							if staff:
								text = "Пришлите решение"
								markup.add(InlineKeyboardButton("Отмена", callback_data=f"menu-{courseid}-{topicid}-{taskid}-cancel"))
								bot.register_next_step_handler_by_chat_id(userid, add_course, "solution", call, f"newmenu-{courseid}-{topicid}-{taskid}-sol-0")
					elif call.data.endswith('foredit') and staff:
						text = f"Пришлите новое {'условие' if action == 'des' else 'объяснение' if action == 'exp' else 'решение'}"
						markup.add(InlineKeyboardButton("Отмена", callback_data=f"menu-{courseid}-{topicid}-{taskid}-cancel"))
						bot.register_next_step_handler_by_chat_id(userid, edit_course, f"{'desctiption' if action == 'des' else 'explanation' if action == 'exp' else 'solution'}", call, f"newmenu-{courseid}-{topicid}-{taskid}-{action}-0")
					elif call.data.endswith('fordelete') and staff:
						text = f"Вы уверены, что хотите удалить {'условие' if action == 'des' else 'объяснение' if action == 'exp' else 'решение'} к заданию " + str(db.getTasks(taskid=taskid, get='task')) + "?"
						markup.add(InlineKeyboardButton("Да", callback_data=f"menu-{courseid}-{topicid}-{taskid}-{action}-fordelete-accept"))
						markup.add(InlineKeyboardButton("Отмена", callback_data=f"menu-{courseid}-{topicid}-{taskid}-{action}-cancel"))
					else:
						if action == "des":
							text = db.getTasks(taskid=taskid, get='Description').split("|new|")[int(page)] if db.getTasks(taskid=taskid, get='Description') is not None and db.getTasks(taskid=taskid, get='Description') != "" else "Нет"
							if staff:
								markup.add(InlineKeyboardButton("Добавить страницу", callback_data=f"menu-{courseid}-{topicid}-{taskid}-{action}-{page}-add"), InlineKeyboardButton("Изменить страницу", callback_data=f"menu-{courseid}-{topicid}-{taskid}-{action}-{page}-edit"), InlineKeyboardButton("Удалить страницу", callback_data=f"menu-{courseid}-{topicid}-{taskid}-{action}-{page}-delete"))
							markup.add(InlineKeyboardButton("<", callback_data=f"menu-{courseid}-{topicid}-{taskid}-{action}-{page}-prev"), InlineKeyboardButton(">", callback_data=f"menu-{courseid}-{topicid}-{taskid}-{action}-{page}-next"))
						elif action == "exp":
							text = db.getTasks(taskid=taskid, get='Explanation').split("|new|")[int(page)] if db.getTasks(taskid=taskid, get='Explanation') is not None and db.getTasks(taskid=taskid, get='Explanation') != "" else "Нет"
							if staff:
								markup.add(InlineKeyboardButton("Добавить страницу", callback_data=f"menu-{courseid}-{topicid}-{taskid}-{action}-{page}-add"), InlineKeyboardButton("Изменить страницу", callback_data=f"menu-{courseid}-{topicid}-{taskid}-{action}-{page}-edit"), InlineKeyboardButton("Удалить страницу", callback_data=f"menu-{courseid}-{topicid}-{taskid}-{action}-{page}-delete"))
							markup.add(InlineKeyboardButton("<", callback_data=f"menu-{courseid}-{topicid}-{taskid}-{action}-{page}-prev"), InlineKeyboardButton(">", callback_data=f"menu-{courseid}-{topicid}-{taskid}-{action}-{page}-next"))
						elif action == "sol":
							if username in db.getUsers(sublevel=1, get='username') or staff:
								text = db.getTasks(taskid=taskid, get='Solution').split("|new|")[int(page)] if db.getTasks(taskid=taskid, get='Solution') is not None and db.getTasks(taskid=taskid, get='Solution') != "" else "Нет"
								if staff:
									markup.add(InlineKeyboardButton("Добавить страницу", callback_data=f"menu-{courseid}-{topicid}-{taskid}-{action}-{page}-add"), InlineKeyboardButton("Изменить страницу", callback_data=f"menu-{courseid}-{topicid}-{taskid}-{action}-{page}-edit"), InlineKeyboardButton("Удалить страницу", callback_data=f"menu-{courseid}-{topicid}-{taskid}-{action}-{page}-delete"))
									markup.add(InlineKeyboardButton("<", callback_data=f"menu-{courseid}-{topicid}-{taskid}-{action}-{page}-prev"), InlineKeyboardButton(">", callback_data=f"menu-{courseid}-{topicid}-{taskid}-{action}-{page}-next"))
							elif username in db.getUsers(sublevel=0, get='username') and username not in banned:
								text = "Чтобы просмотреть решения вам нужна подписка, вы можете приобрести её по кнопке ниже."
								markup.add(InlineKeyboardButton("Купить подписку", callback_data="buy"))
						markup.add(InlineKeyboardButton("Назад", callback_data=f"menu-{courseid}-{topicid}-{taskid}"))
				elif len(call.data.split("-")) == 7:
					courseid = call.data.split("-")[1]
					topicid = call.data.split("-")[2]
					taskid = call.data.split("-")[3]
					action = call.data.split("-")[4]
					page = call.data.split("-")[5]
					if call.data.endswith("add"):
						if action == "des":
							if staff:
								text = "Пришлите страницу условия"
								markup.add(InlineKeyboardButton("Отмена", callback_data=f"menu-{courseid}-{topicid}-{taskid}-{action}-{page}-cancel"))
								bot.register_next_step_handler_by_chat_id(userid, add_course, "despage", call, f"newmenu-{courseid}-{topicid}-{taskid}-{action}-{int(page)+1}")
						elif action == "exp":
							if staff:
								text = "Пришлите страницу объяснения"
								markup.add(InlineKeyboardButton("Отмена", callback_data=f"menu-{courseid}-{topicid}-{taskid}-{action}-{page}-cancel"))
								bot.register_next_step_handler_by_chat_id(userid, add_course, "exppage", call, f"newmenu-{courseid}-{topicid}-{taskid}-{action}-{int(page)+1}")
						elif action == "sol":
							if staff:
								text = "Пришлите страницу решения"
								markup.add(InlineKeyboardButton("Отмена", callback_data=f"menu-{courseid}-{topicid}-{taskid}-{action}-{page}-cancel"))
								bot.register_next_step_handler_by_chat_id(userid, add_course, "solpage", call, f"newmenu-{courseid}-{topicid}-{taskid}-{action}-{int(page)+1}")
					elif call.data.endswith("edit"):
						if action == "des":
							if staff:
								text = "Пришлите новую страницу условия"
								markup.add(InlineKeyboardButton("Отмена", callback_data=f"menu-{courseid}-{topicid}-{taskid}-{action}-{page}-cancel"))
								bot.register_next_step_handler_by_chat_id(userid, edit_course, "despage", call, f"newmenu-{courseid}-{topicid}-{taskid}-{action}-{page}")
						elif action == "exp":
							if staff:
								text = "Пришлите новую страницу объяснения"
								markup.add(InlineKeyboardButton("Отмена", callback_data=f"menu-{courseid}-{topicid}-{taskid}-{action}-{page}-cancel"))
								bot.register_next_step_handler_by_chat_id(userid, edit_course, "exppage", call, f"newmenu-{courseid}-{topicid}-{taskid}-{action}-{page}")
						elif action == "sol":
							if staff:
								text = "Пришлите новую страницу решения"
								markup.add(InlineKeyboardButton("Отмена", callback_data=f"menu-{courseid}-{topicid}-{taskid}-{action}-{page}-cancel"))
								bot.register_next_step_handler_by_chat_id(userid, edit_course, "solpage", call, f"newmenu-{courseid}-{topicid}-{taskid}-{action}-{page}")
					elif call.data.endswith("delete"):
						if action == "des":
							length = len(db.getTasks(taskid=taskid, get='Description').split("|new|")) if db.getTasks(taskid=taskid, get='Description') is not None and db.getTasks(taskid=taskid, get='Description') else 0
						elif action == "exp":
							length = len(db.getTasks(taskid=taskid, get='Explanation').split("|new|")) if db.getTasks(taskid=taskid, get='Explanation') is not None and db.getTasks(taskid=taskid, get='Explanation') else 0
						elif action == "sol":
							length = len(db.getTasks(taskid=taskid, get='Solution').split("|new|")) if db.getTasks(taskid=taskid, get='Solution') is not None and db.getTasks(taskid=taskid, get='Solution') else 0
						if action == "des":
							if staff:
								text = "Пришлите \"Да\" если хотите удалить страницу"
								markup.add(InlineKeyboardButton("Отмена", callback_data=f"menu-{courseid}-{topicid}-{taskid}-{action}-{page}-cancel"))
								bot.register_next_step_handler_by_chat_id(userid, delete_course, "despage", call, f"newmenu-{courseid}-{topicid}-{taskid}{'-'+action+'-0' if length != 0 else ''}")
						elif action == "exp":
							if staff:
								text = "Пришлите \"Да\" если хотите удалить страницу"
								markup.add(InlineKeyboardButton("Отмена", callback_data=f"menu-{courseid}-{topicid}-{taskid}-{action}-{page}-cancel"))
								bot.register_next_step_handler_by_chat_id(userid, delete_course, "exppage", call, f"newmenu-{courseid}-{topicid}-{taskid}{'-'+action+'-0' if length != 0 else ''}")
						elif action == "sol":
							if staff:
								text = "Пришлите \"Да\" если хотите удалить страницу"
								markup.add(InlineKeyboardButton("Отмена", callback_data=f"menu-{courseid}-{topicid}-{taskid}-{action}-{page}-cancel"))
								bot.register_next_step_handler_by_chat_id(userid, delete_course, "solpage", call, f"newmenu-{courseid}-{topicid}-{taskid}{'-'+action+'-0' if length != 0 else ''}")
					elif call.data.endswith("prev"):
						page = int(page)
						if action == "des":
							length = len(db.getTasks(taskid=taskid, get='Description').split("|new|")) if db.getTasks(taskid=taskid, get='Description') is not None and db.getTasks(taskid=taskid, get='Description') else 0
						elif action == "exp":
							length = len(db.getTasks(taskid=taskid, get='Explanation').split("|new|")) if db.getTasks(taskid=taskid, get='Explanation') is not None and db.getTasks(taskid=taskid, get='Explanation') else 0
						elif action == "sol":
							length = len(db.getTasks(taskid=taskid, get='Solution').split("|new|")) if db.getTasks(taskid=taskid, get='Solution') is not None and db.getTasks(taskid=taskid, get='Solution') else 0
						if length != 0:
							if page == 0:
								pass
							elif page > 0:
								call.data = f"menu-{courseid}-{topicid}-{taskid}-{action}-{int(page)-1}"
								bot.process_new_callback_query((call, ))
						else:
							call.data = f"menu-{courseid}-{topicid}-{taskid}"
							bot.process_new_callback_query((call, ))
						return
					elif call.data.endswith("next"):
						page = int(page)
						if action == "des":
							length = len(db.getTasks(taskid=taskid, get='Description').split("|new|")) if db.getTasks(taskid=taskid, get='Description') is not None and db.getTasks(taskid=taskid, get='Description') else 0
						elif action == "exp":
							length = len(db.getTasks(taskid=taskid, get='Explanation').split("|new|")) if db.getTasks(taskid=taskid, get='Explanation') is not None and db.getTasks(taskid=taskid, get='Explanation') else 0
						elif action == "sol":
							length = len(db.getTasks(taskid=taskid, get='Solution').split("|new|")) if db.getTasks(taskid=taskid, get='Solution') is not None and db.getTasks(taskid=taskid, get='Solution') else 0
						if length != 0:
							if page == length-1:
								pass
							elif page < length-1:
								call.data = f"menu-{courseid}-{topicid}-{taskid}-{action}-{int(page)+1}"
								bot.process_new_callback_query((call, ))
						else:
							call.data = f"menu-{courseid}-{topicid}-{taskid}"
							bot.process_new_callback_query((call, ))
						return
		
				if call.data.startswith("new"):
					bot.send_message(userid, text, parse_mode='Markdown', reply_markup=markup)
				else:
					bot.edit_message_text(text, userid, call.message.message_id, parse_mode='Markdown', reply_markup=markup)
		
			elif call.data == "buy":
				userid = call.message.json['chat']['id']
				if userid not in db.getUsers(sublevel=0):
					markup = InlineKeyboardMarkup(row_width=1).add(
						InlineKeyboardButton("Оплатить", url="https://www.donationalerts.com/r/xpozitivez"),
						InlineKeyboardButton("Отменить оплату", callback_data="buy-cancel"),
						InlineKeyboardButton("Проверить состояние", callback_data="check"))
					if username not in db.getCodes(get='Username'):
						message = bot.send_message(userid, f"1Стоимость подписки {price} рублей.\nПри покупке оставьте только этот код в сообщении - {username}", reply_markup=markup)
						db.addCode(username, message.message_id)
					else:
						amount = db.getCodes(username, get='Amount')
						promocode = db.getCodes(username, get='Promocode') if db.getCodes(username, get='Promocode') != '' else None
						messageid = db.getCodes(username, get='Message_id')
						bot.delete_message(userid, messageid)
						message = bot.send_message(userid, f"2Стоимость подписки {amount} рублей {'по подписке '+promocode if promocode is not None else ''}.\nПри покупке оставьте только этот код в сообщении - {username}", reply_markup=markup)
						db.updateCode(username=username, Message_id=message.message_id)
					Thread(target=delayed_delete, args=(userid, message.message_id, 21600)).start()
					
				else:
					bot.send_message(userid, "Подписка уже приобретена")
			elif call.data == "check":
				if username not in db.getReceivedCodes(get='Username'):
					bot.send_message(userid, "Оплата ещё не пришла или вы указали неверный код")
			elif call.data == "buy-cancel":
				try:
					bot.delete_message(userid, db.getCodes(username, get='Message_id'))
				except Exception as e:
					print(e)
				db.deleteCodes(username)
				call.data = "newmainmenu"
				bot.process_new_callback_query((call,))
	except Exception as e:
		print(e)



keep_alive()
Thread(target=check).start()
while True:
	try:
		bot.infinity_polling(skip_pending=True)
	except Exception as e:
		print(e)
		continue