import bcrypt
import streamlit as st
from firebase_admin import firestore  # <--- ESTA É A LINHA QUE FALTAVA
from database import get_db

def buscar_usuario_por_email(email):
    """Busca um usuário no Firestore pelo e-mail."""
    db = get_db()
    try:
        users_ref = db.collection('usuarios')
        # limit(1) é mais eficiente pois só precisamos de um
        query = users_ref.where('email', '==', email).limit(1).stream()
        
        for doc in query:
            user_data = doc.to_dict()
            user_data['id'] = doc.id # Adiciona o ID do documento ao dicionário
            return user_data
            
        return None
    except Exception as e:
        st.error(f"Erro ao buscar usuário: {e}")
        return None

def autenticar_local(login_input, senha):
    """
    Autentica usuário via Firestore usando Email ou CPF.
    login_input: pode ser email ou cpf.
    senha: senha em texto plano.
    """
    db = get_db()
    users_ref = db.collection('usuarios')
    user_found = None
    
    try:
        # 1. Tentar encontrar por E-MAIL
        query_email = users_ref.where('email', '==', login_input).limit(1).stream()
        for doc in query_email:
            user_found = doc.to_dict()
            user_found['id'] = doc.id
            break
        
        # 2. Se não achou por email, tentar por CPF
        if not user_found:
            # Assume que o input já veio formatado do login.py, ou busca direto
            query_cpf = users_ref.where('cpf', '==', login_input).limit(1).stream()
            for doc in query_cpf:
                user_found = doc.to_dict()
                user_found['id'] = doc.id
                break
        
        # 3. Verificar senha
        if user_found:
            stored_hash = user_found.get('senha')
            if stored_hash:
                # bcrypt requer bytes, então encode()
                if bcrypt.checkpw(senha.encode(), stored_hash.encode()):
                    return user_found
    except Exception as e:
        st.error(f"Erro na autenticação: {e}")
        
    return None

def criar_usuario_parcial_google(email, nome):
    """
    Cria um registro inicial para usuários que logaram com Google mas não existem no banco.
    Define 'perfil_completo' como False para forçar o cadastro complementar depois.
    """
    db = get_db()
    
    try:
        novo_user = {
            "nome": nome.upper(),
            "email": email,
            "auth_provider": "google",
            "perfil_completo": False, # Importante: flag para redirecionar para completar cadastro
            "tipo_usuario": None,     # Será definido no completar cadastro
            "data_criacao": firestore.SERVER_TIMESTAMP # <--- AQUI OCORRIA O ERRO
        }
        
        _, doc_ref = db.collection('usuarios').add(novo_user)
        
        # Retorna o usuário já com o ID gerado para colocar na sessão
        novo_user['id'] = doc_ref.id
        return novo_user
        
    except Exception as e:
        st.error(f"Erro ao criar usuário Google: {e}")
        return None
