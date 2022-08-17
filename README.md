# gve_devnet_cisco_sdwan_device_portal
prototype web app that includes a set of configuration functionalities for Cisco SDWAN devices


## Contacts
* Jorge Banegas

## Solution Components
* SDWAN
* VMANAGE

### Prerequisites
* Cisco SDWAN VMANAGE

## Installation/Configuration

Edit the .env file to include the details to connect to VMANAGE

```python
# Viptela
VMANAGE_HOST=
VMANAGE_PORT=443
VMANAGE_USERNAME=
VMANAGE_PASSWORD=
```

Install python dependencies

```python
pip install -r requirements.txt
```

Run Flask server

```python
python app.py
```

View Web app to see list of SDWAN devices and the menu on the right side for each devices

# Screenshots

![/IMAGES/screenshot.png](/IMAGES/screenshot.png)

![/IMAGES/0image.png](/IMAGES/0image.png)

### LICENSE

Provided under Cisco Sample Code License, for details see [LICENSE](LICENSE.md)

### CODE_OF_CONDUCT

Our code of conduct is available [here](CODE_OF_CONDUCT.md)

### CONTRIBUTING

See our contributing guidelines [here](CONTRIBUTING.md)

#### DISCLAIMER:
<b>Please note:</b> This script is meant for demo purposes only. All tools/ scripts in this repo are released for use "AS IS" without any warranties of any kind, including, but not limited to their installation, use, or performance. Any use of these scripts and tools is at your own risk. There is no guarantee that they have been through thorough testing in a comparable environment and we are not responsible for any damage or data loss incurred with their use.
You are responsible for reviewing and testing any scripts you run thoroughly before use in any non-testing environment.
