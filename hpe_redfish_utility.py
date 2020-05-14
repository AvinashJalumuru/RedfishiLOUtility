#!/usr/bin/env python

import argparse
import sys
import os
import redfish
import json

#def readFromEnv():
#    login_host = os.environ['ILO_IP']
#    login_account = os.environ['ILO_USERNAME']
#    login_password = os.environ['ILO_PASSWORD']

class HpeLogicalVolume(object):

    POWER_OFF = "ForceOff"
    POWER_ON  = "On"
    POWER_RESET = "ForceRestart"

    def __init__(self):
         self.loadRedfish()
         self.redfishObj.login()
         self.driveInfos = None
         self.logicalDrivesInfo = None

    def __del__(self):
         if self.redfishObj:
              self.redfishObj.logout()

    def loadRedfish(self):
         login_host = "https://{}".format(os.environ['ILO_IP'])
         login_account = os.environ['ILO_USERNAME']
         login_password = os.environ['ILO_PASSWORD']
         self.redfishObj = redfish.redfish_client(base_url=login_host, username=login_account, password=login_password)

    def getPostState(self):
        iloInfo = self.redfishObj.get('/redfish/v1/Systems/1/')
        return iloInfo.obj["Oem"]["Hpe"]['PostState']

    
    def isBiosLock(self):
        postState = self.getPostState()
        print("Post State : {}".format(postState))
        if postState.upper() in ["INPOSTDISCOVERYCOMPLETE", "FINISHEDPOST", "POWEROFF"]:
            return False

        return True

    def getPowerStatus(self):
        iloInfo = self.redfishObj.get('/redfish/v1/Systems/1/')
        return iloInfo.obj['PowerState']

    def resetPower(self, state):
        iloInfo = self.redfishObj.get('/redfish/v1/Systems/1/')
        resetBody = {}
        if state.lower() == "on":
            resetBody = {"ResetType": self.POWER_ON}

        elif state.lower() == "off":
            resetBody = {"ResetType": self.POWER_OFF}

        elif state.lower() == "force-reset":
            resetBody = {"ResetType": self.POWER_RESET}

        response = self.redfishObj.post("/redfish/v1/systems/1/Actions/ComputerSystem.Reset", body=resetBody)
        if response.status != 200:
            raise Exception("Failed to reset power state to {state}: {msg}".format(state=state, msg=response.text))


    def logicalDrives(self):
        smartConfigInfo = self.redfishObj.get('/redfish/v1/Systems/1/smartstorageconfig/')
        self.logicalDrivesInfo = []
        for lgDrive in smartConfigInfo.obj["LogicalDrives"]:
            drive ={}
            drive["LogicalDriveNumber"] = lgDrive["LogicalDriveNumber"]
            drive["dataDrives"] = lgDrive["DataDrives"]
            drive["capacityGiB"] = lgDrive["CapacityGiB"]
            drive["raidLevel"] = lgDrive["Raid"]
            drive["driveID"] = lgDrive["VolumeUniqueIdentifier"]

            self.logicalDrivesInfo.append(drive)

    def displayLogicalDrives(self):
        self.logicalDrives()
        
        if not self.logicalDrivesInfo:
            print ("\nNo logicals drives present in this system\n")
            return

        print()
        fmt = '{:<20}{:<20}{:<15}{:<35}'
        print(fmt.format('LogicalNumber', 'Capacity', 'Raid', 'VolumeID'), 'DriveLocation')
        print("-" * 110)
        for drive in self.logicalDrivesInfo:
            print(fmt.format(drive['LogicalDriveNumber'], drive['capacityGiB'], drive['raidLevel'], drive['driveID']), drive['dataDrives'])
        print()

    def physicalDrives(self):
        self.driveInfos = []
        for controller in self.redfishObj.get('/redfish/v1/Systems/1/SmartStorage/ArrayControllers').obj["Members"]:
            smartArrayControllerInfo = self.redfishObj.get(controller["@odata.id"] + "/DiskDrives")
            for disk in smartArrayControllerInfo.obj["Members"]:
                driveInfo = {}
                diskInfoObj = self.redfishObj.get(disk["@odata.id"])
                driveInfo["InterfaceType"] = diskInfoObj.obj["InterfaceType"]
                driveInfo["Location"] = diskInfoObj.obj["Location"]
                driveInfo["MediaType"] = diskInfoObj.obj["MediaType"]
                driveInfo["CapacityGB"] = diskInfoObj.obj["CapacityGB"]
                driveInfo["Health"] = diskInfoObj.obj["Status"]["Health"]
                driveInfo["State"] = diskInfoObj.obj["Status"]["State"]
                driveInfo["DiskDriveUse"] = diskInfoObj.obj["DiskDriveUse"]

                self.driveInfos.append(driveInfo)


    def displayPhysicaldrives(self):
        self.physicalDrives()
        
        if not self.driveInfos:
            print ("\nNo physical drives present in this system\n")
            return

        print()
        fmt = '{:<15}{:<15}{:<15}{:<15}'
        print(fmt.format('Location', 'Interface', 'Media', 'Capacity'))
        print("-" * 60)
        for drive in self.driveInfos:
            print(fmt.format(drive['Location'], drive['InterfaceType'], drive['MediaType'], drive['CapacityGB']))
        print()

    def displayBootdrives(self):
        bootSettings = self.redfishObj.get("/redfish/v1/Systems/1/BIOS/Boot/Settings/")
        bootSource = bootSettings.obj["BootSources"]
        bootOrder = bootSettings.obj["PersistentBootConfigOrder"]
        print("")
        for i in bootSource:
            print("{0: <25} : {1: <100}".format(i["StructuredBootString"], i['BootString']))
        print("")

    
    def createLG(self):
        print("\n\n Displaying physical drive Info\n")
        self.displayPhysicaldrives()

        logicalCapacity = input("Enter Capcity Info: ")
        driveTechnology = input("Choose the drive technology (SASHDD, SATAHDD, SASSSD, SATASSD): ")

        raidConfig = "Raid1"
        #raidConfig = input("Select raid configuration (Raid1, Raid5, Raid10): ")

        unassignedDrives = []
      
        for drive in self.driveInfos:
            if drive.get('InterfaceType') in driveTechnology and \
               drive.get('MediaType') in driveTechnology and \
               drive.get("CapacityGB") == int(logicalCapacity) and \
               drive.get("DiskDriveUse").lower() == "raw":
                 unassignedDrives.append(drive.get("Location"))


        if not unassignedDrives:
            print("\nThere are no available physical drives.. Exiting\n")
            exit(0)

        print("\nList of unassigned drives {} \n".format(unassignedDrives))
        RaidMin = {
            "Raid1": 2,
            "Raid5": 3,
            "Raid10": 4
        }

        smartConfigSetting = self.redfishObj.get('/redfish/v1/Systems/1/smartstorageconfig/settings/')
        logicalDriveReqData = smartConfigSetting.obj

        logicalDriveReqData["DataGuard"] = "Disabled"
        logicalDriveReqData["LogicalDrives"] = []

        logicalDrive = {}
        logicalDrive["LogicalDriveName"] = "LogicalDrive_Hpe"
        logicalDrive["Raid"] = raidConfig
        logicalDrive["DataDrives"] = unassignedDrives[:RaidMin[raidConfig]]
        logicalDriveReqData["LogicalDrives"].append(logicalDrive)

        print("Logical drive: {}".format(json.dumps(logicalDriveReqData, indent=2)))
        smartConfigUpdateSetting = self.redfishObj.put('/redfish/v1/Systems/1/smartstorageconfig/settings/', body=logicalDriveReqData)

        if smartConfigUpdateSetting.status != 200 or smartConfigUpdateSetting.status != 200:
            raise Exception("Failed to created RAID configuration")

        print ("Raid configuration updated successful. System reset required to reflect the chagnes")

        if self.getPowerStatus().lower() == "off":
            self.resetPower("on")
        else:
            self.resetPower("force-reset")
         
    def deleteLG(self):
        print("\n\n Displaying logical drive Info\n")
        self.displayLogicalDrives()

        logicalDriveReqData = {}
        logicalDriveReqData["DataGuard"] = "Disabled"
        logicalDriveReqData["LogicalDrives"] = []

        smartConfigDeleteSetting = self.redfishObj.put('/redfish/v1/Systems/1/smartstorageconfig/settings', body=logicalDriveReqData)

        if smartConfigDeleteSetting.status != 200:
            raise Exception("Failed to delete RAID configuration")

        print ("Logical drives successfully deleted. System reset required to reflect the chagnes")

        if self.getPowerStatus().lower() == "off":
            self.resetPower("on")
        else:
            self.resetPower("force-reset")
         
    def getLogicalDriveFromDisk(self, logicalDriveList, phydrive):
        lgDrive = [x for x in logicalDriveList if phydrive in x["DataDrives"]]

        return lgDrive

def exit(code=0):
    sys.exit(code)


################################ PARSING COMMAND LINES ####################################

parser = argparse.ArgumentParser(prog="Hpe Redfish Utility", description="Utility to perform operations HPE iLO")

exclusiveParser = parser.add_mutually_exclusive_group(required=True)
exclusiveParser.add_argument("--create-lv", action='store_true', help="Create logical volume")
exclusiveParser.add_argument("--delete-lv", action='store_true', help="Delete Logical Volume")
exclusiveParser.add_argument('-lv', "--show-lv", action='store_true', help="Show logical Volume")
exclusiveParser.add_argument('-pv', "--show-pv", action='store_true', help="Show physical Volume")

exclusiveParser.add_argument('-s', "--status", action='store_true', help="Show power status of server")
exclusiveParser.add_argument('-r', "--reset", choices=['on', 'off', 'force-reset'], help="Reset the power option")
exclusiveParser.add_argument("--show-boot", action='store_true', help="Show Boot Order"")

myargs = parser.parse_args()

redfishObj = HpeLogicalVolume()

if myargs.create_lv:
    redfishObj.createLG()
elif myargs.delete_lv:
    redfishObj.deleteLG()
elif myargs.show_lv:
    redfishObj.displayLogicalDrives()
elif myargs.show_pv:
    redfishObj.displayPhysicaldrives()
elif myargs.show_boot:
    redfishObj.displayBootdrives()
elif myargs.status:
    status = redfishObj.getPowerStatus()
    print("\nNode is currently powered {}\n".format(status))
elif myargs.reset:
    redfishObj.resetPower(myargs.reset)
    print("\nSystem power is succssfully resetted to {}\n".format(myargs.reset))
