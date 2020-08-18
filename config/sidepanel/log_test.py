#!/usr/bin/python3 
#sys.path.append('~/.pip-appimage')

import sys
from time import sleep
            

if __name__ == "__main__":
    for i in range(90):
        print(f" x{i}")
#        print(f" x{i} ", file=sys.stderr, end="")
#        print('test')
        sleep(0.1)
#        print(f" y{i} ", end="")
        print(f" y{i}")
        sleep(0.1)
#        sys.stderr.write('error')
#        sysc.cstderr.flush()









