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
        return subs.fetchone()
    
    def getUsersBySublevel(self, sublevel) -> list:
        subs = self.cur.execute("SELECT userid FROM users WHERE sublevel = ?", (sublevel,))
        return [y for x in subs.fetchall() for y in x]
    
    def getSubsByUserid(self, userid) -> list:
        subs = self.cur.execute("SELECT sublevel, date, is_admin, is_staff FROM users WHERE userid = ?", (userid,))
        return subs.fetchone()
    
    def addUser(self, id, username, date) -> None:
        self.cur.execute("INSERT INTO users (userid, username, date) VALUES (?, ?, ?)", (id, username, date))
        self.con.commit()
        
    def updateUser(self, userid, username, sublevel, date, is_admin, is_staff) -> None:
        self.cur.execute("UPDATE users SET (username, sublevel, date, is_admin, is_staff)=(?, ?, ?, ?, ?) WHERE userid = ?", (username, sublevel, date, is_admin, is_staff, userid))
        self.con.commit()