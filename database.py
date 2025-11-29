import streamlit as st
import firebase_admin
from firebase_admin import credentials, firestore
import json

def get_db():
    """
    Inicia a conexão com o Firestore de forma segura e inteligente.
    """
    # 1. INICIALIZAÇÃO DO APP (SINGLETON)
    # Verifica se o app já está conectado para não dar erro de "App already exists"
    if not firebase_admin._apps:
        try:
            key_dict = None

            # ESTRATÉGIA 1: Procura seção [firebase] (Padrão atual do seu secrets.toml)
            if "firebase" in st.secrets:
                key_dict = dict(st.secrets["firebase"])

            # ESTRATÉGIA 2: Procura chave 'textkey' (Padrão antigo/Deploy)
            elif "textkey" in st.secrets:
                if isinstance(st.secrets["textkey"], str):
                    key_dict = json.loads(st.secrets["textkey"])
                else:
                    key_dict = dict(st.secrets["textkey"])

            # ESTRATÉGIA 3: Procura na raiz
            elif "project_id" in st.secrets:
                key_dict = dict(st.secrets)

            # Validação
            if key_dict is None:
                st.error("❌ Erro Crítico: Credenciais do Firebase não encontradas no secrets.toml.")
                st.stop()

            # Conecta as credenciais
            cred = credentials.Certificate(key_dict)
            firebase_admin.initialize_app(cred)

        except Exception as e:
            st.error(f"❌ Falha ao inicializar Firebase: {e}")
            st.stop()

    # 2. CONEXÃO COM O BANCO DE DADOS (SELEÇÃO)
    try:
        # TENTATIVA A: Conectar no banco nomeado 'bjj-digital' (Se você criou um secundário)
        db = firestore.client(database='bjj-digital')
        
        # Teste rápido de conexão (tenta ler nada só para ver se a conexão bate)
        # Se o banco não existir, isso vai gerar erro e cair no except
        # (O Python Client geralmente é "lazy", então forçamos o check aqui se necessário, 
        # mas apenas instanciar costuma passar se a sintaxe estiver ok).
        
        return db

    except Exception as e:
        # TENTATIVA B: Fallback para o banco (default)
        # Se o banco 'bjj-digital' não existir, usamos o padrão do projeto
        print(f"⚠️ Banco 'bjj-digital' não encontrado ou erro de acesso. Usando (default). Erro: {e}")
        return firestore.client()
