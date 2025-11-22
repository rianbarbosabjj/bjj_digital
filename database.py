import sqlite3
import os
import bcrypt
import streamlit as st
from config import DB_PATH

def criar_banco():
    """Cria o banco de dados e suas tabelas, caso não existam."""
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # ... (COPIE AQUI TODO O CONTEÚDO DO cursor.executescript DO SEU ARQUIVO ORIGINAL) ...
    # Devido ao tamanho, copiei apenas o início e fim para guiar:
    cursor.executescript("""
    CREATE TABLE IF NOT EXISTS usuarios (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        nome TEXT,
        email TEXT UNIQUE,
        cpf TEXT UNIQUE,
        tipo_usuario TEXT,
        senha TEXT,
        auth_provider TEXT DEFAULT 'local',
        perfil_completo BOOLEAN DEFAULT 0,
        data_criacao DATETIME DEFAULT CURRENT_TIMESTAMP,
        cep TEXT, logradouro TEXT, numero TEXT, complemento TEXT, bairro TEXT, cidade TEXT, uf TEXT
    );
    CREATE TABLE IF NOT EXISTS equipes (id INTEGER PRIMARY KEY AUTOINCREMENT, nome TEXT NOT NULL, descricao TEXT, professor_responsavel_id INTEGER, ativo BOOLEAN DEFAULT 1);
    CREATE TABLE IF NOT EXISTS professores (id INTEGER PRIMARY KEY AUTOINCREMENT, usuario_id INTEGER, equipe_id INTEGER, pode_aprovar BOOLEAN DEFAULT 0, eh_responsavel BOOLEAN DEFAULT 0, status_vinculo TEXT DEFAULT 'pendente', data_vinculo DATETIME DEFAULT CURRENT_TIMESTAMP);
    CREATE TABLE IF NOT EXISTS alunos (id INTEGER PRIMARY KEY AUTOINCREMENT, usuario_id INTEGER, faixa_atual TEXT, turma TEXT, professor_id INTEGER, equipe_id INTEGER, status_vinculo TEXT DEFAULT 'pendente', data_pedido DATETIME DEFAULT CURRENT_TIMESTAMP, exame_habilitado BOOLEAN DEFAULT 0);
    CREATE TABLE IF NOT EXISTS resultados (id INTEGER PRIMARY KEY AUTOINCREMENT, usuario TEXT, modo TEXT, tema TEXT, faixa TEXT, pontuacao INTEGER, tempo TEXT, data DATETIME DEFAULT CURRENT_TIMESTAMP, codigo_verificacao TEXT, acertos INTEGER, total_questoes INTEGER);
    CREATE TABLE IF NOT EXISTS rola_resultados (id INTEGER PRIMARY KEY AUTOINCREMENT, usuario TEXT, faixa TEXT, tema TEXT, acertos INTEGER, total INTEGER, percentual REAL, data DATETIME DEFAULT CURRENT_TIMESTAMP);
    """)

    conn.commit()
    conn.close()

def criar_usuarios_teste():
    # ... (COPIE AQUI A FUNÇÃO criar_usuarios_teste DO SEU ORIGINAL) ...
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    usuarios = [("admin", "admin", "admin@bjj.local"), ("professor", "professor", "professor@bjj.local"), ("aluno", "aluno", "aluno@bjj.local")]
    for nome, tipo, email in usuarios:
        cursor.execute("SELECT id FROM usuarios WHERE nome=?", (nome,))
        if cursor.fetchone() is None:
            senha_hash = bcrypt.hashpw(nome.encode(), bcrypt.gensalt()).decode()
            cursor.execute("INSERT INTO usuarios (nome, tipo_usuario, senha, email, auth_provider, perfil_completo) VALUES (?, ?, ?, ?, 'local', 1)", (nome, tipo, senha_hash, email))
    conn.commit()
    conn.close()
