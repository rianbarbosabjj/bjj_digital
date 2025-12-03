import streamlit as st
import firebase_admin
from firebase_admin import credentials, firestore
import json

def get_db():
    """
    Conexão ESTRITA com o banco 'bjj-digital'.
    Inicializa também o Storage para upload de imagens.
    """
    # 1. Inicializa o App (se ainda não estiver rodando)
    if not firebase_admin._apps:
        try:
            key_dict = None
            
            # Procura as credenciais
            if "firebase" in st.secrets:
                key_dict = dict(st.secrets["firebase"])
            elif "textkey" in st.secrets:
                if isinstance(st.secrets["textkey"], str):
                    key_dict = json.loads(st.secrets["textkey"])
                else:
                    key_dict = dict(st.secrets["textkey"])
            elif "project_id" in st.secrets:
                key_dict = dict(st.secrets)

            if key_dict is None:
                st.error("❌ Credenciais não encontradas no secrets.toml")
                st.stop()

            cred = credentials.Certificate(key_dict)
            
            # Tenta pegar o bucket dos secrets ou usa o padrão
            project_id = key_dict.get("project_id")
            bucket_name = st.secrets.get("storage_bucket", f"{project_id}.appspot.com")

            firebase_admin.initialize_app(cred, {
                'storageBucket': bucket_name
            })

        except Exception as e:
            st.error(f"❌ Erro ao iniciar Firebase App: {e}")
            st.stop()

    # 2. Conecta ESPECIFICAMENTE ao banco 'bjj-digital'
    try:
        db = firestore.client(database_id='bjj-digital')
        return db
    except TypeError:
        return firestore.client()
    except Exception as e:
        st.error(f"❌ Não foi possível conectar ao banco 'bjj-digital'. Erro: {e}")
        st.stop()
