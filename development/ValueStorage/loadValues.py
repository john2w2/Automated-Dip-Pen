import os
import pathlib

# get parent directory of this file
parentDir = pathlib.Path(__file__).parent.resolve()
print(parentDir)


with open('fakeCalib.txt', 'r+') as f:
    f.readline()
    f.readline()
    f.readline()
    f.readline()