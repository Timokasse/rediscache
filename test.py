#!/usr/bin/env python

from time import sleep

from rediscache import rediscache

import time, redis

@rediscache(1, 2)
def getTestValue():
    return (5, 'toto')

if __name__ == '__main__':
    myfunction()
