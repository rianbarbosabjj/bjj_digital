import streamlit as st
import bcrypt
from database import get_db
from utils import formatar_e_validar_cpf
from firebase_admin import firestore

def autenticar_local(usuario_email_ou_cpf, senha):
    db = get_db()
    usuario_input = usuario_email_ou_cpf.lower().strip()
    cpf_formatado = formatar_e_validar_cpf(usuario_email_ou_cpf)
    
    users_ref = db.collection('usuarios')
    usuario_doc = None

    # Busca por Email
    query_email = list(users_ref.where('email', '==', usuario_input).stream())
    for doc in query_email:
        d = doc.to_dict()
        if d.get('auth_provider') != 'google':
            usuario_doc = doc
            break
    
    # Busca por CPF
    if not usuario_doc and cpf_formatado:
        query_cpf = list(users_ref.where('cpf', '==', cpf_formatado).stream())
        for doc in query_cpf:
            d = doc.to_dict()
            if d.get('auth_provider') != 'google':
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

def buscar_usuario_por_email(email):
    db = get_db()
    q = list(db.collection('usuarios').where('email', '==', email.lower().strip()).stream())
    if q:
        d = q[0].to_dict()
        return {"id": q[0].id, "nome": d.get('nome'), "tipo": d.get('tipo_usuario'), "perfil_completo": d.get('perfil_completo')}
    return None

def criar_usuario_parcial_google(email, nome):
    db = get_db()
    novo = {"email": email.lower(), "nome": nome.upper(), "auth_provider": "google", "perfil_completo": False, "tipo_usuario": "aluno", "data_criacao": firestore.SERVER_TIMESTAMP}
    _, ref = db.collection('usuarios').add(novo)
    return {"id": ref.id, "email": email, "nome": nome}
