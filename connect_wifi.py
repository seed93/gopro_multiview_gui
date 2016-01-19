#-*- coding:utf-8 -*-

import subprocess, os, sys
reload(sys)
sys.setdefaultencoding("utf-8")
s = '名称'
os.system('netsh wlan delete profile *')
all_interface = subprocess.Popen("netsh wlan show interface", stdout=subprocess.PIPE).stdout.read()
interface_list = []
for line in all_interface.splitlines():
	if line.find(s.encode('gbk')) > -1:
		name = line[line.find(':')+2:]
		if name == 'WLAN':
			continue
		interface_list.append(name)

print 'total %d interfaces' % len(interface_list)

num = range(1, 17)
for i in range(0,len(interface_list)):
	s = 'netsh wlan add profile filename="GoproNumber%d.xml" interface="%s"' % (num[i], interface_list[i])
	os.system(s)
	s = 'netsh wlan connect name="GoproNumber%d" interface="%s"' % (num[i], interface_list[i])
	os.system(s)
	s = 'netsh interface ip set address name="%s" source=static \
		addr=10.5.5.%d mask=255.255.255.0 gateway=10.5.5.9' % (interface_list[i], num[i]+100)
	os.system(s)
