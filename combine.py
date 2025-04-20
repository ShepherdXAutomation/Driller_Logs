import tkinter as tk
from tkinter import filedialog, messagebox
from tkinter.ttk import Progressbar
from PyPDF2 import PdfMerger
import os
import shutil

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

def combine_pdfs_in_folder(input_folder, output_folder, progress_var):
    folders = [os.path.join(input_folder, d) for d in os.listdir(input_folder) if os.path.isdir(os.path.join(input_folder, d))]
    total_folders = len(folders)

    for idx, folder in enumerate(folders):
        pdf_files = sorted([os.path.join(folder, f) for f in os.listdir(folder) if f.lower().endswith('.pdf')])
        if not pdf_files:
            continue

        merger = PdfMerger()
        for pdf_file in pdf_files:
            merger.append(pdf_file)

        relative_path = os.path.relpath(folder, input_folder)
        target_folder = os.path.join(output_folder, relative_path)
        os.makedirs(target_folder, exist_ok=True)
        combined_pdf_path = os.path.join(target_folder, f"combined_{os.path.basename(folder)}.pdf")

        merger.write(combined_pdf_path)
        merger.close()

        progress_var.set((idx + 1) / total_folders * 100)
        root.update_idletasks()

    messagebox.showinfo("Success", f"Folders combined into {output_folder}")

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

def combine_folders():
    input_dir = filedialog.askdirectory(title="Select Parent Directory")
    if not input_dir:
        return
    output_dir = filedialog.askdirectory(title="Select Output Directory")
    if not output_dir:
        return

    combined_output_dir = os.path.join(output_dir, os.path.basename(input_dir) + '_Combined')
    if os.path.exists(combined_output_dir):
        shutil.rmtree(combined_output_dir)

    progress_var.set(0)
    combine_pdfs_in_folder(input_dir, combined_output_dir, progress_var)

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

combine_folder_button = tk.Button(root, text="Merge PDFs in Folder", command=combine_folders)
combine_folder_button.pack(pady=(0, 10))

root.mainloop()
