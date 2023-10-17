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
        courses = self.cur.execute("SELECT DISTINCT courseid, course FROM menu ORDER BY courseid ASC")
        return courses.fetchall()

    def getTopics(self, courseid):
        topics = self.cur.execute("SELECT DISTINCT topicid, topic FROM menu WHERE courseid = ? ORDER BY topicid ASC", (int(courseid),))
        return topics.fetchall()

    def getTasks(self, courseid, topicid):
        tasks = self.cur.execute("SELECT DISTINCT taskid, task FROM menu WHERE (courseid, topicid) = (?, ?) ORDER BY taskid ASC", (int(courseid), int(topicid)))
        return tasks.fetchall()

    def getExplanation(self, courseid, topicid, taskid):
        explanation = self.cur.execute("SELECT explanation FROM menu WHERE (courseid, topicid, taskid) = (?, ?, ?)", (int(courseid), int(topicid), int(taskid)))
        return explanation.fetchone()

    def getSolution(self, courseid, topicid, taskid):
        solution = self.cur.execute("SELECT solution FROM menu WHERE (courseid, topicid, taskid) = (?, ?, ?)", (int(courseid), int(topicid), int(taskid)))
        return solution.fetchone()

    def addUser(self, id, username, date) -> None:
        self.cur.execute("INSERT INTO users (userid, username, date) VALUES (?, ?, ?)", (id, username, date))
        self.con.commit()

    def updateUser(self, userid, username, sublevel, date, is_admin, is_staff) -> None:
        self.cur.execute(
            "UPDATE users SET (username, sublevel, date, is_admin, is_staff)=(?, ?, ?, ?, ?) WHERE userid = ?",
            (username, sublevel, date, is_admin, is_staff, userid))
        self.con.commit()
