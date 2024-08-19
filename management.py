import subprocess
import tkinter as tk
from tkinter import simpledialog, filedialog, messagebox, Button
from PIL import Image, ImageTk
import fitz  # PyMuPDF
import os
import openpyxl
import threading

class PDFSplitterApp:
    def __init__(self, root):
        self.root = root
        self.root.withdraw()  # Hide the root window

        self.pdf_path, self.keywords, self.output_dir, self.manual_mode = self.get_user_input()
        self.cancelled = False  # Track cancellation

        if self.manual_mode:
            self.manual_mode_split()
        else:
            self.run_split_pdf_by_header()

    def get_user_input(self):
        pdf_path = filedialog.askopenfilename(title="Select PDF File", filetypes=[("PDF Files", "*.pdf")])
        keywords = simpledialog.askstring("Input", "Enter keywords to split by (comma-separated):")
        output_dir = filedialog.askdirectory(title="Select Output Directory")
        mode = messagebox.askyesno("Mode", "Would you like to enable manual mode?")
        return pdf_path, keywords.split(','), output_dir, mode

    def run_split_pdf_by_header(self):
        # Add a pop-up window with a cancel button
        self.cancel_window = tk.Toplevel(self.root)
        self.cancel_window.title("Cancel Operation")
        self.cancel_button = Button(self.cancel_window, text="Cancel", command=self.cancel_operation)
        self.cancel_button.pack(pady=20)

        # Run the splitting in a separate thread to allow cancellation
        self.split_thread = threading.Thread(target=self.split_pdf_by_header_thread)
        self.split_thread.start()

    def split_pdf_by_header_thread(self):
        command = ["python", "Split_PDF_by_header.py", self.pdf_path, "--keywords"] + self.keywords + ["--output_dir", self.output_dir]
        process = subprocess.Popen(command)

        while process.poll() is None:
            if self.cancelled:
                process.terminate()
                messagebox.showinfo("Cancelled", "The splitting operation has been cancelled.")
                self.cancel_window.destroy()
                return

        self.cancel_window.destroy()
        messagebox.showinfo("Completed", "Automatic splitting completed successfully.")

    def cancel_operation(self):
        self.cancelled = True

    def manual_mode_split(self):
        self.pdf_document = fitz.open(self.pdf_path)

        if not os.path.exists(self.output_dir):
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
        if self.cancelled:
            self.pdf_document.close()
            messagebox.showinfo("Cancelled", "The splitting operation has been cancelled.")
            self.root.quit()
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
        split = messagebox.askyesno("Split", f"Split after page {self.page_num + 1}?")

        if split:
            self.split_pdf(self.page_num)
        
        self.page_num += 1
        if self.page_num < len(self.pdf_document):
            self.canvas.delete("all")  # Clear the canvas
            self.show_page()
        else:
            if self.split_start_page < len(self.pdf_document):
                self.split_pdf(len(self.pdf_document) - 1)
            self.pdf_document.close()
            print("Manual splitting completed successfully.")
            self.root.quit()

    def split_pdf(self, page_num):
        if page_num >= self.split_start_page:
            split_pdf_path = os.path.join(self.output_dir, f'split_{self.split_counter}.pdf')
            split_doc = fitz.open()
            for split_page_num in range(self.split_start_page, page_num + 1):
                split_doc.insert_pdf(self.pdf_document, from_page=split_page_num, to_page=split_page_num)
            split_doc.save(split_pdf_path)
            split_doc.close()

            # Check file size and add to large_files list if over 4000 KB
            file_size_kb = os.path.getsize(split_pdf_path) / 1024
            if file_size_kb > 4000:
                self.large_files.append((split_pdf_path, file_size_kb))

            self.split_counter += 1
            self.split_start_page = page_num + 1

def write_large_files_to_excel(large_files, excel_path="output_files_over_4000KB.xlsx"):
    workbook = openpyxl.Workbook()
    sheet = workbook.active
    sheet.title = "Large Files"
    sheet.append(["File Name", "Size (KB)"])

    for file_path, size_kb in large_files:
        sheet.append([file_path, size_kb])

    workbook.save(excel_path)
    print(f"Excel sheet created at {excel_path} with large files listed.")

def main():
    root = tk.Tk()
    app = PDFSplitterApp(root)
    root.mainloop()
    # Write the large files to Excel after the application loop ends
    if hasattr(app, 'large_files'):
        write_large_files_to_excel(app.large_files)

if __name__ == "__main__":
    main()
