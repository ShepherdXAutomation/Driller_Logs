import datetime
import threading
import shutil
import fitz  # PyMuPDF
from PIL import Image, ImageFilter
import numpy as np
import os
import pandas as pd
import tkinter as tk
from tkinter import filedialog, messagebox, Listbox, Scrollbar, Text
from tkinter.ttk import Progressbar, Label, Scale
import time
import mimetypes
from pdf2image import convert_from_path
import pytesseract

Image.MAX_IMAGE_PIXELS = None

# Global event to signal cancellation
cancel_event = threading.Event()
# Global list to store failed files information
failed_files = []
failed_files_lock = threading.Lock()

# Function to generate a unique file name in the output directory
def generate_unique_filename(output_directory, base_filename, extension):
    counter = 1
    unique_filename = f"{base_filename}{extension}"
    
    while os.path.exists(os.path.join(output_directory, unique_filename)):
        unique_filename = f"{base_filename}_{counter}{extension}"
        counter += 1
        
    return unique_filename

def get_file_info(file_path):
    try:
        stats = os.stat(file_path)
        size = stats.st_size / (1024 * 1024)  # Convert bytes to megabytes
        size = round(size, 2)  # Round to 2 decimal places
        mtime = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(stats.st_mtime))
        ctime = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(stats.st_ctime))
        file_type = mimetypes.guess_type(file_path)[0] or 'Unknown'
        return {
            'File Path': file_path,
            'Size (MB)': size,
            'Modified Time': mtime,
            'Created Time': ctime,
            'File Type': file_type
        }
    except Exception as e:
        return {
            'File Path': file_path,
            'Error': f'Failed to get file info: {e}'
        }

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
def is_blank_page(page, text_threshold=10, image_threshold=1, dark_pixel_ratio_threshold=0.01, dpi=150, adaptive_threshold=False, log_widget=None):
    """
    Determine if a PDF page is blank by checking for text using OCR.
    
    Parameters:
    - page: PyMuPDF Page object.
    - text_threshold: Minimum number of characters to consider the page as non-blank based on text.
    - image_threshold: Unused for now, kept for backward compatibility.
    - dark_pixel_ratio_threshold: Unused for now, kept for backward compatibility.
    - dpi: Resolution for rendering the page to an image.
    - adaptive_threshold: Unused for now, kept for backward compatibility.
    - log_widget: Tkinter Text widget for logging (optional).

    Returns:
    - Boolean indicating whether the page is blank.
    """
    def log(message):
        print(message)
        if log_widget:
            log_widget.insert(tk.END, message + "\n")
            log_widget.see(tk.END)

    # 1. Render page to image at specified DPI for OCR
    try:
        # Extract the current PDF document and page number
        pdf_document = page.parent
        page_number = page.number

        # Convert the specific page to an image
        images = convert_from_path(pdf_document.name, first_page=page_number + 1, last_page=page_number + 1, dpi=dpi)
        if not images:
            log("No images were generated from the page for OCR.")
            return False  # Assume not blank if we can't generate the image

        img = images[0]
        log(f"Rendered image size for OCR: {img.size}")
    except Exception as e:
        log(f"Error rendering page to image for OCR: {e}")
        return False  # Unable to render, assume not blank

    # 2. Extract text using OCR
    try:
        ocr_text = pytesseract.image_to_string(img).strip()
        log(f"OCR extracted text length: {len(ocr_text)}")
        log(f"OCR Extracted Text:\n{ocr_text}\n{'-'*40}")
    except Exception as e:
        log(f"Error during OCR text extraction: {e}")
        ocr_text = ""

    # 3. Check if the extracted text meets the threshold to consider it non-blank
    if len(ocr_text) >= text_threshold:
        log("Page contains text detected by OCR.")
        return False  # Page has text, not blank

    log("Page is considered blank based on OCR text extraction.")
    return True  # Page is blank if no sufficient text is found



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
        except Exception as e:
            print(f"Failed to open {file_path}: {e}")
            with failed_files_lock:
                failed_files.append({'File Path': file_path, 'Error': str(e)})
            continue

        pages_to_remove = []

        for page_number in range(len(pdf_document)):
            print(f"Checking page {page_number + 1}/{len(pdf_document)}")
            page = pdf_document[page_number]
            is_blank = is_blank_page(
                page,
                text_threshold=10,
                image_threshold=1,
                dark_pixel_ratio_threshold=0.01,
                dpi=150,
                adaptive_threshold=False
            )
            if is_blank:
                pages_to_remove.append(page_number)
                blanks.append(f"{file_path} - Page {page_number + 1}")
                print(f"Page {page_number + 1} marked for removal.")

        if pages_to_remove:
            print(f"Removing {len(pages_to_remove)} pages.")
            for page_number in reversed(pages_to_remove):
                pdf_document.delete_page(page_number)

            temp_file_path = os.path.join(output_dir, f"temp_{filename}")
            try:
                pdf_document.save(temp_file_path)
                pdf_document.close()
                os.replace(temp_file_path, file_path)
                print(f"Removed blank pages from {file_path}")
            except Exception as e:
                print(f"Failed to remove pages from {file_path}: {e}")
                with failed_files_lock:
                    failed_files.append({'File Path': file_path, 'Error': str(e)})
        else:
            pdf_document.close()
            print(f"No blank pages found in {file_path}")

        progress_label.config(text=f"Processed {idx}/{total_files} files, {len(blanks)} blank pages found and removed")
        progress_bar["value"] = idx
        root.update_idletasks()

    # Get current date and time
    timestamp = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')

    # Save blanks to Excel log with timestamp
    blank_files_log = os.path.join(output_dir, f'Removed_Blank_Pages_{timestamp}.xlsx')
    if os.path.exists(blank_files_log):
        os.remove(blank_files_log)

    df = pd.DataFrame(blanks, columns=['Filename'])
    df.to_excel(blank_files_log, index=False)
    print(f"Excel log saved to {blank_files_log}")

    # Save blanks to Text log with timestamp
    blank_pages_log_txt = os.path.join(output_dir, f'blank_pages_removed_{timestamp}.txt')
    try:
        with open(blank_pages_log_txt, 'w') as txt_file:
            for blank in blanks:
                txt_file.write(f"{blank}\n")
        print(f"Text log saved to {blank_pages_log_txt}")
    except Exception as e:
        print(f"Failed to write text log: {e}")

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
        print(f"Processing file: {input_path}")

        try:
            pdf_document = fitz.open(input_path)
        except Exception as e:
            print(f"Failed to open {input_path}: {e}")
            with failed_files_lock:
                failed_files.append({'File Path': input_path, 'Error': str(e)})
            continue

        pages_to_remove = []

        for page_number in range(len(pdf_document)):
            print(f"Checking page {page_number + 1}/{len(pdf_document)}")
            page = pdf_document[page_number]
            is_blank = is_blank_page(
                page,
                text_threshold=10,
                image_threshold=1,
                dark_pixel_ratio_threshold=0.01,
                dpi=150,
                adaptive_threshold=False
            )
            if is_blank:
                pages_to_remove.append(page_number)
                blanks.append(f"{input_path} - Page {page_number + 1}")
                print(f"Page {page_number + 1} marked for removal.")

        if pages_to_remove:
            print(f"Removing {len(pages_to_remove)} pages.")
            for page_number in reversed(pages_to_remove):
                pdf_document.delete_page(page_number)

            try:
                if len(pdf_document) > 0:
                    pdf_document.save(unique_output_path)
                    print(f"Saved modified PDF to {unique_output_path}")
                pdf_document.close()
            except Exception as e:
                print(f"Failed to save modified PDF {unique_output_path}: {e}")
                with failed_files_lock:
                    failed_files.append({'File Path': unique_output_path, 'Error': str(e)})
        else:
            pdf_document.close()
            print(f"No blank pages found in {input_path}")

        progress_label.config(text=f"Processed {idx}/{total_files} files, {len(blanks)} blank pages found and removed")
        progress_bar["value"] = idx
        root.update_idletasks()
    
    # Get current date and time
    timestamp = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')

    # Save blanks to Excel log with timestamp
    blank_files_log = os.path.join(output_dir, f'Removed_Blank_Pages_{timestamp}.xlsx')
    if os.path.exists(blank_files_log):
        os.remove(blank_files_log)

    df = pd.DataFrame(blanks, columns=['Filename'])
    df.to_excel(blank_files_log, index=False)
    print(f"Excel log saved to {blank_files_log}")

    # Save blanks to Text log with timestamp
    blank_pages_log_txt = os.path.join(output_dir, f'blank_pages_removed_{timestamp}.txt')
    try:
        with open(blank_pages_log_txt, 'w') as txt_file:
            for blank in blanks:
                txt_file.write(f"{blank}\n")
        print(f"Text log saved to {blank_pages_log_txt}")
    except Exception as e:
        print(f"Failed to write text log: {e}")

def add_folders_from_text():
    input_text = text_input_field.get("1.0", tk.END).strip()  # Get input and remove trailing newlines/spaces
    directories = [d.strip() for d in input_text.split(",")]  # Split by comma and strip extra spaces
    for directory in directories:
        if os.path.isdir(directory):
            input_dirs_listbox.insert(tk.END, directory)
        else:
            messagebox.showwarning("Warning", f"'{directory}' is not a valid directory.")

def convert_and_remove_blanks(input_dir, output_dir, progress_label, progress_bar):
    temp_dir = os.path.join(output_dir, "temp")
    os.makedirs(temp_dir, exist_ok=True)
    convert_all_tiffs_in_directory(input_dir, temp_dir, progress_label, progress_bar)
    remove_blank_pages2(temp_dir, output_dir, progress_label, progress_bar)
    shutil.rmtree(temp_dir)

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

def select_parent_folders():
    input_parent_dir = filedialog.askdirectory(title="Select Parent Input Directory")
    output_parent_dir = filedialog.askdirectory(title="Select Parent Output Directory")

    if input_parent_dir and output_parent_dir:
        threading.Thread(target=process_subfolders, args=(input_parent_dir, output_parent_dir, progress_label, progress_bar)).start()
    else:
        messagebox.showwarning("Warning", "Please select both parent input and output directories first.")

def start_convert_large():
    global input_dir, output_dir
    input_dir = filedialog.askdirectory(title="Select Input Directory")
    output_dir = filedialog.askdirectory(title="Select Output Directory")

    if input_dir and output_dir:
        output_dir_label.config(text=f"Output: {output_dir}")  # Update output directory label
        input_dir_label.config(text=f"Input: {input_dir}")    # Update input directory label
        cancel_event.clear()  # Clear the cancel event
        threading.Thread(target=convert_large_tiffs_in_directory, args=(input_dir, output_dir, progress_label, progress_bar)).start()
    else:
        messagebox.showwarning("Warning", "Please select both input and output directories.")

def reduce_tiff_size(input_tiff_path, output_tiff_path, target_size_mb=100):
    try:
        import subprocess
        quality = 85  # Starting quality
        resize_percent = 100  # Starting resize percentage

        while True:
            # Normalize paths
            input_tiff_path = os.path.normpath(input_tiff_path)
            output_tiff_path = os.path.normpath(output_tiff_path)

            # Construct the ImageMagick command
            command = [
                'magick',
                input_tiff_path,
                '-resize', f'{resize_percent}%',
                '-define', 'tiff:tile-geometry=256x256',
                '-compress', 'jpeg',
                '-quality', str(quality),
                output_tiff_path
            ]
            # Run the command
            subprocess.run(command, check=True)

            # Check the output file size
            size_mb = os.path.getsize(output_tiff_path) / (1024 * 1024)
            print(f"Compressed image size: {size_mb:.2f} MB with quality {quality}% and resize {resize_percent}%")

            # Check if the size is acceptable or if minimum thresholds are reached
            if size_mb <= target_size_mb or quality <= 10 or resize_percent <= 10:
                break

            # Adjust quality and resize percentage
            quality -= 5
            resize_percent -= 10

            # Ensure minimum values are not exceeded
            if quality < 10:
                quality = 10
            if resize_percent < 10:
                resize_percent = 10
    except subprocess.CalledProcessError as e:
        print(f"Failed to reduce size of {input_tiff_path}: {e}")
        file_info = get_file_info(input_tiff_path)
        file_info['Error'] = str(e)
        with failed_files_lock:
            failed_files.append(file_info)
        raise e

def convert_large_tiff_to_pdf(tiff_file_path, pdf_file_path):
    try:
        # Normalize paths
        tiff_file_path = os.path.normpath(tiff_file_path)
        pdf_file_path = os.path.normpath(pdf_file_path)

        # Define a temporary path for the resized TIFF
        temp_dir = os.path.join(os.path.dirname(pdf_file_path), 'temp')
        os.makedirs(temp_dir, exist_ok=True)
        temp_tiff_path = os.path.join(temp_dir, 'temp_resized.tif')

        # Reduce the size of the TIFF image
        reduce_tiff_size(tiff_file_path, temp_tiff_path, target_size_mb=100)

        # Convert the resized TIFF to PDF using ImageMagick
        import subprocess
        command = ['magick', temp_tiff_path, '-compress', 'jpeg', pdf_file_path]
        subprocess.run(command, check=True)
        print(f"Converted {tiff_file_path} to {pdf_file_path} using ImageMagick")

        # Remove the temporary resized TIFF file and directory
        os.remove(temp_tiff_path)
        os.rmdir(temp_dir)
    except Exception as e:
        print(f"Failed to convert {tiff_file_path}: {e}")
        file_info = get_file_info(tiff_file_path)
        file_info['Error'] = str(e)
        with failed_files_lock:
            failed_files.append(file_info)

def write_failed_files_log(output_directory):
    if failed_files:
        df = pd.DataFrame(failed_files)
        log_file_path = os.path.join(output_directory, 'failed_files.xlsx')
        if os.path.exists(log_file_path):
            os.remove(log_file_path)
        df.to_excel(log_file_path, index=False)
        print(f"Failed files log saved to {log_file_path}")

root = tk.Tk()
root.title("TIFF to PDF Converter and PDF Blank Page Remover")

frame = tk.Frame(root, padx=20, pady=20)
frame.pack()

output_dir_label = tk.Label(frame, text="Output: None")
output_dir_label.pack(pady=10)

# Listbox to display selected folders
listbox_frame = tk.Frame(frame)
listbox_frame.pack(pady=5, fill=tk.BOTH, expand=True)


text_input_label = tk.Label(frame, text="Paste directories separated by commas:")
text_input_label.pack(pady=5)

text_input_field = Text(frame, height=5, width=60)
text_input_field.pack(pady=5)

add_text_button = tk.Button(frame, text="Add Folders from Text", command=add_folders_from_text)
add_text_button.pack(pady=5)

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
# New button for converting large TIFFs to PDFs
convert_large_btn = tk.Button(frame, text="Convert Large TIFs to PDFs", command=start_convert_large)
convert_large_btn.pack(pady=10)

parent_folders_btn = tk.Button(frame, text="Master Conversion", command=select_parent_folders)  # Existing button
parent_folders_btn.pack(pady=10)

cancel_btn = tk.Button(frame, text="Cancel", command=cancel_operation)
cancel_btn.pack(pady=10)

# Adjusted slider range based on enhanced detection logic
dark_threshold_slider = tk.Scale(frame, from_=100, to=140, orient=tk.HORIZONTAL, label="Sensitivity")
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
