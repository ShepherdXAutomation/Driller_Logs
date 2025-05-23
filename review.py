import os
import fitz  # PyMuPDF
from tkinter import Tk, Label, Button, filedialog, messagebox, Canvas
from PIL import Image, ImageTk

class PDFViewer:
    def __init__(self, master):
        self.master = master
        self.master.title("Quick PDF Viewer")

        self.pdf_document = None
        self.current_pdf = None
        self.current_page = 0
        self.pdf_files = []
        self.canvas = None
        self.tk_img = None

        self.label = Label(master, text="No folder selected")
        self.label.pack(pady=10)

        self.open_button = Button(master, text="Select Folder", command=self.select_folder)
        self.open_button.pack(pady=10)

        self.canvas = Canvas(master)
        self.canvas.pack()

        # Navigation buttons
        self.prev_button = Button(master, text="< Previous", command=self.show_previous_pdf, state='disabled')
        self.prev_button.pack(side='left', padx=5)

        self.next_button = Button(master, text="Next >", command=self.show_next_pdf, state='disabled')
        self.next_button.pack(side='right', padx=5)

        # Buttons to skip forward/backward by 10, 20, 50 logs
        self.skip_back_10 = Button(master, text="<< 10", command=lambda: self.skip_pdfs(-10), state='disabled')
        self.skip_back_10.pack(side='left', padx=5)

        self.skip_back_20 = Button(master, text="<< 20", command=lambda: self.skip_pdfs(-20), state='disabled')
        self.skip_back_20.pack(side='left', padx=5)

        self.skip_back_50 = Button(master, text="<< 50", command=lambda: self.skip_pdfs(-50), state='disabled')
        self.skip_back_50.pack(side='left', padx=5)

        self.skip_forward_10 = Button(master, text="10 >>", command=lambda: self.skip_pdfs(10), state='disabled')
        self.skip_forward_10.pack(side='right', padx=5)

        self.skip_forward_20 = Button(master, text="20 >>", command=lambda: self.skip_pdfs(20), state='disabled')
        self.skip_forward_20.pack(side='right', padx=5)

        self.skip_forward_50 = Button(master, text="50 >>", command=lambda: self.skip_pdfs(50), state='disabled')
        self.skip_forward_50.pack(side='right', padx=5)

        # Delete button
        self.delete_button = Button(master, text="Delete PDF", command=self.delete_pdf, state='disabled')
        self.delete_button.pack(pady=10)

        # Bind arrow keys and 'd' key for delete
        master.bind('<Left>', lambda event: self.show_previous_pdf())
        master.bind('<Right>', lambda event: self.show_next_pdf())
        master.bind('<d>', lambda event: self.delete_pdf())

    def select_folder(self):
        folder_path = filedialog.askdirectory()
        if folder_path:
            self.pdf_files = [os.path.join(folder_path, f) for f in os.listdir(folder_path) if f.endswith('.pdf')]
            self.pdf_files.sort()
            self.label.config(text=f"{len(self.pdf_files)} PDFs found")
            self.current_pdf = 0
            if self.pdf_files:
                self.load_pdf()
                self.update_buttons()

    def load_pdf(self):
        pdf_path = self.pdf_files[self.current_pdf]
        self.pdf_document = fitz.open(pdf_path)
        self.current_page = 0
        self.label.config(text=f"File: {os.path.basename(pdf_path)}")
        self.show_page()

    def show_page(self):
        if self.pdf_document:
            page = self.pdf_document.load_page(self.current_page)
            pix = page.get_pixmap()
            img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
            img.thumbnail((800, 600), Image.LANCZOS)

            self.tk_img = ImageTk.PhotoImage(img)
            self.canvas.config(width=img.width, height=img.height)
            self.canvas.create_image(0, 0, anchor='nw', image=self.tk_img)

    def show_next_pdf(self):
        if self.current_pdf < len(self.pdf_files) - 1:
            self.current_pdf += 1
            self.load_pdf()
            self.update_buttons()

    def show_previous_pdf(self):
        if self.current_pdf > 0:
            self.current_pdf -= 1
            self.load_pdf()
            self.update_buttons()

    def skip_pdfs(self, offset):
        new_index = self.current_pdf + offset
        if 0 <= new_index < len(self.pdf_files):
            self.current_pdf = new_index
            self.load_pdf()
            self.update_buttons()

    def delete_pdf(self):
        if self.pdf_document:
            self.pdf_document.close()
            pdf_path = self.pdf_files[self.current_pdf]
            if messagebox.askyesno("Delete", f"Are you sure you want to delete {os.path.basename(pdf_path)}?"):
                os.remove(pdf_path)
                del self.pdf_files[self.current_pdf]
                if self.current_pdf >= len(self.pdf_files):
                    self.current_pdf -= 1
                if self.pdf_files:
                    self.load_pdf()
                else:
                    self.canvas.delete("all")
                    self.label.config(text="No PDFs remaining")
                    self.update_buttons()

    def update_buttons(self):
        self.prev_button.config(state='normal' if self.current_pdf > 0 else 'disabled')
        self.next_button.config(state='normal' if self.current_pdf < len(self.pdf_files) - 1 else 'disabled')
        self.delete_button.config(state='normal' if self.pdf_files else 'disabled')

        # Enable/disable skip buttons based on the current PDF index
        self.skip_back_10.config(state='normal' if self.current_pdf >= 10 else 'disabled')
        self.skip_back_20.config(state='normal' if self.current_pdf >= 20 else 'disabled')
        self.skip_back_50.config(state='normal' if self.current_pdf >= 50 else 'disabled')
        self.skip_forward_10.config(state='normal' if self.current_pdf <= len(self.pdf_files) - 11 else 'disabled')
        self.skip_forward_20.config(state='normal' if self.current_pdf <= len(self.pdf_files) - 21 else 'disabled')
        self.skip_forward_50.config(state='normal' if self.current_pdf <= len(self.pdf_files) - 51 else 'disabled')

if __name__ == "__main__":
    root = Tk()
    pdf_viewer = PDFViewer(root)
    root.mainloop()
