import fitz
import pytesseract
from PIL import Image
import os
import argparse
import tkinter as tk
from tkinter import messagebox

def ocr_page(page):
    # Convert PDF page to an image
    pix = page.get_pixmap()
    img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
    # Perform OCR on the image
    text = pytesseract.image_to_string(img)
    return text

def split_pdf_by_keywords(pdf_path, keywords, output_dir):
    # Open the PDF file
    pdf_document = fitz.open(pdf_path)
    keywords = [keyword.lower() for keyword in keywords]
    
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    # Variables to keep track of the current split
    split_start_page = 0
    split_counter = 1

    for page_num in range(len(pdf_document)):
        page = pdf_document.load_page(page_num)
        text = ocr_page(page).lower()

        # Debugging: Print the text of the first 5 pages
        if page_num < 5:
            print(f"Page {page_num + 1} Text:\n{text}\n{'-'*40}")

        if any(keyword in text for keyword in keywords):
            # Save the split PDF
            if page_num > split_start_page:
                split_pdf_path = os.path.join(output_dir, f'split_{split_counter}.pdf')
                split_doc = fitz.open()  # Create a new PDF document
                for split_page_num in range(split_start_page, page_num):
                    split_doc.insert_pdf(pdf_document, from_page=split_page_num, to_page=split_page_num)
                split_doc.save(split_pdf_path)
                split_doc.close()
                split_counter += 1

            # Update the start page for the next split
            split_start_page = page_num
    
    # Save the last split
    if split_start_page < len(pdf_document):
        split_pdf_path = os.path.join(output_dir, f'split_{split_counter}.pdf')
        split_doc = fitz.open()  # Create a new PDF document
        for split_page_num in range(split_start_page, len(pdf_document)):
            split_doc.insert_pdf(pdf_document, from_page=split_page_num, to_page=split_page_num)
        split_doc.save(split_pdf_path)
        split_doc.close()

    pdf_document.close()
    print("Splitting completed successfully.")

    # Show completion message with the number of PDFs created
    root = tk.Tk()
    root.withdraw()  # Hide the root window
    messagebox.showinfo("Completed", f"Splitting completed successfully.\nTotal PDFs created: {split_counter}")
    root.destroy()

def main():
    parser = argparse.ArgumentParser(description="Split PDF by keywords")
    parser.add_argument("pdf_path", type=str, help="Path to the PDF file")
    parser.add_argument("--keywords", type=str, nargs="+", default=["Bess Mason Log Service", "Texas Well Log Service", "Panhandle"],
                        help="Keywords to split the PDF by")
    parser.add_argument("--output_dir", type=str, default="../split_pdfs",
                        help="Directory to save the split PDFs")

    args = parser.parse_args()

    split_pdf_by_keywords(args.pdf_path, args.keywords, args.output_dir)

if __name__ == "__main__":
    main()
