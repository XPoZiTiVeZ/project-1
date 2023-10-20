import sqlite3

connection = sqlite3.connect("db.db")
cur = connection.cursor()

class Connection:
    def __init__(self):
        self.con = sqlite3.connect("db.db", check_same_thread=False)
        self.cur = self.con.cursor()

    def getUsers(self, permlevel) -> list:
        clients = self.cur.execute("SELECT userid FROM users WHERE permlevel >= ?", (permlevel, ))
        return [y for x in clients.fetchall() for y in x]
    
    def getUsersByPermlevel(self, permlevel) -> list:
        clients = self.cur.execute("SELECT userid, username FROM users WHERE permlevel = ?", (permlevel, ))
        return clients.fetchall()

    def getSubs(self):
        subs = self.cur.execute("SELECT userid FROM users WHERE sublevel > 0")
        return [y for x in subs.fetchall() for y in x]

    def getUsersBySublevel(self, sublevel) -> list:
        subs = self.cur.execute("SELECT userid FROM users WHERE sublevel = ?", (sublevel,))
        return [y for x in subs.fetchall() for y in x]

    def getInfoByUserid(self, userid):
        info = self.cur.execute("SELECT username, sublevel, endofsubdate, permlevel FROM users WHERE userid = ?", (userid,)).fetchone()
        return info if info is not None else info

    def getUseridByUsername(self, username):
        userid = self.cur.execute("SELECT userid FROM users WHERE username = ?", (username,)).fetchone()
        return userid[0] if userid is not None else userid

    def getSubsByUserid(self, userid) -> list:
        subs = self.cur.execute("SELECT sublevel, endofsubdate, permlevel FROM users WHERE userid = ?", (userid,))
        return subs.fetchone()

    def getCourse(self, courseid):
        course = self.cur.execute("SELECT course FROM courses WHERE id = ?", (courseid, )).fetchone()
        return course[0] if course is not None else course

    def updateCourse(self, courseid, course):
        self.cur.execute("UPDATE courses SET course = ? WHERE id = ?", (course, courseid))
        self.con.commit()

    def deleteCourse(self, courseid):
        Connection().deleteAllTopics(courseid)
        self.cur.execute("DELETE FROM courses WHERE id = ?", (courseid,))
        self.con.commit()

    def getCourses(self):
        courses = self.cur.execute("SELECT id, course FROM courses ORDER BY id ASC")
        return courses.fetchall()

    def getTopic(self, topicid):
        topic = self.cur.execute("SELECT topic FROM topics WHERE id = ?", (topicid, )).fetchone()
        return topic if topic is not None else topic

    def updateTopic(self, courseid, topicid, topic):
        self.cur.execute("UPDATE topics SET topic = ? WHERE (id, courseid) = (?, ?)", (topic, topicid, courseid))
        self.con.commit()

    def deleteTopic(self, topicid):
        Connection().deleteAllTasks(topicid=topicid)
        self.cur.execute("DELETE FROM topics WHERE id = ?", (topicid,))
        self.con.commit()

    def deleteAllTopics(self, courseid):
        Connection().deleteAllTasks(courseid = courseid)
        self.cur.execute("DELETE FROM topics WHERE courseid = ?", (courseid,))
        self.con.commit()

    def getTopics(self, courseid):
        topics = self.cur.execute("SELECT id, topic FROM topics WHERE courseid = ? ORDER BY id ASC", (int(courseid),))
        return topics.fetchall()

    def getTask(self, taskid):
        task = self.cur.execute("SELECT task FROM tasks WHERE id = ?", (taskid, )).fetchone()
        return task[0] if task is not None else task

    def updateTask(self, courseid, topicid, taskid, task):
        self.cur.execute("UPDATE tasks SET task = ? WHERE (id, topicid, courseid) = (?, ?, ?)", (task, taskid, topicid, courseid))
        self.con.commit()

    def deleteTask(self, taskid):
        self.cur.execute("DELETE FROM tasks WHERE id = ?", (taskid,))
        self.con.commit()

    def deleteAllTasks(self, courseid=None, topicid=None):
        if courseid is not None and topicid is not None:
            pass

        elif courseid is not None:
            self.cur.execute("DELETE FROM tasks WHERE courseid = ?", (courseid,))
            self.con.commit()

        elif topicid is not None:
            self.cur.execute("DELETE FROM tasks WHERE topicid = ?", (topicid,))
            self.con.commit()

    def getTasks(self, courseid, topicid):
        tasks = self.cur.execute("SELECT id, task FROM tasks WHERE (courseid, topicid) = (?, ?) ORDER BY id ASC", (int(courseid), int(topicid)))
        return tasks.fetchall()

    def updateExplanation(self, courseid, topicid, taskid, explanation):
        self.cur.execute("UPDATE tasks_info SET (explanation) = (?) WHERE (taskid, topicid, courseid) = (?, ?, ?)", (explanation, taskid, topicid, courseid))
        self.con.commit()

    def getExplanation(self, courseid, topicid, taskid):
        explanation = self.cur.execute("SELECT explanation FROM tasks_info WHERE (courseid, topicid, taskid) = (?, ?, ?)", (int(courseid), int(topicid), int(taskid))).fetchone()
        return explanation[0] if explanation is not None else explanation

    def updateSolution(self, courseid, topicid, taskid, solution):
        self.cur.execute("UPDATE tasks_info SET (solution) = (?) WHERE (taskid, topicid, courseid) = (?, ?, ?)", (solution, taskid, topicid, courseid))
        self.con.commit()

    def getSolution(self, courseid, topicid, taskid):
        solution = self.cur.execute("SELECT solution FROM tasks_info WHERE (courseid, topicid, taskid) = (?, ?, ?)", (int(courseid), int(topicid), int(taskid))).fetchone()
        return solution[0] if solution is not None else solution

    def addCourse(self, course):
        self.cur.execute("INSERT INTO courses (course) VALUES (?)", (course, ))
        self.con.commit()

    def addTopic(self, courseid, topic):
        self.cur.execute("INSERT INTO topics (courseid, topic) VALUES (?, ?)", (courseid, topic))
        self.con.commit()

    def addTask(self, courseid, topicid, task):
        self.cur.execute("INSERT INTO tasks (courseid, topicid, task) VALUES (?, ?, ?)", (courseid, topicid, task))
        self.con.commit()

    def addExplanation(self, courseid, topicid, taskid, explanation):
        if Connection().getExplanation(courseid, topicid, taskid) is None:
            self.cur.execute("INSERT INTO tasks_info (courseid, topicid, taskid, explanation) VALUES (?, ?, ?, ?)", (courseid, topicid, taskid, explanation))
        else:
            self.cur.execute("UPDATE tasks_info SET explanation = ? WHERE (courseid, topicid, taskid) = (?, ?, ?)", (explanation, courseid, topicid, taskid))
        self.con.commit()

    def addSolution(self, courseid, topicid, taskid, solution):
        if Connection().getSolution(courseid, topicid, taskid) is None:
            self.cur.execute("INSERT INTO tasks_info (courseid, topicid, taskid, solution) VALUES (?, ?, ?, ?)", (courseid, topicid, taskid, solution))
        else:
            self.cur.execute("UPDATE tasks_info SET solution = ? WHERE (courseid, topicid, taskid) = (?, ?, ?)", (solution, courseid, topicid, taskid))
        self.con.commit()

    def addUser(self, id, username, endofsubdate) -> None:
        self.cur.execute("INSERT INTO users (userid, username, endofsubdate) VALUES (?, ?, ?)", (id, username, endofsubdate))
        self.con.commit()

    def updateUser(self, userid, username, sublevel, endofsubdate, permlevel) -> None:
        self.cur.execute(f"UPDATE users SET (username, sublevel, endofsubdate, permlevel)=(?, ?, ?, ?) WHERE userid = ?", (username, sublevel, endofsubdate, permlevel, userid))
        self.con.commit()
