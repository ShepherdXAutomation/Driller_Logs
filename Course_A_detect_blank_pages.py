import fitz  # PyMuPDF
from PIL import Image
import numpy as np
import os
import pandas as pd
def is_blank_page_by_pixels(page, dark_threshold=50, black_pixel_threshold=0.01):
    """
    Determine if a page is blank based on the count of truly dark pixels.
    
    Parameters:
    - page: The PDF page object.
    - dark_threshold: Pixel intensity threshold; pixels darker (less than this value) are considered black.
    - black_pixel_threshold: Percentage of dark pixels below which a page is considered blank.
    """
    # Render page as a pixmap (an image)
    pix = page.get_pixmap()
    img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
    
    # Convert the image to grayscale
    gray = img.convert('L')
    
    # Apply threshold to turn gray/dark pixels into white and keep only truly dark pixels as black
    # Any pixel value below 'dark_threshold' is turned black (0), otherwise white (255)
    bw = gray.point(lambda p: 0 if p < dark_threshold else 255, '1')
    
    # Convert to numpy array for analysis
    np_image = np.array(bw)
    
    # Count black pixels (in this '1' image, 0 is black and 1 is white)
    black_pixels = np.sum(np_image == 0)
    total_pixels = np_image.size
    
    # Calculate black pixel ratio
    black_pixel_ratio = black_pixels / total_pixels

    print(f"Black pixels: {black_pixels}")
    
    # Consider the page blank if the black pixel ratio is below the black_pixel_threshold
    return black_pixels < 20
blanks = []
# Example usage:
directory = r"C:\Users\calla\Documents\Shepherd Automation\Shepherd Automation\Code\Natif.AI\Driller_Logs\logs"
for filename in os.listdir(directory):
    pdf_path = os.path.join(directory, filename)
    doc = fitz.open(pdf_path)
    for page_number, page in enumerate(doc, start=1):
        if is_blank_page_by_pixels(page):
            print(f"Page {pdf_path} is considered blank.")
            blanks.append(pdf_path)
        else:
            continue
for item in blanks:
    print(item)
blank_files_log = 'filenames.xlsx'
if os.path.exists(blank_files_log):
    os.remove(blank_files_log)
# Create a DataFrame
df = pd.DataFrame(blanks, columns=['Filename'])
# Save to Excel
df.to_excel('filenames.xlsx', index=False)