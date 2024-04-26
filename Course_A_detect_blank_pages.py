import os
import fitz

directory = r"C:\Users\calla\Documents\Shepherd Automation\Shepherd Automation\Code\Natif.AI\Cooke County\logs"

def is_blank_page(pdf_path, page_number):
    pdf_document = fitz.open(pdf_path)
    page = pdf_document[page_number]
    text = page.get_text("text")
    return not text.strip()  # Check if the page has no visible text

def remove_blank_pages(pdf_path):
    pdf_document = fitz.open(pdf_path)
    pages_to_remove = []

    for page_number in range(len(pdf_document)):
        if is_blank_page(pdf_path, page_number):
            pages_to_remove.append(page_number)

    # Remove blank pages in reverse order to avoid index issues
    for page_number in reversed(pages_to_remove):
        pdf_document.delete_page(page_number)

    # Save the modified PDF
    pdf_document.save("/path/to/modified/pdf/file.pdf")
    pdf_document.close()

# Example usage:


# first, we loop through the directory of files 
    # then we loop through the pages in each file deleting the blank ones
for filename in os.listdir(directory):
    pdf_path = os.path.join(directory, filename)
    pdf_document = fitz.open(pdf_path)
    for page_number in range(len(pdf_document)):
        if is_blank_page(pdf_path, page_number):
            print(f"{pdf_document}:Page {page_number} is blank.")