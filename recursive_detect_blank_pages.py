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
import time
import mimetypes
import pyvips  # Added for handling large TIFF files

Image.MAX_IMAGE_PIXELS = None

# Global event to signal cancellation
cancel_event = threading.Event()

# Global list to store failed files information
failed_files = []
failed_files_lock = threading.Lock()

# Function to get file information
def get_file_info(file_path):
    try:
        stats = os.stat(file_path)
        size = stats.st_size
        mtime = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(stats.st_mtime))
        ctime = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(stats.st_ctime))
        file_type = mimetypes.guess_type(file_path)[0] or 'Unknown'
        return {
            'File Path': file_path,
            'Size (bytes)': size,
            'Modified Time': mtime,
            'Created Time': ctime,
            'File Type': file_type
        }
    except Exception as e:
        return {
            'File Path': file_path,
            'Error': f'Failed to get file info: {e}'
        }

# Function to write failed files log
def write_failed_files_log(output_directory):
    if failed_files:
        df = pd.DataFrame(failed_files)
        log_file_path = os.path.join(output_directory, 'failed_files.xlsx')
        if os.path.exists(log_file_path):
            os.remove(log_file_path)
        df.to_excel(log_file_path, index=False)

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
        file_info = get_file_info(tiff_file_path)
        file_info['Error'] = str(e)
        with failed_files_lock:
            failed_files.append(file_info)

# Convert large TIFF to PDF using pyvips
def convert_large_tiff_to_pdf(tiff_file_path, pdf_file_path):
    try:
        image = pyvips.Image.new_from_file(tiff_file_path, access='sequential')
        pdf_target = pdf_file_path + '[compression=jpeg]'
        image.write_to_file(pdf_target)
        print(f"Converted {tiff_file_path} to {pdf_file_path} using pyvips")
    except Exception as e:
        print(f"Failed to convert {tiff_file_path}: {e}")
        file_info = get_file_info(tiff_file_path)
        file_info['Error'] = str(e)
        with failed_files_lock:
            failed_files.append(file_info)

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

    if failed_files:
        write_failed_files_log(output_directory)

# Convert all large TIFF files in the directory using pyvips
def convert_large_tiffs_in_directory(input_directory, output_directory, progress_label, progress_bar):
    tiff_files = [f for f in os.listdir(input_directory) if f.lower().endswith(('.tif', '.tiff'))]
    total_tiff_files = len(tiff_files)
    progress_bar["maximum"] = total_tiff_files

    for idx, filename in enumerate(tiff_files, 1):
        if cancel_event.is_set():
            progress_label.config(text="Operation canceled.")
            break

        tiff_file_path = os.path.join(input_directory, filename)
        base_filename = os.path.splitext(filename)[0]
        unique_pdf_file_path = os.path.join(
            output_directory,
            generate_unique_filename(output_directory, base_filename, ".pdf")
        )
        convert_large_tiff_to_pdf(tiff_file_path, unique_pdf_file_path)

        progress_label.config(text=f"Converted {idx}/{total_tiff_files} large TIFF files to PDF")
        progress_bar["value"] = idx
        root.update_idletasks()

    if failed_files:
        write_failed_files_log(output_directory)

# Determine if a page is blank based on pixel analysis
def is_blank_page_by_pixels(page, dark_threshold=52):
    try:
        zoom = 0.5  # Adjust zoom factor as needed
        mat = fitz.Matrix(zoom, zoom)
        pix = page.get_pixmap(matrix=mat)
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
    except Exception as e:
        print(f"Failed to process page {page.number}: {e}")
        return False  # Consider non-blank if processing fails

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

        try:
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
        except Exception as e:
            print(f"Failed to process {file_path}: {e}")
            file_info = get_file_info(file_path)
            file_info['Error'] = str(e)
            with failed_files_lock:
                failed_files.append(file_info)
            continue

        progress_label.config(text=f"Processed {idx}/{total_files} files, {len(blanks)} blank pages found and removed")
        progress_bar["value"] = idx
        root.update_idletasks()

    blank_files_log = os.path.join(output_dir, 'filenames.xlsx')
    if os.path.exists(blank_files_log):
        os.remove(blank_files_log)

    df = pd.DataFrame(blanks, columns=['Filename'])
    df.to_excel(blank_files_log, index=False)

    if failed_files:
        write_failed_files_log(output_dir)

def remove_blank_pages2(input_dir, output_dir, progress_label, progress_bar):
    blanks = []
    pdf_files = [f for f in os.listdir(input_dir) if f.lower().endswith('.pdf')]
    total_files = len(pdf_files)
    progress_bar["maximum"] = total_files

    for idx, filename in enumerate(pdf_files, 1):
        if cancel_event.is_set():
            progress_label.config(text="Operation canceled.")
            break

        input_path = os.path.join(input_dir, filename)
        unique_output_path = os.path.join(output_dir, generate_unique_filename(output_dir, os.path.splitext(filename)[0], ".pdf"))

        try:
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
        except Exception as e:
            print(f"Failed to process {input_path}: {e}")
            file_info = get_file_info(input_path)
            file_info['Error'] = str(e)
            with failed_files_lock:
                failed_files.append(file_info)
            continue

        progress_label.config(text=f"Processed {idx}/{total_files} files, {len(blanks)} blank pages found and removed")
        progress_bar["value"] = idx
        root.update_idletasks()

    blank_files_log = os.path.join(output_dir, 'filenames.xlsx')
    if os.path.exists(blank_files_log):
        os.remove(blank_files_log)

    df = pd.DataFrame(blanks, columns=['Filename'])
    df.to_excel(blank_files_log, index=False)

    if failed_files:
        write_failed_files_log(output_dir)

def select_directory():
    global input_dir, output_dir

    input_dir = filedialog.askdirectory(title="Select Input Directory")
    output_dir = filedialog.askdirectory(title="Select Output Directory")

    if input_dir and output_dir:
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)

        total_tiff_files = len([f for f in os.listdir(input_dir) if f.lower().endswith(('.tif', '.tiff'))])
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

def start_convert_large():
    if input_dir and output_dir:
        cancel_event.clear()  # Clear the cancel event
        threading.Thread(target=convert_large_tiffs_in_directory, args=(input_dir, output_dir, progress_label, progress_bar)).start()
    else:
        messagebox.showwarning("Warning", "Please select both input and output directories first.")

def start_remove_blanks():
    if input_dir and output_dir:
        cancel_event.clear()  # Clear the cancel event
        threading.Thread(target=remove_blank_pages, args=(input_dir, output_dir, progress_label, progress_bar)).start()
    else:
        messagebox.showwarning("Warning", "Please select both input and output directories first.")

def start_remove_blanks2():
    if input_dir and output_dir:
        cancel_event.clear()  # Clear the cancel event
        threading.Thread(target=remove_blank_pages2, args=(input_dir, output_dir, progress_label, progress_bar)).start()
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

# New function to process all subfolders
def process_subfolders(input_parent_dir, output_parent_dir, progress_label, progress_bar):
    cancel_event.clear()  # Clear the cancel event
    for subdir in os.listdir(input_parent_dir):
        if cancel_event.is_set():
            progress_label.config(text="Operation canceled.")
            break

        input_subdir = os.path.join(input_parent_dir, subdir)
        output_subdir = os.path.join(output_parent_dir, subdir)
        if os.path.isdir(input_subdir):
            os.makedirs(output_subdir, exist_ok=True)
            convert_and_remove_blanks(input_subdir, output_subdir, progress_label, progress_bar)

    progress_label.config(text="All folders processed successfully.")  # Update progress label after all folders are done

def select_parent_folders():
    input_parent_dir = filedialog.askdirectory(title="Select Parent Input Directory")
    output_parent_dir = filedialog.askdirectory(title="Select Parent Output Directory")

    if input_parent_dir and output_parent_dir:
        threading.Thread(target=process_subfolders, args=(input_parent_dir, output_parent_dir, progress_label, progress_bar)).start()
    else:
        messagebox.showwarning("Warning", "Please select both parent input and output directories first.")

root = tk.Tk()
root.title("TIFF to PDF Converter and PDF Blank Page Remover")

frame = tk.Frame(root, padx=20, pady=20)
frame.pack()

input_dir_label = tk.Label(frame, text="Input: None")
input_dir_label.pack(pady=10)

output_dir_label = tk.Label(frame, text="Output: None")
output_dir_label.pack(pady=10)

select_btn = tk.Button(frame, text="Select Directories", command=select_directory)
select_btn.pack(pady=10)

convert_btn = tk.Button(frame, text="Convert TIFFs to PDFs", command=start_convert)
convert_btn.pack(pady=10)

# New button for converting large TIFFs to PDFs
convert_large_btn = tk.Button(frame, text="Convert Large TIFFs to PDFs", command=start_convert_large)
convert_large_btn.pack(pady=10)

remove_blanks_btn = tk.Button(frame, text="Remove Blank Pages from PDFs", command=start_remove_blanks2)
remove_blanks_btn.pack(pady=10)

convert_and_remove_btn = tk.Button(frame, text="Convert and Remove Blank Pages", command=start_convert_and_remove_blanks)
convert_and_remove_btn.pack(pady=10)

parent_folders_btn = tk.Button(frame, text="Master Conversion", command=select_parent_folders)  # Existing button
parent_folders_btn.pack(pady=10)

cancel_btn = tk.Button(frame, text="Cancel", command=cancel_operation)
cancel_btn.pack(pady=10)

dark_threshold_slider = tk.Scale(frame, from_=50, to=1000, orient=tk.HORIZONTAL, label="Sensitivity")
dark_threshold_slider.set(90)
dark_threshold_slider.pack(pady=10)

slider_label = tk.Label(frame, text="Inverse - Lower sensitivity removes more pages.")
slider_label.pack(pady=10)

progress_label = tk.Label(frame, text="Total TIFF files: 0, Total PDF files: 0")
progress_label.pack(pady=10)

progress_bar = Progressbar(frame, length=300, mode='determinate')
progress_bar.pack(pady=10)

input_dir = ""
output_dir = ""

root.mainloop()
