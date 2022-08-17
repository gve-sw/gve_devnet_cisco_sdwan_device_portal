""" Copyright (c) 2022 Cisco and/or its affiliates.
This software is licensed to you under the terms of the Cisco Sample
Code License, Version 1.1 (the "License"). You may obtain a copy of the
License at
           https://developer.cisco.com/docs/licenses
All use of the material herein must be in accordance with the terms of
the License. All rights not expressly granted by the License are
reserved. Unless required by applicable law or agreed to separately in
writing, software distributed under the License is distributed on an "AS
IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express
or implied. 
"""

# Import Section
from flask import Flask, render_template, request, url_for, redirect
from collections import defaultdict
import datetime
import requests
import json
from dotenv import load_dotenv
#import merakiAPI
from dnacentersdk import api
import os, json, requests, urllib3, openpyxl, time
import pandas as pd
from dotenv import load_dotenv

# load all environment variables
load_dotenv()
vmanage_host = os.getenv("VMANAGE_HOST")
vmanage_port = os.getenv("VMANAGE_PORT")
vmanage_username = os.getenv("VMANAGE_USERNAME")
vmanage_password = os.getenv("VMANAGE_PASSWORD")


# Global variables
app = Flask(__name__)


# convert a excel sheet to json
def excel_to_json(file, sheet_name):
    excel_df = pd.read_excel(file, sheet_name=sheet_name)
    excel_json = json.loads(excel_df.to_json(orient="records"))
    return excel_json

# load mapping file
def load_mapping(workflow):
    print()
    file = "sandbox.xlsx"

    if workflow == 1:
        mapping = excel_to_json(file, "Commission")
    elif workflow == 3:
        mapping = excel_to_json(file, "RMA")
    elif workflow == 4:
        mapping = excel_to_json(file, "Reclassification")
    return mapping, file

# define a class for vManage object
def write_excel(file, sheet_name, data):
    writer = pd.ExcelWriter(file, engine="openpyxl", mode="a", if_sheet_exists="replace")
    fileb = open(file, "rb")
    writer.book = openpyxl.load_workbook(fileb)
    writer.sheets = dict((ws.title, ws) for ws in writer.book.worksheets)
    df = pd.DataFrame(data)
    df.to_excel(writer, sheet_name=sheet_name, index=False)
    writer.close()

class vManage():
    def __init__(self, session):
        self.base_url = f"https://{vmanage_host}:{vmanage_port}"
        self.username = vmanage_username
        self.password = vmanage_password
        if session == None:
            self.session = requests.Session()
        else:
            self.session = session

    # login with 2 steps: get JSESSIONID and X-XSRF-TOKEN
    def authentication(self):
        # vManage authentication - get JSESSIONID
        headers = {
            "Content-Type": "application/x-www-form-urlencoded"
        }
        payload = {
            "j_username": self.username,
            "j_password": self.password
        }
        jsession = self.session.post(f"{self.base_url}/j_security_check", headers=headers, data=payload, verify=False)

        # vManage authentication - get X-XSRF-TOKEN
        token = self.session.get(f"{self.base_url}/dataservice/client/token")
        self.session.headers["X-XSRF-TOKEN"] = token.text

        return self.session

    # vManage get device templates
    def get_device_templates(self):
        response = self.session.get(f"{self.base_url}/dataservice/template/device", verify=False)
        response = json.loads(response.text)
        return response["data"]

    # vManage get feature templates
    def get_feature_templates(self):
        response = self.session.get(f"{self.base_url}/dataservice/template/feature", verify=False)
        response = json.loads(response.text)
        return response["data"]

    # vManage get device list
    def get_device_list(self, category="vedges"):
        response = self.session.get(f"{self.base_url}/dataservice/system/device/{category}", verify=False)
        response = json.loads(response.text)
        return response["data"]

    # vManage get template config
    def get_template_config(self, template_id):
        response = self.session.get(f"{self.base_url}/dataservice/template/device/object/{template_id}", verify=False)
        response = json.loads(response.text)
        return response

    # vManage get template input variables
    def get_template_input(self, template_id, device_id_list):
        headers = {
            "Content-Type": "application/json"
        }
        payload = {
            "deviceIds": device_id_list,
            "isEdited": False,
            "isMasterEdited": False,
            "templateId": template_id
        }
        response = self.session.post(f"{self.base_url}/dataservice/template/device/config/input", headers=headers, data=json.dumps(payload), verify=False)
        response = json.loads(response.text)
        return response["data"]

    # vManage get devices attached to template
    def get_template_attached_devices(self, template_id):
        headers = {
            "Content-Type": "application/json"
        }
        response = self.session.get(f"{self.base_url}/dataservice/template/device/config/attached/{template_id}", headers=headers, verify=False)
        response = json.loads(response.text)
        return response["data"]

    # vManage add feature template
    def add_feature_template(self, template_config):
        headers = {
            "Content-Type": "application/json"
        }
        response = self.session.post(f"{self.base_url}/dataservice/template/feature", headers=headers, data=json.dumps(template_config), verify=False)
        response = json.loads(response.text)
        return response["templateId"]

    # vManage add feature template
    def add_device_template(self, template_config):
        headers = {
            "Content-Type": "application/json"
        }
        response = self.session.post(f"{self.base_url}/dataservice/template/device/feature", headers=headers, data=json.dumps(template_config), verify=False)
        response = json.loads(response.text)
        return response["templateId"]

    # vManage attach router to template
    def attach_template(self, template_id, template_input_variables):
        headers = {
            "Content-Type": "application/json"
        }
        payload = {
            "deviceTemplateList": [{
                "templateId": template_id,
                "device": template_input_variables,
                "isEdited": False,
                "isMasterEdited": False
            }]
        }
        response = self.session.post(f"{self.base_url}/dataservice/template/device/config/attachfeature", headers=headers, data=json.dumps(payload), verify=False)
        response = json.loads(response.text)
        return response

    # vManage detach router from template
    def detach_template(self, device_type, device_uuid, device_ip):
        headers = {
            "Content-Type": "application/json"
        }
        payload = {
            "deviceType": device_type,
            "devices": [{
                "deviceId": device_uuid,
                "deviceIP": device_ip,
            }]
        }
        response = self.session.post(f"{self.base_url}/dataservice/template/config/device/mode/cli", headers=headers, data=json.dumps(payload), verify=False)
        response = json.loads(response.text)
        return response

    # vManage invalidate router certificate
    def invalidate_certificate(self, chasis_number, serial_number):
        headers = {
            "Content-Type": "application/json"
        }
        payload = [{
            "chasisNumber": chasis_number,
            "serialNumber": serial_number,
            "validity": "invalid"
        }]
        response = self.session.post(f"{self.base_url}/dataservice/certificate/save/vedge/list", headers=headers, data=json.dumps(payload), verify=False)
        response = json.loads(response.text)
        return response

    # vManage sync controllers
    def sync_controllers(self):
        response = self.session.post(f"{self.base_url}/dataservice/certificate/vedge/list", verify=False)
        response = json.loads(response.text)
        return response

    # vManage completely remove router
    def decommission_device(self, device_uuid):
        response = self.session.put(f"{self.base_url}/dataservice/system/device/decommission/{device_uuid}", verify=False)
        response = json.loads(response.text)
        return response

    # vManage completely remove router
    def completely_remove_device(self, device_uuid):
        response = self.session.delete(f"{self.base_url}/dataservice/system/device/{device_uuid}", verify=False)
        response = json.loads(response.text)
        return response

    # vManage track action status
    def track_action_status(self, action_id):
        response = self.session.get(f"{self.base_url}/dataservice/device/action/status/{action_id}", verify=False)
        response = json.loads(response.text)
        return response["summary"]["status"]

@app.route('/upload')
def upload():
    return render_template('upload.html')

@app.route('/progress')
def ajax_index():
    global i
    i+=20
    print(i)
    return str(i)

# Methods
# Returns location and time of accessing device
def getSystemTimeAndLocation():
    # request user ip
    userIPRequest = requests.get('https://get.geojs.io/v1/ip.json')
    userIP = userIPRequest.json()['ip']

    # request geo information based on ip
    geoRequestURL = 'https://get.geojs.io/v1/ip/geo/' + userIP + '.json'
    geoRequest = requests.get(geoRequestURL)
    geoData = geoRequest.json()
    
    #create info string
    location = geoData['country']
    timezone = geoData['timezone']
    current_time=datetime.datetime.now().strftime("%d %b %Y, %I:%M %p")
    timeAndLocation = "System Information: {}, {} (Timezone: {})".format(location, current_time, timezone)
    
    return timeAndLocation

#Read data from json file
def getJson(filepath):
	with open(filepath, 'r') as f:
		json_content = json.loads(f.read())
		f.close()

	return json_content

#Write data to json file
def writeJson(filepath, data):
    with open(filepath, "w") as f:
        json.dump(data, f)
    f.close()


##Routes

#collage
@app.route('/')
def collage():
    try:
        #Page without error message and defined header links 
        return render_template('collage.html', hiddenLinks=False, timeAndLocation=getSystemTimeAndLocation())
    except Exception as e: 
        print(e)  
        #OR the following to show error message 
        return render_template('collage.html', error=False, errormessage="CUSTOMIZE: Add custom message here.", errorcode=e, timeAndLocation=getSystemTimeAndLocation())

#Table with menu
@app.route('/devices', methods=['GET', 'POST'])
def devices():
    try:
        auth = vManage(None).authentication()
        #device_templates = vManage(auth).get_device_templates()
        device_list = vManage(auth).get_device_list()

        #Retrieve devices list from json file
        #devices = getJson("devices.json")
        deviceToEdit = {}
        
        #Show table with all devices
        if request.method == 'GET':
            return render_template('devicetablemenu.html', hiddenLinks=False, devices = device_list, timeAndLocation=getSystemTimeAndLocation())


        #Find device to edit in devices list and render edit page (include device info) 
        if request.method == 'POST':
            action =  request.form.get("action")

            if action == 'deviceDetail':
                index =  request.form.get("index")
                device_string = "editEntry" + str(index)
                deviceId =  request.form.get("deviceId")
            
                for device in device_list:
                    if device['uuid'] == deviceId:
                        deviceToEdit = device

                    del deviceToEdit["templateApplyLog"]
                    del deviceToEdit["vedgeCSR"]
                    del deviceToEdit["activity"]
                    del deviceToEdit["availableVersions"]

                    return render_template('device_details.html', hiddenLinks=False,  devices = [deviceToEdit],device = deviceToEdit, timeAndLocation=getSystemTimeAndLocation()) 
            if action == 'editDeviceVars':
                index =  request.form.get("index")
                device_string = "editEntry" + str(index)
                deviceId =  request.form.get("deviceId")
                device_templates = vManage(auth).get_device_templates()
                
                for device in device_list:
                    if device['uuid'] == deviceId:
                        deviceToEdit = device

                mapping, file = load_mapping(1)
                all_template_input = {}
                for row in mapping:
                    template_name = row["TemplateName"]
                    template_id = next(device_template["templateId"] for device_template in device_templates if device_template["templateName"] == template_name)
                    device_chassis_numbers = row["DeviceChassisNumber"].split(",")
                    device_id_list = [device["uuid"] for device in device_list if device["chasisNumber"] in device_chassis_numbers]
                    template_input_sets = vManage(auth).get_template_input(template_id, device_id_list)
                    
                    for template_input_set in template_input_sets:
                        template_input_set.pop("csv-status", None)
                        template_input_set.pop("csv-deviceId", None)
                        template_input_set.pop("csv-deviceIP", None)
                        template_input_set.pop("csv-host-name", None)
                        write_excel(file, template_name, template_input_sets)
                

                return render_template('devicetemplatevars.html', hiddenLinks=False,  device = deviceToEdit,device_template_config=template_input_sets,template_name=template_name,timeAndLocation=getSystemTimeAndLocation())   
            if action == 'detachTemplate':
                index =  request.form.get("index")
                device_string = "editEntry" + str(index)
                deviceId =  request.form.get("deviceId")
                
                for device in device_list:
                    if device['uuid'] == deviceId:
                        deviceToEdit = device
                
                    return render_template('devicedetach.html', hiddenLinks=False,  device = deviceToEdit, timeAndLocation=getSystemTimeAndLocation())   
            if action == 'changeValidity':
                index =  request.form.get("index")
                device_string = "editEntry" + str(index)
                deviceId =  request.form.get("deviceId")
                
                for device in device_list:
                    if device['uuid'] == deviceId:
                        deviceToEdit = device
                
                    return render_template('devicevalidity.html', hiddenLinks=False,  device = deviceToEdit, timeAndLocation=getSystemTimeAndLocation())   


    except Exception as e: 
        print(e)  
        #OR the following to show error message 
        return render_template('tablemenu.html', error=True, devices = devices, errormessage="CUSTOMIZE: Add custom message here.", errorcode=e, timeAndLocation=getSystemTimeAndLocation())

#Edit page for table entry
@app.route('/editTableEntry', methods=['GET', 'POST'])
def editTableEntry():
    try:
        if request.method == 'POST':
            
            #Retrieve devices list from json file
            devices = getJson("devices.json")

            #Submitted form values:
            deviceId = request.form.get("saveEntry")
            deviceName = request.form.get("deviceName")
            deviceCoverage = request.form.get("radio-inline")
            deviceSoftwareType = request.form.get("deviceSoftwareType")
            deviceSoftwareVersion = request.form.get("deviceSoftwareVersion")
            deviceRole = request.form.get("deviceRole")
       
            #Find device to edit in devices list and change the values according to the submitted user input
            for device in devices:
                if device['id'] == deviceId:
                    device['name'] = deviceName
                    device['coverage'] = deviceCoverage
                    device['softwareType'] = deviceSoftwareType
                    device['softwareVersion'] = deviceSoftwareVersion
                    device['role'] = deviceRole

            #Write updated devices info to json file
            writeJson("devices.json", devices)

            #Redirect to table view
            return redirect(url_for('tablemenu'))

    except Exception as e: 
        print(e)  
        #OR the following to show error message 
        return render_template('editTableEntry.html', error=True, errormessage="CUSTOMIZE: Add custom message here.", errorcode=e, timeAndLocation=getSystemTimeAndLocation())

if __name__ == "__main__":
    app.run(host='0.0.0.0', debug=True)