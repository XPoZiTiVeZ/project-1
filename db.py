import sqlite3

class Connection:
	def __init__(self):
		self.con = sqlite3.connect("db.db", check_same_thread=False)
		self.cur = self.con.cursor()


	def getUsers(self, userid=None, username=None, sublevel=None, permlevel=None, bypermlevel=None, get='*') -> list|None:
		if userid is not None:
			result = self.cur.execute(f"SELECT {get} FROM Users WHERE UserId = ?", (userid,)).fetchone()
			if len(get.split(',')) == 1 and get.strip() != '*':
				result = result[0]
		elif username is not None:
			result = self.cur.execute(f"SELECT {get} FROM Users WHERE Username = ?", (username,)).fetchone()
			if len(get.split(',')) == 1 and get.strip() != '*':
				result = result[0]
		elif sublevel is not None:
			result = self.cur.execute(f"SELECT {get} FROM Users WHERE SubscribeLevel = ?", (sublevel,)).fetchall()
			if len(get.split(',')) == 1 and get.strip() != '*':
				result = [y for x in result for y in x]
		elif permlevel is not None:  
			result = self.cur.execute(f"SELECT {get} FROM Users WHERE PermissionLevel >= ?", (permlevel, )).fetchall()
			if len(get.split(',')) == 1 and get.strip() != '*':
				result = [y for x in result for y in x]
		elif bypermlevel is not None:
			result = self.cur.execute(f"SELECT {get} FROM Users WHERE PermissionLevel = ?", (bypermlevel, )).fetchall()
			if len(get.split(',')) == 1 and get.strip() != '*':
				result = [y for x in result for y in x]
		else:
			result = self.cur.execute(f"SELECT {get} FROM Users").fetchall()
			if len(get.split(',')) == 1 and get.strip() != '*':
				result = [y for x in result for y in x]
		return result

	def addUser(self, userid, username) -> None:
		self.cur.execute("INSERT INTO Users (UserId, Username) VALUES (?, ?)", (userid, username))
		self.con.commit()

	def updateUser(self, userid, **kwargs) -> None:
		self.cur.execute(f"UPDATE Users SET ({', '.join(kwargs.keys())}) = ({', '.join('?' * len(kwargs))}) WHERE userid = ?", list(kwargs.values()) + [userid])
		self.con.commit()



	def getCourses(self, courseid=None, get="*") -> list|None:
		if courseid is not None:
			result = self.cur.execute(f"SELECT {get} FROM Courses WHERE CourseId = ?", (courseid, )).fetchone()
			if len(get.split(',')) == 1 and get.strip() != '*':
				result = result[0]
		else:
			result = self.cur.execute(f"SELECT {get} FROM Courses ORDER BY CourseId ASC").fetchall()
			if len(get.split(',')) == 1 and get.strip() != '*':
				result = [y for x in result for y in x]
		return result

	def addCourse(self, course) -> None:
		self.cur.execute("INSERT INTO Courses (Course) VALUES (?)", (course, ))
		self.con.commit()
	
	def updateCourse(self, courseid, course) -> None:
		self.cur.execute("UPDATE Courses SET Course = ? WHERE CourseId = ?", (course, courseid))
		self.con.commit()

	def deleteCourses(self, courseid=None) -> None:
		if courseid is not None:
			self.cur.execute("DELETE FROM Courses WHERE CourseId = ?", (courseid,))
			self.con.commit()
		else:
			self.cur.execute("DELETE FROM Courses")
			self.con.commit()



	def getTopics(self, courseid=None, topicid=None, get="*") -> list|None:
		if courseid is not None:
			result = self.cur.execute(f"SELECT {get} FROM Topics WHERE CourseId = ? ORDER BY TopicId ASC", (courseid, )).fetchall()
			if len(get.split(',')) == 1 and get.strip() != '*':
				result = [y for x in result for y in x]
		elif topicid is not None:
			result = self.cur.execute(f"SELECT {get} FROM Topics WHERE TopicId = ?", (topicid, )).fetchone()
			if len(get.split(',')) == 1 and get.strip() != '*':
				result = result[0]
		else:
			result = self.cur.execute(f"SELECT {get} FROM Topics ORDER BY CourseId ASC").fetchall()
			if len(get.split(',')) == 1 and get.strip() != '*':
				result = [y for x in result for y in x]
		return result

	def addTopic(self, courseid, topic):
		self.cur.execute("INSERT INTO Topics (Courseid, Topic) VALUES (?, ?)", (courseid, topic))
		self.con.commit()

	def updateTopic(self, topicid, topic):
		self.cur.execute("UPDATE Topics SET Topic = ? WHERE TopicId = ?", (topic, topicid))
		self.con.commit()

	def deleteTopics(self, courseid=None, topicid=None):
		if courseid is not None:
			self.cur.execute("DELETE FROM Topics WHERE CourseId = ?", (courseid,))
			self.con.commit()
		if topicid is not None:
			self.cur.execute("DELETE FROM Topics WHERE TopicId = ?", (topicid,))
			self.con.commit()
		else:
			self.cur.execute("DELETE FROM Topics")
			self.con.commit()



	def getTasks(self, courseid=None, topicid=None, taskid=None, get='*'):
		if courseid is not None:
			result = self.cur.execute(f"SELECT {get} FROM Tasks WHERE CourseId = ? ORDER BY CourseId ASC", (courseid, )).fetchall()
			if len(get.split(',')) == 1 and get.strip() != '*':
				result = [y for x in result for y in x]
		elif topicid is not None:
			result = self.cur.execute(f"SELECT {get} FROM Tasks WHERE TopicId = ? ORDER BY CourseId ASC", (topicid, )).fetchall()
			if len(get.split(',')) == 1 and get.strip() != '*':
				result = [y for x in result for y in x]
		elif taskid is not None:
			result = self.cur.execute(f"SELECT {get} FROM Tasks WHERE TaskId = ? ORDER BY CourseId ASC", (taskid, )).fetchone()
			if len(get.split(',')) == 1 and get.strip() != '*':
				result = result[0]
		else:
			result = self.cur.execute(f"SELECT {get} FROM Tasks ORDER BY CourseId ASC", (topicid, )).fetchall()
			if len(get.split(',')) == 1 and get.strip() != '*':
				result = [y for x in result for y in x]
		
		return result

	def addTask(self, courseid, topicid, task):
		self.cur.execute("INSERT INTO Tasks (CourseId, TopicId, Task) VALUES (?, ?, ?)", (courseid, topicid, task))
		self.con.commit()

	def updateTask(self, taskid, task=None, description=None, explanation=None, solution=None):
		if task is not None:
			self.cur.execute("UPDATE Tasks SET Task = ? WHERE TaskId = ?", (task, taskid))
			self.con.commit()
		elif description is not None:
			self.cur.execute("UPDATE Tasks SET Description = ? WHERE TaskId = ?", (description, taskid))
			self.con.commit()
		elif explanation is not None:
			self.cur.execute("UPDATE Tasks SET Explanation = ? WHERE TaskId = ?", (explanation, taskid))
			self.con.commit()
		elif solution is not None:
			self.cur.execute("UPDATE Tasks SET Solution = ? WHERE TaskId = ?", (solution, taskid))
			self.con.commit()

	def deleteTasks(self, courseid=None, topicid=None, taskid=None):
		if courseid is not None:
			self.cur.execute("DELETE FROM Tasks WHERE CourseId = ?", (courseid,))
			self.con.commit()
		elif topicid is not None:
			self.cur.execute("DELETE FROM Tasks WHERE TopicId = ?", (topicid,))
			self.con.commit()
		elif taskid is not None:
			self.cur.execute("DELETE FROM Tasks WHERE Taskid = ?", (taskid,))
			self.con.commit()
		else:
			self.cur.execute("DELETE FROM Tasks")
			self.con.commit()



	def getPromocodes(self, promocodeid=None, promocode=None, get='*'):
		if promocodeid is not None:
			result = self.cur.execute(f"SELECT {get} FROM Promocodes WHERE PromocodeId = ?", (promocodeid,)).fetchone()
			if len(get.split(',')) == 1 and get.strip() != '*':
				result = result[0]
		elif promocode is not None:
			result = self.cur.execute(f"SELECT {get} FROM Promocodes WHERE Promocode = ?", (promocode,)).fetchone()
			if len(get.split(',')) == 1 and get.strip() != '*':
				result = result[0]
		else:
			result = self.cur.execute(f"SELECT {get} FROM Promocodes").fetchall()
			if len(get.split(',')) == 1 and get.strip() != '*':
				result = [y for x in result for y in x]
		return result

	def addPromocode(self, promocode, amount=200, limit=1):
		print(promocode, amount, limit)
		self.cur.execute("INSERT INTO Promocodes (Promocode, Amount, LimitUse) VALUES (?, ?, ?)", (promocode, amount, limit))
		self.con.commit()

	def updatePromocode(self, promocodeid=None, promocode=None, **kwargs):
		if promocode is not None:
			self.cur.execute(f"UPDATE Promocodes SET ({', '.join(kwargs.keys())}) = ({', '.join('?' * len(kwargs))}) WHERE Promocode = ?", list(kwargs.values()) + [promocode])
			self.con.commit()
		elif promocodeid is not None:
			self.cur.execute(f"UPDATE Promocodes SET ({', '.join(kwargs.keys())}) = ({', '.join('?' * len(kwargs))}) WHERE Promocodeid = ?", list(kwargs.values()) + [promocodeid])
			self.con.commit()

	def deletePromocode(self, promocode=None, promocodeid=None):
		if promocode is not None:
			self.cur.execute("DELETE FROM Promocodes WHERE Promocode = ?", (promocode,))
			self.con.commit()
		elif promocodeid is not None:
			self.cur.execute("DELETE FROM Promocodes WHERE PromocodeId = ?", (promocodeid,))
			self.con.commit()
		else:
			self.cur.execute("DELETE FROM Promocodes")
			self.con.commit()



	def getCodes(self, username=None, get='*'):
		if username is not None:
			result = self.cur.execute(f"SELECT {get} FROM PaymentCodes WHERE Username = ?", (username, )).fetchone()
			if len(get.split(',')) == 1 and get.strip() != '*':
				result = result[0]
		else:
			result = self.cur.execute(f"SELECT {get} FROM PaymentCodes").fetchall()
			if len(get.split(',')) == 1 and get.strip() != '*':
					result = [y for x in result for y in x]
		return result

	def addCode(self, username, messageid, promocode=None):
		if promocode is not None:
			amount = Connection().getPromocodes(promocode=promocode, get='Amount')
			self.cur.execute(f"INSERT INTO PaymentCodes (Username, Amount, Promocode, Message_id) VALUES (?, ?, ?, ?)", (username, amount, promocode, messageid))
		else:
			self.cur.execute(f"INSERT INTO PaymentCodes (Username, Message_id) VALUES (?, ?)", (username, messageid))
		self.con.commit()

	def updateCode(self, username, **kwargs):
		self.cur.execute(f"UPDATE PaymentCodes SET ({', '.join(kwargs.keys())}) = ({', '.join('?' * len(kwargs))}) WHERE username = ?", list(kwargs.values()) + [username])
		self.con.commit()

	def deleteCodes(self, username):
		self.cur.execute("DELETE FROM PaymentCodes WHERE username = ?", (username, ))
		self.cur.execute("DELETE FROM ReceivedCodes WHERE username = ?", (username, ))
		self.con.commit()



	def getReceivedCodes(self, username=None, get='*'):
		if username is not None:
			result = self.cur.execute(f"SELECT {get} FROM ReceivedCodes WHERE Username = ?", (username, )).fetchone()
			if len(get.split(',')) == 1 and get.strip() != '*':
				result = result[0]
		else:
			result = self.cur.execute(f"SELECT {get} FROM ReceivedCodes").fetchall()
			if len(get.split(',')) == 1 and get.strip() != '*':
					result = [y for x in result for y in x]
		return result

	def addReceivedCodes(self, username, amount, date):
		self.cur.execute('INSERT INTO ReceivedCodes (username, amount, date) VALUES (?, ?, ?)', (username, amount, date))
		self.con.commit()

if __name__ == "__main__":
	import pandas as pd
	import numpy as np
	subexpire = Connection().getUsers(userid='1349175494', get='SubscribeExpiration')
	print(subexpire)
	data = [Connection().getPromocodes(promocodeid=5, get='Amount')]
	print(pd.DataFrame(np.array(data)))