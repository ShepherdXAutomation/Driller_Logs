import fitz  # PyMuPDF

def split_pdf_by_header(pdf_path, header_text):
    pdf_document = fitz.open(pdf_path)
    output_files = []
    new_pdf = fitz.open()

    for page_num in range(len(pdf_document)):
        page = pdf_document.load_page(page_num)
        text = page.get_text("text")

        if header_text in text and new_pdf.page_count > 0:
            output_filename = f"{header_text}_part_{len(output_files)+1}.pdf"
            new_pdf.save(output_filename)
            output_files.append(output_filename)
            new_pdf = fitz.open()

        new_pdf.insert_pdf(pdf_document, from_page=page_num, to_page=page_num)

    if new_pdf.page_count > 0:
        output_filename = f"{header_text}_part_{len(output_files)+1}.pdf"
        new_pdf.save(output_filename)
        output_files.append(output_filename)

    return output_files

# Usage
split_pdf_by_header('path_to_your_large_pdf.pdf', 'Bess Mason Log Service')
