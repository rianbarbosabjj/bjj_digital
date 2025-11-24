import streamlit as st
import firebase_admin
from firebase_admin import credentials, firestore

# Cache para garantir que a conexão seja feita apenas uma vez
@st.cache_resource
def get_db():
    """Inicializa e retorna a conexão com o Firestore."""
    
    # Verifica se o app do Firebase já não está rodando para evitar erro de inicialização duplicada
    if not firebase_admin._apps:
        try:
            # Carrega as credenciais do secrets.toml
            key_dict = dict(st.secrets["FIREBASE_KEY"])
            
            # Cria o objeto de credencial
            cred = credentials.Certificate(key_dict)
            
            # Inicializa o Firebase
            firebase_admin.initialize_app(cred)
            
            # Retorna o cliente do banco de dados (Firestore)
            # IMPORTANTE: Forçamos o project_id para evitar o erro 404 Not Found
            return firestore.client(project=key_dict['project_id'])
            
        except Exception as e:
            st.error(f"Erro ao conectar com o Firebase: {e}")
            return None
            
    # Se já estiver inicializado, tenta retornar o cliente forçando o projeto novamente
    try:
        key_dict = dict(st.secrets["FIREBASE_KEY"])
        return firestore.client(project=key_dict['project_id'])
    except:
        return firestore.client()

# --- FUNÇÕES LEGADO (MANTIDAS VAZIAS PARA COMPATIBILIDADE) ---
# Como migramos para a nuvem (Firebase), não criamos mais banco local (.db).
# Mantemos as funções vazias para que o app.py não quebre ao tentar chamá-las.

def criar_banco():
    pass

def criar_usuarios_teste():
    pass
