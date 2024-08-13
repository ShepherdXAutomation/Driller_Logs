import fitz  # PyMuPDF
from PIL import Image, ImageTk
import numpy as np
import os
import pandas as pd
import tkinter as tk
from tkinter import filedialog, messagebox, simpledialog
from tkinter.ttk import Progressbar
import json
import urllib.parse
import requests
import sqlite3
import threading
import subprocess

# Global variables for directory selection
input_dir = ""
output_dir = ""

# detect_blank_pages.py functions
def convert_tiff_to_pdf(tiff_file_path, pdf_file_path):
    try:
        tiff_image = Image.open(tiff_file_path)
        if tiff_image.mode != 'RGB':
            tiff_image = tiff_image.convert('RGB')
        tiff_image.save(pdf_file_path, 'PDF', resolution=100.0)
        print(f"Converted {tiff_file_path} to {pdf_file_path}")
    except Exception as e:
        print(f"Failed to convert {tiff_file_path}: {e}")

def convert_all_tiffs_in_directory(input_directory, output_directory, progress_label, progress_bar):
    tiff_files = [f for f in os.listdir(input_directory) if f.lower().endswith('.tif') or f.lower().endswith('.tiff')]
    total_tiff_files = len(tiff_files)
    progress_bar["maximum"] = total_tiff_files

    for idx, filename in enumerate(tiff_files, 1):
        tiff_file_path = os.path.join(input_directory, filename)
        pdf_file_path = os.path.join(output_directory, f"{os.path.splitext(filename)[0]}.pdf")
        convert_tiff_to_pdf(tiff_file_path, pdf_file_path)
        progress_label.config(text=f"Converted {idx}/{total_tiff_files} TIFF files to PDF")
        progress_bar["value"] = idx
        root.update_idletasks()

def is_blank_page_by_pixels(page, dark_threshold=65, black_pixel_threshold=0.01):
    pix = page.get_pixmap()
    img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
    dpi = 72
    inch = dpi
    left_crop = inch
    right_crop = inch
    img_cropped = img.crop((left_crop, 0, img.width - right_crop, img.height))
    gray = img_cropped.convert('L')
    bw = gray.point(lambda p: 0 if p < dark_threshold else 255, '1')
    np_image = np.array(bw)
    black_pixels = np.sum(np_image == 0)
    total_pixels = np_image.size
    return black_pixels < 20

def remove_blank_pages(input_dir, output_dir, progress_label, progress_bar):
    blanks = []
    pdf_files = [f for f in os.listdir(input_dir) if f.lower().endswith('.pdf')]
    total_files = len(pdf_files)
    progress_bar["maximum"] = total_files

    for idx, filename in enumerate(pdf_files, 1):
        input_path = os.path.join(input_dir, filename)
        output_path = os.path.join(output_dir, filename)
        pdf_document = fitz.open(input_path)
        pages_to_remove = []

        for page_number in range(len(pdf_document)):
            if is_blank_page_by_pixels(pdf_document[page_number]):
                pages_to_remove.append(page_number)
                blanks.append(f"{input_path} - Page {page_number + 1}")

        for page_number in reversed(pages_to_remove):
            pdf_document.delete_page(page_number)

        if len(pdf_document) > 0:
            pdf_document.save(output_path)
        pdf_document.close()

        progress_label.config(text=f"Processed {idx}/{total_files} files, {len(blanks)} blank pages found and removed")
        progress_bar["value"] = idx
        root.update_idletasks()
    
    messagebox.showinfo("Complete", "Detection and removal of blank pages completed successfully.")
  

# Driller_Logs_11_28_23.py functions
NATIF_API_BASE_URL = "https://api.natif.ai"
API_KEY = "7G1OxQViCF6KhhAlRHl64p2l8poOCp2s"

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
    return field.get("value") if field else ""

def check_date(date):
    return "19" + date[2:] if date.startswith("20") else date

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
            return float('inf')
    
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
        
        store_in_database(my_well)

        progress_label.config(text=f"Processed {idx}/{total_files} files")
        progress_bar["value"] = idx
        root.update_idletasks()

    messagebox.showinfo("Complete", "Processing completed successfully.")

def start_process_natif():
    directory = select_directory()
    if not directory:
        messagebox.showwarning("Warning", "No directory selected. Exiting.")
        return
    
    thread = threading.Thread(target=process_files, args=(directory, progress_label, progress_bar))
    thread.start()

# management.py functions with threading for progress bar update


    def __init__(self, root):
        self.root = root
class PDFSplitterApp:
    def __init__(self, root):
        self.root = root
        self.pdf_path = None
        self.keywords = None
        self.output_dir = None
        self.manual_mode = None

        # Get user input in the main thread
        self.get_user_input()

        # Run the splitting process in a separate thread
        if self.pdf_path and self.keywords and self.output_dir is not None:
            if self.manual_mode:
                threading.Thread(target=self.manual_mode_split).start()
            else:
                threading.Thread(target=self.run_split_pdf_by_header).start()

    def get_user_input(self):
        # Running all dialogs in the main thread to avoid Tkinter issues
        self.pdf_path = filedialog.askopenfilename(title="Select PDF File", filetypes=[("PDF Files", "*.pdf")])
        if not self.pdf_path:
            return
        self.keywords = simpledialog.askstring("Input", "Enter keywords to split by (comma-separated):")
        if not self.keywords:
            return
        self.output_dir = filedialog.askdirectory(title="Select Output Directory")
        if not self.output_dir:
            return
        self.manual_mode = messagebox.askyesno("Mode", "Would you like to enable manual mode?")

    def run_split_pdf_by_header(self):
        command = ["python", "Split_PDF_by_header.py", self.pdf_path, "--keywords"] + self.keywords.split(',') + ["--output_dir", self.output_dir]
        subprocess.run(command)

    def manual_mode_split(self):
        self.pdf_document = fitz.open(self.pdf_path)

        if not os.path.exists(self.output_dir):
            os.makedirs(self.output_dir)

        self.split_start_page = 0
        self.split_counter = 1
        self.page_num = 0

        self.root.deiconify()  # Show the root window
        self.canvas = tk.Canvas(self.root)
        self.canvas.pack()
        self.show_page()

    def show_page(self):
        page = self.pdf_document.load_page(self.page_num)
        pix = page.get_pixmap()
        img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
        img.thumbnail((800, 600), Image.LANCZOS)

        self.tk_img = ImageTk.PhotoImage(img)
        self.canvas.config(width=img.width, height=img.height)
        self.canvas.create_image(0, 0, anchor=tk.NW, image=self.tk_img)
        
        self.root.update()
        self.ask_split()

    def ask_split(self):
        split = messagebox.askyesno("Split", f"Split after page {self.page_num + 1}?")

        if split:
            self.split_pdf(self.page_num)
        
        self.page_num += 1
        if self.page_num < len(self.pdf_document):
            self.canvas.delete("all")  # Clear the canvas
            self.show_page()
        else:
            if self.split_start_page < len(self.pdf_document):
                self.split_pdf(len(self.pdf_document) - 1)
            self.pdf_document.close()
            print("Manual splitting completed successfully.")
            self.root.quit()

    def split_pdf(self, page_num):
        if page_num >= self.split_start_page:
            split_pdf_path = os.path.join(self.output_dir, f'split_{self.split_counter}.pdf')
            split_doc = fitz.open()
            for split_page_num in range(self.split_start_page, page_num + 1):
                split_doc.insert_pdf(self.pdf_document, from_page=split_page_num, to_page=split_page_num)
            split_doc.save(split_pdf_path)
            split_doc.close()
            self.split_counter += 1
            self.split_start_page = page_num + 1

    def split_pdf(self, page_num):
        if page_num >= self.split_start_page:
            split_pdf_path = os.path.join(self.output_dir, f'split_{self.split_counter}.pdf')
            split_doc = fitz.open()
            for split_page_num in range(self.split_start_page, page_num + 1):
                split_doc.insert_pdf(self.pdf_document, from_page=split_page_num, to_page=split_page_num)
            split_doc.save(split_pdf_path)
            split_doc.close()
            self.split_counter += 1
            self.split_start_page = page_num + 1

def start_pdf_splitter():
    def run_splitter():
        root = tk.Tk()
        app = PDFSplitterApp(root)
        root.mainloop()

    thread = threading.Thread(target=run_splitter)
    thread.start()

# Directory Selection
def select_directory():
    global input_dir, output_dir
    input_dir = filedialog.askdirectory(title="Select Input Directory")
    output_dir = filedialog.askdirectory(title="Select Output Directory")

    if input_dir and output_dir:
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)

        total_tiff_files = len([f for f in os.listdir(input_dir) if f.lower().endswith('.tif') or f.lower().endswith('.tiff')])
        total_pdf_files = len([f for f in os.listdir(input_dir) if f.lower().endswith('.pdf')])
        progress_label.config(text=f"Total TIFF files: {total_tiff_files}, Total PDF files: {total_pdf_files}")

# Main GUI
root = tk.Tk()
root.title("PDF Utility Suite")

frame = tk.Frame(root, padx=20, pady=20)
frame.pack()

select_btn = tk.Button(frame, text="Select Directories", command=select_directory)
select_btn.pack(pady=10)

convert_btn = tk.Button(frame, text="Convert TIFFs to PDFs", command=lambda: convert_all_tiffs_in_directory(input_dir, output_dir, progress_label, progress_bar))
convert_btn.pack(pady=10)

remove_blanks_btn = tk.Button(frame, text="Remove Blank Pages from PDFs", command=lambda: remove_blank_pages(input_dir, output_dir, progress_label, progress_bar))
remove_blanks_btn.pack(pady=10)

natif_btn = tk.Button(frame, text="Process Files via Natif API", command=start_process_natif)
natif_btn.pack(pady=10)

split_pdf_btn = tk.Button(frame, text="Split PDF by Headers (Manual/Auto)", command=start_pdf_splitter)
split_pdf_btn.pack(pady=10)

progress_label = tk.Label(frame, text="Ready")
progress_label.pack(pady=10)

progress_bar = Progressbar(frame, length=300, mode='determinate')
progress_bar.pack(pady=10)

root.mainloop()
