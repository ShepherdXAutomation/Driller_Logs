import os
import shutil
from tkinter import filedialog, Tk

def copy_empty_folders(source_dir, destination_dir):
    # Iterate over all items in the source directory
    for item in os.listdir(source_dir):
        source_path = os.path.join(source_dir, item)
        
        if os.path.isdir(source_path):
            # Create the same folder structure in the destination directory
            destination_path = os.path.join(destination_dir, item)
            os.makedirs(destination_path, exist_ok=True)
            print(f"Copied folder structure: {destination_path}")

# Main function to select directories and copy folder structure
def main():
    root = Tk()
    root.withdraw()  # Hide the main window
    
    source_dir = filedialog.askdirectory(title="Select Source Directory")
    destination_dir = filedialog.askdirectory(title="Select Destination Directory")
    
    if source_dir and destination_dir:
        copy_empty_folders(source_dir, destination_dir)
        print("Folder structure copied successfully.")
    else:
        print("Operation canceled or no directory selected.")

if __name__ == "__main__":
    main()
