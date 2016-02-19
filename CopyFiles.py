
# coding: utf-8

# In[20]:

from CamArrayControl import *
from WifiController import *

num = 6
cam = Camera(num)
batchlist = range(1,8)
for batchnum in batchlist:
    cam.CopyMultiShotFiles('D:/data/2_3/',batchnum)

