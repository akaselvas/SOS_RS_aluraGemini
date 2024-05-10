from flask import Flask, request, render_template, redirect, url_for
from flask_sqlalchemy import SQLAlchemy
from pathlib import Path
import hashlib
import google.generativeai as genai
import os
from flask import session
from markupsafe import Markup

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:////tmp/test.db'
app.config['SECRET_KEY'] = '1234567890'  # Add this line
db = SQLAlchemy(app)

class Result(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    output = db.Column(db.String(5000))
    state = db.Column(db.String(50))  

with app.app_context():
    db.create_all()

genai.configure(api_key="YOUR API KEY HERE")

generation_config = {
  "temperature": 1,
  "top_p": 0.95,
  "top_k": 0,
  "max_output_tokens": 8192,
}

safety_settings = [
  {
    "category": "HARM_CATEGORY_HARASSMENT",
    "threshold": "BLOCK_NONE"
  },
  {
    "category": "HARM_CATEGORY_HATE_SPEECH",
    "threshold": "BLOCK_NONE"
  },
  {
    "category": "HARM_CATEGORY_SEXUALLY_EXPLICIT",
    "threshold": "BLOCK_NONE"
  },
  {
    "category": "HARM_CATEGORY_DANGEROUS_CONTENT",
    "threshold": "BLOCK_NONE"
  },
]

system_instruction = "\nExtraia as seguintes informações, em linhas:\nResgate, medicamento ou mantimento\nEndereço\nGere um link no google maps com o Endereço\nQuantas pessoas e animais\nNome da pessoa\nNumero de telefone\nInformações adicionais \n\nFormato de saída:\n## Informações de Resgate:\n \nResgate, medicamento ou mantimento:\n \nEndereço:\n \nLink Google Maps:\n \n\nQuantas pessoas e animais:\n \nNome da pessoa:\n \nNúmero de telefone:\n \nInformações adicionais:"

model = genai.GenerativeModel(model_name="gemini-1.5-pro-latest",
                              generation_config=generation_config,
                              system_instruction=system_instruction,
                              safety_settings=safety_settings)

@app.route('/', methods=['GET'])
def index():
    return render_template('index.html')

@app.route('/upload', methods=['GET', 'POST'])
def upload_file():
    if request.method == 'POST':
        text = request.form.get('text')
        file = request.files.get('file')
        if file:
            file_path = os.path.join('/tmp', file.filename)
            file.save(file_path)
            convo = model.start_chat(history=[
              {
                "role": "user",
                "parts": [genai.upload_file(file_path)]
              },
            ])
        else:
            convo = model.start_chat(history=[
              {
                "role": "user",
                "parts": [text]
              },
            ])

        convo.send_message(genai.upload_file(file_path) if file else text)
        result = Result(output=convo.last.text)
        with app.app_context():
            db.session.add(result)
            db.session.commit()
            result_id = result.id
        return redirect(url_for('display_chat', result_id=result_id))
    return render_template('2.html')

@app.route('/display_chat/<int:result_id>', methods=['GET'])
def display_chat(result_id):
    result = Result.query.get(result_id)
    result.output = format_output(result.output)
    return render_template('2chat.html', result=result)

def format_output(output):
    # Split the output into lines
    lines = output.split('\n')
    # Initialize an empty list to hold the formatted lines
    formatted_lines = []
    # Iterate over each line
    for line in lines:
        # Check if the line contains a ':' character
        if ':' in line:
            # If it does, split the line into parts based on the first ':' character
            parts = line.split(':', 1)
            # Unpack the parts into key and value
            key, value = parts
            # Wrap the key in a <dt> tag if it's not empty
            if key.strip():
                formatted_lines.append(f'<dt>{key.strip()}</dt>')
            # Wrap the value in a <dd> tag if it's not empty
            if value.strip():
                formatted_lines.append(f'<dd>{value.strip()}</dd>')
    # Join the formatted lines into a single string and return it
    return Markup('\n'.join(formatted_lines))

@app.route('/retrieve', methods=['GET'])
def retrieve_output():
    results = Result.query.order_by(Result.id.desc()).all()
    for result in results:
        result.output = format_output(result.output)
    return render_template('3.html', results=results)

@app.route('/change_state', methods=['POST'])
def change_state():
    result_id = request.form.get('result_id')
    new_state = request.form.get('new_state')

    try:
        # Update state logic using result_id and new_state
        result = Result.query.get(result_id)
        if result:
            result.state = new_state
            db.session.commit()
        return 'State changed successfully!'
    except Exception as e:
        # Log the error for debugging
        print(f"Error changing state: {e}")
        return 'An error occurred. Please try again later.', 500  # Internal Server Errorreturn 'An error occurred. Please try again later.', 500  # Internal Server Error

if __name__ == '__main__':
    app.run(debug=True)
