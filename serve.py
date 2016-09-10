from flask import Flask, render_template, request, redirect, session
from flask.ext.cors import CORS #flask extension for cross origin requests

import json
import argparse
import MySQLdb as mdb

"""
app setup
"""
app = Flask(__name__)
CORS(app) #allows cross origin requests
app.secret_key = 'A0Zr98j/3yX R~XHH!jmN]LWX/,?RTDALKSFJLDSKJFKLSDJF' #sets key for sessions

"""
query functions
"""
def getTigers():
	con = mdb.connect('localhost', 'root', 'visibilitymatters', 'tigerlink')
	with con:
		cur = con.cursor(mdb.cursors.DictCursor)
		cur.execute("select * from tigers order by name")
		rows = cur.fetchall()
	return rows

def updateTiger(id):
	con = mdb.connect('localhost', 'root', 'visibilitymatters', 'tigerlink')
	with con:
		cur = con.cursor(mdb.cursors.DictCursor)
		cur.execute("update tigers set value = 1 where id = " + id)

def resetTigers():
	con = mdb.connect('localhost', 'root', 'visibilitymatters', 'tigerlink')
	with con:
		cur = con.cursor(mdb.cursors.DictCursor)
		cur.execute("update tigers set value = 0")

def getWord():
	con = mdb.connect('localhost', 'root', 'visibilitymatters', 'tigerlink')
	with con:
		cur = con.cursor(mdb.cursors.DictCursor)
		cur.execute("select word from word")
		rows = cur.fetchall()
	return rows[0]["word"]

def changeWord(word):
	con = mdb.connect('localhost', 'root', 'visibilitymatters', 'tigerlink')
	with con:
		cur = con.cursor(mdb.cursors.DictCursor)
		cur.execute("update word set word = \"" + word + "\"")

def addTiger(name):
	con = mdb.connect('localhost', 'root', 'visibilitymatters', 'tigerlink')
	with con:
		cur = con.cursor(mdb.cursors.DictCursor)
		cur.execute("insert into tigers (name, value) values(\"" + name + "\", 0)")

def removeTiger(id):
	con = mdb.connect('localhost', 'root', 'visibilitymatters', 'tigerlink')
	with con:
		cur = con.cursor(mdb.cursors.DictCursor)
		cur.execute("delete from tigers where id = " + str(id))

"""
routes
"""
@app.route('/')
def indexRoute():
	return render_template("index.html")

@app.route("/tigers")
def tigersRoute():
	return render_template("tigers.html", tigers=getTigers())

@app.route("/signin")
def signinRoute():
	return render_template("signin.html", tigers=getTigers())

@app.route("/logout")
def logoutRoute():
	session.pop('admin', None)
	return redirect("/")

@app.route("/admin")
def adminRoute():
	if "admin" in session:
		return render_template("admin.html", word=getWord(), tigers=getTigers())
	else:
		return redirect("/login")

@app.route("/login", methods=["GET", "POST"])
def loginRoute():
	if request.method == "GET":
		return render_template("login.html", incorrect=False)
	if request.method == "POST":
		if request.values["password"] == "adminpass":
			session["admin"] = True
			return "true"
		else:
			return "false"

"""
api routes
"""
@app.route("/changeword")
def changewordRoute():
	if "admin" in session:
		changeWord(request.args["word"])
		return "true"
	else:
		return "false"	

@app.route("/addtiger", methods=["POST"])
def addtigerRoute():
	if "admin" in session:
		addTiger(request.values["name"])
		return "true"
	else:
		return "false"

@app.route("/removetiger", methods=["POST"])
def removeTigerRoute():
	if "admin" in session:
		removeTiger(request.values["id"])
		return "true"
	else:
		return "false"

"""
realtime server
"""
import tornado.web
from tornado.websocket import WebSocketHandler
from tornado.ioloop import PeriodicCallback,IOLoop
import tornado.wsgi
import sockjs.tornado



connections = [] #array of connected users
class ChatConnection(sockjs.tornado.SockJSConnection): #websocket tornado class
    def on_open(self, info):
        connections.append(self)
    def on_message(self, message):
		data = json.loads(message)
		if data["type"] == "user_login":
			if data["word"] == getWord(): #if correct word of the day
				#send response that user was logged in
				response = {}
				response["type"] = "verification_response"
				response["data"] = "true"
				self.send(json.dumps(response))
				#send broadcast to update the tigers site
				broadcastResponse = {}
				broadcastResponse["type"] = "user_login"
				broadcastResponse["id"] = data["id"]
				broadcastResponse["name"] = data["name"]
				self.broadcast(connections, json.dumps(broadcastResponse))
				#update tiger in database
				updateTiger(data["id"])
			else:
				#send response that the word was incorrect
				response = {}
				response["type"] = "verification_response"
				response["data"] = "false"
				self.send(json.dumps(response))

		if data["type"] == "reset_tigers":
			resetTigers()
			response = {}
			response["type"] = "tigers_reset"
			self.broadcast(connections, json.dumps(response))
    def on_close(self):
        connections.remove(self)

wsgi_app=tornado.wsgi.WSGIContainer(app)
ChatRouter = sockjs.tornado.SockJSRouter(ChatConnection, '/realtime') #class for websocket
application=tornado.web.Application(
	ChatRouter.urls +
	[(r'.*',tornado.web.FallbackHandler,{'fallback':wsgi_app })]
	)

if __name__ == "__main__":
	parser = argparse.ArgumentParser(description='Tiger links realtime server') #argument parser
	parser.add_argument('-p','--port', help='port number', required=False) #argument for supplying a port
	args = vars(parser.parse_args()) #list of arguments
	port = 80 #default port
	if args['port'] != None: #if port is specified, assign port
		port = args['port']
	#start server
	print "serving on port " + str(port)
	application.listen(port)
	IOLoop.instance().start()