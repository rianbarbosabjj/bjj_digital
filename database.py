import streamlit as st
import firebase_admin
from firebase_admin import credentials, firestore

# Cache para garantir que a conexão seja feita apenas uma vez
@st.cache_resource
def get_db():
    """Inicializa e retorna a conexão com o Firestore."""
    
    # Nome exato do banco
    DATABASE_NAME = 'bjjdigital'

    if not firebase_admin._apps:
        try:
            # Carrega as credenciais
            if "FIREBASE_KEY" not in st.secrets:
                st.error("Secrets do Firebase não encontrados.")
                return None
                
            key_dict = dict(st.secrets["FIREBASE_KEY"])
            
            # Cria credencial
            cred = credentials.Certificate(key_dict)
            
            # Inicializa o App com o ID do projeto explícito nas opções
            # Isso ajuda o SDK a rotear corretamente para o banco
            firebase_admin.initialize_app(cred, {
                'projectId': key_dict.get('project_id'),
            })
            
        except Exception as e:
            st.error(f"Erro ao inicializar Firebase: {e}")
            return None
            
    try:
        # Tenta conectar especificando o banco
        return firestore.client(database=DATABASE_NAME)
    except TypeError:
        # Se a versão instalada for antiga e não aceitar 'database',
        # tenta conectar sem argumento (vai para o default)
        st.warning("Versão antiga da biblioteca detectada. Tentando conexão padrão...")
        return firestore.client()
    except Exception as e:
        st.error(f"Erro ao obter cliente Firestore: {e}")
        return None

# --- FUNÇÕES LEGADO ---
def criar_banco(): pass
def criar_usuarios_teste(): pass
