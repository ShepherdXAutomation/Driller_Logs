import os
import threading
import fitz  # PyMuPDF
import pytesseract
from PIL import Image
from pdf2image import convert_from_path
from tkinter import filedialog, messagebox, Listbox, Scrollbar
import tkinter as tk
from tkinter.ttk import Progressbar, Label, Button, Scale
import numpy as np
import traceback
import shutil

# Default headers, footers, and continuation indicators
DEFAULT_HEADERS = ["Log Service", "Bess Mason", "Zing", "Texas Well", "Woodson Oil", "Zingery", "Survey"]
DEFAULT_FOOTERS = []
CONTINUATION_INDICATORS = []

# Global event to signal cancellation
cancel_event = threading.Event()

def log_overwritten_file(log_file_path, file_path):
    """Log the overwritten file to a log file."""
    with open(log_file_path, 'a') as log_file:
        log_file.write(f"Overwritten: {file_path}\n")

def extract_text_with_ocr(image):
    return pytesseract.image_to_string(image)

def detect_header_and_footer(text, headers, footers):
    has_header = any(header in text for header in headers)
    has_footer = any(footer in text for footer in footers)
    return has_header, has_footer

def is_back_page_continued(pdf_path, continuation_indicators, log):
    images = convert_from_path(pdf_path)
    if not images:
        return False, ""
    
    image = images[0]  # Assume single-page PDF for simplicity
    
    # Try to extract text using PyMuPDF and OCR
    text = ""
    try:
        # Attempt to extract text with PyMuPDF
        doc = fitz.open(pdf_path)
        first_page = doc.load_page(0)
        text = first_page.get_text()
    except Exception as e:
        log.insert(tk.END, f"Error with PyMuPDF text extraction: {e}\n")
    
    if not text.strip():
        # Fallback to OCR if no text was extracted with PyMuPDF
        log.insert(tk.END, f"No text found with PyMuPDF for {pdf_path}, trying OCR...\n")
        text = extract_text_with_ocr(image)
    
    # Output the extracted text to the log for debugging
    log.insert(tk.END, f"Extracted text from {pdf_path}:\n{text}\n{'-'*40}\n")
     
    # Check for continuation indicators
    is_continued = any(indicator in text.lower() for indicator in continuation_indicators)
    return is_continued, text

def process_pdfs(input_dirs, output_dir, headers, footers, continuation_indicators, log, progress):
    cancel_event.clear()  # Clear the cancel event
    total_folders = len(input_dirs)
    progress["maximum"] = total_folders

    for idx, input_folder in enumerate(input_dirs, 1):
        if cancel_event.is_set():
            progress_label.config(text="Operation canceled.")
            break

        # Calculate the relative path and create corresponding output directory
        relative_path = os.path.relpath(input_folder, os.path.commonpath(input_dirs))
        output_subdir = os.path.join(output_dir, relative_path)
        os.makedirs(output_subdir, exist_ok=True)

        # List of all files in the input directory
        all_files = [os.path.join(input_folder, f) for f in os.listdir(input_folder)]
        pdf_files = sorted([f for f in all_files if f.lower().endswith('.pdf')])
        non_pdf_files = [f for f in all_files if not f.lower().endswith('.pdf')]

        # Track files that are part of a merge
        merged_files = set()

        # Process and merge PDFs
        merged_files_count = 0
        
        for i in range(len(pdf_files) - 1):
            front_pdf_path = pdf_files[i]
            back_pdf_path = pdf_files[i + 1]
            
            log.insert(tk.END, f"Processing pair: {front_pdf_path} and {back_pdf_path}\n")
            
            try:
                # Extract text from the front page using OCR only
                text = ""
                try:
                    image = convert_from_path(front_pdf_path)[0]
                    text = extract_text_with_ocr(image)
                except Exception as e:
                    log.insert(tk.END, f"Unexpected error during OCR: {e}\n")
                    log.insert(tk.END, f"Traceback: {traceback.format_exc()}\n")
                    continue
                
                # Check for header on the front page
                has_header, _ = detect_header_and_footer(text.lower(), [header.lower() for header in headers], footers)
                
                # Check if the back page is missing a header
                try:
                    image = convert_from_path(back_pdf_path)[0]
                    back_text = extract_text_with_ocr(image)
                    back_has_header, _ = detect_header_and_footer(back_text.lower(), [header.lower() for header in headers], footers)
                except Exception as e:
                    log.insert(tk.END, f"Unexpected error during OCR: {e}\n")
                    log.insert(tk.END, f"Traceback: {traceback.format_exc()}\n")
                    continue
                
                # Condition: Front page has a header, back page is missing header = match
                if has_header and not back_has_header:
                    # Create the output file path with a "merged" suffix in the correct output subdir
                    base_name = os.path.basename(front_pdf_path)
                    merged_file_path = os.path.join(output_subdir, f'{os.path.splitext(base_name)[0]}_merged.pdf')
                    
                    # Merge the PDFs
                    merger = fitz.open()
                    merger.insert_pdf(fitz.open(front_pdf_path))
                    merger.insert_pdf(fitz.open(back_pdf_path))
                    merger.save(merged_file_path)
                    merger.close()
                    
                    log.insert(tk.END, f"Merged file created: {merged_file_path}\n")
                    merged_files_count += 1

                    # Mark these files as merged
                    merged_files.add(front_pdf_path)
                    merged_files.add(back_pdf_path)
                else:
                    log.insert(tk.END, f"Skipped merging: Front page missing header or back page has a header.\n")

            except Exception as e:
                log.insert(tk.END, f"Failed to process pair {front_pdf_path} and {back_pdf_path}: {e}\n")
                log.insert(tk.END, f"Traceback: {traceback.format_exc()}\n")
                continue

        # Copy **all** original PDF files (including those part of a merge)
        for pdf_file in pdf_files:
            original_dest_path = os.path.join(output_subdir, os.path.basename(pdf_file))
            try:
                shutil.copy(pdf_file, original_dest_path)
                log.insert(tk.END, f"Copied original {os.path.basename(pdf_file)} to {output_subdir}\n")
            except Exception as e:
                log.insert(tk.END, f"Failed to copy original {os.path.basename(pdf_file)} to {output_subdir}: {e}\n")

        # Copy non-PDF files to the output directory
        for file_path in non_pdf_files:
            dest_file_path = os.path.join(output_subdir, os.path.basename(file_path))
            try:
                shutil.copy(file_path, dest_file_path)
                log.insert(tk.END, f"Copied {os.path.basename(file_path)} to {output_subdir}\n")
            except Exception as e:
                log.insert(tk.END, f"Failed to copy {os.path.basename(file_path)} to {output_subdir}: {e}\n")

        if merged_files_count == 0:
            log.insert(tk.END, f"No files were merged in {input_folder}.\n")
        else:
            log.insert(tk.END, f"{merged_files_count} files merged in {input_folder}.\n")

        # Update progress
        progress["value"] = idx
        log.see(tk.END)  # Scroll log to the latest entry
        log.update_idletasks()  # Ensure the GUI updates

    messagebox.showinfo("Completed", f"PDF merging process completed. Processed {total_folders} folders.")





def add_folder():
    folder = filedialog.askdirectory(title="Select Input Directory")
    if folder:
        input_dirs_listbox.insert(tk.END, folder)

def remove_selected_folder():
    selected_indices = input_dirs_listbox.curselection()
    for index in reversed(selected_indices):  # Reverse to avoid issues while deleting
        input_dirs_listbox.delete(index)

def select_folders_with_listbox():
    output_dir = filedialog.askdirectory(title="Select Output Directory")
    
    if not output_dir:
        messagebox.showwarning("Warning", "Please select an output directory.")
        return
    output_dir_label.config(text=f"Output: {output_dir}")  # Update output directory label
    input_dirs = list(input_dirs_listbox.get(0, tk.END))
    
    if not input_dirs:
        messagebox.showwarning("Warning", "No folders selected.")
        return

    threading.Thread(target=process_pdfs, args=(input_dirs, output_dir, DEFAULT_HEADERS, DEFAULT_FOOTERS, CONTINUATION_INDICATORS, log, progress_bar)).start()

def cancel_operation():
    cancel_event.set()  # Signal the cancel event

root = tk.Tk()
root.title("PDF Merge Tool")

frame = tk.Frame(root, padx=20, pady=20)
frame.pack()

output_dir_label = tk.Label(frame, text="Output: None")
output_dir_label.pack(pady=10)

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

remove_folder_btn = tk.Button(frame, text="Remove Selected Folder(s)", command=remove_selected_folder)
remove_folder_btn.pack(pady=5)

process_btn = tk.Button(frame, text="Process Selected Folders", command=select_folders_with_listbox)
process_btn.pack(pady=10)

cancel_btn = tk.Button(frame, text="Cancel", command=cancel_operation)
cancel_btn.pack(pady=10)

# Create a scrolled text widget for logs
log = tk.Text(frame, wrap=tk.WORD, height=10, width=60)
log.pack(pady=10)

progress_bar = Progressbar(frame, length=300, mode='determinate')
progress_bar.pack(pady=10)

root.mainloop()
