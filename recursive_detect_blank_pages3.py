import threading
import shutil
import fitz  # PyMuPDF
from PIL import Image
import numpy as np
import os
import pandas as pd
import tkinter as tk
from tkinter import filedialog, messagebox, Listbox, Scrollbar
from tkinter.ttk import Progressbar, Label, Scale

# Global event to signal cancellation
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
        tiff_image = Image.open(tiff_file_path)
        if tiff_image.mode != 'RGB':
            tiff_image = tiff_image.convert('RGB')
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
def is_blank_page_by_pixels(page, dark_threshold=90):
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
    print(f"Page has {black_pixel_ratio:.2%} black pixels.")
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
        print(f"Processing file: {file_path}")

        pdf_document = fitz.open(file_path)
        pages_to_remove = []

        for page_number in range(len(pdf_document)):
            print(f"Checking page {page_number + 1}/{len(pdf_document)}")
            if is_blank_page_by_pixels(pdf_document[page_number], dark_threshold=dark_threshold_slider.get()):
                pages_to_remove.append(page_number)
                blanks.append(f"{file_path} - Page {page_number + 1}")
                print(f"Page {page_number + 1} marked for removal.")

        if pages_to_remove:
            print(f"Removing {len(pages_to_remove)} pages.")
            for page_number in reversed(pages_to_remove):
                pdf_document.delete_page(page_number)

            temp_file_path = os.path.join(output_dir, f"temp_{filename}")
            pdf_document.save(temp_file_path)
            pdf_document.close()

            os.replace(temp_file_path, file_path)
        else:
            pdf_document.close()

        progress_label.config(text=f"Processed {idx}/{total_files} files, {len(blanks)} blank pages found and removed")
        progress_bar["value"] = idx
        root.update_idletasks()

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
        output_dir_label.config(text=f"Output: {output_dir}")

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
    temp_dir = os.path.join(output_dir, "temp")
    os.makedirs(temp_dir, exist_ok=True)
    convert_all_tiffs_in_directory(input_dir, temp_dir, progress_label, progress_bar)
    remove_blank_pages2(temp_dir, output_dir, progress_label, progress_bar)
    shutil.rmtree(temp_dir)

def cancel_operation():
    cancel_event.set()  # Signal the cancel event

def start_remove_blanks2():
    if input_dir and output_dir:
        threading.Thread(target=remove_blank_pages2, args=(input_dir, output_dir, progress_label, progress_bar)).start()
    else:
        messagebox.showwarning("Warning", "Please select both input and output directories first.")

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

    threading.Thread(target=process_selected_folders, args=(input_dirs, output_dir, progress_label, progress_bar)).start()

def remove_blanks_with_listbox():
    output_dir = filedialog.askdirectory(title="Select Output Directory")
    
    if not output_dir:
        messagebox.showwarning("Warning", "Please select an output directory.")
        return
    output_dir_label.config(text=f"Output: {output_dir}")  # Update output directory label
    input_dirs = list(input_dirs_listbox.get(0, tk.END))
    
    if not input_dirs:
        messagebox.showwarning("Warning", "No folders selected.")
        return

    threading.Thread(target=process_selected_folders_blanks, args=(input_dirs, output_dir, progress_label, progress_bar)).start()

def convert_pdf_with_listbox():
    output_dir = filedialog.askdirectory(title="Select Output Directory")
    
    if not output_dir:
        messagebox.showwarning("Warning", "Please select an output directory.")
        return
    output_dir_label.config(text=f"Output: {output_dir}")  # Update output directory label
    input_dirs = list(input_dirs_listbox.get(0, tk.END))
    
    if not input_dirs:
        messagebox.showwarning("Warning", "No folders selected.")
        return

    threading.Thread(target=process_selected_folders_convert, args=(input_dirs, output_dir, progress_label, progress_bar)).start()
    

# Use the same `process_selected_folders` function as before
def process_selected_folders(input_dirs, output_dir, progress_label, progress_bar):
    cancel_event.clear()  # Clear the cancel event
    total_folders = len(input_dirs)
    progress_bar["maximum"] = total_folders

    for idx, input_dir in enumerate(input_dirs, 1):
        if cancel_event.is_set():
            progress_label.config(text="Operation canceled.")
            break
        
        folder_name = os.path.basename(input_dir)
        output_subdir = os.path.join(output_dir, folder_name)
        os.makedirs(output_subdir, exist_ok=True)
        convert_and_remove_blanks(input_dir, output_subdir, progress_label, progress_bar)

        progress_label.config(text=f"Processed {idx}/{total_folders} folders")
        progress_bar["value"] = idx
        root.update_idletasks()

    progress_label.config(text="All selected folders processed successfully.")  # Update progress label after all folders are done

def process_selected_folders_blanks(input_dirs, output_dir, progress_label, progress_bar):
    cancel_event.clear()  # Clear the cancel event
    total_folders = len(input_dirs)
    progress_bar["maximum"] = total_folders

    for idx, input_dir in enumerate(input_dirs, 1):
        if cancel_event.is_set():
            progress_label.config(text="Operation canceled.")
            break
        
        folder_name = os.path.basename(input_dir)
        output_subdir = os.path.join(output_dir, folder_name)
        os.makedirs(output_subdir, exist_ok=True)
        print(input_dir)
        remove_blank_pages2(input_dir, output_subdir, progress_label, progress_bar)

        progress_label.config(text=f"Processed {idx}/{total_folders} folders")
        progress_bar["value"] = idx
        root.update_idletasks()

    progress_label.config(text="All selected folders processed successfully.")  # Update progress label after all folders are done

def process_selected_folders_convert(input_dirs, output_dir, progress_label, progress_bar):
    cancel_event.clear()  # Clear the cancel event
    total_folders = len(input_dirs)
    progress_bar["maximum"] = total_folders

    for idx, input_dir in enumerate(input_dirs, 1):
        if cancel_event.is_set():
            progress_label.config(text="Operation canceled.")
            break
        
        folder_name = os.path.basename(input_dir)
        output_subdir = os.path.join(output_dir, folder_name)
        os.makedirs(output_subdir, exist_ok=True)
        print(input_dir)
        convert_all_tiffs_in_directory(input_dir, output_subdir, progress_label, progress_bar)

        progress_label.config(text=f"Processed {idx}/{total_folders} folders")
        progress_bar["value"] = idx
        root.update_idletasks()

    progress_label.config(text="All selected folders processed successfully.")  # Update progress label after all folders are done

root = tk.Tk()
root.title("TIFF to PDF Converter and PDF Blank Page Remover")

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

convert_pdf_btn = tk.Button(frame, text="Convert to PDF", command=convert_pdf_with_listbox)
convert_pdf_btn.pack(pady=10)

remove_blanks_btn = tk.Button(frame, text="Remove Blanks", command=remove_blanks_with_listbox)
remove_blanks_btn.pack(pady=10)

select_btn = tk.Button(frame, text="Convert to PDF AND Remove Blanks", command=select_folders_with_listbox)
select_btn.pack(pady=10)

cancel_btn = tk.Button(frame, text="Cancel", command=cancel_operation)
cancel_btn.pack(pady=10)

dark_threshold_slider = tk.Scale(frame, from_=65, to=125, orient=tk.HORIZONTAL, label="Sensitivity")
dark_threshold_slider.set(100)
dark_threshold_slider.pack(pady=10)

slider_label = tk.Label(frame, text="Inverse - Lower sensitivity removes more pages. For best results use 90 for single page PDF's and 120 for multipage PDFs.")
slider_label.pack(pady=10)

progress_label = tk.Label(frame, text="Total TIFF files: 0, Total PDF files: 0")
progress_label.pack(pady=10)

progress_bar = Progressbar(frame, length=300, mode='determinate')
progress_bar.pack(pady=10)

input_dir = ""
output_dir = ""

root.mainloop()
