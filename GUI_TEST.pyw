from Tkinter import *
from ttk import *
from WifiControl import *
import json
import sys
from CamArrayControl import *
from multiprocessing import Process
import threading
TerminateAlive = False
#GLOBAL VARIABLES:
MacMapPath = "D:/gopro_multiview_gui/macmap.json"
CmdPath = "D:/gopro_multiview_gui/newcommand.json"
root = Tk()
maxcamnum = 16
colnum = 4                #Panel Item Numbers
cb = []                   #Camera CheckButtons.
camvar = []               #Camera State
selectvar = BooleanVar()   #Select All camera chk bx
previewvar = BooleanVar()  #Preview chkbx
parallelvar = BooleanVar() #is parallel
DataPath = StringVar()
cmdvar = StringVar()       #command variable
camarray = []               #camera array reference
currentcamarray = []       #Current Selected Camera id  
wificntr = WifiController()
isparallel = False
keepalivethread = []
getstatusthread = []
previewprocess = []
camarraycmd = CameraArrayCommand()
MacMap = json.load(open(MacMapPath))
AliveLock = threading
#init CamVar for checkboxes
for iter in range (0,maxcamnum):
    camvar.append(BooleanVar())
    
#init camera commands:
with open(CmdPath) as jscmd:
    cmddict = json.load(jscmd)

#init camera reference:
for camid in range(0,maxcamnum):
    camarray.append(Camera(camid+1))
camarraycmd.RegisterMacs(camarray,MacMap)
#Binding Functions:
def VideoControl():
    cmd = cmdvar.get().split(':')
    Control(cmddict['Video'][cmd[0]][cmd[1]])
    return

def PhotoControl():
    cmd = cmdvar.get().split(':')
    Control(cmddict['Photo'][cmd[0]][cmd[1]])
    return

def MultiShotControl():
    cmd = cmdvar.get().split(':')
    Control(cmddict['MultiShot'][cmd[0]][cmd[1]])
    return

def SetupControl():
    cmd = cmdvar.get().split(':')
    Control(cmddict['Setup'][cmd[0]][cmd[1]])
    return

def UtilsControl():
    cmd = cmdvar.get().split(':')
    Control(cmddict['Utils'][cmd[0]][cmd[1]])
    return

def Control(url):
    if len(currentcamarray)==0:
        print "No Camera Selected!"
    if not isparallel:
        camarraycmd.SetControl(currentcamarray,url)
    else:
        CameraArrayCommand_Parralell(camarraycmd.GetOpener(currentcamarray),url)
    return

def SelectAllCam():
    global camvar
    if selectvar.get():
        for cbid in range(0,maxcamnum):
            if str(cb[cbid].cget('state'))=="normal":
                #print cb[cbid].cget('state')
                #cb[cbid].state(['selected'])
                camvar[cbid].set(True)
    else:
        for cbid in range(0,maxcamnum):
            #if str(cb[cbid].cget('state'))=="normal":
            #cb[cbid].state(['!selected'])
            camvar[cbid].set(False)
    UpdateSelectedCameras()
    return

def Wake():
    if len(currentcamarray)==0:
        print "No Camera Selected!"
    camarraycmd.Wake(currentcamarray)
    return

def UpdateSelectedCameras():
    currentcamarray [:] = []
    for camid in range(0,len(camvar)):
        if camvar[camid].get():
            #print camid
            currentcamarray.append(camarray[camid])
    print len(currentcamarray)
    return

def UpdateParallel():
    global isparallel
    if parallelvar.get()==1:
        isparallel=True
    else:
        isparallel=False
    return
    
def Preview():
    global TerminateAlive
    print len(currentcamarray)
    if len(currentcamarray)==0:
        print "No Camera Selected!"
        return
    if previewvar.get():
        TerminateAlive = False
        camarraycmd.SetControl(currentcamarray,cmddict['Utils']['Stream']['Start'])
        keepalivethread[:]=[]
        keepalivethread.append(threading.Thread(target = KeepAlive,args=(currentcamarray,)))
        keepalivethread[0].start()
        StreamMultiCam(currentcamarray)
    else:
        TerminateAlive = True
        camarraycmd.SetControl(currentcamarray,cmddict['Utils']['Stream']['Stop'])
    return

def KeepAlive(camarray):
    print "alive"
    MESSAGE = "_GPHD_:%u:%u:%d:%1lf\n" % (0, 0, 2, 0)
    UDP_IP = "10.5.5.9"
    UDP_PORT = 8554
    KEEP_ALIVE_PERIOD = 2500
    while True:
        if(TerminateAlive):
            return
        for cam in camarray:
            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            sock.bind((cam.ip,8080))
            sock.sendto(MESSAGE, (UDP_IP, UDP_PORT))
            sock.close()
        sleep(KEEP_ALIVE_PERIOD/1000)

def QuickConnect():
    wificntr.QuickConnect()
    return

def QuickStat():
    wificntr.QuickStat()
    return

def RemoveAll():
    wificntr.RemoveAllProfile()
    return

def UpdateConnection():
    connectedcams = wificntr.GetConnectedGopros()
    if len(connectedcams)==0:
        cballcam.configure(state="disabled")
    else:
        cballcam.configure(state="normal")
        
    for cbid in range(0,maxcamnum):
        if (cbid+1) in  connectedcams:
            cb[cbid].configure(state="normal")
        else:
            cb[cbid].configure(state="disabled")
    return

def ClearLog():
    log.configure(state="normal")
    log.delete("1.0",END)
    log.configure(state="disabled")
    return

def StartFFplay(cam):
        print "FFPLAY!"
        prefix = "ffplay -fflags nobuffer -f:v mpegts -probesize 8192 udp://"
        print prefix + "%s?localaddr=%s" % (cam.ip, cam.ip)
        os.system(prefix + "%s:8554?localaddr=%s" % (cam.ip, cam.ip))
        
def StreamMultiCam(CameraArray):
    print "Streaming! %d cams"%len(currentcamarray)
    previewprocess[:]=[]
    for index in range(0,len(currentcamarray)):
        previewprocess.append(Thread(target=StartFFplay,args=(currentcamarray[index],)))
        previewprocess[index].start()
        #previewprocess[index].run()

def CopyAllMS():
    if len(currentcamarray)==0:
        print "No Camera Selected!"
        return
    print DataPath.get()
    camarraycmd.GetAllMultiShotFiles(currentcamarray,DataPath.get())
def CopyLast():
    if len(currentcamarray)==0:
        print "No Camera Selected!"
        return
    print DataPath.get()
    camarraycmd.GetLastImage(currentcamarray,DataPath.get())

#LOG redirect:
class TextRedirector(object):
    def __init__(self, widget, tag="stdout"):
        self.widget = widget
        self.tag = tag

    def write(self, str):
        self.widget.configure(state="normal")
        self.widget.insert("end", str, (self.tag,))
        self.widget.see("end")
        self.widget.configure(state="disabled")

###GUI SET UP###

#Panels Setup
p0 = Panedwindow(root, orient=HORIZONTAL)
controlpanelparent=Labelframe(p0, text='')
logpanel=Labelframe(p0, text='LoggingPanel: ')
p = Panedwindow(controlpanelparent, orient=VERTICAL)
controlpanel = Labelframe(p, text='Control Panel: ')
camchoosepanel = Labelframe(p, text='Camera Choosing Panel: ')   # second panel
utilpanel = Labelframe(p, text='Utility Panel: ')   
wifipanel = Labelframe(p, text='Wifi Panel: ') 
#logpanel  = Labelframe(p, text='Logging Panel: ',height=500) 

#Control Panel:
controltabs = Notebook(controlpanel)
videotab = Frame(controlpanel)
phototab = Frame(controlpanel)
multishottab = Frame(controlpanel)
setuptab = Frame(controlpanel)


#Video Tabs:
cnttmp = 0
for key1 in sorted(cmddict['Video']):
    mb = Menubutton(videotab, text=key1, width=20)
    mb.menu = Menu(mb, tearoff = 0)
    mb["menu"] = mb.menu
    for key2 in sorted(cmddict['Video'][key1]):
        mb.menu.add_radiobutton(label="%s:%s"%(key1,key2), command=VideoControl, variable = cmdvar)
    r = cnttmp / colnum
    c = cnttmp % colnum
    mb.grid(row = r, column = c)
    cnttmp = cnttmp+1
#Photo Tabs:
cnttmp = 0
for key1 in sorted(cmddict['Photo']):
    mb = Menubutton(phototab, text=key1, width=20)
    mb.menu = Menu(mb, tearoff = 0)
    mb["menu"] = mb.menu
    for key2 in sorted(cmddict['Photo'][key1]):
        mb.menu.add_radiobutton(label="%s:%s"%(key1,key2), command= PhotoControl, variable = cmdvar)
    r = cnttmp / colnum
    c = cnttmp % colnum
    mb.grid(row = r, column = c)
    cnttmp = cnttmp+1
#MultiShot Tabs:
cnttmp = 0
for key1 in sorted(cmddict['MultiShot']):
    mb = Menubutton(multishottab, text=key1, width=20)
    mb.menu = Menu(mb, tearoff = 0)
    mb["menu"] = mb.menu
    for key2 in sorted(cmddict['MultiShot'][key1]): 
        mb.menu.add_radiobutton(label="%s:%s"%(key1,key2), command=MultiShotControl, variable = cmdvar)
    r = cnttmp / colnum
    c = cnttmp % colnum
    mb.grid(row = r, column = c)
    cnttmp = cnttmp+1
#Setup Tab:
cnttmp = 0
for key1 in sorted(cmddict['Setup']):
    mb = Menubutton(setuptab, text=key1, width=20)
    mb.menu = Menu(mb, tearoff = 0)
    mb["menu"] = mb.menu
    for key2 in sorted(cmddict['Setup'][key1]):
        mb.menu.add_radiobutton(label="%s:%s"%(key1,key2), command=SetupControl, variable = cmdvar)
    r = cnttmp / colnum
    c = cnttmp % colnum
    mb.grid(row = r, column = c)
    cnttmp = cnttmp+1


#camera choosing panel:

    for camid in range(1,maxcamnum+1):
         cb.append(Checkbutton(camchoosepanel, text="Gopro %2d"%camid,width=20,\
                          variable=camvar[camid-1],onvalue=1,\
                          offvalue=0,command=UpdateSelectedCameras,state='disable'))
         c = (camid-1) / colnum
         r = (camid-1) % colnum
         cb[camid-1].grid(row = r, column = c)
    cballcam = Checkbutton(camchoosepanel, text="Select All",width=20,\
                          variable=selectvar,onvalue=1,\
                          offvalue=0,command=SelectAllCam,state='disable')
    cballcam.grid(column=c+1,row=r)
#Button(f1, text='Exit', command=root.destroy).pack(padx=100, pady=100)
#Button(utilpanel, text='OOO', command=root.destroy).pack(padx=100, pady=100)

#Utility panel:
b = Button(utilpanel,text = 'Press Shutter',command = lambda: Control(cmddict['Utils']['Shutter']['Press']),width = 20)
b.grid(column=2,row=0)
b = Button(utilpanel,text = 'Release Shutter',command = lambda: Control(cmddict['Utils']['Shutter']['Release']),width = 20)
b.grid(column=3,row=0)
mb = Menubutton(utilpanel, text="Locate", width=20)
mb.menu = Menu(mb, tearoff = 0)
mb["menu"] = mb.menu
for key2 in sorted(cmddict['Utils']["Locate"]):
    mb.menu.add_radiobutton(label=("Locate:%s"%key2), command=UtilsControl,variable = cmdvar)
mb.grid(column=0,row=0)
mb = Menubutton(utilpanel, text="Delete", width=20)
mb.menu = Menu(mb, tearoff = 0)
mb["menu"] = mb.menu
for key2 in sorted(cmddict['Utils']["Delete"]):
    mb.menu.add_radiobutton(label=("Delete:%s"%key2), command=UtilsControl,variable = cmdvar)
mb.grid(column=1,row=0)
b = Button(utilpanel,text = 'Sleep',command = lambda: Control(cmddict['Utils']['Sleep']),width = 20)
b.grid(column=4,row=0)
b = Button(utilpanel,text = 'Wake',command = Wake,width = 20)
b.grid(column=5,row=0)
cb1 = Checkbutton(utilpanel,text="Preview",variable=previewvar,onvalue=1,offvalue=0,command=Preview)
cb1.grid(column=0,row=1)
cb2 = Checkbutton(utilpanel,text="Is Parallel",variable=parallelvar,onvalue=1,offvalue=0,command=UpdateParallel)
cb2.grid(column=1,row=1)
b = Button(utilpanel,text = 'Copy All MultiShot',command = CopyAllMS,width = 20)
b.grid(column=3,row=2)
b = Button(utilpanel,text = 'Copy Last File',command = CopyLast,width = 20)
b.grid(column=2,row=2)
e = Entry(utilpanel, textvariable=DataPath)
e.grid(column=1,row=2)
b = Button(utilpanel,text = 'Photo',command = lambda: Control(cmddict['Primary Modes']['Photo']),width = 20)
b.grid(column=3,row=1)
b = Button(utilpanel,text = 'Video',command = lambda: Control(cmddict['Primary Modes']['Video']),width = 20)
b.grid(column=4,row=1)
b = Button(utilpanel,text = 'MultiShot',command = lambda: Control(cmddict['Primary Modes']['MultiShot']),width = 20)
b.grid(column=5,row=1)
#WiFi Panel:
b = Button(wifipanel,text = 'Quick Connect',command = QuickConnect)
b.grid(column=1,row=0)
b = Button(wifipanel,text = 'Quick Stat',command = QuickStat)
b.grid(column=2,row=0)
b = Button(wifipanel,text = 'Remove All',command = RemoveAll)
b.grid(column=3,row=0)
b = Button(wifipanel,text = 'Update Connection',command = UpdateConnection)
b.grid(column=4,row=0)
b = Button(wifipanel,text = 'Clear Log',command = ClearLog)
b.grid(column=5,row=0)

#Log Panel:
frame = Frame(logpanel,height = 500)
frame.pack(side="top", fill="both", expand=True)
log = Text(frame,wrap="word",height = 500)
log.pack(side="top", fill="both")
logscroll = Scrollbar(root,orient="vertical", command=log.yview)
log.configure(yscrollcommand=logscroll.set)
logscroll.pack(side="right", fill="y")
log.tag_configure("stderr", foreground="#b22222")
sys.stdout = TextRedirector(log, "stdout")
sys.stderr = TextRedirector(log, "stderr")

#Add Panels and Tags
p0.pack()
p0.add(controlpanelparent)
p0.add(logpanel)
p.pack()
p.add(controlpanel)
p.add(camchoosepanel)
p.add(utilpanel)
p.add(wifipanel)
#p.add(logpanel)
controltabs.add(videotab, text = "Video")
controltabs.add(phototab, text = "Photo")
controltabs.add(multishottab, text = "MultiShot")
controltabs.add(setuptab,text = "General Setup")
controltabs.grid(column = 1,row = 1)

if __name__ == '__main__':
    print 'asdafff'
    root.mainloop()
    print 'asdafff'
exit()
