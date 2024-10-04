import os

def list_full_directories_to_file(folder_path, output_file):
    try:
        # Get all items in the folder
        items = os.listdir(folder_path)
        
        # Filter and list only directories, and generate full paths
        directories = [os.path.join(folder_path, item) for item in items if os.path.isdir(os.path.join(folder_path, item))]
        
        # Join full paths with commas and write to file
        with open(output_file, 'w') as file:
            file.write(",".join(directories))
        
        print(f"Full directory paths written to {output_file}")
            
    except Exception as e:
        print(f"Error occurred: {e}")

# Usage
folder_path = r'I:\\'
output_path = r'I:\\output.txt'
list_full_directories_to_file(folder_path, output_path)
