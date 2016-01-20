#-*- coding: utf-8 -*-

from Tkinter import *
import tkMessageBox
import json
from collections import OrderedDict
import re
import sys, os, platform, subprocess
import functools, httplib, urllib2, socket
from time import sleep
from multiprocessing import Process, Pipe, Pool
import tkFileDialog
import struct
reload(sys)
sys.setdefaultencoding("utf-8")
pf = platform.system()

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
			sock.close()
		sleep(KEEP_ALIVE_PERIOD/1000)

def find_all_ip():
	if pf == "Darwin" or pf == "Linux":
		ipconfig_process = subprocess.Popen("ifconfig", stdout=subprocess.PIPE)
		output = ipconfig_process.stdout.read()
		iplist = []
		for line in output.splitlines():
			if line.find('inet') > -1:
				st = line.find(':')+1
				ip = line[st:line.find(' ',st)]
				if ip.find('10.5.5.') > -1:#
					iplist.append(ip)
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

def printlog(s):
	text['state'] = 'normal'
	text.insert(END, s.encode('utf8')+'\n')
	text['state'] = 'disabled'

def convertGBK(s):
	if pf == "Windows":
		return str(s).decode('gbk')
	return str(s)

def control():
	url = cmd_dict[value.get()]
	if isclient == 'server':
		parent_conn.send(url)
	send_cmd(url)

def send_cmd(url):
	result = {}
	for ip in opener:
		try:
			result[ip] = opener[ip].open(url, timeout=2).read()
		except Exception, e:
			printlog(ip + " failed\n" + convertGBK(e))
	return result

def start_ffmpeg(ip):
	prefix = "ffplay -fflags nobuffer -f:v mpegts -probesize 8192 udp://"
	printlog(prefix + "%s?localaddr=%s" % (ip, ip))
	os.system(prefix + "%s:8554?localaddr=%s" % (ip, ip))

def preview():
	if isprev.get():
		for ip in iplist:
			ffmpeg[ip] = Process(target=start_ffmpeg, args=(ip,))
			ffmpeg[ip].start()
		#pool.map_async(start_ffmpeg, iplist)
		send_cmd(stream_start)
	else:
		for ip in iplist:
			ffmpeg[ip].terminate()
		if pf == "Darwin" or pf == "Linux":
			os.system('pkill -9 ffplay')
		elif pf == "Windows":
			os.system('taskkill /F /IM ffplay.exe')
		send_cmd(stream_stop)

def wake_on_lan():
	for ip in iplist:
		macaddress = 'd4d91990386f'#mac_map[ip_to_ssid[ip]]
		data = ''.join(['FFFFFFFFFFFF', macaddress * 20])
		send_data = ''
		# Split up the hex values and pack.
		for i in range(0, len(data), 2):
			send_data = ''.join([send_data, struct.pack('B', int(data[i:i+2], 16))])
		# Broadcast it to the LAN.
		try:
			sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
			sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
			sock.bind((ip,8080))
			sock.sendto(send_data, ('10.5.5.9', 9))
			sock.close()
		except Exception, e:
			printlog(ip+' failed '+convertGBK(e))

def power_change():
	if ispower.get():
		wake_on_lan()
	else:
		send_cmd(power_off)

def load_json(filename):
	try:
		f = file(cmd_file_name)
	except IOError:
		show_message(cmd_file_name+' not found')
		exit()
	try:
		js = json.load(f, object_pairs_hook=OrderedDict)
	except Exception, e:
		show_message('json read failed\n' + convertGBK(e))
		exit()
	return js

def get_img():
	'''
	for ip in opener:
		result = opener[ip].open('http://10.5.5.9/videos/MISC/version.txt', timeout=1).read()
		print ip, result
	return
	'''
	path = tkFileDialog.askdirectory()
	if not path:
		return
	result = send_cmd(list_file)
	num = int(edit.get())
	if num <= 0:
		show_message("number should be greater than zero")
		return
	for ip in result:
		subpath = path+'/'+ip+'/'
		if not os.path.exists(subpath):
			os.mkdir(subpath)
		try:
			filelist = json.loads(result[ip])
			filelist = filelist['media'][0]['fs']
			if num > len(filelist):
				num = len(filelist)
			for file in filelist[-num:]:
				lastfile = file['n']
				data = opener[ip].open(get_file_url+lastfile, timeout=5).read()
				with open(subpath+lastfile, "wb") as code:
					code.write(data)
		except Exception, e:
			printlog(ip + convertGBK(e))
			continue
	show_message('get image done')

def start_server(conn):
	printlog('start server at '+server_ip)
	s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
	address = (server_ip, 12345)
	s.bind(address)
	s.listen(5)
	ss, addr = s.accept()
	printlog('got connect from '+addr)
	while True:
		ss.send(conn.recv())

def start_client():
	s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
	address = (server_ip, 12345)
	s.connect(address)
	printlog('got connect from '+server_ip)
	while True:
		data = s.recv(512)
		printlog(data)
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
	power_off = js['power_off']
	mac_map = js['mac_map']
except Exception, e:
	show_message('insufficient parameters\n' + convertGBK(e))
	exit()

# get connected gopro
iplist = find_all_ip()
ip_to_ssid = {}
for ip in iplist:
	ip_to_ssid[ip] = 'GoproNumber%d' % int(ip[-2:])
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
if isclient == 'server':
	parent_conn, child_conn = Pipe()
	socket_proc = Process(target=start_server, args=(child_conn,))
elif isclient == 'client':
	socket_proc = Process(target=start_client)

isprev = IntVar()
cb = Checkbutton(root, text='preview', variable=isprev, \
			onvalue = 1, offvalue = 0, command=preview)
cb.grid(row=i+1, column=0)
edit = Entry(root)
edit.grid(row=i+1, column=1)
bu = Button(root, text='get_last_img', command=get_img)
bu.grid(row=i+1, column=2)
ispower = IntVar()
power = Checkbutton(root, text='power', variable=ispower, \
			onvalue = 1, offvalue = 0, command=power_change)
power.grid(row=i+1, column=3)
text = Text(root)
text.grid(row=i+2, column=0, columnspan=columns_num)
text['state'] = 'disabled'

if __name__ == '__main__':
	if isclient:
		socket_proc.start()
	alive = Process(target=keep_alive)
	alive.start()
	printlog('%d gopros connected' % len(iplist))
	for ip in ip_to_ssid:
		printlog('---'+ip+': '+ip_to_ssid[ip])
	#global pool
	#pool = Pool(processes=8)
	root.mainloop()
	alive.terminate()
	if isclient:
		socket_proc.terminate()