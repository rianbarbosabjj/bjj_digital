import streamlit as st
import bcrypt
from database import get_db
from utils import formatar_e_validar_cpf
from firebase_admin import firestore

def autenticar_local(usuario_email_ou_cpf, senha):
    """
    Autentica o usuário verificando email ou CPF no Firestore.
    Versão Robusta: Aceita usuários sem o campo 'auth_provider' definido.
    """
    db = get_db()
    
    # Limpeza básica da entrada
    usuario_input = usuario_email_ou_cpf.lower().strip()
    cpf_formatado = formatar_e_validar_cpf(usuario_email_ou_cpf)
    
    users_ref = db.collection('usuarios')
    usuario_doc = None

    # --- ESTRATÉGIA 1: BUSCA POR EMAIL ---
    query_email = list(users_ref.where('email', '==', usuario_input).stream())
    
    for doc in query_email:
        d = doc.to_dict()
        # Se for conta Google, ignoramos (pois não tem senha)
        if d.get('auth_provider') == 'google':
            continue
        
        # Aceitamos 'local' OU se o campo não existir (usuários antigos)
        usuario_doc = doc
        break
    
    # --- ESTRATÉGIA 2: BUSCA POR CPF (se não achou por email) ---
    if not usuario_doc and cpf_formatado:
        query_cpf = list(users_ref.where('cpf', '==', cpf_formatado).stream())
        for doc in query_cpf:
            d = doc.to_dict()
            if d.get('auth_provider') == 'google':
                continue
            
            usuario_doc = doc
            break
            
    # --- VERIFICAÇÃO DA SENHA ---
    if usuario_doc:
        dados = usuario_doc.to_dict()
        senha_hash = dados.get('senha')
        
        if senha_hash:
            try:
                # Converte inputs para bytes, necessário para o bcrypt
                senha_bytes = senha.encode('utf-8')
                hash_bytes = senha_hash.encode('utf-8')
                
                if bcrypt.checkpw(senha_bytes, hash_bytes):
                    tipo_perfil = dados.get('tipo_usuario', 'aluno')
                    
                    return {
                        "id": usuario_doc.id,
                        "nome": dados.get('nome'),
                        "tipo": tipo_perfil,
                        "email": dados.get('email'),
                        "precisa_trocar_senha": dados.get('precisa_trocar_senha', False)
                    }
            except Exception as e:
                print(f"Erro ao verificar hash: {e}")
                # Em caso de erro na criptografia (banco corrompido), retorna falha
                return None
        
    return None

def buscar_usuario_por_email(email_ou_cpf):
    """Busca usuário para o fluxo do Google Auth."""
    db = get_db()
    users_ref = db.collection('usuarios')
    usuario_doc = None
    
    # Garante lowercase para busca
    email_clean = email_ou_cpf.lower().strip()
    
    query = list(users_ref.where('email', '==', email_clean).stream())
    
    if len(query) > 0:
        usuario_doc = query[0]
        
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
        "email": email.lower(), # Força salvar email minúsculo
        "nome": nome.upper(),
        "auth_provider": "google",
        "perfil_completo": False,
        "tipo_usuario": "aluno", 
        "data_criacao": firestore.SERVER_TIMESTAMP
    }
    
    _, doc_ref = db.collection('usuarios').add(novo_usuario)
    
    return {
        "id": doc_ref.id, 
        "email": email, 
        "nome": nome
    }
