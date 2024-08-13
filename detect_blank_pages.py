import fitz  # PyMuPDF
from PIL import Image
import numpy as np
import os
import pandas as pd
import tkinter as tk
from tkinter import filedialog, messagebox
from tkinter.ttk import Progressbar

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

def is_blank_page_by_pixels(page, dark_threshold=52, black_pixel_threshold=0.01):
    # Convert PDF page to pixmap
    pix = page.get_pixmap()
    img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
    
    # Calculate the amount to crop (approximately 1 inch on left and right)
    dpi = 72  # Assume 72 DPI
    inch = dpi  # 1 inch in pixels
    left_crop = inch
    right_crop = inch
    
    # Crop the image
    img_cropped = img.crop((left_crop, 0, img.width - right_crop, img.height))
    
    # Convert the image to grayscale
    gray = img_cropped.convert('L')
    
    # Apply threshold to turn gray/dark pixels into white and keep only truly dark pixels as black
    bw = gray.point(lambda p: 0 if p < dark_threshold else 255, '1')
    
    # Convert to numpy array for analysis
    np_image = np.array(bw)
    
    # Count black pixels (in this '1' image, 0 is black and 1 is white)
    black_pixels = np.sum(np_image == 0)
    total_pixels = np_image.size
    
    black_pixel_ratio = black_pixels / total_pixels

    print(f"Black pixels: {black_pixels}")
    
    # Consider the page blank if the black pixel ratio is below the black_pixel_threshold
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
        total_pdf_files = len([f for f in os.listdir(input_dir) if f.lower().endswith('.pdf')])
        progress_label.config(text=f"Total TIFF files: {total_tiff_files}, Total PDF files: {total_pdf_files}")

def start_convert():
    if input_dir and output_dir:
        convert_all_tiffs_in_directory(input_dir, output_dir, progress_label, progress_bar)
    else:
        messagebox.showwarning("Warning", "Please select both input and output directories first.")

def start_remove_blanks():
    if input_dir and output_dir:
        remove_blank_pages(input_dir, output_dir, progress_label, progress_bar)
    else:
        messagebox.showwarning("Warning", "Please select both input and output directories first.")

root = tk.Tk()
root.title("TIFF to PDF Converter and PDF Blank Page Remover")

frame = tk.Frame(root, padx=20, pady=20)
frame.pack()

select_btn = tk.Button(frame, text="Select Directories", command=select_directory)
select_btn.pack(pady=10)

convert_btn = tk.Button(frame, text="Convert TIFFs to PDFs", command=start_convert)
convert_btn.pack(pady=10)

remove_blanks_btn = tk.Button(frame, text="Remove Blank Pages from PDFs", command=start_remove_blanks)
remove_blanks_btn.pack(pady=10)

progress_label = tk.Label(frame, text="Total TIFF files: 0, Total PDF files: 0")
progress_label.pack(pady=10)

progress_bar = Progressbar(frame, length=300, mode='determinate')
progress_bar.pack(pady=10)

input_dir = ""
output_dir = ""

root.mainloop()
