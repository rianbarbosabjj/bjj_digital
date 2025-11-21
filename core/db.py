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
    # TABELA DE QUESTÕES (MODELO PROFISSIONAL)
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
    # TABELA DE EXAMES CONFIGURADOS PELO PROFESSOR
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
    # TABELA DE EXAMES REALIZADOS PELO ALUNO
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
