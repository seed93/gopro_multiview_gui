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
    def __init__(self,ind,tot=4):
        self.timeout = tot
        self.index = ind
        self.ip = "10.5.5.%d"%(ind+100)
        self.opener = urllib2.build_opener(BoundHTTPHandler(source_address=(self.ip, 0)))
        self.isAlive = False
    def SendUrlCmd(self,url):
        
        #print "sending gopro %d: \n"%self.index
        try:
            result = self.opener.open(url, timeout=self.timeout).read()
            return result
        except Exception,e:
            print "CAM%d: "%self.index +str(e)
        #print "sending finished \n"
       
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
        rawlist = json.loads(self.SendUrlCmd("http://10.5.5.9:8080/gp/gpMediaList"))['media'][0]
        filelist = rawlist['fs']
        filename = filelist[-1]['n']
        dirname = rawlist['d']
        print filename
        data = self.SendUrlCmd("http://10.5.5.9:8080/videos/DCIM/%s/"%dirname+filename)
        with open(os.path.join(campath,filename),'wb') as target:
            target.write(data)
        print("finished.")
    def CopyAllMultiShotFiles(self,path,batchnum=-1):
        tolerance = 5
        rawlist = json.loads(self.SendUrlCmd("http://10.5.5.9:8080/gp/gpMediaList"))['media'][0]
        gpfilepath = "http://10.5.5.9:8080/videos/DCIM/%s/"%rawlist['d']
        for data in rawlist['fs']:
            if data.has_key('g') and data.has_key('b') and data.has_key('l'):
                tmppathroot = os.path.join(path,"batch%d"%int(data['g']))
                print "  Transferring Batch%d(%s-%s):\n"%(int(data['g']),data['b'],data['l'])
                if not os.path.exists(tmppathroot):
                    os.mkdir(tmppathroot)
                tmppath = os.path.join(tmppathroot,"Cam%d"%self.index)
                if not os.path.exists(tmppath):
                    os.mkdir(tmppath)
                for fid in range(int(data['b']),int(data['l'])+1):
                    filename = "G%03d%04d.JPG"%(int(data['g']),fid)
                    rawpic = self.SendUrlCmd(gpfilepath+filename)
                    with open(os.path.join(tmppath,filename),'wb') as target:
                        target.write(rawpic)
                    print "    "+filename+"Transffered."
                print "  Batch%d(%s-%s) Transfered.\n"%(int(data['g']),data['b'],data['l'])
    def CopyMultiShotFiles(self,path,batchnum):
        rawlist = json.loads(self.SendUrlCmd("http://10.5.5.9:8080/gp/gpMediaList"))['media'][0]
        gpfilepath = "http://10.5.5.9:8080/videos/DCIM/%s/"%rawlist['d']
        for data in rawlist['fs']:
            if data.has_key('g') and data.has_key('b') and data.has_key('l'):
                if int(data['g'])==int(batchnum):
                    for fid in range(int(data['b']),int(data['l'])+1):
                        filename = "G%03d%04d.JPG"%(int(data['g']),fid)
                        print data
                        rawpic = self.SendUrlCmd(gpfilepath+filename)
                        tmppathroot = os.path.join(path,"batch%d"%int(data['g']))
                        if not os.path.exists(tmppathroot):
                            os.mkdir(tmppathroot)
                        tmppath = os.path.join(tmppathroot,"Cam%d"%self.index)
                        if not os.path.exists(tmppath):
                            os.mkdir(tmppath)
                        with open(os.path.join(tmppath,filename),'wb') as target:
                            target.write(rawpic)
                        print "    "+filename+"Transffered."
                    print "  Batch%d(%s-%s) Transfered.\n"%(int(data['g']),data['b'],data['l'])    

                
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
    def GetLastImage(self,camarray,path):
        for cam in camarray:
            cam.GetLastImg(path)
    def GetOpener(self,camarray):
        opener = []
        for cam in camarray:
            opener.append(cam.opener)
        return opener
    def GetAllMultiShotFiles(self,camarray,path):
        for cam in camarray:
            cam.CopyAllMultiShotFiles(path)
    def GetMultiShotFiles(self,camarray,path,batchnum):
        for cam in camarray:
            cam.CopyMultiShotFiles(path,batchnum)

        
def CameraArrayCommand_Parralell(camarrayopener,url):
    threading= []
    for iterid in range(0,len(camarrayopener)):
        print 'creating thread!\n'
        threading.append(Thread(target=SendCmd, args=(camarrayopener[iterid],url,iterid)))
        threading[iterid].start()
        print 'thread created!\n'
    return

def SendCmd(opener,url,iterid):
    print 'started!'
    try:
        result = opener.open(url, timeout=4).read()
    except Exception,e:
        print "cam %d: "%iterid + str(e)





