import os
import tkinter as tk
from tkinter import filedialog

def remove_indexed_drew_from_folders(root_folder):
    for root, dirs, files in os.walk(root_folder):
        for dir_name in dirs:
            if "[indexed_drew]" in dir_name:
                new_dir_name = dir_name.replace("[indexed_drew]", "").strip()
                old_dir_path = os.path.join(root, dir_name)
                new_dir_path = os.path.join(root, new_dir_name)
                
                # Rename the folder
                os.rename(old_dir_path, new_dir_path)
                print(f'Renamed: "{old_dir_path}" to "{new_dir_path}"')

def select_folder_and_rename():
    root = tk.Tk()
    root.withdraw()  # Hide the root window
    folder_path = filedialog.askdirectory(title="Select Folder to Process")
    
    if folder_path:
        remove_indexed_drew_from_folders(folder_path)
        print("Folder renaming completed.")
    else:
        print("No folder selected.")

if __name__ == "__main__":
    select_folder_and_rename()
