# RedfishUtility
Redfish scripts to perform basic operations of HPE iLO.

The basic operations include:
- Create Logical drive
- Delete Logical drives
- Display Logical drives
- Display Physical drives
- Show boot order
- Check the iLO power status
- Set the iLO power status

## Pre-requisites

1. This python script is implemented based on redfish.

```pip3 install redfish```

2. Script uses environmental variables to authenticate the iLO. Export the below variables before running the script
export ILO_IP="<ILO_IPADDR>"
export ILO_USERNAME="<ILO_USERNAME>"
export ILO_PASSWORD='<ILO_PASSWORD>'

## Usage

./hpe_redfish_utility.py (--create-lv | --delete-lv | -lv | -pv | -s | -r {on,off,force-reset} | --show-boot)

Utility to perform operations HPE iLO

optional arguments:
  -h, --help            show this help message and exit
  --create-lv           Create logical volume
  --delete-lv           Delete Logical Volume
  -lv, --show-lv        Show logical Volume
  -pv, --show-pv        Show physical Volume
  -s, --status          Show power status of server
  -r {on,off,force-reset}, --reset {on,off,force-reset}
                        Reset the power option
  --show-boot           Show Boot Order
