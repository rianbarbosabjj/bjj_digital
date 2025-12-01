import streamlit as st
import pandas as pd
import bcrypt
import random
import time 
from datetime import datetime, time as dtime # CORREÇÃO: 'dtime' evita conflito com o módulo 'time'
from database import get_db
from firebase_admin import firestore

# =========================================
# LISTA PADRÃO DE FAIXAS (GLOBAL)
# =========================================
FAIXAS_COMPLETAS = [
    "Cinza e Branca", "Cinza", "Cinza e Preta",
    "Amarela e Branca", "Amarela", "Amarela e Preta",
    "Laranja e Branca", "Laranja", "Laranja e Preta",
    "Verde e Branca", "Verde", "Verde e Preta",
    "Azul", "Roxa", "Marrom", "Preta"
]

# =========================================
# 1. GESTÃO DE USUÁRIOS
# =========================================
def gestao_usuarios(usuario_logado):
    st.markdown("<h1 style='color:#FFD700;'>👥 Gestão de Usuários</h1>", unsafe_allow_html=True)
    db = get_db()
    
    users_ref = db.collection('usuarios').stream()
    lista_users = []
    
    for doc in users_ref:
        d = doc.to_dict()
        user_safe = {
            "id": doc.id,
            "nome": d.get('nome', 'Sem Nome'),
            "email": d.get('email', '-'),
            "cpf": d.get('cpf', '-'),
            "tipo_usuario": d.get('tipo_usuario', 'aluno'),
            "faixa_atual": d.get('faixa_atual', 'Branca'),
            "cep": d.get('cep', ''),
            "logradouro": d.get('logradouro', ''),
            "numero": d.get('numero', ''),
            "complemento": d.get('complemento', ''),
            "bairro": d.get('bairro', ''),
            "cidade": d.get('cidade', ''),
            "uf": d.get('uf', '')
        }
        lista_users.append(user_safe)
        
    if not lista_users:
        st.warning("Nenhum usuário encontrado.")
        return

    filtro = st.text_input("🔍 Buscar por Nome, Email ou CPF:")
    df = pd.DataFrame(lista_users)
    
    if filtro:
        f = filtro.upper()
        df = df[
            df['nome'].str.upper().str.contains(f, na=False) | 
            df['email'].str.upper().str.contains(f, na=False) | 
            df['cpf'].str.contains(f, na=False)
        ]

    st.dataframe(
        df[['nome', 'email', 'tipo_usuario', 'faixa_atual']], 
        use_container_width=True,
        hide_index=True
    )
    
    st.markdown("---")

    st.subheader("🛠️ Editar ou Excluir Usuário")
    if df.empty:
        st.warning("Nenhum usuário encontrado para editar.")
        return
        
    opcoes_usuarios = df.to_dict('records')
    usuario_selecionado = st.selectbox("Selecione o usuário:", opcoes_usuarios, format_func=lambda x: f"{x['nome']} ({x['email']})")
    
    if usuario_selecionado:
        with st.expander(f"✏️ Editar dados de {usuario_selecionado['nome']}", expanded=False):
            with st.form(key=f"edit_full_{usuario_selecionado['id']}"):
                st.markdown("##### 👤 Dados Pessoais")
                c1, c2 = st.columns(2)
                novo_nome = c1.text_input("Nome:", value=usuario_selecionado['nome'])
                novo_email = c2.text_input("E-mail:", value=usuario_selecionado['email'])
                c3, c4 = st.columns(2)
                novo_cpf = c3.text_input("CPF:", value=usuario_selecionado['cpf'])
                
                tipos = ["aluno", "professor", "admin"]
                idx_t = tipos.index(usuario_selecionado['tipo_usuario']) if usuario_selecionado['tipo_usuario'] in tipos else 0
                novo_tipo = c4.selectbox("Perfil:", tipos, index=idx_t)

                idx_f = FAIXAS_COMPLETAS.index(usuario_selecionado['faixa_atual']) if usuario_selecionado['faixa_atual'] in FAIXAS_COMPLETAS else 0
                novo_faixa = st.selectbox("Faixa Atual:", FAIXAS_COMPLETAS, index=idx_f)
                
                st.markdown("---")
                st.markdown("##### 🔐 Alterar Senha")
                nova_senha_admin = st.text_input("Nova Senha:", type="password", help="Preencha apenas se quiser alterar.")
                
                st.markdown("---")
                st.markdown("##### 🏠 Endereço")
                e1, e2 = st.columns([1, 3])
                novo_cep = e1.text_input("CEP:", value=usuario_selecionado['cep'])
                novo_logr = e2.text_input("Logradouro:", value=usuario_selecionado['logradouro'])
                novo_numero = st.text_input("Número:", value=usuario_selecionado.get('numero', ''))
                novo_complemento = st.text_input("Complemento:", value=usuario_selecionado.get('complemento', ''))
                e3, e4, e5 = st.columns(3)
                novo_bairro = e3.text_input("Bairro:", value=usuario_selecionado.get('bairro', ''))
                novo_cidade = e4.text_input("Cidade:", value=usuario_selecionado.get('cidade', ''))
                novo_uf = e5.text_input("UF:", value=usuario_selecionado.get('uf', ''))
                
                if st.form_submit_button("💾 SALVAR ALTERAÇÕES", type="primary", use_container_width=True):
                    try:
                        dados_update = {
                            "nome": novo_nome.upper(),
                            "email": novo_email.lower().strip(),
                            "cpf": novo_cpf,
                            "tipo_usuario": novo_tipo,
                            "faixa_atual": novo_faixa,
                            "cep": novo_cep,
                            "logradouro": novo_logr.upper(),
                            "numero": novo_numero,
                            "complemento": novo_complemento,
                            "bairro": novo_bairro.upper(),
                            "cidade": novo_cidade.upper(),
                            "uf": novo_uf.upper()
                        }
                        if nova_senha_admin:
                            hashed = bcrypt.hashpw(nova_senha_admin.encode(), bcrypt.gensalt()).decode()
                            dados_update["senha"] = hashed
                            dados_update["precisa_trocar_senha"] = True
                            st.info("Senha alterada!")
                        db.collection('usuarios').document(usuario_selecionado['id']).update(dados_update)
                        st.success("Atualizado com sucesso!")
                        time.sleep(1)
                        st.rerun()
                    except Exception as e: 
                        st.error(f"Erro: {e}")

        st.write("")
        with st.container(border=True):
            c_aviso, c_botao = st.columns([3, 1])
            c_aviso.warning(f"Deseja excluir **{usuario_selecionado['nome']}** permanentemente?")
            if c_botao.button("🗑️ EXCLUIR", key=f"del_u_{usuario_selecionado['id']}", type="primary"):
                try:
                    db.collection('usuarios').document(usuario_selecionado['id']).delete()
                    st.toast("Usuário excluído.")
                    time.sleep(1)
                    st.rerun()
                except Exception as e:
                    st.error(f"Erro ao excluir usuário: {e}")

# =========================================
# 2. GESTÃO DE QUESTÕES
# =========================================
def gestao_questoes():
    st.markdown("<h1 style='color:#FFD700;'>🧠 Banco de Questões</h1>", unsafe_allow_html=True)
    
    user = st.session_state.usuario
    tipo_user = str(user.get("tipo", "")).lower()
    
    if tipo_user not in ["admin", "professor"]:
        st.error("Acesso negado.")
        return
        
    db = get_db()
    docs_q = list(db.collection('questoes').stream())
    aprovadas = []; pendentes = []; edicoes = []; temas_set = set()

    for doc in docs_q:
        d = doc.to_dict(); d['id'] =
