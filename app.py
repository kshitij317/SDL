from flask import Flask, request, redirect, url_for, send_file, render_template
import pandas as pd
import os
import uuid

app = Flask(__name__)

# Update the path for Windows (adjust the folder as needed)
UPLOAD_FOLDER = 'uploads/'  # Use a relative path
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# Ensure the upload folder exists
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

# Function to clean data
def clean_data(df):
    try:
        start_row = df[df.iloc[:, 0].str.contains("S.No.", na=False)].index[0]
    except IndexError:
        raise ValueError("Could not find 'S.No.' in the file. Please ensure the file is properly formatted.")
    
    df_cleaned = df[start_row:]
    df_cleaned.columns = df_cleaned.iloc[0]
    df_cleaned = df_cleaned.drop(df_cleaned.index[0])
    df_cleaned = df_cleaned[['Enrollment No.', 'Name', 'Average %']].dropna()
    df_cleaned['Average %'] = pd.to_numeric(df_cleaned['Average %'], errors='coerce')
    
    return df_cleaned

# Function to validate generated CSV file
def validate_generated_file(file_path, threshold):
    try:
        df = pd.read_csv(file_path)

        # Ensure the expected columns are present
        required_columns = ['Enrollment No.', 'Name', 'Average %']
        if not all(column in df.columns for column in required_columns):
            raise ValueError(f"Missing required columns in the generated file. Found columns: {df.columns}")

        # Ensure that the Average % values are below the threshold
        if not all(df['Average %'] < threshold):
            raise ValueError("Some rows in the file have an 'Average %' that is above the threshold.")

        return True, "File validation successful!"
    except Exception as e:
        return False, str(e)

# Function to process uploaded files
def process_attendance(file_paths, threshold):
    combined_data = pd.DataFrame()

    for file in file_paths:
        df = pd.read_csv(file)
        df_cleaned = clean_data(df)
        combined_data = pd.concat([combined_data, df_cleaned], ignore_index=True)

    df_below_threshold = combined_data[combined_data['Average %'] < threshold]

    output_file_name = f'students_below_{threshold}_percent_{uuid.uuid4().hex}.csv'
    output_file_path = os.path.join(app.config['UPLOAD_FOLDER'], output_file_name)
    
    # Write the filtered data to CSV
    df_below_threshold.to_csv(output_file_path, index=False)

    # Validate the generated CSV file
    is_valid, message = validate_generated_file(output_file_path, threshold)

    if is_valid:
        print("Validation passed:", message)
        return output_file_path
    else:
        print("Validation failed:", message)
        os.remove(output_file_path)  # Remove the file if validation fails
        raise ValueError(f"File generation failed: {message}")

@app.route('/')
def upload_form():
    return render_template('upload_form.html')

@app.route('/upload', methods=['POST'])
def upload_files():
    if 'files' not in request.files:
        return 'No file part'
    
    files = request.files.getlist('files')
    file_paths = []

    # Get the custom threshold value from the form
    try:
        threshold = float(request.form['threshold'])
    except ValueError:
        return 'Invalid threshold value'

    for file in files:
        if file and file.filename.endswith('.csv'):
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], file.filename)
            file.save(filepath)
            file_paths.append(filepath)

    try:
        output_file = process_attendance(file_paths, threshold)
        return redirect(url_for('download_file', filename=os.path.basename(output_file)))
    except ValueError as e:
        return str(e)  # Return an error message to the user

@app.route('/download/<filename>')
def download_file(filename):
    return send_file(os.path.join(app.config['UPLOAD_FOLDER'], filename), as_attachment=True)

if __name__ == '__main__':
    app.run(debug=True)
