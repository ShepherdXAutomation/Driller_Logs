import sqlite3

# Connect to the database (it will create the database if it doesn't exist)
conn = sqlite3.connect('well_data.db')
cursor = conn.cursor()

# Create a table for the well data with the Materials column before the Hyperlink column
cursor.execute('''
CREATE TABLE IF NOT EXISTS wells (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    file_name TEXT,
    log_service TEXT,
    company TEXT,
    county TEXT,
    farm TEXT,
    commenced_date TEXT,
    completed_date TEXT,
    total_depth TEXT,
    initial_production TEXT,
    location TEXT,
    well_number TEXT,
    elevation TEXT,
    materials TEXT,
    hyperlink TEXT
)
''')

# Commit the changes and close the connection
conn.commit()
conn.close()
