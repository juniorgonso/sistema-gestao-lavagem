from flask import Flask, jsonify, request
from flask_cors import CORS
import sqlite3
from datetime import datetime 

app = Flask(__name__)
CORS(app)

def get_db_connection():
    conn = sqlite3.connect('banco.db')
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # 1. NOVA COLUNA 'role' ADICIONADA AQUI
    cursor.execute('''CREATE TABLE IF NOT EXISTS usuarios (
        id INTEGER PRIMARY KEY AUTOINCREMENT, 
        username TEXT UNIQUE NOT NULL, 
        password TEXT NOT NULL,
        role TEXT DEFAULT 'funcionario' 
    )''')
    
    cursor.execute('''CREATE TABLE IF NOT EXISTS servicos (
        id INTEGER PRIMARY KEY AUTOINCREMENT, 
        placa TEXT NOT NULL, 
        modelo TEXT NOT NULL, 
        tipo_lavagem TEXT NOT NULL, 
        status TEXT DEFAULT 'Pendente',
        data_entrada TEXT,
        data_conclusao TEXT,
        usuario_registro TEXT
    )''')
    
    cursor.execute("SELECT * FROM usuarios WHERE username = 'admin'")
    if cursor.fetchone() is None:
        # 2. ADMIN CRIADO COM O CARGO 'admin'
        cursor.execute("INSERT INTO usuarios (username, password, role) VALUES ('admin', 'admin', 'admin')")
    
    conn.commit()
    conn.close() 

# 1. Login
@app.route('/login', methods=['POST'])
def login():
    dados = request.get_json()
    conn = get_db_connection()
    usuario = conn.execute("SELECT * FROM usuarios WHERE username = ? AND password = ?", (dados['username'], dados['password'])).fetchone()
    conn.close()
    if usuario:
        # 3. O LOGIN AGORA AVISA O APLICATIVO QUAL É O CARGO DA PESSOA
        return jsonify({
            "mensagem": "Login com sucesso!", 
            "sucesso": True,
            "role": usuario['role'],
            "username": usuario['username']
        }), 200
    return jsonify({"mensagem": "Usuário ou senha incorretos!", "sucesso": False}), 401

# 2. Listar PENDENTES
@app.route('/servicos', methods=['GET'])
def listar_pendentes():
    conn = get_db_connection()
    servicos = conn.execute("SELECT * FROM servicos WHERE status = 'Pendente'").fetchall()
    conn.close()
    return jsonify([dict(ix) for ix in servicos]), 200

# 3. Adicionar novo serviço
@app.route('/servicos', methods=['POST'])
def adicionar_servico():
    dados = request.get_json()
    data_atual = datetime.now().strftime("%d/%m/%Y às %H:%M") 
    
    # Captura quem enviou do aplicativo
    quem_registrou = dados.get('usuario_registro', 'Desconhecido')
    
    conn = get_db_connection()
    conn.execute("INSERT INTO servicos (placa, modelo, tipo_lavagem, data_entrada, usuario_registro) VALUES (?, ?, ?, ?, ?)", 
                 (dados['placa'], dados['modelo'], dados['tipo_lavagem'], data_atual, quem_registrou))
    conn.commit()
    conn.close()
    return jsonify({"mensagem": "Serviço adicionado com sucesso!"}), 201

# 4. Concluir serviço
@app.route('/servicos/<int:id>/concluir', methods=['PUT'])
def concluir_servico(id):
    data_atual = datetime.now().strftime("%d/%m/%Y às %H:%M")
    conn = get_db_connection()
    conn.execute("UPDATE servicos SET status = 'Concluido', data_conclusao = ? WHERE id = ?", (data_atual, id))
    conn.commit()
    conn.close()
    return jsonify({"mensagem": "Serviço concluído com sucesso!"}), 200

# 5. Histórico
@app.route('/historico', methods=['GET'])
def listar_historico():
    conn = get_db_connection()
    servicos = conn.execute("SELECT * FROM servicos WHERE status = 'Concluido' ORDER BY id DESC").fetchall()
    conn.close()
    return jsonify([dict(ix) for ix in servicos]), 200

# 6. Cadastro de Usuário (Novo usuário entra como 'cliente')
@app.route('/cadastro', methods=['POST'])
def registar_usuario():
    dados = request.get_json()
    usuario = dados.get('username')
    senha = dados.get('password')

    if not usuario or not senha:
        return jsonify({"mensagem": "Por favor, preencha todos os campos!", "sucesso": False}), 400

    conn = get_db_connection()
    try:
        conn.execute("INSERT INTO usuarios (username, password, role) VALUES (?, ?, 'cliente')", (usuario, senha))
        conn.commit()
        return jsonify({"mensagem": "Usuário registrado com sucesso!", "sucesso": True}), 201
    except sqlite3.IntegrityError:
        return jsonify({"mensagem": "Este nome de usuário já está sendo usado!", "sucesso": False}), 400
    finally:
        conn.close()

# ==========================================
# NOVAS ROTAS DE ADMINISTRAÇÃO DE USUÁRIOS
# ==========================================

# 7. Listar todos os usuários (Para a tela do Admin)
@app.route('/usuarios', methods=['GET'])
def listar_usuarios():
    conn = get_db_connection()
    # Não vamos retornar as senhas por segurança!
    usuarios = conn.execute("SELECT id, username, role FROM usuarios").fetchall()
    conn.close()
    return jsonify([dict(ix) for ix in usuarios]), 200

# 8. Editar cargo ou nome do usuário
@app.route('/usuarios/<int:id>', methods=['PUT'])
def editar_usuario(id):
    dados = request.get_json()
    novo_username = dados.get('username')
    novo_role = dados.get('role') # admin ou funcionario
    
    conn = get_db_connection()
    conn.execute("UPDATE usuarios SET username = ?, role = ? WHERE id = ?", (novo_username, novo_role, id))
    conn.commit()
    conn.close()
    return jsonify({"mensagem": "Usuário atualizado com sucesso!"}), 200

# 9. Apagar usuário
@app.route('/usuarios/<int:id>', methods=['DELETE'])
def deletar_usuario(id):
    conn = get_db_connection()
    # Impede que o Admin apague a si mesmo (id 1)
    if id == 1:
        return jsonify({"mensagem": "Não é possível apagar o Administrador principal!"}), 403
        
    conn.execute("DELETE FROM usuarios WHERE id = ?", (id,))
    conn.commit()
    conn.close()
    return jsonify({"mensagem": "Usuário apagado com sucesso!"}), 200

if __name__ == '__main__':
    init_db()
    app.run(debug=True, host='0.0.0.0', port=5000)