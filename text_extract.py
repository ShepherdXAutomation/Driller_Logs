import fitz  # PyMuPDF

def test_text_extraction(pdf_path):
    try:
        doc = fitz.open(pdf_path)
        for page_num in range(len(doc)):
            page = doc[page_num]
            text = page.get_text().strip()
            print(f"Page {page_num + 1} Text ({len(text)} chars):")
            print(text[:200] + '...' if len(text) > 200 else text)  # Print first 200 chars
            print("-" * 80)
        doc.close()
    except Exception as e:
        print(f"Error opening {pdf_path}: {e}")

# Replace with the path to one of your PDFs
pdf_path = r"C:/Users/ChrisClayton/Desktop/test/BROWN DRILLERS LOGS BY OPERATOR G PDF MASTER_71.pdf"
test_text_extraction(pdf_path)
