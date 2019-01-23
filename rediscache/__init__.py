#!/usr/bin/env python
'''
 .+"+.+"+.+"+.+"+.
(                 )
 ) rediscache.py (
(                 )
 "+.+"+.+"+.+"+.+"

rediscache is a function decorator that will cache its result in a Redis database.

Parameters:
- refresh: the number of seconds after which the cached data will be refreshed using the decorated function.
- expire: the number of seconds after which the cached data will altogether disapear from the Redis database.
- default: the value that will be returned if the data is not found in the cache.
- host, port, db, password: the details to connect to the redis database server.

Note:
A key associated to the decorated function is created using the function name and its parameters. This is based
on the value returned by the repr() function (ie: the __repr__() member) of each paramter. user defined objects
will have this function return by default a string like this:
"<amadeusbook.services.EmployeesService object at 0x7f41dedd7128>"
This will not do as each instance of the object will have a different representation no matter what. The direct
consequence will be that each key in the cache will be different, so values in cache will never be reused.
So you need to make sure that your parameters return a meaningful representation value.

TODO:
- Store statistic data in Redis database
'''

import json
import os
import sys
import threading

from colorama import Fore
# Fore: BLACK, RED, GREEN, YELLOW, BLUE, MAGENTA, CYAN, WHITE, RESET.
# Back: BLACK, RED, GREEN, YELLOW, BLUE, MAGENTA, CYAN, WHITE, RESET.
# Style: DIM, NORMAL, BRIGHT, RESET_ALL.
from executiontime import printexecutiontime

import redis

PREFIX = "."

def rediscache(refresh, expire, default='', host='localhost', port=6379, db=0, password=None, enableCache=True):
    '''
    This decorator will cache the return value of a function.
    Note: This function returns a decorator. This allows to have a decorator that accepts parameters.
    '''
    def decorator(function):
        '''
        The decorator itself returns a wrapper function that will replace the original one.
        '''
        @printexecutiontime(Fore.YELLOW + '[' + function.__name__ + ']Total execution time of Redis decorator: {0}' + Fore.RESET)
        def wrapper(*args, **kwargs):
            '''
            This wrapper calculates and displays the execution time of the function.
            '''
            @printexecutiontime(Fore.RED + '[' + function.__name__ + ']Execution time of call to function and storage in Redis: {0}' + Fore.RESET)
            def refreshvalue(key):
                '''
                This gets the value provided by the function and stores it in local Redis database
                '''
                r_server = redis.StrictRedis(host=host, port=port, db=db, password=password)
                value = function(*args, **kwargs)
                r_server.setex(key, expire, json.dumps(value))
                r_server.setex(PREFIX + key, refresh, 1)

            def refreshvalueinthread(key):
                '''
                Run the refresh value in a separate thread
                '''
                thread = threading.Thread(target=refreshvalue, args=(key,))
                thread.start()

            def refreshvalueinfork(key):
                '''
                Fork a child process to refresh the value
                '''
                if os.fork():
                    refreshvalueinthread(key)
                    sys.exit()

            '''
            This is check whether the cache has been enabled or not
            '''
            if not enableCache:
                # If the enable cache flag is passed
                value = json.dumps(function(*args, **kwargs))
            else :
                # Lets create a key from the function's name and its parameters values
                key = function.__name__ + str(args) + str(kwargs)

                r_server = redis.StrictRedis(host=host, port=port, db=db, password=password)

                # Check if the value is available in Redis database
                if r_server.setnx(key, default):
                    # The value is not in the Redis database.
                    # Will return a default value and store it for next people requesting it.
                    # Also we trigger the refresh of the value

                    # Stop other requests from refreshing the value
                    r_server.set(PREFIX + key, 1)

                    # Make sure value cannot stay in the DB forever
                    r_server.expire(key, expire)

                    # Trigger refresh of value
                    refreshvalueinthread(key)
                else:
                    # The value is in the database, let's see if it needs refreshing.
                    if r_server.setnx(PREFIX + key, 1):
                        # The control key expired, the value needs refresing.
                        refreshvalueinthread(key)
                # Return whatever is now stored in Redis.
                # It could be the default value, an old value, or the refreshed one.
                value = r_server.get(key).decode('utf-8')
            return value
        wrapper._no_rediscache = function # This allows bypassing the cache by accessing directly to the cached function
        return wrapper
    return decorator
