import streamlit as st
import bcrypt
from database import get_db
from utils import formatar_e_validar_cpf
from firebase_admin import firestore

def autenticar_local(usuario_email_ou_cpf, senha):
    """
    Autentica o usuário verificando email ou CPF no Firestore.
    """
    db = get_db()
    
    # Limpeza básica
    usuario_input = usuario_email_ou_cpf.lower().strip()
    cpf_formatado = formatar_e_validar_cpf(usuario_email_ou_cpf)
    
    users_ref = db.collection('usuarios')
    usuario_doc = None

    # Busca por Email
    query_email = list(users_ref.where('email', '==', usuario_input).stream())
    for doc in query_email:
        d = doc.to_dict()
        if d.get('auth_provider') == 'google': continue
        usuario_doc = doc
        break
    
    # Busca por CPF
    if not usuario_doc and cpf_formatado:
        query_cpf = list(users_ref.where('cpf', '==', cpf_formatado).stream())
        for doc in query_cpf:
            d = doc.to_dict()
            if d.get('auth_provider') == 'google': continue
            usuario_doc = doc
            break
            
    if usuario_doc:
        dados = usuario_doc.to_dict()
        senha_hash = dados.get('senha')
        
        if senha_hash:
            try:
                if bcrypt.checkpw(senha.encode('utf-8'), senha_hash.encode('utf-8')):
                    return {
                        "id": usuario_doc.id,
                        "nome": dados.get('nome'),
                        "tipo": dados.get('tipo_usuario', 'aluno'),
                        "email": dados.get('email'),
                        "precisa_trocar_senha": dados.get('precisa_trocar_senha', False)
                    }
            except: return None
    return None

def buscar_usuario_por_email(email_ou_cpf):
    db = get_db()
    email_clean = email_ou_cpf.lower().strip()
    query = list(db.collection('usuarios').where('email', '==', email_clean).stream())
    if len(query) > 0:
        usuario_doc = query[0]
        dados = usuario_doc.to_dict()
        return {
            "id": usuario_doc.id,
            "nome": dados.get('nome'),
            "tipo": dados.get('tipo_usuario', 'aluno'),
            "perfil_completo": dados.get('perfil_completo', False),
            "email": dados.get('email')
        }
    return None

def criar_usuario_parcial_google(email, nome):
    db = get_db()
    novo = {
        "email": email.lower(),
        "nome": nome.upper(),
        "auth_provider": "google",
        "perfil_completo": False,
        "tipo_usuario": "aluno", 
        "data_criacao": firestore.SERVER_TIMESTAMP
    }
    _, doc_ref = db.collection('usuarios').add(novo)
    return {"id": doc_ref.id, "email": email, "nome": nome}
