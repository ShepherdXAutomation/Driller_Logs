import os
import fitz

directory = "C:\Users\calla\Documents\Shepherd Automation\Shepherd Automation\Code\Natif.AI\Cooke County\logs"

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
    pdf_document = os.path.join(directory, filename)
    for page_number in range(len(pdf_document)):
        if is_blank_page(pdf_path, page_number):
            print(f"Page {page_number} is blank.")