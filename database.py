import streamlit as st
import firebase_admin
from firebase_admin import credentials
from google.cloud import firestore as google_firestore 

# Cache para garantir que a conexão seja feita apenas uma vez
@st.cache_resource
def get_db():
    """Inicializa e retorna a conexão com o Firestore."""
    
    # 🔴 APONTANDO PARA O BANCO NATIVO (CORRETO)
    DATABASE_NAME = 'bjj-digital'

    try:
        if "FIREBASE_KEY" not in st.secrets:
            st.error("Secrets do Firebase não encontrados.")
            return None
            
        key_dict = dict(st.secrets["FIREBASE_KEY"])
        project_id = key_dict.get("project_id")

        if not firebase_admin._apps:
            cred = credentials.Certificate(key_dict)
            firebase_admin.initialize_app(cred)

        app = firebase_admin.get_app()
        cred_object = app.credential.get_credential()

        # Conecta no banco nativo
        db = google_firestore.Client(
            project=project_id,
            credentials=cred_object,
            database=DATABASE_NAME
        )
        
        return db

    except Exception as e:
        st.error(f"Erro crítico ao conectar no banco '{DATABASE_NAME}': {e}")
        return None

def criar_banco(): pass
def criar_usuarios_teste(): pass
