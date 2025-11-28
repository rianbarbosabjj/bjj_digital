import streamlit as st
import bcrypt
from database import get_db
from utils import formatar_e_validar_cpf
from firebase_admin import firestore

def autenticar_local(usuario_email_ou_cpf, senha):
    """
    Autentica o usuário verificando email ou CPF no Firestore.
    Retorna dicionário com dados do usuário + flag 'precisa_trocar_senha'.
    """
    db = get_db()
    cpf_formatado = formatar_e_validar_cpf(usuario_email_ou_cpf)
    
    users_ref = db.collection('usuarios')
    usuario_doc = None

    # 1. Busca por Email
    query_email = users_ref.where('email', '==', usuario_email_ou_cpf).stream()
    for doc in query_email:
        d = doc.to_dict()
        if d.get('auth_provider') == 'local':
            usuario_doc = doc
            break
    
    # 2. Busca por CPF (se não achou por email)
    if not usuario_doc and cpf_formatado:
        query_cpf = users_ref.where('cpf', '==', cpf_formatado).stream()
        for doc in query_cpf:
            d = doc.to_dict()
            if d.get('auth_provider') == 'local':
                usuario_doc = doc
                break
            
    if usuario_doc:
        dados = usuario_doc.to_dict()
        senha_hash = dados.get('senha')
        
        # Verifica a senha
        if senha_hash and bcrypt.checkpw(senha.encode(), senha_hash.encode()):
            tipo_perfil = dados.get('tipo_usuario', 'aluno')
            
            # Retorna os dados incluindo a flag de troca de senha
            return {
                "id": usuario_doc.id,
                "nome": dados.get('nome'),
                "tipo": tipo_perfil,
                "email": dados.get('email'),
                "precisa_trocar_senha": dados.get('precisa_trocar_senha', False)
            }
        
    return None

def buscar_usuario_por_email(email_ou_cpf):
    """Busca usuário para o fluxo do Google Auth."""
    db = get_db()
    users_ref = db.collection('usuarios')
    usuario_doc = None
    
    query = users_ref.where('email', '==', email_ou_cpf).stream()
    for doc in query:
        usuario_doc = doc
        break
        
    if usuario_doc:
        dados = usuario_doc.to_dict()
        tipo_perfil = dados.get('tipo_usuario', 'aluno')
        
        return {
            "id": usuario_doc.id,
            "nome": dados.get('nome'),
            "tipo": tipo_perfil,
            "perfil_completo": dados.get('perfil_completo', False),
            "email": dados.get('email')
        }
        
    return None

def criar_usuario_parcial_google(email, nome):
    """Cria o registro inicial vindo do Google."""
    db = get_db()
    
    novo_usuario = {
        "email": email,
        "nome": nome.upper(),
        "auth_provider": "google",
        "perfil_completo": False,
        "tipo_usuario": "aluno", # Default até completar cadastro
        "data_criacao": firestore.SERVER_TIMESTAMP
    }
    
    _, doc_ref = db.collection('usuarios').add(novo_usuario)
    
    return {
        "id": doc_ref.id, 
        "email": email, 
        "nome": nome
    }
