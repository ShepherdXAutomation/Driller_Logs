import os

db_path = 'C:/Users/calla/desktop/driller_logs/well_data.db'

# Check if the file exists
if not os.path.exists(db_path):
    print(f"Database file not found: {db_path}")
else:
    print(f"Database file found: {db_path}")