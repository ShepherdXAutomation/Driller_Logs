import os
import tkinter as tk
from tkinter import filedialog, messagebox

def count_files_in_directory(directory):
    file_count = 0
    for root, dirs, files in os.walk(directory):
        file_count += len(files)
    return file_count

def select_folder():
    folder_path = filedialog.askdirectory()
    if folder_path:
        total_files = count_files_in_directory(folder_path)
        messagebox.showinfo("File Count", f"Total number of files in '{folder_path}' and its subfolders: {total_files}")

if __name__ == "__main__":
    root = tk.Tk()
    root.title("File Counter")

    select_button = tk.Button(root, text="Select Folder", command=select_folder)
    select_button.pack(pady=20)

    root.mainloop()
