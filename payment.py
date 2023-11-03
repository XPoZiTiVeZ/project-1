from dotenv import load_dotenv
from db import Connection
from datetime import datetime
import socketio
import json
import os


load_dotenv()
da_token = os.environ['da_token']
db = Connection()

sio = socketio.Client()
@sio.on('connect')
def on_connect():
	sio.emit('add-user', {"token": da_token, "type": "alert_widget"})

@sio.on('donation')
def on_message(data):
	donation = json.loads(data)
	db.addReceivedCodes(donation['message'], donation['amount'], datetime.today().strftime('%d-%m-%Y'))

sio.connect('wss://socket.donationalerts.ru:443', transports='websocket')