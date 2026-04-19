import json
import urllib.parse
import requests
import os
import sqlite3
import tkinter as tk
from tkinter import filedialog, messagebox, Listbox, Scrollbar
from tkinter.ttk import Progressbar
import threading
import time

# Natif API constants
NATIF_API_BASE_URL = "https://api.natif.ai"
API_KEY = "r5KeXmtDF0Au07Tc3seyRBzrFAH5h2mx"  # TODO: Insert your API key here

class Well:
    def __init__(self, file_name, log_service, company, county, farm, commenced_date, completed_date, total_depth, initial_production, location, well_number, elevation, hyperlink, materials=None):
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
        self.materials = materials or []

def extract(field, result):
    """Extract field value handling nested structures like county.county"""
    extractions = result.get("extractions", {})
    field_data = extractions.get(field, {})
    
    # Handle nested structure (e.g., county.county)
    if isinstance(field_data, dict) and field in field_data:
        nested_data = field_data[field]
        if isinstance(nested_data, dict):
            return nested_data.get("value")
    
    # Handle standard structure
    elif isinstance(field_data, dict):
        return field_data.get("value")
    
    # Handle simple values
    elif field_data is not None:
        return field_data
    
    return ""

def check_date(date):
    if date is None or not isinstance(date, str):
        return ""  # Return an empty string or a default value if date is None or not a string
    
    input_string = date.strip()  # Ensure there are no leading or trailing spaces
    if input_string.startswith("20"):
        modified_string = "19" + input_string[2:]
        return modified_string
    else:
        return date


# Updated process_via_natif_api function with retry logic and result retrieval
def process_via_natif_api(file_path, workflow_id, language, include):
    headers = {"Accept": "application/json", "Authorization": f"ApiKey {API_KEY}"}
    params = {"include": include}
    workflow_config = {"language": language}
    url = f"{NATIF_API_BASE_URL}/processing/{workflow_id}?{urllib.parse.urlencode(params, doseq=True)}"

    # Submit the file for processing
    with open(file_path, "rb") as file:
        response = requests.post(
            url,
            headers=headers,
            data={"parameters": json.dumps(workflow_config)},
            files={"file": file},
        )
        if not response.ok:
            raise Exception(f"Error submitting file: {response.text}")

    # Extract processing_id from the response
    processing_id = response.json().get("processing_id")
    if not processing_id:
        raise Exception("No processing_id returned by the API.")

    print(f"File submitted successfully. Processing ID: {processing_id}")

    # Retry logic for long-running workflows
    while response.status_code == 202:
        print("Processing in progress. Retrying...")
        time.sleep(5)  # Wait before retrying
        result_url = f"{NATIF_API_BASE_URL}/processing/results/{processing_id}"
        response = requests.get(result_url, headers=headers)

    # Final result retrieval
    if response.ok:
        return response.json()
    else:
        raise Exception(f"Error retrieving results: {response.text}")

def add_folder():
    folder = filedialog.askdirectory(title="Select Input Directory")
    if folder:
        input_dirs_listbox.insert(tk.END, folder)

def remove_selected_folder():
    selected_indices = input_dirs_listbox.curselection()
    for index in reversed(selected_indices):
        input_dirs_listbox.delete(index)

def store_in_database(well):
    conn = sqlite3.connect('well_data.db')
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS wells (
            file_name TEXT,
            log_service TEXT,
            company TEXT,
            county TEXT,
            farm TEXT,
            commenced_date TEXT,
            completed_date TEXT,
            total_depth TEXT,
            initial_production TEXT,
            location TEXT,
            well_number TEXT,
            elevation TEXT,
            hyperlink TEXT,
            materials TEXT
        )
    ''')
    cursor.execute('''
        INSERT INTO wells (file_name, log_service, company, county, farm, commenced_date, completed_date, total_depth, initial_production, location, well_number, elevation, hyperlink, materials)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', (well.file_name, well.log_service, well.company, well.county, well.farm, well.commenced_date, well.completed_date, well.total_depth, well.initial_production, well.location, well.well_number, well.elevation, well.hyperlink, json.dumps(well.materials, indent=4)))
    conn.commit()
    conn.close()

def process_files(input_dirs, progress_label, progress_bar, current_file_label):
    total_files = sum(len([file for file in os.listdir(folder) if file.endswith(".pdf")]) for folder in input_dirs)
    progress_bar["maximum"] = total_files
    processed_files = 0

    for folder in input_dirs:
        pdf_files = [file for file in os.listdir(folder) if file.endswith(".pdf")]
        
        for idx, filename in enumerate(pdf_files, 1):
            file_path = os.path.join(folder, filename)
            workflow = "0f89941a-f867-4444-a981-b571fd98467d"
            lang = "de"
            include = ["extractions", "ocr"]

            # Update the current file label
            current_file_label.config(text=f"Processing: {filename}")
            
            result = process_via_natif_api(file_path, workflow, lang, include)
            
            # Print the API response result to the command line
            print(f"API response for {filename}: {json.dumps(result, indent=4)}")
            # Debug: show extracted materials from the result
            extracted_materials = extract("materials", result)
            print(f"Extracted materials for {filename}: {extracted_materials!r}")
            
            build_hyperlink = f'=HYPERLINK("{file_path}", "{filename}")'
            
            materials = extract("materials", result) or []
            my_well = Well(
                file_path,
                log_service=extract("log_service", result),
                company=extract('company', result),
                county=extract('county', result),
                farm=extract('farm', result),
                commenced_date=extract('commenced', result),
                completed_date=extract('completed', result),
                total_depth=extract('total_depth', result),
                initial_production=extract("initial_production", result),
                location=extract('location', result),
                well_number=extract('well_number', result),
                elevation=extract('elevation', result),
                hyperlink=build_hyperlink,
                materials=materials
            )
            my_well.commenced_date = check_date(my_well.commenced_date)
            my_well.completed_date = check_date(my_well.completed_date)
            
            # Store in the SQL database
            store_in_database(my_well)

            # Make the well available to the GUI and update the results listbox
            processed_wells.append(my_well)
            root.after(0, lambda mw=my_well: add_result_to_listbox(mw))

            processed_files += 1
            progress_label.config(text=f"Processed {processed_files}/{total_files} files")
            progress_bar["value"] = processed_files

def start_process():
    input_dirs = list(input_dirs_listbox.get(0, tk.END))
    if not input_dirs:
        messagebox.showwarning("Warning", "No directories selected. Exiting.")
        return
    
    thread = threading.Thread(target=process_files, args=(input_dirs, progress_label, progress_bar, current_file_label))
    thread.start()

# Function to add all child folders in the selected directory
def add_child_folders():
                # Debug: print materials being stored
                try:
                    print(f"Inserting to DB — file: {well.file_name}, materials: {well.materials!r}")
                except Exception:
                    print("Inserting to DB — file: (unable to print file name or materials)")

                cursor.execute('''
                    INSERT INTO wells (file_name, log_service, company, county, farm, commenced_date, completed_date, total_depth, initial_production, location, well_number, elevation, hyperlink, materials)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (well.file_name, well.log_service, well.company, well.county, well.farm, well.commenced_date, well.completed_date, well.total_depth, well.initial_production, well.location, well.well_number, well.elevation, well.hyperlink, json.dumps(well.materials, indent=4)))
                folder_path = os.path.join(root_dir, dir_name)
                input_dirs_listbox.insert(tk.END, folder_path)

# GUI Setup
root = tk.Tk()
root.title("Natif API PDF Processor")

frame = tk.Frame(root, padx=20, pady=20)
frame.pack()

# Listbox to display selected folders
listbox_frame = tk.Frame(frame)
listbox_frame.pack(pady=5, fill=tk.BOTH, expand=True)

input_dirs_listbox = Listbox(listbox_frame, selectmode=tk.MULTIPLE, width=60, height=10)
input_dirs_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

scrollbar = Scrollbar(listbox_frame, orient=tk.VERTICAL)
scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
input_dirs_listbox.config(yscrollcommand=scrollbar.set)
scrollbar.config(command=input_dirs_listbox.yview)

# Buttons to add or remove folders
add_folder_btn = tk.Button(frame, text="Add Folder", command=add_folder)
add_folder_btn.pack(pady=5)

add_child_folders_btn = tk.Button(frame, text="Add All Child Folders", command=add_child_folders)
add_child_folders_btn.pack(pady=5)

remove_folder_btn = tk.Button(frame, text="Remove Selected Folder(s)", command=remove_selected_folder)
remove_folder_btn.pack(pady=5)

# Run button to start the process
run_btn = tk.Button(frame, text="Run", command=start_process)
run_btn.pack(pady=10)

progress_label = tk.Label(frame, text="Select directories to start.")
progress_label.pack(pady=10)

progress_bar = Progressbar(frame, length=300, mode='determinate')
progress_bar.pack(pady=10)

# Label to display the current file being processed
current_file_label = tk.Label(frame, text="Current file: None")
current_file_label.pack(pady=10)

# In-memory list of processed wells for lookup from the GUI
processed_wells = []

# Results listbox to show processed files and allow opening materials popup
results_frame = tk.Frame(frame)
results_frame.pack(pady=5, fill=tk.BOTH, expand=True)

results_listbox = Listbox(results_frame, width=80, height=8)
results_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

results_scroll = Scrollbar(results_frame, orient=tk.VERTICAL)
results_scroll.pack(side=tk.RIGHT, fill=tk.Y)
results_listbox.config(yscrollcommand=results_scroll.set)
results_scroll.config(command=results_listbox.yview)

def add_result_to_listbox(well):
    display = f"{os.path.basename(well.file_name)}  —  {well.company or ''}  —  {well.log_service or ''}"
    results_listbox.insert(tk.END, display)

def on_result_double_click(event):
    sel = results_listbox.curselection()
    if not sel:
        return
    idx = sel[0]
    well = processed_wells[idx]
    show_materials_popup(well.materials)

results_listbox.bind("<Double-1>", on_result_double_click)

# Function to display materials in a pop-up window
def show_materials_popup(materials):
    popup = tk.Toplevel()
    popup.title("Materials Found")

    materials_label = tk.Label(popup, text="Materials Found:", font=("Arial", 14))
    materials_label.pack(pady=10)

    materials_listbox = Listbox(popup, width=50, height=15)
    materials_listbox.pack(pady=10)

    for material in materials:
        materials_listbox.insert(tk.END, material)

    close_button = tk.Button(popup, text="Close", command=popup.destroy)
    close_button.pack(pady=10)

root.mainloop()
