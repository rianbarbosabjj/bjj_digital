import streamlit as st
import firebase_admin
from firebase_admin import credentials, firestore
import json

def get_db():
    """
    Inicia a conexão com o Firestore de forma segura.
    Verifica se o app já está inicializado para evitar erros de duplicidade.
    """
    # Verifica se já existe uma instância do Firebase rodando
    if not firebase_admin._apps:
        try:
            key_dict = None

            # ESTRATÉGIA 1: Procura por uma chave chamada "textkey" (comum em tutoriais)
            if "textkey" in st.secrets:
                # Se for string, converte para JSON; se já for dict, usa direto
                if isinstance(st.secrets["textkey"], str):
                    key_dict = json.loads(st.secrets["textkey"])
                else:
                    key_dict = dict(st.secrets["textkey"])

            # ESTRATÉGIA 2: Procura por chaves na raiz do secrets (formato padrão TOML)
            elif "project_id" in st.secrets:
                key_dict = dict(st.secrets)

            # ESTRATÉGIA 3: Procura por uma seção [firebase]
            elif "firebase" in st.secrets:
                key_dict = dict(st.secrets["firebase"])

            # Se não achou nada
            if key_dict is None:
                st.error("❌ Erro de Configuração: Não foi possível encontrar as credenciais do Firebase no secrets.toml.")
                st.stop()

            # Conecta
            cred = credentials.Certificate(key_dict)
            firebase_admin.initialize_app(cred)

        except Exception as e:
            st.error(f"❌ Falha ao conectar no Banco de Dados: {e}")
            st.stop()

    return firestore.client()
