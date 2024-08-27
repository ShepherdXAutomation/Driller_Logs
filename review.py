import os
from tkinter import Tk, Label, Button, filedialog, PhotoImage
from PyPDF2 import PdfFileReader
from PIL import Image, ImageTk
import io

class PDFViewer:
    def __init__(self, master):
        self.master = master
        self.master.title("PDF Quick Viewer")
        
        self.label = Label(master, text="No folder selected")
        self.label.pack(pady=10)

        self.image_label = Label(master)
        self.image_label.pack()

        self.prev_button = Button(master, text="< Previous", command=self.show_previous_pdf, state='disabled')
        self.prev_button.pack(side='left', padx=20)

        self.next_button = Button(master, text="Next >", command=self.show_next_pdf, state='disabled')
        self.next_button.pack(side='right', padx=20)

        self.open_button = Button(master, text="Select Folder", command=self.select_folder)
        self.open_button.pack(pady=20)

        self.pdf_files = []
        self.current_index = -1

    def select_folder(self):
        folder_path = filedialog.askdirectory()
        if folder_path:
            self.pdf_files = [os.path.join(folder_path, f) for f in os.listdir(folder_path) if f.endswith('.pdf')]
            self.pdf_files.sort()
            self.label.config(text=f"{len(self.pdf_files)} PDFs found")
            self.current_index = 0
            if self.pdf_files:
                self.show_pdf()
                self.update_buttons()

    def show_pdf(self):
        pdf_path = self.pdf_files[self.current_index]
        with open(pdf_path, 'rb') as file:
            pdf_reader = PdfFileReader(file)
            first_page = pdf_reader.getPage(0)
            pdf_text = first_page.extract_text()
            self.label.config(text=f"File: {os.path.basename(pdf_path)}")
            self.display_pdf_image(first_page)

    def display_pdf_image(self, pdf_page):
        pdf_image = pdf_page.extract_text()
        img = Image.new("RGB", (600, 800), (255, 255, 255))
        img = ImageTk.PhotoImage(img)
        self.image_label.config(image=img)
        self.image_label.image = img

    def show_next_pdf(self):
        if self.current_index < len(self.pdf_files) - 1:
            self.current_index += 1
            self.show_pdf()
            self.update_buttons()

    def show_previous_pdf(self):
        if self.current_index > 0:
            self.current_index -= 1
            self.show_pdf()
            self.update_buttons()

    def update_buttons(self):
        if self.current_index == 0:
            self.prev_button.config(state='disabled')
        else:
            self.prev_button.config(state='normal')
        
        if self.current_index == len(self.pdf_files) - 1:
            self.next_button.config(state='disabled')
        else:
            self.next_button.config(state='normal')

if __name__ == "__main__":
    root = Tk()
    pdf_viewer = PDFViewer(root)
    root.mainloop()
