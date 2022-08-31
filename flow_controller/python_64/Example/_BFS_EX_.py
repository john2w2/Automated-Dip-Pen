#Tested with Python 3.5.1 (IDE Eclipse V4.5.2 + Pydev V5.0.0)
#add python_xx and python_xx/DLL to the project path 

import sys
from _ast import Load
sys.path.append('D:/dev/SDK/DLL64/DLL64') #add the path of the library here
sys.path.append('D:/dev/SDK/Python_64')#add the path of the LoadElveflow.py

from ctypes import *

from array import array

from Elveflow64 import *


#
# Initialization of BRS ( ! ! ! REMEMBER TO USE .encode('ascii')
#
Instr_ID=c_int32()
print("Instrument name and regulator types hardcoded in the python script")
#see User guide to determine regulator type NI MAX to determine the instrument name 
error=BFS_Initialization("ASRL13::INSTR".encode('ascii'),byref(Instr_ID)) #Chose the com port, can be ASRLXXX::INSTR (where XXX=port number)
# all functions will return error code to help you to debug your code, for further information see user guide
print('error:%d' % error)
print("BFS ID: %d" % Instr_ID.value)

#
#Main loops 
#
    
repeat=True
while repeat:
    answer=input('what to do (get_density, get_flow, get_temperature, set_filter or exit) : ')
    
        
    if answer=="get_density":
        density=c_double(-1)
        error=BFS_Get_Density(Instr_ID.value,byref(density))
        print('Density: ',density.value)
        
    if answer=="get_flow":
        flow=c_double(-1)
        error=BFS_Get_Flow(Instr_ID.value,byref(flow))
        print('flow: ',flow.value)
        print('Remember that density need to be measured at least once before since density is used to measure the flow. If measurement frequency is not critical, always measure first density and then flow')

    if answer=="get_temperature":
        temperature=c_double(-1)
        error=BFS_Get_Temperature(Instr_ID.value,byref(temperature))
        print('temperature: ',temperature.value)
    
    if answer=="set_filter":
        filter=0.001
        filter=input("select filter(1= minimum filter, 0,00001 maximum filter) : ")
        filter=float(filter)
        filter=c_double(filter) #convert to c_double
        error=BFS_Set_Filter(Instr_ID.value,filter)
            
    
    if answer=='exit':
        repeat=False
    
    print( 'error :', error)
    error=0
        

error=BFS_Destructor(Instr_ID.value)

    