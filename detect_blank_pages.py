import fitz  # PyMuPDF
from PIL import Image
import numpy as np
import os
import pandas as pd
import tkinter as tk
from tkinter import filedialog, messagebox
from tkinter.ttk import Progressbar

def is_blank_page_by_pixels(page, dark_threshold=50, black_pixel_threshold=0.01):
    """
    Determine if a page is blank based on the count of truly dark pixels.
    
    Parameters:
    - page: The PDF page object.
    - dark_threshold: Pixel intensity threshold; pixels darker (less than this value) are considered black.
    - black_pixel_threshold: Percentage of dark pixels below which a page is considered blank.
    """
    pix = page.get_pixmap()
    img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
    
    gray = img.convert('L')
    
    bw = gray.point(lambda p: 0 if p < dark_threshold else 255, '1')
    
    np_image = np.array(bw)
    
    black_pixels = np.sum(np_image == 0)
    total_pixels = np_image.size
    
    black_pixel_ratio = black_pixels / total_pixels

    print(f"Black pixels: {black_pixels}")
    
    return black_pixels < 20

def remove_blank_pages(input_dir, output_dir, progress_label, progress_bar):
    blanks = []
    pdf_files = [f for f in os.listdir(input_dir) if f.endswith('.pdf')]
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

        total_files = len([f for f in os.listdir(input_dir) if f.endswith('.pdf')])
        progress_label.config(text=f"Total PDF files: {total_files}")

def start_process():
    if input_dir and output_dir:
        remove_blank_pages(input_dir, output_dir, progress_label, progress_bar)
    else:
        messagebox.showwarning("Warning", "Please select both input and output directories first.")

root = tk.Tk()
root.title("PDF Blank Page Remover")

frame = tk.Frame(root, padx=20, pady=20)
frame.pack()

select_btn = tk.Button(frame, text="Select Directories", command=select_directory)
select_btn.pack(pady=10)

run_btn = tk.Button(frame, text="Run", command=start_process)
run_btn.pack(pady=10)

progress_label = tk.Label(frame, text="Total PDF files: 0")
progress_label.pack(pady=10)

progress_bar = Progressbar(frame, length=300, mode='determinate')
progress_bar.pack(pady=10)

input_dir = ""
output_dir = ""

root.mainloop()
