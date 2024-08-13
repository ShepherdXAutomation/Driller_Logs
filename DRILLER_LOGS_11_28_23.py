import json
import urllib.parse
import requests
import os
import sqlite3
import tkinter as tk
from tkinter import filedialog, messagebox
from tkinter.ttk import Progressbar
import threading

#Take in input directory, move them to output directory and ensure they have a unique name, upload them to natif, then take the response and store it to SQLite

NATIF_API_BASE_URL = "https://api.natif.ai"
API_KEY = "7G1OxQViCF6KhhAlRHl64p2l8poOCp2s"  # TODO: Insert or load your API-key secret here

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
    field = result.get("extractions", {}).get(field, {})
    if field is not None:
        return field.get("value")
    else:
        return ""

def check_date(date):
    input_string = date
    if input_string.startswith("20"):
        modified_string = "19" + input_string[2:]
        return modified_string
    else:
        return date

def process_via_natif_api(file_path, workflow, language, include):
    headers = {"Accept": "application/json", "Authorization": f"ApiKey {API_KEY}"}
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
            RESULT_URI = f"{NATIF_API_BASE_URL}/processing/results/{processing_id}?{urllib.parse.urlencode(params)}"
            response = requests.get(RESULT_URI, headers=headers)
        return response.json()

def select_directory():
    directory = filedialog.askdirectory(title="Select Directory")
    return directory

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
            hyperlink TEXT
        )
    ''')
    cursor.execute('''
        INSERT INTO wells (file_name, log_service, company, county, farm, commenced_date, completed_date, total_depth, initial_production, location, well_number, elevation, hyperlink)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', (well.file_name, well.log_service, well.company, well.county, well.farm, well.commenced_date, well.completed_date, well.total_depth, well.initial_production, well.location, well.well_number, well.elevation, well.hyperlink))
    conn.commit()
    conn.close()

def process_files(directory, progress_label, progress_bar):
    pdf_files = [file for file in os.listdir(directory) if file.endswith(".pdf")]
    
    def extract_part_number(filename):
        try:
            return int(filename.split('_')[1])
        except (IndexError, ValueError):
            return float('inf')  # Place files without '_<number>' at the end
    
    pdf_files_sorted = sorted(pdf_files, key=extract_part_number)
    total_files = len(pdf_files_sorted)
    progress_bar["maximum"] = total_files

    for idx, filename in enumerate(pdf_files_sorted, 1):
        file_path = os.path.join(directory, filename)
        workflow = "912286fc-dae2-4e29-95a2-e04563a2d667"
        lang = "de"
        include = ["extractions", "ocr"]
        result = process_via_natif_api(file_path, workflow, lang, include)
        build_hyperlink = f'=HYPERLINK("{file_path}", "{filename}")'
        
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
            hyperlink=build_hyperlink
        )
        my_well.commenced_date = check_date(my_well.commenced_date)
        my_well.completed_date = check_date(my_well.completed_date)
        
        # Store in the SQL database
        store_in_database(my_well)

        progress_label.config(text=f"Processed {idx}/{total_files} files")
        progress_bar["value"] = idx
        root.update_idletasks()

    messagebox.showinfo("Complete", "Processing completed successfully.")

def start_process():
    directory = select_directory()
    if not directory:
        messagebox.showwarning("Warning", "No directory selected. Exiting.")
        return
    
    thread = threading.Thread(target=process_files, args=(directory, progress_label, progress_bar))
    thread.start()

root = tk.Tk()
root.title("Natif API PDF Processor")

frame = tk.Frame(root, padx=20, pady=20)
frame.pack()

run_btn = tk.Button(frame, text="Run", command=start_process)
run_btn.pack(pady=10)

progress_label = tk.Label(frame, text="Select directories to start.")
progress_label.pack(pady=10)

progress_bar = Progressbar(frame, length=300, mode='determinate')
progress_bar.pack(pady=10)

root.mainloop()
