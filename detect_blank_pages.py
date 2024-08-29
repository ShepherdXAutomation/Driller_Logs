import threading
import shutil
import fitz  # PyMuPDF
from PIL import Image
import numpy as np
import os
import pandas as pd
import tkinter as tk
from tkinter import filedialog, messagebox
from tkinter.ttk import Progressbar, Label, Scale

# Global event to signal cancelation
cancel_event = threading.Event()

# Function to generate a unique file name in the output directory
def generate_unique_filename(output_directory, base_filename, extension):
    counter = 1
    unique_filename = f"{base_filename}{extension}"
    
    while os.path.exists(os.path.join(output_directory, unique_filename)):
        unique_filename = f"{base_filename}_{counter}{extension}"
        counter += 1
        
    return unique_filename

# Convert TIFF to PDF ensuring the file name is unique
def convert_tiff_to_pdf(tiff_file_path, pdf_file_path):
    try:
        # Open the TIFF file
        tiff_image = Image.open(tiff_file_path)

        # Ensure the image is in RGB mode
        if tiff_image.mode != 'RGB':
            tiff_image = tiff_image.convert('RGB')

        # Save the image as a PDF
        tiff_image.save(pdf_file_path, 'PDF', resolution=100.0)
        print(f"Converted {tiff_file_path} to {pdf_file_path}")
    except Exception as e:
        print(f"Failed to convert {tiff_file_path}: {e}")

# Convert all TIFF files in the directory
def convert_all_tiffs_in_directory(input_directory, output_directory, progress_label, progress_bar):
    tiff_files = [f for f in os.listdir(input_directory) if f.lower().endswith('.tif') or f.lower().endswith('.tiff')]
    total_tiff_files = len(tiff_files)
    progress_bar["maximum"] = total_tiff_files

    for idx, filename in enumerate(tiff_files, 1):
        if cancel_event.is_set():
            progress_label.config(text="Operation canceled.")
            break

        tiff_file_path = os.path.join(input_directory, filename)
        base_filename = os.path.splitext(filename)[0]
        unique_pdf_file_path = os.path.join(output_directory, generate_unique_filename(output_directory, base_filename, ".pdf"))
        convert_tiff_to_pdf(tiff_file_path, unique_pdf_file_path)
        
        progress_label.config(text=f"Converted {idx}/{total_tiff_files} TIFF files to PDF")
        progress_bar["value"] = idx
        root.update_idletasks()

# Determine if a page is blank based on pixel analysis
def is_blank_page_by_pixels(page, dark_threshold=52):
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
    black_pixel_ratio = black_pixels / total_pixels
    print(f"Page has {black_pixel_ratio:.2%} black pixels.")  # Debug output
    return black_pixel_ratio < 0.01  # Adjust this threshold as needed

def remove_blank_pages(input_dir, output_dir, progress_label, progress_bar):
    blanks = []
    pdf_files = [f for f in os.listdir(output_dir) if f.lower().endswith('.pdf')]
    total_files = len(pdf_files)
    progress_bar["maximum"] = total_files

    for idx, filename in enumerate(pdf_files, 1):
        if cancel_event.is_set():
            progress_label.config(text="Operation canceled.")
            break

        file_path = os.path.join(output_dir, filename)
        print(f"Processing file: {file_path}")  # Debug output

        pdf_document = fitz.open(file_path)
        pages_to_remove = []

        for page_number in range(len(pdf_document)):
            print(f"Checking page {page_number + 1}/{len(pdf_document)}")  # Debug output
            if is_blank_page_by_pixels(pdf_document[page_number], dark_threshold=dark_threshold_slider.get()):
                pages_to_remove.append(page_number)
                blanks.append(f"{file_path} - Page {page_number + 1}")
                print(f"Page {page_number + 1} marked for removal.")  # Debug output

        if pages_to_remove:
            print(f"Removing {len(pages_to_remove)} pages.")  # Debug output
            for page_number in reversed(pages_to_remove):
                pdf_document.delete_page(page_number)

            # Save to a temporary file
            temp_file_path = os.path.join(output_dir, f"temp_{filename}")
            pdf_document.save(temp_file_path)
            pdf_document.close()

            # Replace original file with the updated file
            os.replace(temp_file_path, file_path)
        else:
            pdf_document.close()

        progress_label.config(text=f"Processed {idx}/{total_files} files, {len(blanks)} blank pages found and removed")
        progress_bar["value"] = idx
        root.update_idletasks()

    if not cancel_event.is_set():
        messagebox.showinfo("Complete", "Detection and removal of blank pages completed successfully.")
    
    blank_files_log = os.path.join(output_dir, 'filenames.xlsx')
    if os.path.exists(blank_files_log):
        os.remove(blank_files_log)
    
    df = pd.DataFrame(blanks, columns=['Filename'])
    df.to_excel(blank_files_log, index=False)

def remove_blank_pages2(input_dir, output_dir, progress_label, progress_bar):
    blanks = []
    pdf_files = [f for f in os.listdir(input_dir) if f.lower().endswith('.pdf')]
    total_files = len(pdf_files)
    progress_bar["maximum"] = total_files

    for idx, filename in enumerate(pdf_files, 1):
        input_path = os.path.join(input_dir, filename)
        unique_output_path = os.path.join(output_dir, generate_unique_filename(output_dir, os.path.splitext(filename)[0], ".pdf"))
        pdf_document = fitz.open(input_path)
        pages_to_remove = []

        for page_number in range(len(pdf_document)):
            if is_blank_page_by_pixels(pdf_document[page_number], dark_threshold=dark_threshold_slider.get()):
                pages_to_remove.append(page_number)
                blanks.append(f"{input_path} - Page {page_number + 1}")

        for page_number in reversed(pages_to_remove):
            pdf_document.delete_page(page_number)

        if len(pdf_document) > 0:
            pdf_document.save(unique_output_path)
        pdf_document.close()

        progress_label.config(text=f"Processed {idx}/{total_files} files, {len(blanks)} blank pages found and removed")
        progress_bar["value"] = idx
        root.update_idletasks()
    
    messagebox.showinfo("Complete", "Detection and removal of blank pages completed successfully.")
    
    blank_files_log = os.path.join(output_dir, 'filenames.xlsx')
    if os.path.exists(blank_files_log):
        os.remove(blank_files_log)
    
    df = pd.DataFrame(blanks, columns=['Filename'])
    df.to_excel(blank_files_log, index=False)

def select_directory():
    global input_dir, output_dir

    input_dir = filedialog.askdirectory(title="Select Input Directory")
    output_dir = filedialog.askdirectory(title="Select Output Directory")

    if input_dir and output_dir:
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)

        total_tiff_files = len([f for f in os.listdir(input_dir) if f.lower().endswith('.tif') or f.lower().endswith('.tiff')])
        total_pdf_files = len([f for f in os.listdir(output_dir) if f.lower().endswith('.pdf')])
        progress_label.config(text=f"Total TIFF files: {total_tiff_files}, Total PDF files: {total_pdf_files}")
        input_dir_label.config(text=f"Input: {input_dir}")
        output_dir_label.config(text=f"Output: {output_dir}")  # Update output directory label

def start_convert():
    if input_dir and output_dir:
        cancel_event.clear()  # Clear the cancel event
        threading.Thread(target=convert_all_tiffs_in_directory, args=(input_dir, output_dir, progress_label, progress_bar)).start()
    else:
        messagebox.showwarning("Warning", "Please select both input and output directories first.")

def start_remove_blanks():
    if input_dir and output_dir:
        cancel_event.clear()  # Clear the cancel event
        threading.Thread(target=remove_blank_pages, args=(input_dir, output_dir, progress_label, progress_bar)).start()
    else:
        messagebox.showwarning("Warning", "Please select both input and output directories first.")

def start_convert_and_remove_blanks():
    if input_dir and output_dir:
        cancel_event.clear()  # Clear the cancel event
        threading.Thread(target=convert_and_remove_blanks, args=(input_dir, output_dir, progress_label, progress_bar)).start()
    else:
        messagebox.showwarning("Warning", "Please select both input and output directories first.")

def convert_and_remove_blanks(input_dir, output_dir, progress_label, progress_bar):
    # Step 1: Convert all TIFF files to PDFs
    temp_dir = os.path.join(output_dir, "temp")
    # Create the "temp" directory if it doesn't exist
    os.makedirs(temp_dir, exist_ok=True)
    convert_all_tiffs_in_directory(input_dir, temp_dir, progress_label, progress_bar)
   

    # Step 2: Remove blank pages from the generated PDFs
    remove_blank_pages2(temp_dir, output_dir, progress_label, progress_bar)
    shutil.rmtree(temp_dir)



def cancel_operation():
    cancel_event.set()  # Signal the cancel event

def start_remove_blanks2():
    if input_dir and output_dir:
        threading.Thread(target=remove_blank_pages2, args=(input_dir, output_dir, progress_label, progress_bar)).start()
    else:
        messagebox.showwarning("Warning", "Please select both input and output directories first.")

root = tk.Tk()
root.title("TIFF to PDF Converter and PDF Blank Page Remover")

frame = tk.Frame(root, padx=20, pady=20)
frame.pack()

input_dir_label = tk.Label(frame, text="Input: None")
input_dir_label.pack(pady=10)

output_dir_label = tk.Label(frame, text="Output: None")  # Label for output directory
output_dir_label.pack(pady=10)

select_btn = tk.Button(frame, text="Select Directories", command=select_directory)
select_btn.pack(pady=10)

convert_btn = tk.Button(frame, text="Convert TIFFs to PDFs", command=start_convert)
convert_btn.pack(pady=10)

remove_blanks_btn = tk.Button(frame, text="Remove Blank Pages from PDFs", command=start_remove_blanks2)
remove_blanks_btn.pack(pady=10)

convert_and_remove_btn = tk.Button(frame, text="Convert and Remove Blank Pages", command=start_convert_and_remove_blanks)
convert_and_remove_btn.pack(pady=10)

cancel_btn = tk.Button(frame, text="Cancel", command=cancel_operation)  # Cancel button
cancel_btn.pack(pady=10)

# Add slider for adjusting pixel darkness threshold
dark_threshold_slider = tk.Scale(frame, from_=50, to=95, orient=tk.HORIZONTAL, label="Sensitivity (Inverse - Lower sensitivity removes more pages.)")
dark_threshold_slider.set(52)  # Default value
dark_threshold_slider.pack(pady=10)

progress_label = tk.Label(frame, text="Total TIFF files: 0, Total PDF files: 0")
progress_label.pack(pady=10)

progress_bar = Progressbar(frame, length=300, mode='determinate')
progress_bar.pack(pady=10)

input_dir = ""
output_dir = ""

root.mainloop()
