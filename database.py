import streamlit as st
import firebase_admin
from firebase_admin import credentials, firestore

# Cache para garantir que a conexão seja feita apenas uma vez
@st.cache_resource
def get_db():
    """Inicializa e retorna a conexão com o Firestore."""
    
    # O NOME DO SEU BANCO (Descoberto pelo script)
    # Não mude isso, pois é o nome que está criado no Google
    DATABASE_NAME = 'bjjdigital'

    # Verifica se o app do Firebase já não está rodando
    if not firebase_admin._apps:
        try:
            # Carrega as credenciais do secrets.toml
            key_dict = dict(st.secrets["FIREBASE_KEY"])
            
            # Cria o objeto de credencial
            cred = credentials.Certificate(key_dict)
            
            # Inicializa o Firebase
            # Nota: Não passamos o project_id aqui para evitar conflitos antigos
            firebase_admin.initialize_app(cred)
            
        except Exception as e:
            st.error(f"Erro ao inicializar Firebase: {e}")
            return None
            
    # Retorna o cliente conectado explicitamente ao banco 'bjjdigital'
    try:
        return firestore.client(database=DATABASE_NAME)
    except TypeError:
        # Se der erro de versão, tentamos forçar a atualização das libs
        st.error("Erro de versão da biblioteca. Atualize o requirements.txt")
        return None
    except Exception as e:
        st.error(f"Erro ao conectar no banco '{DATABASE_NAME}': {e}")
        return None

# --- FUNÇÕES LEGADO ---
def criar_banco(): pass
def criar_usuarios_teste(): pass
