import sqlite3
import threading

DB_PATH = "bjj_digital.db"

# Mutex para evitar "database is locked"
db_lock = threading.Lock()


def conectar():
    """Conecta ao banco com controle de bloqueio."""
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn


# ============================================================
# CRIAÇÃO DAS TABELAS
# ============================================================

def inicializar_banco():
    """Cria as tabelas caso não existam."""
    with db_lock:
        conn = conectar()
        cursor = conn.cursor()

        # Usuários
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS usuarios (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nome TEXT NOT NULL,
            email TEXT UNIQUE,
            senha TEXT,
            cpf TEXT UNIQUE,
            tipo TEXT DEFAULT 'aluno',
            faixa TEXT,
            telefone TEXT,
            endereco TEXT,
            bairro TEXT,
            cidade TEXT,
            estado TEXT,
            cep TEXT,
            numero TEXT,
            criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        """)

        # Equipes
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS equipes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nome TEXT NOT NULL UNIQUE,
            professor_id INTEGER,
            FOREIGN KEY(professor_id) REFERENCES usuarios(id)
        );
        """)

        # Questões por faixa
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS questoes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            faixa TEXT NOT NULL,
            pergunta TEXT NOT NULL,
            alternativa_a TEXT,
            alternativa_b TEXT,
            alternativa_c TEXT,
            alternativa_d TEXT,
            correta TEXT
        );
        """)

        # Exames realizados
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS exames (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            usuario_id INTEGER NOT NULL,
            faixa TEXT NOT NULL,
            nota REAL NOT NULL,
            aprovado INTEGER NOT NULL,
            data TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(usuario_id) REFERENCES usuarios(id)
        );
        """)

        # Certificados (QR code + PDF)
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS certificados (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            usuario_id INTEGER NOT NULL,
            faixa TEXT NOT NULL,
            codigo_qr TEXT,
            caminho_pdf TEXT,
            data TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(usuario_id) REFERENCES usuarios(id)
        );
        """)

        conn.commit()
        conn.close()


# ============================================================
# FUNÇÕES UTILITÁRIAS PADRÃO
# ============================================================

def executar(query, params=()):
    """Executa INSERT, UPDATE ou DELETE com garantia de commit."""
    with db_lock:
        conn = conectar()
        cursor = conn.cursor()
        try:
            cursor.execute(query, params)
            conn.commit()
        finally:
            conn.close()


def consultar_um(query, params=()):
    """Retorna apenas 1 registro."""
    with db_lock:
        conn = conectar()
        cursor = conn.cursor()
        cursor.execute(query, params)
        resultado = cursor.fetchone()
        conn.close()
        return resultado


def consultar_todos(query, params=()):
    """Retorna lista de registros."""
    with db_lock:
        conn = conectar()
        cursor = conn.cursor()
        cursor.execute(query, params)
        resultado = cursor.fetchall()
        conn.close()
        return resultado


# ============================================================
# FUNÇÕES DE ALTO NÍVEL (PÚBLICAS)
# ============================================================

def inserir_usuario(nome, email, senha_hash, cpf, tipo="aluno"):
    executar("""
        INSERT INTO usuarios (nome, email, senha, cpf, tipo)
        VALUES (?, ?, ?, ?, ?)
    """, (nome, email, senha_hash, cpf, tipo))


def buscar_usuario_por_email(email):
    return consultar_um("SELECT * FROM usuarios WHERE email = ?", (email,))


def buscar_usuario_por_id(id_user):
    return consultar_um("SELECT * FROM usuarios WHERE id = ?", (id_user,))


def cpf_existe(cpf):
    return consultar_um("SELECT id FROM usuarios WHERE cpf = ?", (cpf,)) is not None


def email_existe(email):
    return consultar_um("SELECT id FROM usuarios WHERE email = ?", (email,)) is not None


def atualizar_endereco(id_user, dados):
    executar("""
        UPDATE usuarios
        SET endereco=?, bairro=?, cidade=?, estado=?, cep=?, numero=?
        WHERE id=?
    """, (
        dados["endereco"], dados["bairro"], dados["cidade"],
        dados["estado"], dados["cep"], dados["numero"], id_user
    ))


def salvar_certificado(usuario_id, faixa, codigo_qr, caminho_pdf):
    executar("""
        INSERT INTO certificados (usuario_id, faixa, codigo_qr, caminho_pdf)
        VALUES (?, ?, ?, ?)
    """, (usuario_id, faixa, codigo_qr, caminho_pdf))

