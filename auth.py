import sqlite3
import bcrypt
from config import DB_PATH
from utils import formatar_e_validar_cpf

# 3. Autenticação local (Login/Senha)
def autenticar_local(usuario_email_ou_cpf, senha):
    """
    Atualizado: Autentica o usuário local usando NOME, EMAIL ou CPF.
    """
    # 📝 Tenta formatar para CPF para verificar se a entrada é um CPF
    cpf_formatado = formatar_e_validar_cpf(usuario_email_ou_cpf) 

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # 1. Tenta autenticar usando NOME ou EMAIL (a entrada original)
    cursor.execute(
        "SELECT id, nome, tipo_usuario, senha FROM usuarios WHERE (nome=? OR email=?) AND auth_provider='local'", 
        (usuario_email_ou_cpf, usuario_email_ou_cpf) 
    )
    dados = cursor.fetchone()
    
    # 2. Se a busca por NOME/EMAIL falhar e a entrada for um CPF válido, tenta autenticar por CPF
    if not dados and cpf_formatado:
        cursor.execute(
            "SELECT id, nome, tipo_usuario, senha FROM usuarios WHERE cpf=? AND auth_provider='local'", 
            (cpf_formatado,) # Busca usando o CPF formatado
        )
        dados = cursor.fetchone()
        
    conn.close()
    
    # 3. Verifica a senha no resultado final
    if dados and bcrypt.checkpw(senha.encode(), dados[3].encode()):
        return {"id": dados[0], "nome": dados[1], "tipo": dados[2]}
        
    return None

# 4. Funções de busca e criação de usuário
def buscar_usuario_por_email(email_ou_cpf):
    """
    Busca um usuário pelo email (principalmente usado para Auth Social)
    e retorna seus dados. Também verifica o CPF para garantir unicidade cruzada.
    """
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    cpf_formatado = formatar_e_validar_cpf(email_ou_cpf)

    # Busca por 'email' (o caso mais comum) ou 'cpf' (se a entrada for um CPF válido)
    if cpf_formatado:
        cursor.execute(
            "SELECT id, nome, tipo_usuario, perfil_completo FROM usuarios WHERE email=? OR cpf=?", 
            (email_ou_cpf, cpf_formatado)
        )
    else:
        cursor.execute(
            "SELECT id, nome, tipo_usuario, perfil_completo FROM usuarios WHERE email=?", 
            (email_ou_cpf,)
        )
        
    dados = cursor.fetchone()
    conn.close()
    
    if dados:
        return {
            "id": dados[0], 
            "nome": dados[1], 
            "tipo": dados[2], 
            "perfil_completo": bool(dados[3])
        }
        
    return None

def criar_usuario_parcial_google(email, nome):
    """Cria um registro inicial para um novo usuário do Google."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    try:
        cursor.execute(
            """
            INSERT INTO usuarios (email, nome, auth_provider, perfil_completo)
            VALUES (?, ?, 'google', 0)
            """, (email, nome)
        )
        conn.commit()
        novo_id = cursor.lastrowid
        conn.close()
        return {"id": novo_id, "email": email, "nome": nome}
    except sqlite3.IntegrityError: # Email já existe
        conn.close()
        return None
