import os
import threading
import fitz  # PyMuPDF
import pytesseract
from PIL import Image
from pdf2image import convert_from_path
from skimage.metrics import structural_similarity as ssim
import cv2
import numpy as np
import tkinter as tk
from tkinter import filedialog, messagebox, scrolledtext, simpledialog, ttk

# Default headers, footers, and continuation indicators
DEFAULT_HEADERS = ["Log Service"]
DEFAULT_FOOTERS = []
CONTINUATION_INDICATORS = []

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

def compare_images(image1, image2):
    # Convert images to grayscale
    gray1 = cv2.cvtColor(np.array(image1), cv2.COLOR_BGR2GRAY)
    gray2 = cv2.cvtColor(np.array(image2), cv2.COLOR_BGR2GRAY)
    
    # Resize images to the same size if they have different dimensions
    if gray1.shape != gray2.shape:
        gray2 = cv2.resize(gray2, (gray1.shape[1], gray1.shape[0]))

    # Calculate SSIM between the two images
    score, diff = ssim(gray1, gray2, full=True)
    return score


def process_pdfs(input_folder, output_folder, headers, footers, continuation_indicators, log, progress):
    pdf_files = sorted([os.path.join(input_folder, f) for f in os.listdir(input_folder) if f.endswith('.pdf')])
    
    merged_files_count = 0
    total_files = len(pdf_files) - 1
    progress['maximum'] = total_files
    
    for i in range(total_files):
        front_pdf_path = pdf_files[i]
        back_pdf_path = pdf_files[i + 1]
        
        log.insert(tk.END, f"Processing pair: {front_pdf_path} and {back_pdf_path}\n")
        
        # Extract text from the front page using PyMuPDF
        text = ""
        try:
            doc = fitz.open(front_pdf_path)
            first_page = doc.load_page(0)
            text = first_page.get_text()
        except Exception as e:
            log.insert(tk.END, f"Error with PyMuPDF text extraction on front page: {e}\n")
        
        if not text.strip():
            log.insert(tk.END, f"No text found with PyMuPDF for {front_pdf_path}, trying OCR...\n")
            image = convert_from_path(front_pdf_path)[0]
            text = extract_text_with_ocr(image)
        
        # Output the extracted text to the log for debugging
        log.insert(tk.END, f"Extracted text from front page {front_pdf_path}:\n{text}\n{'-'*40}\n")
        
        # Check for header on the front page
        has_header, _ = detect_header_and_footer(text.lower(), [header.lower() for header in headers], footers)
        
        # Check if the back page is missing a header
        is_continued, back_text = is_back_page_continued(back_pdf_path, continuation_indicators, log)
        back_has_header, _ = detect_header_and_footer(back_text.lower(), [header.lower() for header in headers], footers)
        
        # Debugging output to understand the issue
        log.insert(tk.END, f"Header detected on front page: {has_header}\n")
        log.insert(tk.END, f"Header detected on back page: {back_has_header}\n")

        # Condition: Front page has a header, back page is missing header = match
        if has_header and not back_has_header:
            # Create the output file name based on the first file's name
            base_name = os.path.basename(front_pdf_path)
            output_pdf = os.path.join(output_folder, f'{os.path.splitext(base_name)[0]}_merged.pdf')
            
            merger = fitz.open()
            merger.insert_pdf(fitz.open(front_pdf_path))
            merger.insert_pdf(fitz.open(back_pdf_path))
            merger.save(output_pdf)
            merger.close()
            log.insert(tk.END, f"Merged file created: {output_pdf}\n")
            merged_files_count += 1
        else:
            log.insert(tk.END, f"Skipped merging: Front page missing header or back page has a header.\n")

        # Update progress
        progress['value'] = i + 1
        log.see(tk.END)  # Scroll log to the latest entry
        log.update_idletasks()  # Ensure the GUI updates

    messagebox.showinfo("Completed", f"PDF merging process completed. {merged_files_count} files created.")






def start_processing(headers, footers, continuation_indicators, log, progress):
    input_folder = filedialog.askdirectory(title="Select Input Folder")
    if not input_folder:
        return

    output_folder = filedialog.askdirectory(title="Select Output Folder")
    if not output_folder:
        return

    # Run the processing in a separate thread
    threading.Thread(target=process_pdfs, args=(input_folder, output_folder, headers, footers, continuation_indicators, log, progress)).start()

def edit_keywords(current_list, title):
    def add_keyword():
        keyword = simpledialog.askstring("Input", f"Enter {title} keyword:")
        if keyword:
            current_list.append(keyword)
            update_listbox()

    def remove_keyword():
        selected = listbox.curselection()
        if selected:
            current_list.pop(selected[0])
            update_listbox()

    def update_listbox():
        listbox.delete(0, tk.END)
        for item in current_list:
            listbox.insert(tk.END, item)

    keyword_window = tk.Toplevel()
    keyword_window.title(f"Edit {title} Keywords")
    listbox = tk.Listbox(keyword_window)
    listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

    button_frame = tk.Frame(keyword_window)
    button_frame.pack(side=tk.RIGHT, fill=tk.Y)

    add_button = tk.Button(button_frame, text="Add", command=add_keyword)
    add_button.pack(pady=5)

    remove_button = tk.Button(button_frame, text="Remove", command=remove_keyword)
    remove_button.pack(pady=5)

    update_listbox()

    keyword_window.mainloop()

def create_gui():
    root = tk.Tk()
    root.title("PDF Merge Tool")

    # Configure grid layout
    root.columnconfigure(0, weight=1)
    root.rowconfigure(0, weight=1)
    root.rowconfigure(1, weight=0)
    root.rowconfigure(2, weight=0)

    # Create a frame for buttons
    button_frame = tk.Frame(root)
    button_frame.grid(row=0, column=0, sticky="ew", padx=10, pady=10)

    headers = DEFAULT_HEADERS.copy()
    footers = DEFAULT_FOOTERS.copy()
    continuation_indicators = CONTINUATION_INDICATORS.copy()

    process_button = tk.Button(button_frame, text="Select Folders and Process", command=lambda: start_processing(headers, footers, continuation_indicators, log, progress))
    process_button.grid(row=0, column=0, padx=10, pady=5)

    edit_headers_button = tk.Button(button_frame, text="Edit Headers", command=lambda: edit_keywords(headers, "Header"))
    edit_headers_button.grid(row=0, column=1, padx=10, pady=5)

    edit_footers_button = tk.Button(button_frame, text="Edit Footers", command=lambda: edit_keywords(footers, "Footer"))
    edit_footers_button.grid(row=0, column=2, padx=10, pady=5)

    edit_continuation_button = tk.Button(button_frame, text="Edit Continuation Indicators", command=lambda: edit_keywords(continuation_indicators, "Continuation Indicator"))
    edit_continuation_button.grid(row=0, column=3, padx=10, pady=5)

    # Create a scrolled text widget for logs
    log = scrolledtext.ScrolledText(root, wrap=tk.WORD, height=15)
    log.grid(row=1, column=0, sticky="nsew", padx=10, pady=10)

    # Create a progress bar
    progress = ttk.Progressbar(root, orient=tk.HORIZONTAL, length=100, mode='determinate')
    progress.grid(row=2, column=0, sticky="ew", padx=10, pady=10)

    root.mainloop()

if __name__ == "__main__":
    create_gui()
