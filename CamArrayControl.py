import json
from collections import OrderedDict
import re
import sys, os, platform, subprocess
import functools, httplib, urllib2, socket
from threading import Thread
from time import sleep
from multiprocessing import Process, Pipe
import struct

class BoundHTTPHandler(urllib2.HTTPHandler):
	def __init__(self, source_address=None, debuglevel=0):
		urllib2.HTTPHandler.__init__(self, debuglevel)
		self.http_class = functools.partial(httplib.HTTPConnection,
				source_address=source_address)
	def http_open(self, req):
		return self.do_open(self.http_class, req)
    

class Camera():
    def __init__(self,ind):
        self.index = ind
        self.ip = "10.5.5.%d"%(ind+100)
        self.opener = urllib2.build_opener(BoundHTTPHandler(source_address=(self.ip, 0)))
        self.isAlive = False
    def SendUrlCmd(self,url):
        print "sending gopro %d: \n"%self.index
        result = self.opener.open(url, timeout=4).read()
        print "sending finished \n"
        return result
    def RegisterMac(self,macaddr):
        self.mac = macaddr
    def GetMac(self):
        text = self.SendUrlCmd("http://10.5.5.9/videos/MISC/version.txt")
        return text[74:86]
    def Wake(self):
        macaddress = self.mac
        data = ''.join(['FFFFFFFFFFFF', macaddress * 20])
        send_data = ''
        # Split up the hex values and pack.
        for i in range(0, len(data), 2):
            send_data = ''.join([send_data,struct.pack('B', int(data[i: i + 2], 16))])
        # Broadcast it to the LAN.
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        sock.bind((self.ip,8080))
        sock.sendto(send_data, ('10.5.5.9', 9))
        sock.shutdown(socket.SHUT_RDWR)
        sock.close()
    def Sleep(self):
        self.SendUrlCmd("http://10.5.5.9/gp/gpControl/command/system/sleep")
    def GetLastImg(self,path):
        print "Transsferring Gopro%d:\n"%self.index
        campath = os.path.join(path,"Cam%d"%self.index)
        if not os.path.exists(campath):
            os.mkdir(campath)
        filelist = json.loads(self.SendUrlCmd("http://10.5.5.9:8080/gp/gpMediaList"))['media'][0]['fs']
        filename = filelist[-1]['n']
        print filename
        #GOPRO 4 has a unique naming convention
        if self.index==4:
            data = self.SendUrlCmd("http://10.5.5.9:8080/videos/DCIM/101GOPRO/"+filename)
        else:
            data = self.SendUrlCmd("http://10.5.5.9:8080/videos/DCIM/100GOPRO/"+filename)
        with open(os.path.join(campath,filename),'wb') as target:
            target.write(data)
        print("finished.")


class CameraArrayCommand():
    def __init__(self):
        return
    def RegisterMacs(self,camarr,macmap):
        for cam in camarr:
            mac = macmap["GoproNumber%d"%cam.index]
            cam.RegisterMac(mac)
    def SetControl(self,camarr,url):
        for cam in camarr:
            try:
                cam.SendUrlCmd(url)
            except Exception,e:
                print "cam%d"%cam.index+" failed:"+str(e)
                continue
    def Wake(self,camarray):
        for cam in camarray:
            try:
                cam.Wake()
            except Exception,e:
                print "cam%d"%cam.index+" failed:"+str(e)
                continue
    def Sleep(self,camarray):
        for cam in camarray:
            try:
                cam.Sleep()
            except Exception,e:
                print "cam%d"%cam.index+" failed:"+str(e)
                continue
    def GetLastImage(self,camarray):
        for cam in camarray:
            cam.GetLastImg("D:\goproData")
        
    
def ReadJson(path):
    cmd_file_name = 'command.json'
    js = load_json(os.path.join(path,cmd_file_name))

    cmddict = dict()
    try:
        cmddict["controls"] = js['controls']
        cmddict["mac_map"] = js['mac_map']
    except Exception, e:
        print str(e)
        exit()
    return cmddict
        
def load_json(cmd_file_name):
    f = file(cmd_file_name)
    js = json.load(f, object_pairs_hook=OrderedDict)
    return js
        
def StartFFplay(cam):
        cam.SendUrlCmd("http://10.5.5.9/gp/gpControl/execute?p1=gpStream&c1=restart")
        prefix = "ffplay -fflags nobuffer -f:v mpegts -probesize 8192 udp://"
        print prefix + "%s?localaddr=%s" % (cam.ip, cam.ip)
        os.system(prefix + "%s:8554?localaddr=%s" % (cam.ip, cam.ip))

def KeepAliveSingle(cam):
    MESSAGE = "_GPHD_:%u:%u:%d:%1lf\n" % (0, 0, 2, 0)
    UDP_IP = "10.5.5.9"
    UDP_PORT = 8554
    KEEP_ALIVE_PERIOD = 2500
    if sys.version_info.major >= 3:
        MESSAGE = bytes(MESSAGE, "utf-8")
    while True:
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.bind((cam.ip,8080))
        sock.sendto(MESSAGE, (UDP_IP, UDP_PORT))
        sock.close()
    sleep(KEEP_ALIVE_PERIOD/1000)
    
    
def StreamSingle(cam):
    streamthread = Process(target = cam.StartFFplay)
    streamthread.start()
    cam.SendUrlCmd("http://10.5.5.9/gp/gpControl/execute?p1=gpStream&c1=restart")
    return streamthread

def EndStream(cam,streamthread):
    streamthread.terminate()
    cam.SendUrlCmd("http://10.5.5.9/gp/gpControl/execute?p1=gpStream&c1=stop")

def ConvertControlJson(source):
    target = dict()
    for cntritem in source['controls']:
        name = cntritem["name"]
        target[name] = cntritem["submenu"]
    return target
        