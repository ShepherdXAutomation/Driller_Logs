import tkinter as tk
from tkinter import ttk, messagebox
import sqlite3
import webbrowser
import re
import os
import ctypes

def get_total_records():
    conn = sqlite3.connect('well_data.db')
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM wells")
    total = cursor.fetchone()[0]
    conn.close()
    return total

def search_database(query, column):
    conn = sqlite3.connect('well_data.db')
    cursor = conn.cursor()
    if query:
        sql_query = f"SELECT * FROM wells WHERE {column} LIKE ?"
        cursor.execute(sql_query, ('%' + query + '%',))
    else:
        sql_query = "SELECT * FROM wells LIMIT 1000"
        cursor.execute(sql_query)
    results = cursor.fetchall()
    conn.close()
    return results

def on_search():
    query = search_entry.get()
    column = column_var.get()
    results = search_database(query, column)
    update_treeview(results)

def update_treeview(results):
    for row in tree.get_children():
        tree.delete(row)
    for result in results:
        tree.insert('', 'end', values=result)

def extract_file_path(hyperlink):
    match = re.search(r'HYPERLINK\("([^"]+)', hyperlink)
    return match.group(1) if match else None

def on_item_double_click(event):
    selected_item = tree.selection()
    if selected_item:
        item = tree.item(selected_item)
        hyperlink = item['values'][-1]  # Assuming the hyperlink is the last column
        file_path = extract_file_path(hyperlink)
        if file_path:
            webbrowser.open(file_path)

def create_gui():
    global search_entry, column_var, tree, total_records_label
    
    root = tk.Tk()
    root.title("Well Data Search")

   
     # Set the taskbar icon using a relative path
    icon_path = os.path.join(os.path.dirname(__file__), 'assets', 'view.png')
    
    
    # Change taskbar icon using ctypes
    app_id = 'mycompany.myproduct.subproduct.version'  # Arbitrary string
    ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(app_id)
    hwnd = ctypes.windll.user32.GetActiveWindow()
    hicon = ctypes.windll.user32.LoadImageW(None, icon_path, 1, 0, 0, 0x00000010)
    ctypes.windll.user32.SendMessageW(hwnd, 0x0080, 1, hicon)
   
    frame = ttk.Frame(root, padding="10")
    frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
    
    ttk.Label(frame, text="Search Query:").grid(row=0, column=0, sticky=tk.W)
    search_entry = ttk.Entry(frame, width=50)
    search_entry.grid(row=0, column=1, sticky=(tk.W, tk.E))
    
    ttk.Label(frame, text="Search Column:").grid(row=1, column=0, sticky=tk.W)
    column_var = tk.StringVar()
    column_options = ['file_name', 'log_service', 'company', 'county', 'farm', 'commenced_date', 'completed_date', 'total_depth', 'initial_production', 'location', 'well_number', 'elevation', 'materials']
    column_menu = ttk.OptionMenu(frame, column_var, column_options[0], *column_options)
    column_menu.grid(row=1, column=1, sticky=(tk.W, tk.E))
    
    search_button = ttk.Button(frame, text="Search", command=on_search)
    search_button.grid(row=2, column=0, columnspan=2, sticky=(tk.W, tk.E))
    
    total_records_label = ttk.Label(frame, text=f"Total Records: {get_total_records()}")
    total_records_label.grid(row=3, column=0, columnspan=2, sticky=tk.W)

    columns = ['id', 'file_name', 'log_service', 'company', 'county', 'farm', 'commenced_date', 'completed_date', 'total_depth', 'initial_production', 'location', 'well_number', 'elevation', 'materials', 'hyperlink']
    tree = ttk.Treeview(frame, columns=columns, show='headings')
    for col in columns:
        tree.heading(col, text=col)
        tree.column(col, width=100)
    tree.grid(row=4, column=0, columnspan=2, sticky=(tk.W, tk.E, tk.N, tk.S))

    tree.bind('<Double-1>', on_item_double_click)
    
    # Add vertical scrollbar
    vsb = ttk.Scrollbar(frame, orient="vertical", command=tree.yview)
    vsb.grid(row=4, column=2, sticky='ns')
    tree.configure(yscrollcommand=vsb.set)

    # Add horizontal scrollbar
    hsb = ttk.Scrollbar(frame, orient="horizontal", command=tree.xview)
    hsb.grid(row=5, column=0, columnspan=2, sticky='ew')
    tree.configure(xscrollcommand=hsb.set)

    # Make the frame expandable
    root.columnconfigure(0, weight=1)
    root.rowconfigure(0, weight=1)
    frame.columnconfigure(1, weight=1)
    frame.rowconfigure(4, weight=1)
    
    root.mainloop()

if __name__ == "__main__":
    create_gui()