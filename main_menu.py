import subprocess
import tkinter as tk
from tkinter import simpledialog, filedialog, messagebox, Button
from PIL import Image, ImageTk
import fitz  # PyMuPDF
import os
import openpyxl
import logging
import time

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
        logging.info("Initializing PDFSplitterApp")
        self.root = root
        self.root.withdraw()  # Hide the root window

        self.pdf_path, self.keywords, self.output_dir, self.manual_mode = self.get_user_input()
        self.cancelled = False  # Track cancellation
        self.process = None  # Initialize process as None

        self.root.protocol("WM_DELETE_WINDOW", self.on_close)  # Handle the "X" button

        if self.manual_mode:
            logging.info("Starting manual mode")
            self.manual_mode_split()
        else:
            logging.info("Starting automatic mode")
            self.run_split_pdf_by_header()

    def get_user_input(self):
        logging.info("Prompting user for input")
        pdf_path = filedialog.askopenfilename(title="Select PDF File", filetypes=[("PDF Files", "*.pdf")])
        keywords = simpledialog.askstring("Input", "Enter keywords to split by (comma-separated):")
        output_dir = filedialog.askdirectory(title="Select Output Directory")
        mode = messagebox.askyesno("Mode", "Would you like to enable manual mode?")
        logging.info(f"User selected PDF: {pdf_path}, Keywords: {keywords}, Output Directory: {output_dir}, Manual Mode: {mode}")
        return pdf_path, keywords.split(','), output_dir, mode

    def run_split_pdf_by_header(self):
        logging.info("Running split PDF by header")
        # Add a pop-up window with a cancel button
        self.cancel_window = tk.Toplevel(self.root)
        self.cancel_window.title("Cancel Operation")
        self.cancel_button = Button(self.cancel_window, text="Cancel", command=self.cancel_operation)
        self.cancel_button.pack(pady=20)

        # Run the splitting directly without a separate thread
        self.split_pdf_by_header_thread()

    def split_pdf_by_header_thread(self):
        logging.info("Starting split_pdf_by_header_thread")
        command = ["python", "Split_PDF_by_header.py", self.pdf_path, "--keywords"] + self.keywords + ["--output_dir", self.output_dir]
        logging.info(f"Executing command: {command}")
        self.process = subprocess.Popen(command)
        logging.info(f"Subprocess started with PID: {self.process.pid}")

        while self.process.poll() is None:
            logging.info("Process still running")
            if self.cancelled:
                logging.info("Process cancelled, attempting to terminate")
                self.process.terminate()
                self.process.wait()  # Wait for the process to terminate
                logging.info("Process terminated")
                messagebox.showinfo("Cancelled", "The splitting operation has been cancelled.")
                self.cancel_window.destroy()
                return

            time.sleep(1)  # Add sleep to reduce CPU usage in the loop

        logging.info("Process completed")
        self.cancel_window.destroy()
        messagebox.showinfo("Completed", "Automatic splitting completed successfully.")

    def cancel_operation(self):
        logging.info("Cancellation requested")
        self.cancelled = True

    def manual_mode_split(self):
        logging.info("Manual mode split initiated")
        self.pdf_document = fitz.open(self.pdf_path)

        if not os.path.exists(self.output_dir):
            logging.info(f"Output directory {self.output_dir} does not exist, creating it")
            os.makedirs(self.output_dir)

        self.split_start_page = 0
        self.split_counter = 1
        self.page_num = 0
        self.large_files = []

        self.root.deiconify()  # Show the root window
        self.canvas = tk.Canvas(self.root)
        self.canvas.pack()

        # Add a cancel button to the manual mode window
        self.cancel_button = Button(self.root, text="Cancel", command=self.cancel_operation)
        self.cancel_button.pack(pady=10)

        self.show_page()

    def show_page(self):
        logging.info(f"Showing page {self.page_num + 1}")
        if self.cancelled:
            logging.info("Operation cancelled during show_page")
            self.cleanup()
            return

        page = self.pdf_document.load_page(self.page_num)
        pix = page.get_pixmap()
        img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
        img.thumbnail((800, 600), Image.LANCZOS)

        self.tk_img = ImageTk.PhotoImage(img)
        self.canvas.config(width=img.width, height=img.height)
        self.canvas.create_image(0, 0, anchor=tk.NW, image=self.tk_img)
        
        self.root.update()
        self.ask_split()

    def ask_split(self):
        logging.info(f"Asking for split decision after page {self.page_num + 1}")
        split = messagebox.askyesno("Split", f"Split after page {self.page_num + 1}?")

        if split:
            logging.info(f"Splitting after page {self.page_num + 1}")
            self.split_pdf(self.page_num)
        
        self.page_num += 1
        if self.page_num < len(self.pdf_document):
            self.canvas.delete("all")  # Clear the canvas
            self.show_page()
        else:
            if self.split_start_page < len(self.pdf_document):
                logging.info("Final split after last page")
                self.split_pdf(len(self.pdf_document) - 1)
            self.cleanup()

    def split_pdf(self, page_num):
        logging.info(f"Splitting PDF from page {self.split_start_page + 1} to {page_num + 1}")
        if page_num >= self.split_start_page:
            original_file_name = os.path.splitext(os.path.basename(self.pdf_path))[0]
            
            split_pdf_path = os.path.join(self.output_dir, f'{original_file_name}_{self.split_counter}.pdf')

            logging.info(f"Original file name: {original_file_name}")
            logging.info(f"Generated split file path: {split_pdf_path}")
            
            split_doc = fitz.open()
            for split_page_num in range(self.split_start_page, page_num + 1):
                split_doc.insert_pdf(self.pdf_document, from_page=split_page_num, to_page=split_page_num)
            split_doc.save(split_pdf_path)
            split_doc.close()

            file_size_kb = os.path.getsize(split_pdf_path) / 1024
            if file_size_kb > 4000:
                logging.info(f"File {split_pdf_path} is large ({file_size_kb} KB), adding to large_files list")
                self.large_files.append((split_pdf_path, file_size_kb))

            self.split_counter += 1
            self.split_start_page = page_num + 1

    def cleanup(self):
        logging.info("Cleaning up and closing the application")
        self.pdf_document.close()
        if self.process and self.process.poll() is None:
            logging.info(f"Process with PID {self.process.pid} still running, attempting to terminate")
            self.process.terminate()
            self.process.wait()
            logging.info("Process terminated during cleanup")
        if hasattr(self, 'root'):
            self.root.quit()

    def on_close(self):
        logging.info("Close requested via window manager")
        self.cancel_operation()
        logging.info("Exiting application")
        self.cleanup()

def write_large_files_to_excel(large_files, excel_path="output_files_over_4000KB.xlsx"):
    logging.info(f"Writing large files to Excel at {excel_path}")
    workbook = openpyxl.Workbook()
    sheet = workbook.active
    sheet.title = "Large Files"
    sheet.append(["File Name", "Size (KB)"])

    for file_path, size_kb in large_files:
        logging.info(f"Adding {file_path} with size {size_kb} KB to Excel sheet")
        sheet.append([file_path, size_kb])

    workbook.save(excel_path)
    logging.info(f"Excel sheet created at {excel_path} with large files listed.")

# Main execution
logging.info("Starting main application")
root = tk.Tk()
app = PDFSplitterApp(root)
root.mainloop()
logging.info("Main loop terminated, writing large files to Excel")
if hasattr(app, 'large_files'):
    write_large_files_to_excel(app.large_files)