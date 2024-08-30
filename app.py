import os
import re
from flask import Flask, render_template, request, send_file, abort, url_for
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import text
from urllib.parse import unquote

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///C:/Users/ChrisClayton/desktop/Driller_Logs/well_data.db'
db = SQLAlchemy(app)

class Well(db.Model):
    __tablename__ = 'wells'

    id = db.Column(db.Integer, primary_key=True)
    file_name = db.Column(db.String(100))
    log_service = db.Column(db.String(100))
    company = db.Column(db.String(100))
    county = db.Column(db.String(100))
    farm = db.Column(db.String(100))
    commenced_date = db.Column(db.String(100))
    completed_date = db.Column(db.String(100))
    total_depth = db.Column(db.String(100))
    initial_production = db.Column(db.String(100))
    location = db.Column(db.String(100))
    well_number = db.Column(db.String(100))
    elevation = db.Column(db.String(100))
    materials = db.Column(db.Text)
    hyperlink = db.Column(db.String(255))

# Confirm the connection
with app.app_context():
    try:
        db.session.execute(text('SELECT 1'))
        print("Successfully connected to the database.")
    except Exception as e:
        print(f"Failed to connect to the database: {e}")

@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        filters = []
        columns = ['file_name', 'log_service', 'company', 'county', 'farm', 'commenced_date', 
                   'completed_date', 'total_depth', 'initial_production', 'location', 
                   'well_number', 'elevation', 'materials']
        
        # Loop through each column and check if a corresponding query was provided
        for column in columns:
            query = request.form.get(column)
            if query:
                filters.append(getattr(Well, column).like(f'%{query}%'))

        if filters:
            wells = Well.query.with_entities(
                Well.id,
                Well.file_name,
                Well.log_service,
                Well.company,
                Well.county,
                Well.farm,
                Well.commenced_date,
                Well.completed_date,
                Well.total_depth,
                Well.initial_production,
                Well.location,
                Well.well_number,
                Well.elevation,
                Well.materials,
                Well.hyperlink
            ).filter(*filters).all()
        else:
            wells = Well.query.with_entities(
                Well.id,
                Well.file_name,
                Well.log_service,
                Well.company,
                Well.county,
                Well.farm,
                Well.commenced_date,
                Well.completed_date,
                Well.total_depth,
                Well.initial_production,
                Well.location,
                Well.well_number,
                Well.elevation,
                Well.materials,
                Well.hyperlink
            ).limit(10000).all()
    else:
        wells = Well.query.with_entities(
            Well.id,
            Well.file_name,
            Well.log_service,
            Well.company,
            Well.county,
            Well.farm,
            Well.commenced_date,
            Well.completed_date,
            Well.total_depth,
            Well.initial_production,
            Well.location,
            Well.well_number,
            Well.elevation,
            Well.materials,
            Well.hyperlink
        ).limit(10000).all()

    return render_template('index.html', wells=wells)

@app.route('/serve-file/')
def serve_file():
    raw_file_path = request.args.get('file_path')

    # Debug statements
    print(f"Debug: Received file_path argument: {raw_file_path}")

    if not raw_file_path:
        print("Debug: No file_path received, returning 404")
        abort(404)

    # Decode URL-encoded characters
    raw_file_path = unquote(raw_file_path)
    print(f"Debug: Decoded file path: {raw_file_path}")

    # Extract the correct file path using regex
    match = re.search(r'HYPERLINK\(["\']([^"\']+)["\']', raw_file_path, re.IGNORECASE)
    if match:
        extracted_path = match.group(1)
        print(f"Debug: Extracted file path from hyperlink: {extracted_path}")
    else:
        print("Debug: Failed to extract file path from the hyperlink, returning 404")
        abort(404)  # If we can't extract the path, return 404

    # Normalize the file path to handle different separators
    normalized_path = os.path.normpath(extracted_path)
    print(f"Debug: Normalized file path: {normalized_path}")

    # Check if the file exists
    if not os.path.isfile(normalized_path):
        print(f"Debug: File does not exist: {normalized_path}")
        abort(404)

    try:
        print(f"Debug: Serving file: {normalized_path}")
        return send_file(normalized_path, as_attachment=False)
    except Exception as e:
        print(f"Debug: Error serving file: {e}")
        abort(404)

if __name__ == "__main__":
    with app.app_context():
        db.create_all()
    app.run(debug=True, host= '0.0.0.0', port=5001)
