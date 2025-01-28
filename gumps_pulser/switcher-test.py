#!/usr/bin/python3

import gpio as GPIO

switch_map = {"101001": "S1 S3", "101010": "S1 S4", "101011": "S1 S5", "101100": "S1 S6", "101000": "S1 S7",
              "101111": "S1 S8", "001001": "S2 S3", "001010": "S2 S4", "001011": "S2 S5", "001100": "S2 S6", 
              "001000": "S2 S7", "001111": "S2 S8"}

switch_states = list(switch_map.keys())
#self.gpio_pins = [45, 44, 37, 36, 35, 34]
gpio_pins = [34, 35, 36, 37, 44, 45]

for gpioPin in gpio_pins:
    GPIO.setup(gpioPin, GPIO.OUT)

curr_state_index = 0
while True:
    if curr_state_index < len(switch_states):
        userInput = input()
        print(switch_map[switch_states[curr_state_index]])
        curr_state = switch_states[curr_state_index]
        curr_state_index += 1
        for i in range(len(gpio_pins)):
            if curr_state[i] == '1':
                GPIO.output(gpio_pins[i], GPIO.HIGH)
            else:
                GPIO.output(gpio_pins[i], GPIO.LOW)
            # print(gpio_pins[i], curr_state[i]) # shows pin numbers and the status of the pin
    else:
        break