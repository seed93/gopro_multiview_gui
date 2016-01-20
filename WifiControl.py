
# coding: utf-8

# In[116]:

import subprocess, os, sys
class WifiController():
    def __init__(self):
        self.interfaces = []
        self.interfacesnumber = 0
        self.mappingpath = ""
    def RemoveAllProfile(self):
        os.system('netsh wlan delete profile *')
    def RegisterAllInterfaces(self):
        allinterface = self.GetRawInterfaceInfo()
        self.interfacesnumber = 0
        self.interfaces = []
        for line in allinterface.splitlines():
            if line.find('Name')>-1:
                self.interfaces.append(dict())
                self.interfacesnumber+=1
                self.interfaces[self.interfacesnumber-1]['Name'] = line[line.find(":")+2:]
            elif line.find('Physical')>-1:
                self.interfaces[self.interfacesnumber-1]['Mac'] = line[line.find(":")+2:]
            elif line.find('State')>-1:
                self.interfaces[self.interfacesnumber-1]['State'] = line[line.find(":")+2:]
            elif (line.find('SSID')>-1 and line.find('BSSID')==-1):
                self.interfaces[self.interfacesnumber-1]['SSID'] = line[line.find(":")+2:]
    def GetRawInterfaceInfo(self,isprint = 0):
        allinterface = subprocess.Popen("netsh wlan show interface", stdout=subprocess.PIPE).stdout.read()
        allinterface = allinterface.decode('cp437')
        if (isprint==1):
            print allinterface
        return allinterface
    def GetDisconnectedInterfaceName(self):
        name = []
        for interface in self.interfaces:
            if interface['State']=="disconnected":
                name.append(interface['Name'])
        return name
    def QuickStat(self):
        for interface in self.interfaces:
            if interface.has_key("SSID"):
                print interface['Name']+' : '+interface['SSID']+'\n'
            else:
                print interface['Name']+' : '+interface['State']+'\n'
        return
    def ConnectByName(self,name,goproID):
        s = 'netsh wlan add profile filename="GoproNumber%d.xml" interface="%s"' % (goproID, name)
        print subprocess.Popen(s, stdout=subprocess.PIPE).stdout.read().decode('cp437')
        s = 'netsh wlan connect name="GoproNumber%d" interface="%s"' % (goproID, name)
        print subprocess.Popen(s, stdout=subprocess.PIPE).stdout.read().decode('cp437')
        s = 'netsh interface ip set address name="%s" source=static             addr=10.5.5.%d mask=255.255.255.0 gateway=10.5.5.9' % (name, goproID+100)
        print subprocess.Popen(s, stdout=subprocess.PIPE).stdout.read().decode('cp437')
        self.RegisterAllInterfaces
    def GetConnectedGopros(self):
        connectedgopros = []
        for interface in self.interfaces:
            if(interface.has_key("SSID") and interface["SSID"].find('GoproNumber')>-1):
                connectedgopros.append(int(interface["SSID"][11:]))
        return connectedgopros
    def QuickConnect(self):
        names = self.GetDisconnectedInterfaceName()
        onlinegp = self.GetConnectedGopros()
        offlinegp=[]
        for id in range(1,17):
            if id in onlinegp:
                continue
            else:
                offlinegp.append(id)
        for i in range(0,len(names)):
            self.ConnectByName(names[i],offlinegp[i])
        return

