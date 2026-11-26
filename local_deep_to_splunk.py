
import json
import requests
import pandas as pd
import urllib3

# Disable SSL warnings (only if required by your corporate proxy)
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


# Function 1: Read XLSM file and convert sheets to JSON
def excel_to_json(file_path):

    # Read all sheets from XLSM file
    excel_data = pd.read_excel(
        file_path,
        engine="openpyxl",
        sheet_name=None
    )

    json_data = {}

    for sheet_name, df in excel_data.items():

        # Handle empty values
        df = df.astype(object).where(pd.notnull(df), None)

        # Convert each sheet into JSON records
        sheet_json = df.to_json(
            orient="records",
            date_format="iso"
        )

        json_data[sheet_name] = json.loads(sheet_json)

        print(
            f"Sheet: {sheet_name} | "
            f"Records: {len(json_data[sheet_name])}"
        )

    return json_data


# Function 2: Index JSON data into Splunk using HEC
def api_call_to_splunk(json_data):

    splunk_url = "https://rb-itoa-splunk-cc-ps.de.bosch.com:8088"  # Replace with your Splunk instance URL
    hec_token = "fa316928-f105-4745-be80-754d193e5322"  # Replace with your Splunk HEC token

    splunk_index = "main"
    splunk_source = "python_script"
    splunk_sourcetype = "_json"

    headers = {
        "Authorization": f"Splunk {hec_token}",
        "Content-Type": "application/json"
    }

    success_count = 0
    failed_count = 0

    for sheet_name, records in json_data.items():

        print(f"\nIndexing Sheet: {sheet_name}")

        for record in records:

            event_data = {
                "event": record,
                "sourcetype": splunk_sourcetype,
                "index": splunk_index,
                "source": splunk_source
            }

            try:
                response = requests.post(
                    f"{splunk_url}/services/collector",
                    headers=headers,
                    data=json.dumps(event_data, default=str),
                    verify=False,
                    timeout=30
                )

                if response.status_code == 200:

                    result = response.json()

                    if result.get("code") == 0:
                        success_count += 1
                    else:
                        failed_count += 1
                        print(f"HEC Error: {result}")

                else:
                    failed_count += 1
                    print(
                        f"HTTP Error: {response.status_code} "
                        f"| {response.text}"
                    )

            except requests.exceptions.RequestException as e:

                failed_count += 1
                print(f"Connection Error: {e}")

        print(f"Completed Sheet: {sheet_name}")

    print("\n========== SPLUNK INDEXING SUMMARY ==========")
    print(f"Total Records : {success_count + failed_count}")
    print(f"Successful    : {success_count}")
    print(f"Failed        : {failed_count}")
    print("=============================================")


# Main Execution
if __name__ == "__main__":

    # Local XLSM file path
    file_path = r"C:\AUV3KOR\Splunk\vmoss\Deep\DEEP_API_data_from_PowerBI.xlsm"

    # Step 1: Convert Excel sheets to JSON
    json_data = excel_to_json(file_path)

    # Step 2: Index JSON records into Splunk
    api_call_to_splunk(json_data)
