import tkinter as tk
from tkinter import filedialog, messagebox
from tkinter.ttk import Progressbar
from PyPDF2 import PdfMerger

def merge_pdfs(pdf_list, output_path, progress_var):
    merger = PdfMerger()
    total_files = len(pdf_list)
    
    for idx, pdf in enumerate(pdf_list):
        merger.append(pdf)
        progress_var.set((idx + 1) / total_files * 100)
        root.update_idletasks()

    merger.write(output_path)
    merger.close()

    messagebox.showinfo("Success", f"PDFs merged into {output_path}")

def select_files():
    files = filedialog.askopenfilenames(title="Select PDF files", filetypes=[("PDF Files", "*.pdf")])
    file_list.delete(0, tk.END)
    for file in files:
        file_list.insert(tk.END, file)

def start_merge():
    files = list(file_list.get(0, tk.END))
    if not files:
        messagebox.showwarning("No Files", "Please select at least two PDF files.")
        return

    progress_var.set(0)
    output_file = filedialog.asksaveasfilename(defaultextension=".pdf", filetypes=[("PDF Files", "*.pdf")])
    if not output_file:
        return
    
    merge_pdfs(files, output_file, progress_var)

# GUI Setup
root = tk.Tk()
root.title("PDF Merger")

file_frame = tk.Frame(root)
file_frame.pack(padx=10, pady=10)

file_list = tk.Listbox(file_frame, width=50, height=10)
file_list.pack(side=tk.LEFT, padx=(0, 10))

scrollbar = tk.Scrollbar(file_frame)
scrollbar.pack(side=tk.LEFT, fill=tk.Y)
file_list.config(yscrollcommand=scrollbar.set)
scrollbar.config(command=file_list.yview)

select_button = tk.Button(root, text="Select PDF Files", command=select_files)
select_button.pack(pady=(0, 10))

progress_var = tk.DoubleVar()
progress_bar = Progressbar(root, variable=progress_var, maximum=100)
progress_bar.pack(padx=10, pady=10, fill=tk.X)

merge_button = tk.Button(root, text="Merge PDFs", command=start_merge)
merge_button.pack(pady=(0, 10))

root.mainloop()
