#-*- coding: utf-8 -*-

from Tkinter import *
import tkMessageBox
import json
from collections import OrderedDict
import re
import sys, os, platform, subprocess
import functools, httplib, urllib2, socket
from threading import Thread
from time import sleep
from multiprocessing import Process, Pipe
import tkFileDialog
reload(sys)
sys.setdefaultencoding("utf-8")

class BoundHTTPHandler(urllib2.HTTPHandler):
	def __init__(self, source_address=None, debuglevel=0):
		urllib2.HTTPHandler.__init__(self, debuglevel)
		self.http_class = functools.partial(httplib.HTTPConnection,
				source_address=source_address)
	def http_open(self, req):
		return self.do_open(self.http_class, req)

def set_sender(iplist):
	opener = {}
	for ip in iplist:
		# send command
		handler = BoundHTTPHandler(source_address=(ip, 0))
		opener[ip] = urllib2.build_opener(handler)
	return opener

def keep_alive():
	MESSAGE = "_GPHD_:%u:%u:%d:%1lf\n" % (0, 0, 2, 0)
	UDP_IP = "10.5.5.9"
	UDP_PORT = 8554
	KEEP_ALIVE_PERIOD = 2500
	if sys.version_info.major >= 3:
		MESSAGE = bytes(MESSAGE, "utf-8")
	while True:
		for ip in iplist:
			sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
			sock.bind((ip,8080))
			sock.sendto(MESSAGE, (UDP_IP, UDP_PORT))
		sleep(KEEP_ALIVE_PERIOD/1000)

def find_all_ip():
	pf = platform.system()
	ipstr = '([0-9]{1,3}\.){3}[0-9]{1,3}'
	if pf == "Darwin" or pf == "Linux":
		ipconfig_process = subprocess.Popen("ifconfig", stdout=subprocess.PIPE)
		output = ipconfig_process.stdout.read()
		ip_pattern = re.compile('(inet %s)' % ipstr)
		if pf == "Linux":
			ip_pattern = re.compile('(inet addr:%s)' % ipstr)
		pattern = re.compile(ipstr)
		iplist = []
		for ipaddr in re.finditer(ip_pattern, str(output)):
			ip = pattern.search(ipaddr.group())
			if ip.group() != "127.0.0.1":
				iplist.append(ip.group())
		return iplist
	elif pf == "Windows":
		ipconfig_process = subprocess.Popen("ipconfig", stdout=subprocess.PIPE)
		output = ipconfig_process.stdout.read()
		iplist = []
		for line in output.splitlines():
			if line.find('IPv4') > -1:
				ip = line[line.rfind(' ')+1:]
				if ip.find('10.5.5.') > -1:#
					iplist.append(ip)
		return iplist

def show_message(s):
	tkMessageBox.showinfo("Message", s)

def control():
	url = cmd_dict[value.get()]
	parent_conn.send(url)
	send_cmd(url)

def send_cmd(url):
	result = {}
	for ip in opener:
		try:
			result[ip] = opener[ip].open(url, timeout=1).read()
		except Exception, e:
			show_message(ip + " failed\n" + str(e))
	return result

def start_ffmpeg(ip):
	prefix = "ffplay -fflags nobuffer -f:v mpegts -probesize 8192 udp://"
	print prefix + "%s?localaddr=%s" % (ip, ip)
	os.system(prefix + "%s:8554?localaddr=%s" % (ip, ip))

def preview():
	if isprev.get():
		for ip in iplist:
			ffmpeg[ip] = Process(target=start_ffmpeg, args=(ip,))
			ffmpeg[ip].start()
		send_cmd(stream_start)
	else:
		for ip in iplist:
			ffmpeg[ip].terminate()
		pf = platform.system()
		if pf == "Darwin" or pf == "Linux":
			os.system('pkill -9 ffplay')
		elif pf == "Windows":
			os.system('taskkill /F /IM ffplay.exe')
		send_cmd(stream_stop)

def load_json(filename):
	try:
		f = file(cmd_file_name)
	except IOError:
		show_message(cmd_file_name+' not found')
		exit()
	try:
		js = json.load(f, object_pairs_hook=OrderedDict)
	except Exception, e:
		show_message('json read failed\n' + str(e))
		exit()
	return js

def get_img():
	path = tkFileDialog.askdirectory()
	result = send_cmd(list_file)
	for ip in result:
		subpath = path+'/'+ip+'/'
		if not os.path.exists(subpath):
			os.mkdir(subpath)
		try:
			filelist = json.loads(result[ip])
			lastfile = filelist['media'][0]['fs'][-1]['n']
			data = opener[ip].open(get_file_url+lastfile, timeout=5).read()
			with open(subpath+lastfile, "wb") as code:
				code.write(data)
		except Exception, e:
			print str(e)
			continue

def start_server(conn):
	s.listen(5)
	ss, addr = s.accept()
	print 'got connect from ', addr
	while True:
		ss.send(conn.recv())

def start_client():
	while True:
		data = s.recv(512)
		print data
		send_cmd(data)

# load json
cmd_file_name = 'command.json'
js = load_json(cmd_file_name)
try:
	columns_num = js['columns_num']
	controls = js['controls']
	stream_start = js['stream']['start']
	stream_stop = js['stream']['stop']
	list_file = js['list_file']
	get_file_url = js['file_path']
	server_ip = js['server_ip']
	isclient = js['isclient']
except Exception, e:
	show_message('insufficient parameters\n' + str(e))
	exit()

# get connected gopro
iplist = find_all_ip()
print iplist
opener = set_sender(iplist)
ffmpeg = {}

# init gui
root = Tk()
value = StringVar()
i = 0
cmd_dict = {}
for item in controls:
	name = item['name']
	mb = Menubutton(root, text=name, width=20)
	mb.menu = Menu(mb, tearoff = 0)
	mb["menu"] = mb.menu
	for sub in item['submenu']:
		text = name + ": " + sub
		cmd_dict[text] = item['submenu'][sub]
		mb.menu.add_radiobutton(label=text, command=control, variable = value)
	r = i / columns_num
	c = i % columns_num
	mb.grid(row = r, column = c)
	i = i+1

root.title('gopro controller with %d gopros (%s)' % (len(iplist), isclient))
s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
address = (server_ip, 12345)
if isclient == 'server':
	s.bind(address)
	parent_conn, child_conn = Pipe()
	socket_proc = Process(target=start_server, args=(child_conn,))
	socket_proc.start()
else:
	s.connect(address)
	socket_proc = Process(target=start_client)
	socket_proc.start()

isprev = IntVar()
cb = Checkbutton(root, text='preview', variable=isprev, \
			onvalue = 1, offvalue = 0, command=preview)
cb.grid(row=i+1, column=0, columnspan=columns_num/2)
bu = Button(root, text='get_last_img', command=get_img)
bu.grid(row=i+1, column=columns_num/2, columnspan=columns_num/2)


if __name__ == '__main__':
	threading = Process(target=keep_alive)
	threading.start()
	root.mainloop()
	threading.terminate()
	s.close()
	socket_proc.terminate()