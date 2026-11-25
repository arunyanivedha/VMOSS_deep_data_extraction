import io
import json
import requests
import pandas as pd
import ssl
import urllib3
from office365.sharepoint.client_context import ClientContext
from office365.runtime.auth.user_credential import UserCredential
from office365.sharepoint.files.file import File

# Disable SSL warnings and verification for corporate proxy
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
ssl._create_default_https_context = ssl._create_unverified_context

# Monkey-patch requests to disable SSL verification globally for this session
original_request = requests.Session.request
def patched_request(self, *args, **kwargs):
    kwargs['verify'] = False
    return original_request(self, *args, **kwargs)
requests.Session.request = patched_request

# Function to download file from SharePoint
def download_file_from_sharepoint(sharepoint_url, file_relative_url, username, password):
    context = ClientContext(sharepoint_url).with_credentials(
        UserCredential(username, password))
    file = context.web.get_file_by_server_relative_url(file_relative_url)
    context.load(file)
    context.execute_query() 
    
    # Read the file content into memory
    file_content = file.read()
    file_stream = io.BytesIO(file_content)

    # Use pandas to read the Excel file
    global sharepoint_file 
    sharepoint_file = pd.read_excel(file_stream, engine='openpyxl', sheet_name=None)
    
    for sheet in sharepoint_file:
        # Convert the pandas DataFrame to JSON format
        sharepoint_sheet = sharepoint_file[sheet].to_json(orient='records', date_format='iso')
        sharepoint_sheet = json.loads(sharepoint_sheet)


        # Copy the file to the remote server
        api_call_to_splunk(sharepoint_sheet)

    


def api_call_to_splunk(sharepoint_file):
    splunk_url = "https://rb-itoa-splunk-cc-ps.de.bosch.com:8088"  # Replace with your Splunk instance URL
    hec_token = "fa316928-f105-4745-be80-754d193e5322"  # Replace with your Splunk HEC token
    splunk_index = "main"  # Target index in Splunk
    splunk_source = "python_script"
    splunk_sourcetype = "_json"
 
    # Headers
    headers = {
        "Authorization": f"Splunk {hec_token}",
        "Content-Type": "application/json"
    }
 

    # Event Data
    event_data = {
    "event": sharepoint_file,
    "sourcetype": splunk_sourcetype,
    "index": splunk_index,
    "source": splunk_source
}
 
    # Send Data to Splunk HEC
    response = requests.post(f"{splunk_url}/services/collector", headers=headers, data=json.dumps(event_data), verify=True)
    
    # Print Response
    print(f"Response Code: {response.status_code}")
    print(f"Response Text: {response.text}")

# SharePoint details
sharepoint_url = "https://bosch.sharepoint.com/sites/msteams_1e27b471/"
file_relative_url = "/sites/msteams_1e27b471/Shared Documents/DEEP/DEEP_API_data_from_PowerBI.xlsm"
username = "BWC1KOR@bosch.com"
password = "Ganesh1996?9"


# Download file from SharePoint
download_file_from_sharepoint(sharepoint_url, file_relative_url, username, password)
