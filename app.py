# Importando as bibliotecas necessárias
from flask import Flask, request, render_template, redirect, url_for
from flask_sqlalchemy import SQLAlchemy
import hashlib
import google.generativeai as genai
import os
from flask import session
from markupsafe import Markup

# Inicializando a aplicação Flask
app = Flask(__name__)

# Configurando o banco de dados SQLite
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:////tmp/test.db'
app.config['SECRET_KEY'] = '1234567890'  # Adicione esta linha

# Inicializando o objeto SQLAlchemy
db = SQLAlchemy(app)

# Definindo o modelo de dados Result
class Result(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    output = db.Column(db.String(5000))
    state = db.Column(db.String(50))  

# Criando todas as tabelas do banco de dados
with app.app_context():
    db.create_all()

# Configurando a API do Gemini
genai.configure(api_key="YOUR API KEY HERE")

# Configurando os parâmetros de geração do modelo
generation_config = {
  "temperature": 1,
  "top_p": 0.95,
  "top_k": 0,
  "max_output_tokens": 8192,
}

# Configurando as configurações de segurança do modelo
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

# Definindo a instrução do sistema para o modelo
system_instruction = "\nExtraia as seguintes informações, em linhas:\nResgate, medicamento ou mantimento\nEndereço\nGere um link no google maps com o Endereço\nQuantas pessoas e animais\nNome da pessoa\nNumero de telefone\nInformações adicionais \n\nFormato de saída:\n## Informações de Resgate:\n \nResgate, medicamento ou mantimento:\n \nEndereço:\n \nLink Google Maps:\n \n\nQuantas pessoas e animais:\n \nNome da pessoa:\n \nNúmero de telefone:\n \nInformações adicionais:"

# Inicializando o modelo generativo
model = genai.GenerativeModel(model_name="gemini-1.5-pro-latest",
                              generation_config=generation_config,
                              system_instruction=system_instruction,
                              safety_settings=safety_settings)

# Definindo a rota principal
@app.route('/', methods=['GET'])
def index():
    return render_template('index.html')

# Definindo a rota para upload de arquivos
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

# Definindo a rota
@app.route('/display_chat/<int:result_id>', methods=['GET'])
def display_chat(result_id):
    result = Result.query.get(result_id)
    result.output = format_output(result.output)
    return render_template('2chat.html', result=result)

# Função para formatar a saída
def format_output(output):
    # Dividir a saída em linhas
    lines = output.split('\n')
    # Inicializar uma lista vazia para guardar as linhas formatadas
    formatted_lines = []
    # Iterar sobre cada linha
    for line in lines:
        # Verificar se a linha contém um caractere ':'
        if ':' in line:
            # Se sim, dividir a linha em partes com base no primeiro caractere ':'
            parts = line.split(':', 1)
            # Desempacotar as partes em chave e valor
            key, value = parts
            # Envolva a chave em uma tag <dt> se não estiver vazia
            if key.strip():
                formatted_lines.append(f'<dt>{key.strip()}</dt>')
            # Envolva o valor em uma tag <dd> se não estiver vazia
            if value.strip():
                formatted_lines.append(f'<dd>{value.strip()}</dd>')
    # Juntar as linhas formatadas em uma única string e retorná-la
    return Markup('\n'.join(formatted_lines))

# Definindo a rota para recuperar a saída
@app.route('/retrieve', methods=['GET'])
def retrieve_output():
    results = Result.query.order_by(Result.id.desc()).all()
    for result in results:
        result.output = format_output(result.output)
    return render_template('3.html', results=results)

# Definindo a rota para alterar o estado ddos botoes
@app.route('/change_state', methods=['POST'])
def change_state():
    result_id = request.form.get('result_id')
    new_state = request.form.get('new_state')

    try:
        # Lógica de atualização do estado usando result_id e new_state
        result = Result.query.get(result_id)
        if result:
            result.state = new_state
            db.session.commit()
        return 'State changed successfully!'
    except Exception as e:
        # Log the error for debugging
        print(f"Error changing state: {e}")
        return 'Pcorreu algum erro.', 500  # Internal Server Error
    
if __name__ == '__main__':
    app.run(debug=True)
