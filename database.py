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
            
            # Procura as credenciais em vários formatos comuns
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
            
            # --- LÓGICA DE BUSCA DO BUCKET (CORRIGIDA) ---
            project_id = key_dict.get("project_id")
            bucket_name = None

            # 1. Tenta pegar de dentro da chave [firebase] (Onde pedimos para colocar)
            if "storage_bucket" in key_dict:
                bucket_name = key_dict["storage_bucket"]
            
            # 2. Se não achou, tenta na raiz dos secrets
            if not bucket_name:
                bucket_name = st.secrets.get("storage_bucket")
            
            # 3. Se ainda não achou, tenta o padrão do projeto (project-id.appspot.com)
            if not bucket_name and project_id:
                bucket_name = f"{project_id}.appspot.com"

            # Inicializa o app com o bucket configurado
            firebase_admin.initialize_app(cred, {
                'storageBucket': bucket_name
            })

        except Exception as e:
            st.error(f"❌ Erro ao iniciar Firebase App: {e}")
            st.stop()

    # 2. Conecta ESPECIFICAMENTE ao banco 'bjj-digital'
    try:
        # Tenta conectar com database_id explícito
        db = firestore.client(database_id='bjj-digital')
        return db
    except TypeError:
        # Fallback para versões antigas da lib que não aceitam database_id
        return firestore.client()
    except Exception as e:
        st.error(f"❌ Não foi possível conectar ao banco 'bjj-digital'. Erro: {e}")
        st.stop()
