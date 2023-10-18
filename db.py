import sqlite3


class Connection:
    def __init__(self):
        self.con = sqlite3.connect("db.db", check_same_thread=False)
        self.cur = self.con.cursor()

    def getUsers(self) -> list:
        clients = self.cur.execute("SELECT userid FROM users")
        return [y for x in clients.fetchall() for y in x]

    def getSubs(self):
        subs = self.cur.execute("SELECT userid FROM users WHERE sublevel > 0")
        return [y for x in subs.fetchall() for y in x]

    def getStaffs(self):
        staffs = self.cur.execute("SELECT userid FROM users WHERE is_staff = 1")
        return [y for x in staffs.fetchall() for y in x]

    def getAdmins(self):
        admins = self.cur.execute("SELECT userid FROM users WHERE is_admin = 1")
        return [y for x in admins.fetchall() for y in x]

    def getUsersBySublevel(self, sublevel) -> list:
        subs = self.cur.execute("SELECT userid FROM users WHERE sublevel = ?", (sublevel,))
        return [y for x in subs.fetchall() for y in x]

    def getInfoByUserid(self, userid):
        info = self.cur.execute("SELECT sublevel, date, is_admin, is_staff FROM users WHERE userid = ?", (userid,))
        return info.fetchall()[0]

    def getSubsByUserid(self, userid) -> list:
        subs = self.cur.execute("SELECT sublevel, date, is_admin, is_staff FROM users WHERE userid = ?", (userid,))
        return subs.fetchone()

    def getCourses(self):
        courses = self.cur.execute("SELECT id, course FROM courses ORDER BY id ASC")
        return courses.fetchall()

    def getTopics(self, courseid):
        topics = self.cur.execute("SELECT id, topic FROM topics WHERE courseid = ? ORDER BY id ASC", (int(courseid),))
        return topics.fetchall()

    def getTasks(self, courseid, topicid):
        tasks = self.cur.execute("SELECT id, task FROM tasks WHERE (courseid, topicid) = (?, ?) ORDER BY id ASC", (int(courseid), int(topicid)))
        return tasks.fetchall()

    def getExplanation(self, courseid, topicid, taskid):
        explanation = self.cur.execute("SELECT explanation FROM tasks_info WHERE (courseid, topicid, taskid) = (?, ?, ?)", (int(courseid), int(topicid), int(taskid)))
        return explanation.fetchone()

    def getSolution(self, courseid, topicid, taskid):
        solution = self.cur.execute("SELECT solution FROM tasks_info WHERE (courseid, topicid, taskid) = (?, ?, ?)", (int(courseid), int(topicid), int(taskid)))
        return solution.fetchone()

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

    def addUser(self, id, username, date) -> None:
        self.cur.execute("INSERT INTO users (userid, username, date) VALUES (?, ?, ?)", (id, username, date))
        self.con.commit()

    def updateUser(self, userid, username, sublevel, date, is_admin, is_staff) -> None:
        self.cur.execute(
            "UPDATE users SET (username, sublevel, date, is_admin, is_staff)=(?, ?, ?, ?, ?) WHERE userid = ?",
            (username, sublevel, date, is_admin, is_staff, userid))
        self.con.commit()
