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
    
    # vManage edit feature template input
    def edit_feature_template(self, template_id, device_id_list,template_config):
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
                "device": json.dumps(template_input_variables),
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
    def change_certificate(self, chasis_number, serial_number,validity):
        headers = {
            "Content-Type": "application/json"
        }
        payload = [{
            "chasisNumber": chasis_number,
            "serialNumber": serial_number,
            "validity": validity
        }]
        response = self.session.post(f"{self.base_url}/dataservice/certificate/save/vedge/list", headers=headers, data=json.dumps(payload), verify=False)
        response = json.loads(response.text)
        return response

    # vManage sync controllers
    def sync_controllers(self):
        response = self.session.post(f"{self.base_url}/dataservice/certificate/vedge/list", verify=False)
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
            code =  request.form.get("code")

            deviceId = request.form.get("editEntry")

            try:
                action_string = "action" + "_" + deviceId
                action = request.form.get(action_string)
            except:
                pass

            code =  request.form.get("code")
            if code == "detach":
                action = request.form.get("action")
            if action == 'deviceDetail':

                for device in device_list:
                    if device['uuid'] == deviceId:
                        deviceToEdit = device

                deviceToEdit.pop("templateApplyLog", None)
                deviceToEdit.pop("vedgeCSR", None)
                return render_template('device_details.html', hiddenLinks=False,  devices = [deviceToEdit],device = deviceToEdit, timeAndLocation=getSystemTimeAndLocation()) 
            if action == 'editDeviceVars':
                device_templates = vManage(auth).get_device_templates()
                
                for device in device_list:
                    if device['uuid'] == deviceId:
                        deviceToEdit = device

                try:
                    template_id = deviceToEdit['templateId']
                except:
                    device_list = vManage(auth).get_device_list()
                    return render_template('devicetablemenu.html', hiddenLinks=False, devices = device_list, error=True, errormessage="No template attached to this device",timeAndLocation=getSystemTimeAndLocation())
                for template in device_templates:
                    if template['templateId'] == template_id:
                        template_id = template['templateId']
                        template_name = template['templateName']
                        


                device_id_list = [deviceToEdit['uuid']]

                template_input_sets = vManage(auth).get_template_input(template_id, device_id_list)

                '''
                for template_input_set in template_input_sets:
                    template_input_set.pop("csv-status", None)
                    template_input_set.pop("csv-deviceId", None)
                    template_input_set.pop("csv-deviceIP", None)
                    template_input_set.pop("csv-host-name", None)
                '''
                    
                return render_template('devicetemplatevars.html', hiddenLinks=False,  device = deviceToEdit,template_id=template_id,device_template_config=template_input_sets,template_name=template_name,timeAndLocation=getSystemTimeAndLocation())
            if action == 'detachTemplate':
                code =  request.form.get("code")
                if code == "detach":
                        device_hostname = request.form.get("hostname")
                        device_list = vManage(auth).get_device_list()
                        device_details = next(device for device in device_list if "host-name" in device and device["host-name"] == device_hostname)
                        vManage(auth).detach_template(device_details["deviceType"], device_details["uuid"], device_details["deviceIP"])
                
                device_list = vManage(auth).get_device_list()
                for device in device_list:
                    if device['uuid'] == deviceId:
                        deviceToEdit = device
                try:
                    template_name = deviceToEdit['template']
                except:
                    template_name = 'No template attached'
                    device_list = vManage(auth).get_device_list()
                    return render_template('devicetablemenu.html', hiddenLinks=False, devices = device_list, error=True, errormessage="No template attached to this device",timeAndLocation=getSystemTimeAndLocation())
                
                try: 
                    template_status = deviceToEdit['templateStatus']
                except:
                    template_status = 'N/A'
                    device_list = vManage(auth).get_device_list()
                    return render_template('devicetablemenu.html', hiddenLinks=False, error=True,template_name=template_name,errormessage="No template attached to this device",template_status=template_status, device = deviceToEdit, timeAndLocation=getSystemTimeAndLocation())   

                return render_template('devicedetach.html', hiddenLinks=False, template_name=template_name, template_status=template_status, device = deviceToEdit, timeAndLocation=getSystemTimeAndLocation())   
            if action == 'changeValidity':
                for device in device_list:
                    if device['uuid'] == deviceId:
                        deviceToEdit = device
                
                validity = deviceToEdit['validity']
                return render_template('devicevalidity.html', hiddenLinks=False,  validity=validity, device = deviceToEdit, timeAndLocation=getSystemTimeAndLocation())   


    except Exception as e: 
        print(e)  
        #OR the following to show error message 
        return render_template('devicetablemenu.html', error=True, devices = devices, errormessage="CUSTOMIZE: Add custom message here.", errorcode=e, timeAndLocation=getSystemTimeAndLocation())

@app.route('/validity', methods=['POST'])
def validity():
    validity = request.form.get("editEntry")

    auth = vManage(None).authentication()
    device_list = vManage(auth).get_device_list()

    deviceToEdit = {}

    deviceId = request.form.get("device_id")

    for device in device_list:
                    if device['uuid'] == deviceId:
                        deviceToEdit = device

    resp = vManage(auth).change_certificate(chasis_number=deviceToEdit['chasisNumber'],serial_number=deviceToEdit['serialNumber'],validity=validity)

    device_list = vManage(auth).get_device_list()

    deviceToEdit = {}

    deviceId = request.form.get("device_id")

    for device in device_list:
                    if device['uuid'] == deviceId:
                        deviceToEdit = device

    return render_template('devicevalidity.html', hiddenLinks=False,  validity=validity, device = deviceToEdit, timeAndLocation=getSystemTimeAndLocation())   

@app.route('/template', methods=['POST'])
def template():

    code =  request.form.get("code")

    if code == "edit":
        temp_id =  request.form.get("temp_id")
        device_id =  request.form.get("device_id")   
        keys = request.form.getlist("key")
        values = request.form.getlist("value")

        template_config = {}

        for key,value in zip(keys,values):
            template_config[key] = str(value)


        payload = {
                "deviceTemplateList": [
                    {
                    "templateId": temp_id,
                    "device": [template_config],
                    "isEdited": False,
                    "isMasterEdited": False,
                    "isDraftDisabled": False
                    }
                ]
            }

        auth = vManage(None).authentication()
        vManage(auth).attach_template(temp_id, template_config)
        deviceId = device_id

    auth = vManage(None).authentication()
    #device_templates = vManage(auth).get_device_templates()
    device_list = vManage(auth).get_device_list()

    deviceToEdit = {}
    device_templates = vManage(auth).get_device_templates()

    deviceId = request.form.get("editEntry")

    for device in device_list:
        if device['uuid'] == deviceId:
            deviceToEdit = device

    for template in device_templates:
        if template['templateId'] == deviceToEdit['templateId']:
            template_id = template['templateId']
            template_name = template['templateName']


    device_id_list = [deviceToEdit['uuid']]

    template_input_sets = vManage(auth).get_template_input(template_id, device_id_list)

    '''    
    for template_input_set in template_input_sets:
        template_input_set.pop("csv-status", None)
        template_input_set.pop("csv-deviceId", None)
        template_input_set.pop("csv-deviceIP", None)
        template_input_set.pop("csv-host-name", None)
    '''

    return render_template('devicetemplatevars.html', hiddenLinks=False,  device = deviceToEdit,device_template_config=template_input_sets,template_name=template_name,timeAndLocation=getSystemTimeAndLocation())

if __name__ == "__main__":
    app.run(host='0.0.0.0', debug=True)