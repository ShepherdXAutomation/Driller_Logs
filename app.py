import os
import re
from flask import Flask, render_template, request, send_file, abort, url_for, jsonify
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import text, or_  # Importing the or_ function for SQLAlchemy filters
from urllib.parse import unquote
from dotenv import load_dotenv
load_dotenv()

app = Flask(__name__)

# Check for an environment variable to use the earlier version of the database
use_early_version = os.getenv('USE_EARLY_DB', 'false').lower() == 'true'

if use_early_version:
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + os.path.join(os.path.dirname(__file__), 'instance', 'early_versions', 'well_data.db')
else:
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + os.path.join(os.path.dirname(__file__), 'well_data.db')

db = SQLAlchemy(app)

# Debugging prints to verify environment variable and database path
print(f"USE_EARLY_DB: {os.getenv('USE_EARLY_DB')}, use_early_version: {use_early_version}")
print(f"Database path: {app.config['SQLALCHEMY_DATABASE_URI']}")

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
    page = int(request.args.get('page', 1))  # Current page number
    per_page = 100  # Results per page
    offset = (page - 1) * per_page

    if request.method == 'POST':
        filters = []
        columns = ['file_name', 'log_service', 'company', 'county', 'farm', 'commenced_date', 
                   'completed_date', 'total_depth', 'initial_production', 'location', 
                   'well_number', 'elevation', 'materials']
        
        for column in columns:
            query = request.form.get(column)
            if query:
                filters.append(getattr(Well, column).like(f'%{query}%'))

        query = Well.query.filter(*filters) if filters else Well.query
    else:
        query = Well.query

    total_results = query.count()  # Total number of results
    wells = query.offset(offset).limit(per_page).all()

    return render_template(
        'index.html',
        wells=wells,
        total_results=total_results,
        current_page=page,
        total_pages=(total_results + per_page - 1) // per_page,  # Total pages
        start=offset + 1,
        end=min(offset + per_page, total_results)
    )

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

@app.route('/delete_entry/<int:id>', methods=['DELETE'])
def delete_entry(id):
    well = Well.query.get(id)
    if well:
        db.session.delete(well)
        db.session.commit()
        return jsonify({'message': 'Entry deleted successfully'}), 200
    return jsonify({'message': 'Entry not found'}), 404
@app.route('/search', methods=['POST'])
def search():
    filters = []
    columns = [
        'log_service', 'company', 'county', 'farm', 'commenced_date',
        'completed_date', 'total_depth', 'initial_production', 'location',
        'well_number', 'elevation', 'materials'
    ]

    # Add debug prints to verify received form data
    print("Form data received:", request.form)

    for column in columns:
        query = request.form.get(column)
        if query:
            print(f"Adding filter for {column}: {query}")
            filters.append(getattr(Well, column).like(f'%{query}%'))

    '''page = int(request.args.get('page', 1))  # Current page
    per_page = int(request.args.get('limit', 100))  # Results per page
    offset = (page - 1) * per_page
    '''
    
    page = 1  # Always load the first page
    per_page = 100  # Show up to 100 results
    offset = (page - 1) * per_page
    
    query = Well.query.filter(*filters) if filters else Well.query
    total_results = query.count()
    wells = query.offset(offset).limit(per_page).all()

    # Debug the final query results
    print(f"Total results after filters: {total_results}")

    return render_template(
        'index.html',
        wells=wells,
        total_results=total_results,
        current_page=page,
        total_pages=(total_results + per_page - 1) // per_page,
        start=offset + 1,
        end=min(offset + per_page, total_results)
    )



@app.route('/update/<int:id>', methods=['POST'])
def update_row(id):
    data = request.json  # Parse the incoming JSON data
    print(f"Received data for row {id}: {data}")  # Debug: log received data

    # Map column indices to database fields
    column_mapping = {
        2: "log_service",
        3: "company",
        4: "county",
        5: "farm",
        6: "commenced_date",
        7: "completed_date",
        8: "total_depth",
        9: "initial_production",
        10: "location",
        11: "well_number",
        12: "elevation",
        13: "materials",
    }

    # Build update query
    updates = []
    params = {"id": id}
    for index, value in data.items():
        try:
            # Strip "column" prefix and convert to int
            column_index = int(index.replace("column", ""))
            column_name = column_mapping.get(column_index)
            if column_name:
                updates.append(f"{column_name} = :{column_name}")
                params[column_name] = value
        except ValueError:
            print(f"Invalid column key: {index}")  # Debug: log invalid keys

    # Only proceed if there's data to update
    if updates:
        query = text(f"UPDATE wells SET {', '.join(updates)} WHERE id = :id")
        db.session.execute(query, params)
        db.session.commit()
        return jsonify({"success": True})

    return jsonify({"success": False, "error": "No valid data provided"}), 400

SPECIAL_KEY_TERMS = [
    "O SD", "O. SD", "O. STN", "O STN", "SO", "S/O", "SSG", "SSO", "SS/O", 
    "SG", "SO&G", "SO&W", "SHG O", "SD SO", "O", "OIH", "O&G", "O&GCM", 
    "OS&W", "OAW", "OO", "OC", "OCM", "OCW", "OC SW", "SC", "OIH", 
    "G&O", "G&O CM", "G O", "FNT", "FLUO", "ST", "STN", "STRKS", "SPKS", "TR"
]

@app.route('/data', methods=['GET'])
def get_paginated_data():
    page = int(request.args.get('page', 1))  # Current page
    per_page = int(request.args.get('limit', 100))  # Results per page
    filters = []  # Build your filters logic

    print(f"Received page request: {page}")  # Debug log

    # Add filters for other columns
    columns = ['log_service', 'company', 'county', 'farm', 'commenced_date',
               'completed_date', 'total_depth', 'initial_production', 'location',
               'well_number', 'elevation', 'materials']
    for column in columns:
        query = request.args.get(column)
        if query:
            # Add LIKE filters for standard columns
            filters.append(getattr(Well, column).like(f'%{query}%'))

    # Handle special key terms in the "materials" column
    materials_query = request.args.get('materials', '').strip()  # Get "materials" query
    if materials_query:
        # Split input into words
        terms = materials_query.split()
        # Separate special terms from normal terms
        special_terms = [term for term in terms if term.upper() in SPECIAL_KEY_TERMS]
        normal_terms = [term for term in terms if term.upper() not in SPECIAL_KEY_TERMS]

        # Add filters for special terms (OR conditions)
        if special_terms:
            special_conditions = [Well.materials.like(f'%{term}%') for term in special_terms]
            filters.append(or_(*special_conditions))  # OR together special term conditions

        # Add filters for normal terms (AND conditions)
        if normal_terms:
            normal_conditions = [Well.materials.like(f'%{term}%') for term in normal_terms]
            filters.extend(normal_conditions)  # Add normal term conditions as separate filters

    # Combine filters and execute query
    query = Well.query.filter(*filters) if filters else Well.query
    total_results = query.count()
    offset = (page - 1) * per_page
    wells = query.offset(offset).limit(per_page).all()

    print(f"Received page request: {page}")  # Log the requested page
    print(f"Current filters: {request.args}")  # Log the applied filters
    print(f"Offset: {offset}, Limit: {per_page}, Results on Page: {len(wells)}")  # Debug log
    print(f"Total Results: {total_results}, Total Pages: {(total_results + per_page - 1) // per_page}")  # Debug log

    # Serialize results
    serialized_wells = [
        {
            "id": well.id,
            "hyperlink": well.hyperlink,
            "log_service": well.log_service,
            "company": well.company,
            "county": well.county,
            "farm": well.farm,
            "commenced_date": well.commenced_date,
            "completed_date": well.completed_date,
            "total_depth": well.total_depth,
            "initial_production": well.initial_production,
            "location": well.location,
            "well_number": well.well_number,
            "elevation": well.elevation,
            "materials": well.materials,
        }
        for well in wells
    ]

    return jsonify({
        "results": serialized_wells,
        "total_results": total_results,
        "current_page": page,
        "total_pages": (total_results + per_page - 1) // per_page,
        "start": offset + 1,
        "end": min(offset + per_page, total_results),
    })

def preprocess_materials_search(query):
    terms = query.split()  # Split the input by spaces
    special_terms = [term for term in terms if term.upper() in SPECIAL_KEY_TERMS]
    normal_terms = [term for term in terms if term.upper() not in SPECIAL_KEY_TERMS]
    return special_terms, normal_terms


if __name__ == "__main__":
    with app.app_context():
        db.create_all()
    app.run(debug=True, host= '0.0.0.0', port=5001)
