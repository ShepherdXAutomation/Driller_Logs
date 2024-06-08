import subprocess
import tkinter as tk
from tkinter import simpledialog, filedialog, messagebox
from PIL import Image, ImageTk
import fitz  # PyMuPDF
import os

def get_user_input():
    root = tk.Tk()
    root.withdraw()  # Hide the root window

    pdf_path = filedialog.askopenfilename(title="Select PDF File", filetypes=[("PDF Files", "*.pdf")])
    keywords = simpledialog.askstring("Input", "Enter keywords to split by (comma-separated):")
    output_dir = filedialog.askdirectory(title="Select Output Directory")
    mode = messagebox.askyesno("Mode", "Would you like to enable manual mode?")

    return pdf_path, keywords.split(','), output_dir, mode

def run_split_pdf_by_header(pdf_path, keywords, output_dir):
    command = ["python", "Split_PDF_by_header.py", pdf_path, "--keywords"] + keywords + ["--output_dir", output_dir]
    subprocess.run(command)

def manual_mode_split(pdf_path, output_dir):
    pdf_document = fitz.open(pdf_path)
    
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    split_start_page = 0
    split_counter = 1

    for page_num in range(len(pdf_document)):
        page = pdf_document.load_page(page_num)
        pix = page.get_pixmap()
        img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
        img.show()

        root = tk.Tk()
        root.withdraw()  # Hide the root window
        split = messagebox.askyesno("Split", f"Split after page {page_num + 1}?")
        root.destroy()

        if split:
            if page_num > split_start_page:
                split_pdf_path = os.path.join(output_dir, f'split_{split_counter}.pdf')
                split_doc = fitz.open()
                for split_page_num in range(split_start_page, page_num):
                    split_doc.insert_pdf(pdf_document, from_page=split_page_num, to_page=split_page_num)
                split_doc.save(split_pdf_path)
                split_doc.close()
                split_counter += 1
            split_start_page = page_num + 1

    if split_start_page < len(pdf_document):
        split_pdf_path = os.path.join(output_dir, f'split_{split_counter}.pdf')
        split_doc = fitz.open()
        for split_page_num in range(split_start_page, len(pdf_document)):
            split_doc.insert_pdf(pdf_document, from_page=split_page_num, to_page=split_page_num)
        split_doc.save(split_pdf_path)
        split_doc.close()

    pdf_document.close()
    print("Manual splitting completed successfully.")

def main():
    pdf_path, keywords, output_dir, manual_mode = get_user_input()
    if manual_mode:
        manual_mode_split(pdf_path, output_dir)
    else:
        run_split_pdf_by_header(pdf_path, keywords, output_dir)

if __name__ == "__main__":
    main()
