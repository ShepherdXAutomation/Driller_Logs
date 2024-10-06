import fitz  # PyMuPDF
import pytesseract
from PIL import Image, ImageTk
import os
import tkinter as tk
from tkinter import filedialog, messagebox, simpledialog, ttk
import logging
import threading

# Set up logging
log_file_path = os.path.join(os.getcwd(), 'pdf_splitter.log')
logging.basicConfig(filename=log_file_path, level=logging.DEBUG,
                    format='%(asctime)s - %(levelname)s - %(message)s')

# Adding a stream handler to log to the console
console = logging.StreamHandler()
console.setLevel(logging.DEBUG)
formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
console.setFormatter(formatter)
logging.getLogger().addHandler(console)

class PDFSplitterApp:
    def __init__(self, root):
        self.root = root
        self.pdf_document = None
        self.split_start_page = 0
        self.split_counter = 1
        self.page_num = 0
        self.canvas = None
        self.output_dir = None
        self.pdf_paths = []
        self.large_files = []
        self.progress_bar = None
        self.progress_label = None
        self.cancelled = False
        self.split_thread = None

    def ocr_page(self, page):
        """Perform OCR on a PDF page to extract text."""
        pix = page.get_pixmap()
        img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
        text = pytesseract.image_to_string(img)
        return text

    def get_next_available_filename(self, base_name, output_dir):
        """Get the next available filename that doesn't overwrite existing files."""
        counter = 1
        while True:
            file_name = f'{base_name}_{counter}.pdf'
            if not os.path.exists(os.path.join(output_dir, file_name)):
                return file_name
            counter += 1

    def split_pdf_by_keywords(self, pdf_path, keywords, output_dir):
        """Split the PDF based on the occurrence of keywords."""
        if self.cancelled:
            logging.info("Splitting operation cancelled before starting.")
            return

        pdf_document = fitz.open(pdf_path)
        keywords = [keyword.lower() for keyword in keywords]

        original_file_name = os.path.splitext(os.path.basename(pdf_path))[0]
        pdf_output_dir = os.path.join(output_dir, original_file_name)  # Create folder named after the PDF
        if not os.path.exists(pdf_output_dir):
            os.makedirs(pdf_output_dir)

        split_start_page = 0
        self.split_counter = 1  # Reset the counter for each new operation

        total_pages = len(pdf_document)

        for page_num in range(total_pages):
            if self.cancelled:
                logging.info("Splitting operation cancelled by user.")
                return

            page = pdf_document.load_page(page_num)
            text = self.ocr_page(page).lower()

            if any(keyword in text for keyword in keywords):
                if page_num > split_start_page:
                    split_file_name = self.get_next_available_filename(original_file_name, pdf_output_dir)
                    split_pdf_path = os.path.join(pdf_output_dir, split_file_name)
                    split_doc = fitz.open()
                    for split_page_num in range(split_start_page, page_num):
                        split_doc.insert_pdf(pdf_document, from_page=split_page_num, to_page=split_page_num)
                    split_doc.save(split_pdf_path)
                    split_doc.close()
                    self.split_counter += 1

                split_start_page = page_num

            # Update the progress bar for the current file
            self.update_progress_bar(page_num + 1, total_pages)

        if not self.cancelled and split_start_page < total_pages:
            split_file_name = self.get_next_available_filename(original_file_name, pdf_output_dir)
            split_pdf_path = os.path.join(pdf_output_dir, split_file_name)
            split_doc = fitz.open()
            for split_page_num in range(split_start_page, total_pages):
                split_doc.insert_pdf(pdf_document, from_page=split_page_num, to_page=split_page_num)
            split_doc.save(split_pdf_path)
            split_doc.close()

            if not self.cancelled:
                logging.info(f"Splitting completed for {pdf_path}. Total PDFs created: {self.split_counter}")

    def start_splitting(self):
        self.cancelled = False  # Reset the cancelled flag

        # Select multiple PDF files
        pdf_paths = filedialog.askopenfilenames(title="Select PDF Files", filetypes=[("PDF Files", "*.pdf")])
        if not pdf_paths:
            return

        keywords = simpledialog.askstring("Input", "Enter keywords to split by (comma-separated):")
        if not keywords:
            return

        output_dir = filedialog.askdirectory(title="Select Output Directory")
        if not output_dir:
            return

        keywords = keywords.split(',')

        # Run splitting in a separate thread to keep GUI responsive
        self.split_thread = threading.Thread(target=self.process_multiple_pdfs, args=(pdf_paths, keywords, output_dir))
        self.split_thread.start()

    def process_multiple_pdfs(self, pdf_paths, keywords, output_dir):
        total_files = len(pdf_paths)
        for idx, pdf_path in enumerate(pdf_paths, start=1):
            if self.cancelled:
                logging.info("Splitting operation cancelled. Stopping all further processing.")
                break

            file_name = os.path.basename(pdf_path)  # Get just the file name, not the full path
            logging.info(f"Processing {file_name}")
            self.current_file_label.config(text=f"Processing: {file_name}")
            self.progress_label.config(text=f"Processing file {idx}/{total_files}")
            self.split_pdf_by_keywords(pdf_path, keywords, output_dir)

        self.progress_bar["value"] = 0  # Reset the progress bar after completion
        self.progress_label.config(text="Progress: 0%")  # Reset the progress label
        self.current_file_label.config(text="")  # Clear the current file label
        self.cancelled = False  # Reset cancellation flag

        if not self.cancelled:
            messagebox.showinfo("Completed", "Splitting completed for all selected files.")

    def update_progress_bar(self, current_page, total_pages):
        """Update the progress bar for the current file."""
        progress_percentage = int((current_page / total_pages) * 100)
        self.progress_bar["value"] = progress_percentage
        self.progress_label.config(text=f"Progress: {progress_percentage}%")
        self.root.update_idletasks()

    def cancel_splitting(self):
        self.cancelled = True
        logging.info("Splitting operation cancelled by user.")

    def start_manual_splitting(self):
        self.pdf_paths = filedialog.askopenfilenames(title="Select PDF Files", filetypes=[("PDF Files", "*.pdf")])
        if not self.pdf_paths:
            return

        self.output_dir = filedialog.askdirectory(title="Select Output Directory")
        if not self.output_dir:
            return

        self.root.withdraw()  # Hide the root window
        self.manual_split_window = tk.Toplevel(self.root)
        self.manual_split_window.title("Manual PDF Splitter")
        self.manual_split_window.geometry("850x700")

        self.canvas = tk.Canvas(self.manual_split_window)
        self.canvas.pack()

        self.cancel_button = tk.Button(self.manual_split_window, text="Cancel", command=self.cancel_manual_splitting)
        self.cancel_button.pack(pady=0)

        self.split_next_pdf()

    def split_next_pdf(self):
        if self.pdf_paths:
            self.pdf_path = self.pdf_paths.pop(0)
            self.original_file_name = os.path.splitext(os.path.basename(self.pdf_path))[0]
            self.pdf_document = fitz.open(self.pdf_path)
            self.split_start_page = 0
            self.split_counter = 1
            self.page_num = 0
            self.show_page()
        else:
            self.cleanup()

    def cancel_manual_splitting(self):
        self.manual_split_window.destroy()
        self.cleanup()

    def show_page(self):
        if self.page_num < len(self.pdf_document):
            page = self.pdf_document.load_page(self.page_num)
            pix = page.get_pixmap()
            img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
            img.thumbnail((800, 600), Image.LANCZOS)

            self.tk_img = ImageTk.PhotoImage(img)
            self.canvas.config(width=img.width, height=img.height)
            self.canvas.create_image(0, 0, anchor=tk.NW, image=self.tk_img)

            self.manual_split_window.update()
            self.ask_split()
        else:
            if self.split_start_page < len(self.pdf_document):
                self.split_pdf(len(self.pdf_document) - 1)
            self.split_next_pdf()

    def ask_split(self):
        split = messagebox.askyesno("Split", f"Split after page {self.page_num + 1}?")

        if split:
            self.split_pdf(self.page_num)

        self.page_num += 1
        if self.page_num < len(self.pdf_document):
            self.canvas.delete("all")  # Clear the canvas
            self.show_page()

    def split_pdf(self, page_num):
        if page_num >= self.split_start_page:
            pdf_output_dir = os.path.join(self.output_dir, self.original_file_name)
            if not os.path.exists(pdf_output_dir):
                os.makedirs(pdf_output_dir)

            split_file_name = self.get_next_available_filename(self.original_file_name, pdf_output_dir)
            split_pdf_path = os.path.join(pdf_output_dir, split_file_name)

            split_doc = fitz.open()
            for split_page_num in range(self.split_start_page, page_num + 1):
                split_doc.insert_pdf(self.pdf_document, from_page=split_page_num, to_page=split_page_num)
            split_doc.save(split_pdf_path)
            split_doc.close()

            self.split_counter += 1
            self.split_start_page = page_num + 1

    def cleanup(self):
        if self.pdf_document:
            self.pdf_document.close()
        if hasattr(self, 'manual_split_window') and self.manual_split_window.winfo_exists():
            self.manual_split_window.destroy()
        self.root.deiconify()  # Show the root window again


def main():
    root = tk.Tk()
    root.title("PDF Splitter")

     # Set the window size to start at 600px width and 400px height
    root.geometry("600x400")  # Set the width to 600px and height to 400px

    # Create a fixed-size frame inside the root window
    container = tk.Frame(root, width=600, height=30)
    container.pack_propagate(False)  # Prevent the frame from resizing to fit the contents
    container.pack(fill="both", expand=True)

    app = PDFSplitterApp(root)

    tk.Button(root, text="Start Automatic Splitting", command=app.start_splitting).pack(pady=5)
    tk.Button(root, text="Start Manual Splitting", command=app.start_manual_splitting).pack(pady=5)

    # Add progress bar and label
    app.progress_bar = ttk.Progressbar(root, orient="horizontal", length=200, mode="determinate")
    app.progress_bar.pack(pady=5)

    app.progress_label = tk.Label(root, text="Progress: 0%")
    app.progress_label.pack(pady=5)

    # Add a label to show the current file being processed
    app.current_file_label = tk.Label(root, text="Processing: None")
    app.current_file_label.pack(pady=5)

    # Add cancel button
    cancel_button = tk.Button(root, text="Cancel", command=app.cancel_splitting)
    cancel_button.pack(pady=5)

    # Adjust the main window size to fit the widgets snugly
    root.update_idletasks()  # Ensure all widgets are rendered
    root.geometry(f"{root.winfo_reqwidth()}x{root.winfo_reqheight()}")  # Resize window to fit widgets

    root.mainloop()


if __name__ == "__main__":
    main()
