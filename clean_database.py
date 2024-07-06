import sqlite3

# Connect to the database
conn = sqlite3.connect('well_data.db')
cursor = conn.cursor()

# Clear the wells table
cursor.execute('DELETE FROM wells')

# Commit the changes and close the connection
conn.commit()
conn.close()

print("Database cleared successfully.")
