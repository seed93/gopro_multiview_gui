
# coding: utf-8

# In[1]:

from multiprocessing import Process, Pipe
from CamArrayControl import *
import socket
def CameraArrayCommand_Parralell(camarrayopener,url):
    threading= []
    for iterid in range(0,len(camarrayopener)):
        print 'creating thread!\n'
        threading.append(Process(target=SendCmd_test, args=(camarrayopener[iterid],url,iterid)))
        threading[iterid].start()
        print 'thread created!\n'
def BuildCameraArrayOpener(camarray):
    opener = []
    for cam in camarray:
        opener.append(cam.opener)
    return opener
def SendCmd_test(opener,url,iterid):
    print 'started!'
    try:
        result = opener.open(url, timeout=4).read()
    except Exception,e:
        print "cam %d: "%iterid + str(e)

def KeepAlive(camarray):
    MESSAGE = "_GPHD_:%u:%u:%d:%1lf\n" % (0, 0, 2, 0)
    UDP_IP = "10.5.5.9"
    UDP_PORT = 8554
    KEEP_ALIVE_PERIOD = 2500
    while True:
        for cam in camarray:
            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            sock.bind((cam.ip,8080))
            sock.sendto(MESSAGE, (UDP_IP, UDP_PORT))
            sock.close()
        sleep(KEEP_ALIVE_PERIOD/1000)
def StreamMultiCam(camarray):
    for cam in camarray:
        thread = Process(target=StartFFplay,args=(cam,))
        thread.start()
    
if __name__=='__main__':
    print "enter"
    camarray = []
    for id in range(1,17):
        camarray.append(Camera(id))
    js = ReadJson('D:\gopro_multiview_gui')
    cmddict = ConvertControlJson(js);
    camarraycmd = CameraArrayCommand()
    camarraycmd.RegisterMacs(camarray,js['mac_map'])
    #camarraycmd.SetControl(camarray,cmddict['Primary modes']['MultiShot'])
    #camarraycmd.SetControl(camarray,cmddict['Secondary modes']['Timelapse (MultiShot)'])
    #camarraycmd.SetControl(camarray,cmddict['Timelapse Interval']['0.5'])
    #camarraycmd.SetControl(camarray,cmddict['Photo resolution']['7MP Medi'])
    #camarraycmd.SetControl(camarray,cmddict['Field Of View']['Medium'])
    #camarraycmd.SetControl(camarray,cmddict['White Balance']['6500k'])
    #camarraycmd.SetControl(camarray,cmddict['EV']['0'])
    Thread = Process(target = KeepAlive,args=(camarray[0:4],))
    Thread.start()
    StreamMultiCam(camarray[0:4])
    # In[2]:



