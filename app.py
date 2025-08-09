import os
import time
import uuid
import google.generativeai as genai
from flask import Flask, request, render_template, redirect, url_for
from werkzeug.utils import secure_filename
from dotenv import load_dotenv
from markdown import markdown

load_dotenv()

app = Flask(__name__)

# Configure upload folder and ensure it exists
app.config['UPLOAD_FOLDER'] = 'uploads/'
if not os.path.exists(app.config['UPLOAD_FOLDER']):
    os.makedirs(app.config['UPLOAD_FOLDER'])

app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16 MB limit
ALLOWED_EXTENSIONS = {'txt', 'py', 'js', 'java', 'c', 'cpp', 'html', 'css', 'php', 'rb', 'go', 'rs', 'ts', 'swift', 'kt'}

# Function to check for allowed file extensions
def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# Configure the Gemini API key
api_key = os.getenv("GEMINI_API_KEY")
if not api_key:
    raise ValueError("GEMINI_API_KEY is not set in the environment variables")
@app.route('/')
def index():
    return render_template('index.html', error=None)

@app.route('/upload', methods=['POST'])
def upload_file():
    if 'file' not in request.files:
        return render_template('index.html', error="No file part in the request")
    
    file = request.files['file']
    if file.filename == '':
        return render_template('index.html', error="No file selected")
    
    if file and allowed_file(file.filename):
        # Generate a unique filename to avoid conflicts
        filename = secure_filename(file.filename)
        unique_filename = f"{uuid.uuid4().hex}_{int(time.time())}_{filename}"
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], unique_filename)
        try:
            file.save(filepath)
        except Exception as e:
            return render_template('index.html', error=f"Failed to save file: {str(e)}")

        try:
            # Process the file with Gemini
            vulnerability_report = check_vulnerabilities(filepath)
            # Convert markdown to HTML
            report_html = markdown(vulnerability_report, extensions=['extra', 'fenced_code'])
        finally:
            # Clean up the uploaded file
            if os.path.exists(filepath):
                try:
                    os.remove(filepath)
                except Exception as e:
                    print(f"Warning: Failed to delete file {filepath}: {str(e)}")

        return render_template('result.html', report=report_html)
    else:
        return render_template('index.html', error="Invalid file type. Supported types: " + ", ".join(ALLOWED_EXTENSIONS))

def check_vulnerabilities(filepath):
    """
    This function sends the code to the Gemini API for vulnerability checking.
    """
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            code = f.read()

        model = genai.GenerativeModel('gemini-2.5-flash')  # Updated to a valid model
        prompt = f"""
        Analyze the following code for security vulnerabilities. Provide a detailed report in Markdown format, including:
        - The type of vulnerability
        - The line number (if applicable)
        - A description of the issue
        - A suggested fix
        If no vulnerabilities are found, state that explicitly.

        Code:
        ```{code}```
        """
        response = model.generate_content(prompt)
        
        if not response.text:
            return "No response from Gemini API. Please check your API key and model availability."
        
        return response.text

    except Exception as e:
        return f"Error analyzing file: {str(e)}. Please ensure the file is valid and the Gemini API is accessible."

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0')