#!/usr/bin/python3
# -*- coding: latin-1 -*-
import multiprocessing as mp
from datetime import datetime
import pprint
import random
import time


def printf(format, *args):
  print(format % args,end='' )

def listEc2HavingThisTagKeyAndStateOnSingleRegion(self, key, state, region):
  print("Request in region " + region)
  i = []
  for j in range(1,2):
      obj = {u'RegionName':region, u'InstancesId':"i-" + str(j) + "-" + str(random.randrange(1000,9999))}
      time.sleep(1)
      i.append(obj)
  return i

def listEc2HavingThisTagKeyAndState(self, key, state, regions):
  i = []
  pool = mp.Pool(16)
  results = pool.starmap(listEc2HavingThisTagKeyAndStateOnSingleRegion, [(self, key, state, r) for r in regions])
  pool.close()
  i = results
  #for r in regions:
  #  printf("Search for instances in region %s at state %s and a tag named %s:\n", r, state, key)
  #  obj = listEc2HavingThisTagKeyAndStateOnSingleRegion(self, key, state, r)
  #  i.append(obj)
    
    
  return i
  
if __name__ == '__main__':
  NOW = int(round(time.time() * 1000))
  i = listEc2HavingThisTagKeyAndState(None, "TheKey", "TheState", ["us-east-1", "eu-west-1", "eu-west-2", "eu-west-3", "R1", "R2", "R3", "R4"])
  pprint.pprint(i);
  EXECTIME = int(round(time.time() * 1000)) - NOW
  print("%s END RequestId: <none> in %d ms" % (datetime.now() , EXECTIME ))