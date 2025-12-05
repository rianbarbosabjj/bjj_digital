import streamlit as st
import firebase_admin
from firebase_admin import credentials, firestore
import json

# ====================================================
# CONSTANTES GLOBAIS (Centralizadas)
# ====================================================
# Use estas listas em todo o sistema importando de database
# Ex: from database import FAIXAS_COMPLETAS, OPCOES_SEXO

FAIXAS_COMPLETAS = [
    " ", "Cinza e Branca", "Cinza", "Cinza e Preta",
    "Amarela e Branca", "Amarela", "Amarela e Preta",
    "Laranja e Branca", "Laranja", "Laranja e Preta",
    "Verde e Branca", "Verde", "Verde e Preta",
    "Azul", "Roxa", "Marrom", "Preta"
]

OPCOES_SEXO = ["Masculino", "Feminino"]

NIVEIS_DIFICULDADE = [1, 2, 3, 4]

MAPA_NIVEIS = {
    1: "🟢 Fácil", 
    2: "🔵 Médio", 
    3: "🟠 Difícil", 
    4: "🔴 Muito Difícil"
}

def get_badge_nivel(n):
    """Função auxiliar para retornar o badge formatado"""
    return MAPA_NIVEIS.get(n, "⚪ ?")


# ====================================================
# CONEXÃO COM FIREBASE
# ====================================================

@st.cache_resource
def get_db():
    """
    Conexão ESTRITA com o banco 'bjj-digital'.
    Usa cache_resource para manter a conexão ativa e não reconectar a cada reload.
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
            
            # --- LÓGICA DE BUCKET (SEM ADIVINHAÇÃO) ---
            # 1. Tenta pegar direto da chave [firebase]
            bucket_name = key_dict.get("storage_bucket")
            
            # 2. Se não tiver lá, tenta na raiz dos secrets
            if not bucket_name:
                bucket_name = st.secrets.get("storage_bucket")
            
            # 3. Se ainda não achou, tenta montar o padrão NOVO (.firebasestorage.app)
            if not bucket_name:
                project_id = key_dict.get("project_id")
                if project_id:
                    bucket_name = f"{project_id}.firebasestorage.app"
            
            if not bucket_name:
                st.error("❌ Erro Crítico: 'storage_bucket' não encontrado no secrets.toml.")
                st.stop()

            # Inicializa
            firebase_admin.initialize_app(cred, {
                'storageBucket': bucket_name
            })

        except Exception as e:
            st.error(f"❌ Erro ao iniciar Firebase App: {e}")
            st.stop()

    # 2. Conecta ESPECIFICAMENTE ao banco 'bjj-digital'
    try:
        # Tenta conectar ao banco específico (BJJ Digital)
        db = firestore.client(database_id='bjj-digital')
        return db
    except TypeError:
        # Fallback para ambientes que não suportam database_id (emulador ou versões antigas)
        return firestore.client()
    except Exception as e:
        st.error(f"❌ Não foi possível conectar ao banco 'bjj-digital'. Erro: {e}")
        st.stop()
