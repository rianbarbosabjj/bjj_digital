import streamlit as st
import pandas as pd
import time
from database import get_db
from firebase_admin import firestore
# Importamos o dashboard para usar dentro da aba
from views import dashboard 

# =========================================
# FUNÇÃO: GESTÃO DE EQUIPES (Código Existente)
# =========================================
def gestao_equipes():
    st.subheader("👥 Gestão de Equipes")
    db = get_db()
    
    # Formulário para criar nova equipe
    with st.form("nova_equipe"):
        c1, c2 = st.columns([3, 1])
        nome_eq = c1.text_input("Nome da Nova Equipe:")
        if c2.form_submit_button("➕ Criar Equipe"):
            if nome_eq:
                db.collection('equipes').add({
                    "nome": nome_eq.upper(),
                    "criado_por": st.session_state.usuario['nome'],
                    "data_criacao": firestore.SERVER_TIMESTAMP
                })
                st.success(f"Equipe {nome_eq} criada!"); time.sleep(1); st.rerun()
            else:
                st.warning("Digite um nome.")

    st.markdown("---")

    # Listar Equipes
    equipes = list(db.collection('equipes').stream())
    if not equipes:
        st.info("Nenhuma equipe cadastrada.")
    else:
        for doc in equipes:
            d = doc.to_dict()
            with st.expander(f"🥋 {d.get('nome', 'Sem Nome')}"):
                st.caption(f"ID: {doc.id}")
                
                # Listar alunos desta equipe
                alunos = list(db.collection('alunos').where('equipe_id', '==', doc.id).stream())
                if alunos:
                    st.markdown("**Alunos na equipe:**")
                    for al in alunos:
                        # Busca nome do usuário
                        user_doc = db.collection('usuarios').document(al.to_dict()['usuario_id']).get()
                        if user_doc.exists:
                            st.text(f"- {user_doc.to_dict().get('nome')}")
                else:
                    st.caption("Nenhum aluno nesta equipe.")
                
                if st.button("🗑️ Excluir Equipe", key=f"del_eq_{doc.id}"):
                    db.collection('equipes').document(doc.id).delete()
                    st.rerun()

# =========================================
# FUNÇÃO PRINCIPAL: PAINEL DO PROFESSOR (COM ABAS)
# =========================================
def painel_professor():
    st.markdown("<h1 style='color:#FFD770;'>👨‍🏫 Painel do Professor</h1>", unsafe_allow_html=True)
    
    if st.button("🏠 Voltar ao Início", key="btn_voltar_prof"):
        st.session_state.menu_selection = "Início"; st.rerun()

    # --- AQUI ESTÁ A MUDANÇA: CRIAÇÃO DE ABAS ---
    tab1, tab2 = st.tabs(["👥 Gestão de Equipes", "📊 Estatísticas & Dashboard"])
    
    with tab1:
        gestao_equipes()
        
    with tab2:
        # Chamamos o dashboard aqui dentro
        dashboard.dashboard_professor()
