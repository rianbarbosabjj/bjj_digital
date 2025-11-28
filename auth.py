# auth.py
import streamlit as st
import bcrypt
from database import get_db
from firebase_admin import firestore

def autenticar_local(login_input, senha_input):
    """
    Autentica usuário por CPF ou Email + Senha (com hash bcrypt).
    Retorna o dicionário do usuário ou None.
    """
    db = get_db()
    users_ref = db.collection('usuarios')
    
    # Tenta buscar por Email
    query_email = list(users_ref.where('email', '==', login_input).stream())
    
    user_doc = None
    
    if query_email:
        user_doc = query_email[0]
    else:
        # Se não achou por email, tenta por CPF
        query_cpf = list(users_ref.where('cpf', '==', login_input).stream())
        if query_cpf:
            user_doc = query_cpf[0]
    
    if user_doc:
        user_data = user_doc.to_dict()
        
        # Se for login social (Google), não tem senha
        if user_data.get("auth_provider") == "google":
            return None
            
        stored_hash = user_data.get("senha")
        if stored_hash:
            # Verifica a senha usando bcrypt
            # Nota: encode() transforma a string em bytes, necessário para o bcrypt
            if bcrypt.checkpw(senha_input.encode('utf-8'), stored_hash.encode('utf-8')):
                user_data['id'] = user_doc.id
                return user_data
                
    return None

def buscar_usuario_por_email(email):
    """Retorna dados do usuário se existir, ou None."""
    db = get_db()
    users_ref = db.collection('usuarios')
    results = list(users_ref.where('email', '==', email).stream())
    
    if results:
        data = results[0].to_dict()
        data['id'] = results[0].id
        return data
    return None

def criar_usuario_parcial_google(email, nome):
    """Cria usuário vindo do Google (sem senha)."""
    db = get_db()
    novo_user = {
        "email": email,
        "nome": nome,
        "auth_provider": "google",
        "perfil_completo": False,
        "data_criacao": firestore.SERVER_TIMESTAMP,
        "tipo_usuario": "aluno" # Default, depois ele muda no cadastro
    }
    _, doc_ref = db.collection('usuarios').add(novo_user)
    novo_user['id'] = doc_ref.id
    return novo_user
