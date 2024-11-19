import json
import urllib.parse
import requests
from time import sleep

NATIF_API_BASE_URL = "https://api.natif.ai"
API_KEY = "r5KeXmtDF0Au07Tc3seyRBzrFAH5h2mx"

def process_via_natif_api(file_path, workflow, language, include):
    headers = {
        "Accept": "application/json",
        "Authorization": "ApiKey " + API_KEY
    }
    
    params = {"include": include}
    workflow_config = {"language": language}
    url = f"{NATIF_API_BASE_URL}/processing/{workflow}?{urllib.parse.urlencode(params, doseq=True)}"
    
    with open(file_path, "rb") as file:
        response = requests.post(
            url,
            headers=headers,
            data={"parameters": json.dumps(workflow_config)},
            files={"file": file}
        )
        
    if response.status_code == 202:
        processing_id = response.json()["processing_id"]
        result_url = f"{NATIF_API_BASE_URL}/processing/results/{processing_id}"
        
        while True:
            response = requests.get(
                f"{result_url}?{urllib.parse.urlencode(params, doseq=True)}",
                headers=headers
            )
            
            if response.status_code == 200:
                return response.json()
            sleep(2)
    
    return response.json()

def print_all_extractions(result):
    """Print all extractions including nested fields"""
    extractions = result.get("extractions", {})
    
    print("\n=== Extraction Results ===")
    for field, data in extractions.items():
        print(f"\nField: {field}")
        
        # Handle nested fields (like county.county)
        if isinstance(data, dict) and field in data:
            nested_data = data[field]
            if isinstance(nested_data, dict):
                value = nested_data.get("value", "N/A")
                confidence = nested_data.get("confidence", "N/A")
                print(f"Value: {value}")
                print(f"Confidence: {confidence}")
                
                # Print additional nested info if needed
                validation_problem = nested_data.get("validation_problem", "N/A")
                note = nested_data.get("note", "N/A")
                if validation_problem or note:
                    print(f"Validation Problem: {validation_problem}")
                    if note:
                        print(f"Note: {note}")
        
        # Handle standard fields
        elif isinstance(data, dict) and "value" in data:
            value = data.get("value", "N/A")
            confidence = data.get("confidence", "N/A")
            print(f"Value: {value}")
            print(f"Confidence: {confidence}")
        
        # Handle simple values
        else:
            print(f"Value: {data}")
    
    print("\n========================")

if __name__ == "__main__":
    workflow = "cb19bee2-32f3-47f1-bd0f-4579d337883d"
    file_path = "G:\\MASTER_DIRECTORY\\PALO PINTO_TP RR_BLK 2_SOURCE M G CHENEY_ANZAC PDF MASTER\\PALO PINTO_TP RR_BLK 2_SOURCE M G CHENEY_ANZAC PDF MASTER_75.pdf"
    lang = "de"
    include = ["extractions", "ocr"]
    
    try:
        result = process_via_natif_api(file_path, workflow, lang, include)
        print_all_extractions(result)
        
        # Save full response for reference
        with open('natif_response.json', 'w', encoding='utf-8') as f:
            json.dump(result, f, indent=2, ensure_ascii=False)
            print("\nFull response saved to 'natif_response.json'")
            
    except Exception as e:
        print(f"Error: {str(e)}")