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
        self.pdf_path = None
        self.original_file_name = None
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
        pdf_document = fitz.open(pdf_path)
        keywords = [keyword.lower() for keyword in keywords]

        if not os.path.exists(output_dir):
            os.makedirs(output_dir)

        split_start_page = 0
        self.split_counter = 1  # Reset the counter for each new operation
        original_file_name = os.path.splitext(os.path.basename(pdf_path))[0]

        total_pages = len(pdf_document)
        self.progress_bar["maximum"] = total_pages

        for page_num in range(total_pages):
            if self.cancelled:
                logging.info("Splitting operation cancelled by user.")
                messagebox.showinfo("Cancelled", "The splitting operation has been cancelled.")
                break

            page = pdf_document.load_page(page_num)
            text = self.ocr_page(page).lower()

            if any(keyword in text for keyword in keywords):
                if page_num > split_start_page:
                    split_file_name = self.get_next_available_filename(original_file_name, output_dir)
                    split_pdf_path = os.path.join(output_dir, split_file_name)
                    split_doc = fitz.open()
                    for split_page_num in range(split_start_page, page_num):
                        split_doc.insert_pdf(pdf_document, from_page=split_page_num, to_page=split_page_num)
                    split_doc.save(split_pdf_path)
                    split_doc.close()
                    self.split_counter += 1

                split_start_page = page_num

            self.progress_bar["value"] = page_num + 1
            progress_percentage = int((page_num + 1) / total_pages * 100)
            self.progress_label.config(text=f"Progress: {progress_percentage}%")
            self.root.update_idletasks()

        if not self.cancelled and split_start_page < total_pages:
            split_file_name = self.get_next_available_filename(original_file_name, output_dir)
            split_pdf_path = os.path.join(output_dir, split_file_name)
            split_doc = fitz.open()
            for split_page_num in range(split_start_page, total_pages):
                split_doc.insert_pdf(pdf_document, from_page=split_page_num, to_page=split_page_num)
            split_doc.save(split_pdf_path)
            split_doc.close()

            if not self.cancelled:
                messagebox.showinfo("Completed", f"Splitting completed successfully.\nTotal PDFs created: {self.split_counter}")

        self.progress_bar["value"] = 0  # Reset the progress bar after completion
        self.progress_label.config(text="Progress: 0%")  # Reset the progress label
        self.cancelled = False  # Reset cancellation flag

    def start_splitting(self):
        self.cancelled = False  # Reset the cancelled flag
        pdf_path = filedialog.askopenfilename(title="Select PDF File", filetypes=[("PDF Files", "*.pdf")])
        if not pdf_path:
            return

        keywords = simpledialog.askstring("Input", "Enter keywords to split by (comma-separated):")
        if not keywords:
            return

        output_dir = filedialog.askdirectory(title="Select Output Directory")
        if not output_dir:
            return

        keywords = keywords.split(',')

        # Run splitting in a separate thread to keep GUI responsive
        self.split_thread = threading.Thread(target=self.split_pdf_by_keywords, args=(pdf_path, keywords, output_dir))
        self.split_thread.start()

    def cancel_splitting(self):
        self.cancelled = True
        # No need to join the thread; just allow it to exit naturally

    def start_manual_splitting(self):
        self.pdf_path = filedialog.askopenfilename(title="Select PDF File", filetypes=[("PDF Files", "*.pdf")])
        if not self.pdf_path:
            return

        self.output_dir = filedialog.askdirectory(title="Select Output Directory")
        if not self.output_dir:
            return

        self.original_file_name = os.path.splitext(os.path.basename(self.pdf_path))[0]

        self.pdf_document = fitz.open(self.pdf_path)

        if not os.path.exists(self.output_dir):
            os.makedirs(self.output_dir)

        self.split_start_page = 0
        self.split_counter = 1
        self.page_num = 0

        self.root.withdraw()  # Hide the root window
        self.manual_split_window = tk.Toplevel(self.root)
        self.manual_split_window.title("Manual PDF Splitter")
        self.manual_split_window.geometry("850x700")

        self.canvas = tk.Canvas(self.manual_split_window)
        self.canvas.pack()

        self.cancel_button = tk.Button(self.manual_split_window, text="Cancel", command=self.cancel_manual_splitting)
        self.cancel_button.pack(pady=0)

        self.show_page()

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
            self.cleanup()

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
            split_file_name = self.get_next_available_filename(self.original_file_name, self.output_dir)
            split_pdf_path = os.path.join(self.output_dir, split_file_name)

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

    app = PDFSplitterApp(root)

    tk.Button(root, text="Start Automatic Splitting", command=app.start_splitting).pack(pady=5)
    tk.Button(root, text="Start Manual Splitting", command=app.start_manual_splitting).pack(pady=5)

    # Add progress bar and label
    app.progress_bar = ttk.Progressbar(root, orient="horizontal", length=200, mode="determinate")
    app.progress_bar.pack(pady=5)

    app.progress_label = tk.Label(root, text="Progress: 0%")
    app.progress_label.pack(pady=5)

    # Add cancel button
    cancel_button = tk.Button(root, text="Cancel", command=app.cancel_splitting)
    cancel_button.pack(pady=5)

    # Adjust the main window size to fit the widgets snugly
    root.update_idletasks()  # Ensure all widgets are rendered
    root.geometry(f"{root.winfo_reqwidth()}x{root.winfo_reqheight()}")  # Resize window to fit widgets

    root.mainloop()

if __name__ == "__main__":
    main()