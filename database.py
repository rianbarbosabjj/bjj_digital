import streamlit as st
import firebase_admin
from firebase_admin import credentials
from google.cloud import firestore as google_firestore # Importação direta da lib poderosa

# Cache para garantir que a conexão seja feita apenas uma vez
@st.cache_resource
def get_db():
    """Inicializa e retorna a conexão com o Firestore."""
    
    # Nome exato do seu banco de dados
    DATABASE_NAME = 'bjjdigital'

    try:
        # 1. Recupera as chaves do secrets
        if "FIREBASE_KEY" not in st.secrets:
            st.error("Secrets do Firebase não encontrados.")
            return None
            
        key_dict = dict(st.secrets["FIREBASE_KEY"])
        project_id = key_dict.get("project_id")

        # 2. Inicializa o App do Firebase (para autenticação geral) se necessário
        if not firebase_admin._apps:
            cred = credentials.Certificate(key_dict)
            firebase_admin.initialize_app(cred)

        # 3. CRIAÇÃO MANUAL DO CLIENTE (O Pulo do Gato 🐱)
        # Em vez de usar firebase_admin.firestore.client(), 
        # nós criamos o cliente diretamente usando a credencial e o nome do banco.
        
        # Pegamos a credencial autenticada do app já iniciado
        app = firebase_admin.get_app()
        cred_object = app.credential.get_credential()

        # Conectamos explicitamente no banco 'bjjdigital'
        db = google_firestore.Client(
            project=project_id,
            credentials=cred_object,
            database=DATABASE_NAME
        )
        
        return db

    except Exception as e:
        st.error(f"Erro crítico ao conectar no banco '{DATABASE_NAME}': {e}")
        return None

# --- FUNÇÕES LEGADO ---
def criar_banco(): pass
def criar_usuarios_teste(): pass
