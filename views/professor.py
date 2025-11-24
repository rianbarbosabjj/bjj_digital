import streamlit as st
import pandas as pd
from database import get_db

def painel_professor():
    st.markdown("<h1 style='color:#FFD700;'>👩‍🏫 Painel do Professor</h1>", unsafe_allow_html=True)
    db = get_db()
    user = st.session_state.usuario
    
    # 1. Descobre quais equipes este professor lidera (ou é vinculado)
    # Precisamos do ID do usuário no documento 'professores'
    prof_query = db.collection('professores').where('usuario_id', '==', user['id']).stream()
    prof_doc = next(prof_query, None)
    
    if not prof_doc:
        st.warning("Você não está cadastrado como professor.")
        return
        
    prof_data = prof_doc.to_dict()
    equipe_id = prof_data.get('equipe_id') # ID da equipe vinculada
    
    if not equipe_id:
        st.info("Você não está vinculado a nenhuma equipe.")
        return

    # 2. Busca pendências nessa equipe
    alunos_pend = db.collection('alunos')\
        .where('equipe_id', '==', equipe_id)\
        .where('status_vinculo', '==', 'pendente').stream()
        
    lista_pend = []
    for doc in alunos_pend:
        d = doc.to_dict()
        # Busca nome do aluno
        u_doc = db.collection('usuarios').document(d['usuario_id']).get()
        if u_doc.exists:
            u_data = u_doc.to_dict()
            lista_pend.append({
                "id_doc": doc.id, # ID do documento na coleção 'alunos'
                "nome": u_data.get('nome'),
                "faixa": d.get('faixa_atual')
            })
            
    if not lista_pend:
        st.info("Nenhuma pendência.")
    else:
        st.write("### Alunos Pendentes")
        for p in lista_pend:
            c1, c2, c3 = st.columns([3, 1, 1])
            c1.write(f"**{p['nome']}** ({p['faixa']})")
            if c2.button("✅", key=f"ok_{p['id_doc']}"):
                db.collection('alunos').document(p['id_doc']).update({"status_vinculo": "ativo"})
                st.success(f"{p['nome']} aprovado!")
                st.rerun()
            if c3.button("❌", key=f"no_{p['id_doc']}"):
                db.collection('alunos').document(p['id_doc']).update({"status_vinculo": "rejeitado"})
                st.warning("Rejeitado.")
                st.rerun()

def gestao_equipes():
    st.markdown("<h1 style='color:#FFD700;'>🏛️ Gestão de Equipes</h1>", unsafe_allow_html=True)
    st.info("Funcionalidade em migração para o Firestore (Exige lógica complexa de relacionamentos).")
