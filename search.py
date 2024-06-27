import tkinter as tk
from tkinter import ttk, messagebox
import sqlite3
import webbrowser
import re

def search_database(query, column):
    conn = sqlite3.connect('well_data.db')
    cursor = conn.cursor()
    sql_query = f"SELECT * FROM wells WHERE {column} LIKE ?"
    cursor.execute(sql_query, ('%' + query + '%',))
    results = cursor.fetchall()
    conn.close()
    return results

def on_search():
    query = search_entry.get()
    column = column_var.get()
    if not query:
        messagebox.showwarning("Input Error", "Please enter a search query.")
        return
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
    global search_entry, column_var, tree
    
    root = tk.Tk()
    root.title("Well Data Search")

    frame = ttk.Frame(root, padding="10")
    frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
    
    ttk.Label(frame, text="Search Query:").grid(row=0, column=0, sticky=tk.W)
    search_entry = ttk.Entry(frame, width=50)
    search_entry.grid(row=0, column=1, sticky=(tk.W, tk.E))
    
    ttk.Label(frame, text="Search Column:").grid(row=1, column=0, sticky=tk.W)
    column_var = tk.StringVar()
    column_options = ['file_name', 'log_service', 'company', 'county', 'farm', 'commenced_date', 'completed_date', 'total_depth', 'initial_production', 'location', 'well_number', 'elevation']
    column_menu = ttk.OptionMenu(frame, column_var, column_options[0], *column_options)
    column_menu.grid(row=1, column=1, sticky=(tk.W, tk.E))
    
    search_button = ttk.Button(frame, text="Search", command=on_search)
    search_button.grid(row=2, column=0, columnspan=2, sticky=(tk.W, tk.E))
    
    columns = ['id', 'file_name', 'log_service', 'company', 'county', 'farm', 'commenced_date', 'completed_date', 'total_depth', 'initial_production', 'location', 'well_number', 'elevation', 'hyperlink']
    tree = ttk.Treeview(frame, columns=columns, show='headings')
    for col in columns:
        tree.heading(col, text=col)
        tree.column(col, width=100)
    tree.grid(row=3, column=0, columnspan=2, sticky=(tk.W, tk.E, tk.N, tk.S))

    tree.bind('<Double-1>', on_item_double_click)
    
    # Add vertical scrollbar
    vsb = ttk.Scrollbar(frame, orient="vertical", command=tree.yview)
    vsb.grid(row=3, column=2, sticky='ns')
    tree.configure(yscrollcommand=vsb.set)

    # Add horizontal scrollbar
    hsb = ttk.Scrollbar(frame, orient="horizontal", command=tree.xview)
    hsb.grid(row=4, column=0, columnspan=2, sticky='ew')
    tree.configure(xscrollcommand=hsb.set)

    # Make the frame expandable
    root.columnconfigure(0, weight=1)
    root.rowconfigure(0, weight=1)
    frame.columnconfigure(1, weight=1)
    frame.rowconfigure(3, weight=1)
    
    root.mainloop()

if __name__ == "__main__":
    create_gui()
