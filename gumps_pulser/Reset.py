# -* coding: utf-8 -*

"""
-------------------------------------------------------------------------------
-------------------------------------------------------------------------------
FileName:ip_func.py
Date Created: 10-Aug-2017
Description:Program to reset the PI before launching the Pulser application

Copyright:Copyright ©2017,Detect Technologies Pvt.Ltd. 
--------------------------------------------------------------------------------
--------------------------------------------------------------------------------
"""
import gpio as GPIO
import time
# Reset Code

# set up the GPIO channels - one input and one output
GPIO.setup(33, GPIO.OUT)

GPIO.output(33, GPIO.LOW)
time.sleep(3)

GPIO.output(33, GPIO.HIGH)
time.sleep(10)

#GPIO.cleanup()
print('Reset Raspberry PI pins for microcontroller')
