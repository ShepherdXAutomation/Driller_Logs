import json
import urllib.parse
import openpyxl
import requests
import os
# CREAT DRILLER LOG OBJECT VIA CLASS
NATIF_API_BASE_URL = "https://api.natif.ai"
API_KEY = ""  # TODO: Insert or load your API-key secret here

class Well:
    def __init__(self, file_name, log_service, company, county, farm, commenced_date, completed_date, total_depth, initial_production, location, well_number, elevation, hyperlink):
        self.file_name = file_name
        self.log_service = log_service
        self.company = company
        self.county = county
        self.farm = farm
        self.commenced_date = commenced_date
        self.completed_date = completed_date
        self.total_depth = total_depth
        self.initial_production = initial_production
        self.location = location
        self.well_number = well_number
        self.elevation = elevation
        self.hyperlink = hyperlink
def extract(field, result):
    name = field
    field = result.get("extractions", {}).get(field, {})
    if field is not None:
        return field.get("value")
    else:
        return ""
def check_date(date):
    input_string = date
    # Check if the string starts with '20'
    if input_string.startswith("20"):
    # Replace '20' with '19'
        modified_string = "19" + input_string[2:]
        return modified_string
    else:
        return date
def process_via_natif_api(file_path, workflow, language, include):
    # Encapsulates HTTP calls to the natif.ai processing API
    headers = {"Accept": "application/json", "Authorization": "ApiKey " + API_KEY}
    params = {"include": include}
    workflow_config = {"language": language}
    url = f"{NATIF_API_BASE_URL}/processing/{workflow}?{urllib.parse.urlencode(params, doseq=True)}"
    with open(file_path, "rb") as file:
        response = requests.post(
            url,
            headers=headers,
            data={"parameters": json.dumps(workflow_config)},
            files={"file": file},
        )
        if not response.ok:
            raise Exception(response.text)
        while response.status_code == 202:
            processing_id = response.json()["processing_id"]
            RESULT_URI = f"${NATIF_API_BASE_URL}/processing/results/{processing_id}?{params}"
            url = RESULT_URI.format(
                processing_id=processing_id, params=urllib.parse.urlencode(params)
            )
            response = requests.get(url, headers=headers)
        return response.json()
def loop():
    directory = "./logs/"
    # Loop through files in the directory
    pdf_files = [file for file in os.listdir(directory) if file.endswith(".pdf")]
    pdf_files_sorted = sorted(pdf_files, key=lambda x: int(x.split('_Part')[1].split('.')[0]))
    
    for filename in pdf_files_sorted:
        file_path = os.path.join(directory, filename)  # Get the full file path
        print(file_path)
        relative_path = f"./logs/{filename}"  # Create the relative path
        workflow = "912286fc-dae2-4e29-95a2-e04563a2d667"
        print(file_path)
        lang = "de"
        include = ["extractions","ocr"]
        result = process_via_natif_api(file_path, workflow, lang, include)
        build_hyperlink = f'=HYPERLINK("./logs/{filename}", "{filename}")'
        print(build_hyperlink)
        my_well = Well( file_path, log_service=extract("log_service", result), company=extract('company', result), county=extract('county',result), farm=extract('farm', result), commenced_date=extract('commenced', result), completed_date=extract('completed', result), total_depth=extract('total_depth', result), initial_production=extract("intitial_procution",result), location=extract('location', result), well_number=extract('well_number', result), elevation=extract('elevation', result), hyperlink=build_hyperlink)
        # NEED THIS CODE BECAUSE IT NATIF.AI RETURNS 19** AS 20**. BASICALLY, FOR SOME REASON IT ADDS 100 YEARS. SO WE HAVE TO CHECK FOR THAT ON THE JSON RESPONSE AND ACCOUNT FOR IT.
        my_well.commenced_date = check_date(my_well.commenced_date)
        my_well.completed_date = check_date(my_well.completed_date)
        # Load the workbook
        workbook = openpyxl.load_workbook('my_workbook.xlsx')
        # Select the worksheet
        worksheet = workbook.active
        # Append the object as a single row
        row = [my_well.log_service, my_well.company, my_well.county, my_well.farm, my_well.commenced_date, my_well.completed_date, my_well.total_depth, my_well.initial_production, my_well.location, my_well.well_number, my_well.elevation, my_well.hyperlink]
        worksheet.append(row)
        # Save the workbook
        workbook.save('my_workbook.xlsx')

if __name__ == "__main__":
  loop()  



# PULL THE LOG SERVICE
# PULL COMPANY
# PULL COUNTY
# PULL FARM
# PULL COMMENCED
# PULL COMPLETED
# PULL TOTAL_DEPTH
# PULL INITIAL_PRODUCTION
# PULL LOCATION
# PULL WELL_NUMBER
# PULL ELEVATION
# EXPORT EACH OBJECT TO A ROW IN A CSV 
