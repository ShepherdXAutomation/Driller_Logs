from flask import Flask, render_template, request, redirect, url_for, send_file, flash
import fitz  # PyMuPDF
import os
import threading
from werkzeug.utils import secure_filename

app = Flask(__name__)
app.secret_key = 'supersecretkey'  # Needed for flashing messages

UPLOAD_FOLDER = 'uploads'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# Ensure the upload directory exists
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# Track background process
process_thread = None
cancelled = False

@app.route('/', methods=['GET', 'POST'])
def pdf_splitter():
    global process_thread, cancelled
    
    if request.method == 'POST':
        # Handle file upload
        if 'file' not in request.files:
            return redirect(request.url)
        
        file = request.files['file']
        if file.filename == '':
            return redirect(request.url)

        output_dir = request.form.get('output_dir')
        if not output_dir:
            flash('Output directory is required!', 'error')
            return redirect(request.url)

        # Ensure output directory exists
        os.makedirs(output_dir, exist_ok=True)

        if file:
            filename = secure_filename(file.filename)
            file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            file.save(file_path)

            # Extract keywords
            keywords = request.form.get('keywords', '').split(',')
            manual_mode = request.form.get('manual_mode') == 'on'

            # Start the processing in a separate thread
            cancelled = False
            process_thread = threading.Thread(target=process_pdf, args=(file_path, keywords, output_dir, manual_mode))
            process_thread.start()
            process_thread.join()  # Wait for the thread to finish

            if not cancelled:
                flash('Processing completed! You can download the files from the output folder.', 'success')
            else:
                flash('Processing was cancelled.', 'error')

            return redirect(url_for('pdf_splitter'))

    return render_template('pdf_splitter.html')

@app.route('/download/<filename>')
def download_file(filename):
    return send_file(filename, as_attachment=True)

def process_pdf(file_path, keywords, output_dir, manual_mode):
    global cancelled
    doc = fitz.open(file_path)
    base_filename = os.path.splitext(os.path.basename(file_path))[0]

    split_counter = 1
    split_start_page = 0

    for page_num in range(len(doc)):
        if cancelled:
            break

        page = doc.load_page(page_num)
        text = page.get_text("text")

        if manual_mode:
            # Prompt user to decide whether to split after each page
            user_decision = request.form.get(f'split_after_page_{page_num+1}')
            if user_decision == 'yes':
                save_split_pdf(doc, split_start_page, page_num, base_filename, split_counter, output_dir)
                split_start_page = page_num + 1
                split_counter += 1

        else:
            # Automatic split based on keywords
            for keyword in keywords:
                if keyword.strip() and keyword in text:
                    save_split_pdf(doc, split_start_page, page_num, base_filename, split_counter, output_dir)
                    split_start_page = page_num + 1
                    split_counter += 1
                    break

    if not cancelled and split_start_page < len(doc):
        save_split_pdf(doc, split_start_page, len(doc) - 1, base_filename, split_counter, output_dir)

    doc.close()

def save_split_pdf(doc, start_page, end_page, base_filename, split_counter, output_dir):
    output_filename = f'{base_filename}_part_{split_counter}.pdf'
    output_path = os.path.join(output_dir, output_filename)

    split_doc = fitz.open()
    for page_num in range(start_page, end_page + 1):
        split_doc.insert_pdf(doc, from_page=page_num, to_page=page_num)
    split_doc.save(output_path)
    split_doc.close()

if __name__ == '__main__':
    app.run(debug=True)
