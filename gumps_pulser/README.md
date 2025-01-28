# PulserSoftware
Pulser software to acquire data from TI MCU through UART port.

## Table of Contents

[[_TOC_]]

## Code compatibility
- Architecture   - arm64,armhf
- Python version - Python 2.7
- Platforms      - All ARM based Platforms

## Hardware Architecture
![Semantic description of image](/misc/images/gumps_pulser1.png "Pulser Hardware architecture")
- IMX7D processor (running on linux) interfaces with TI delfino MCU.
- TI MCU in turn interfaces with pulse board
- TI MCU is programmed for following
    - Sample waveform from RX amplifier
    - Averaging data from RX amplifier
    - Trigger pulser board to start pulsing
    - Change frequency of operation of pulse board
- IM7D sets the following config in TI MCU
    - Frequency
    - Buffer size
    - Averaging size
    - Trigger transmission and reception

## Installation
**Setting up code**
``` bash
sudo apt-get update
sudo apt-get install crudini
git clone git@gitlab.com:DetectTechnologies/GUMPS/GUMPS-SD/gumps_pulser.git /home/dt
cd /home/dt/gumps_pulser
cat setup/requirements | xargs sudo apt-get install  # Install requirements
sudo chmod +x launcher.sh # make launcher script executable
```
**Server and Pulser related config**

Set Pulser Name
Set API endpoints and credentials
``` bash
crudini --set config.ini "Server Settings" "URL" "<Server URL>"
crudini --set config.ini "Server Settings" "PULSER_NAME" "<Pulser name>"
crudini --set config.ini "Server Settings" "LOGIN_URL" "<Server URL for login>"
crudini --set config.ini "Server Settings" "USERNAME" "<Username for login>"
crudini --set config.ini "Server Settings" "PASSWORD" "<Password for login>"
```

**Setting up systemd service**
``` bash
sudo cp setup/pulser_hanning.service /etc/systemd/system/pulser_hanning.service # Copy systemd service file
sudo systemctl daemon-reload
sudo systemctl enable pulser_hanning # To enable pulser service at boot
sudo systemctl start pulser_hanning # To start pulser service
sudo journalctl -u -f pulser_hanning
```

**Testing the code without systemd**
``` bash
sudo systemctl stop pulser_hanning # Stop the service 
./launcher.sh # launch pulser code without systemd
```

## Debugging

### Switcher configuration mismatch

1. Check if switcher cables are secured properly
2. If problem still persists use `python3 switcher-test.py` to check which combinations are not working
3. Some switchers maybe using old pin config, for that use `self.gpio_pins = [45, 44, 37, 36, 35, 34]` as pin map.
in config_parser.py line 261

### Low storage

1. `sudo journalctl --vacuum-size=10M` to delete logs
2. Check if backup data is full, in folder UploadQ, delete some files

### Not connecting to server (Cannot get data and time, upload error)

1. Check if internet is working `ping google.com`
2. If internet works ask software team if server is up, forward the errors encountered to them.

### Unable to get config

This happens if software reset is not working in cerebro board.
1. Check if R81 is shorted in cerebro board



