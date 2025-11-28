import streamlit as st
import bcrypt
from database import get_db
from utils import formatar_e_validar_cpf
from firebase_admin import firestore

def autenticar_local(usuario_email_ou_cpf, senha):
    db = get_db()
    cpf_formatado = formatar_e_validar_cpf(usuario_email_ou_cpf)
    
    users_ref = db.collection('usuarios')
    usuario_doc = None

    # Busca por Email
    query_email = users_ref.where('email', '==', usuario_email_ou_cpf).stream()
    for doc in query_email:
        d = doc.to_dict()
        if d.get('auth_provider') == 'local':
            usuario_doc = doc
            break
    
    # Busca por CPF
    if not usuario_doc and cpf_formatado:
        query_cpf = users_ref.where('cpf', '==', cpf_formatado).stream()
        for doc in query_cpf:
            d = doc.to_dict()
            if d.get('auth_provider') == 'local':
                usuario_doc = doc
                break
            
    if usuario_doc:
        dados = usuario_doc.to_dict()
        senha_hash = dados.get('senha')
        
        if senha_hash and bcrypt.checkpw(senha.encode(), senha_hash.encode()):
            tipo_perfil = dados.get('tipo_usuario', 'aluno')
            
            return {
                "id": usuario_doc.id,
                "nome": dados.get('nome'),
                "tipo": tipo_perfil,
                "email": dados.get('email'),
                # AQUI ESTÁ A CHAVE PARA FUNCIONAR:
                "precisa_trocar_senha": dados.get('precisa_trocar_senha', False)
            }
        
    return None
Passo 2: Atualizar o app.py (Para bloquear a entrada)
Agora o app.py precisa saber o que fazer com essa informação.

Certifique-se de ter import bcrypt no topo do app.py.

Adicione a função da tela de troca.

Atualize o final do arquivo (if __name__ == "__main__":).

Copie o código abaixo e substitua o seu app.py (tome cuidado para manter seus imports de views se tiver mudado algo, mas a estrutura é essa):

Python

import streamlit as st
import os
import sys
import bcrypt # <--- OBRIGATÓRIO
from database import get_db

# ... (Mantenha suas configurações de página e CSS aqui) ...
st.set_page_config(page_title="BJJ Digital", page_icon="assets/logo.png", layout="wide")
# ... (Seus styles css) ...

# Imports das views
try:
    from streamlit_option_menu import option_menu
    from views import login, geral, aluno, professor, admin
except ImportError: pass

# =========================================
# NOVA FUNÇÃO: TELA DE TROCA
# =========================================
def tela_troca_senha_obrigatoria():
    c1, c2, c3 = st.columns([1, 2, 1])
    with c2:
        if os.path.exists("assets/logo.png"):
            st.image("assets/logo.png", width=150)
            
        with st.container(border=True):
            st.markdown("<h3 style='text-align:center; color:#FFD770;'>🔒 Troca de Senha</h3>", unsafe_allow_html=True)
            st.warning("Detectamos uma redefinição recente. Por segurança, crie uma nova senha.")
            
            with st.form("frm_troca"):
                ns = st.text_input("Nova Senha:", type="password")
                cs = st.text_input("Confirmar Nova Senha:", type="password")
                btn = st.form_submit_button("Salvar Nova Senha", type="primary", use_container_width=True)
            
            if btn:
                if ns and ns == cs:
                    try:
                        uid = st.session_state.usuario['id']
                        hashed = bcrypt.hashpw(ns.encode(), bcrypt.gensalt()).decode()
                        
                        db = get_db()
                        # Atualiza senha e REMOVE a trava
                        db.collection('usuarios').document(uid).update({
                            "senha": hashed, 
                            "precisa_trocar_senha": False
                        })
                        
                        st.success("Senha atualizada! Redirecionando...")
                        st.session_state.usuario['precisa_trocar_senha'] = False
                        st.rerun()
                    except Exception as e: st.error(f"Erro: {e}")
                else: st.error("Senhas inválidas ou não conferem.")

# =========================================
# LÓGICA PRINCIPAL (APP_PRINCIPAL)
# =========================================
def app_principal():
    # ... (Seu código normal do app_principal vai aqui) ...
    # ... (Sidebar, Menus, Roteamento das views) ...
    # Vou resumir aqui para não ficar gigante, mantenha o seu app_principal atual
    usuario = st.session_state.usuario
    st.sidebar.title(f"Olá, {usuario['nome']}")
    if st.sidebar.button("Sair"):
        st.session_state.clear()
        st.rerun()
    
    # Exemplo simples de router, use o seu:
    geral.tela_inicio()


# =========================================
# EXECUÇÃO (O "MAIN" QUE DECIDE TUDO)
# =========================================
if __name__ == "__main__":
    if "usuario" not in st.session_state: st.session_state.usuario = None
    if "registration_pending" not in st.session_state: st.session_state.registration_pending = None

    # 1. Se tem cadastro pendente (Google)
    if st.session_state.registration_pending:
        login.tela_completar_cadastro(st.session_state.registration_pending)
    
    # 2. Se o usuário está logado
    elif st.session_state.usuario:
        
        # ---> AQUI É O PULO DO GATO <---
        # Verifica se a flag é True. Se for, trava na tela de troca.
        if st.session_state.usuario.get("precisa_trocar_senha") is True:
            tela_troca_senha_obrigatoria()
        else:
            # Se for False (ou não existir), entra no app
            app_principal()
            
    # 3. Se não está logado
    else:
        login.tela_login()

def buscar_usuario_por_email(email_ou_cpf):
    db = get_db()
    users_ref = db.collection('usuarios')
    usuario_doc = None
    
    query = users_ref.where('email', '==', email_ou_cpf).stream()
    for doc in query:
        usuario_doc = doc
        break
        
    if usuario_doc:
        dados = usuario_doc.to_dict()
        tipo_perfil = dados.get('tipo_usuario', 'aluno')
        
        return {
            "id": usuario_doc.id,
            "nome": dados.get('nome'),
            "tipo": tipo_perfil,
            "perfil_completo": dados.get('perfil_completo', False),
            "email": dados.get('email')
        }
        
    return None

def criar_usuario_parcial_google(email, nome):
    db = get_db()
    novo_usuario = {
        "email": email,
        "nome": nome.upper(),
        "auth_provider": "google",
        "perfil_completo": False,
        "tipo_usuario": "aluno",
        "data_criacao": firestore.SERVER_TIMESTAMP
    }
    _, doc_ref = db.collection('usuarios').add(novo_usuario)
    return {"id": doc_ref.id, "email": email, "nome": nome}
