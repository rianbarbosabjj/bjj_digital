import sqlite3
import json
from datetime import datetime

DB_NAME = "bjj_digital.db"

# ============================================================
# CONEXÃO
# ============================================================

def conectar():
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    return conn

# ============================================================
# INICIALIZAÇÃO DO BANCO
# ============================================================

def inicializar_banco():
    conn = conectar()
    cursor = conn.cursor()

    # ============================================
    # TABELA DE USUÁRIOS
    # ============================================
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS usuarios (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        nome TEXT,
        email TEXT UNIQUE,
        cpf TEXT UNIQUE,
        endereco TEXT,
        tipo TEXT,
        senha TEXT,
        criado_em TEXT
    );
    """)

    # ============================================
    # TABELA DE QUESTÕES
    # ============================================
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS questoes (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        tema TEXT NOT NULL,
        faixa TEXT NOT NULL,
        pergunta TEXT NOT NULL,
        opcoes TEXT NOT NULL,
        resposta TEXT NOT NULL,
        imagem TEXT,
        video TEXT
    );
    """)

    # ============================================
    # TABELA DE EXAMES CONFIG
    # ============================================
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS exames_config (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        nome TEXT NOT NULL,
        faixa TEXT NOT NULL,
        questoes_ids TEXT NOT NULL,
        embaralhar INTEGER DEFAULT 1,
        ativo INTEGER DEFAULT 0,
        professor_id INTEGER,
        criado_em TEXT
    );
    """)

    # ============================================
    # TABELA DE EXAMES REALIZADOS
    # ============================================
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS exames (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        usuario_id INTEGER NOT NULL,
        exame_config_id INTEGER NOT NULL,
        acertos INTEGER,
        total INTEGER,
        percentual REAL,
        aprovado INTEGER,
        data TEXT
    );
    """)

    # ============================================
    # TABELA DE CERTIFICADOS  (CORRIGIDA)
    # ============================================
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS certificados (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        usuario_id INTEGER NOT NULL,
        exame_config_id INTEGER NOT NULL,
        data_emissao TEXT NOT NULL,
        codigo TEXT,
        verificado INTEGER DEFAULT 0,
        FOREIGN KEY(usuario_id) REFERENCES usuarios(id),
        FOREIGN KEY(exame_config_id) REFERENCES exames_config(id)
    );
    """)
    # ============================================
    # TABELA MODO ROLA  
    # ============================================   
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS modo_rola (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        vencedor_id INTEGER,
        perdedor_id INTEGER,
        resultado TEXT,
        data TEXT DEFAULT CURRENT_TIMESTAMP
    );
    """)
    # ============================================
    # CRIAR ADMIN PADRÃO (se não existir)
    # ============================================
    cursor.execute("SELECT * FROM usuarios WHERE email='admin'")
    existe_admin = cursor.fetchone()

    if not existe_admin:
        from bcrypt import hashpw, gensalt

        senha_hash = hashpw("admin".encode(), gensalt()).decode()

        cursor.execute("""
            INSERT INTO usuarios (nome, email, cpf, endereco, tipo, senha, criado_em)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (
            "Administrador",
            "admin",
            None,
            None,
            "admin",
            senha_hash,
            datetime.now().strftime("%d/%m/%Y %H:%M")
        ))

        print(">> Usuário ADMIN criado com sucesso!")

    conn.commit()
    conn.close()

# ============================================================
# FUNÇÕES GENÉRICAS
# ============================================================

def consultar_todos(query, params=()):
    conn = conectar()
    cursor = conn.cursor()
    cursor.execute(query, params)
    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]

def consultar_um(query, params=()):
    conn = conectar()
    cursor = conn.cursor()
    cursor.execute(query, params)
    row = cursor.fetchone()
    conn.close()
    return dict(row) if row else None

def executar(query, params=()):
    conn = conectar()
    cursor = conn.cursor()
    cursor.execute(query, params)
    conn.commit()
    conn.close()

def executar_retorna_id(query, params=()):
    conn = conectar()
    cursor = conn.cursor()
    cursor.execute(query, params)
    conn.commit()
    last_id = cursor.lastrowid
    conn.close()
    return last_id
