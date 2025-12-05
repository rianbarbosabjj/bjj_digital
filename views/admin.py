import streamlit as st
import pandas as pd
import bcrypt
import time 
import io 
from datetime import datetime, date, time as dtime 
from database import get_db, OPCOES_SEXO
from firebase_admin import firestore

# Tenta importar o dashboard
try:
    from views.dashboard_admin import render_dashboard_geral
except ImportError:
    def render_dashboard_geral(): st.warning("Dashboard não encontrado.")

# Importa utils
try:
    from utils import (
        carregar_todas_questoes, 
        salvar_questoes, 
        fazer_upload_midia, 
        normalizar_link_video, 
        verificar_duplicidade_ia,
        IA_ATIVADA 
    )
except ImportError:
    IA_ATIVADA = False
    def carregar_todas_questoes(): return []
    def salvar_questoes(t, q): pass
    def fazer_upload_midia(f): return None
    def normalizar_link_video(u): return u
    def verificar_duplicidade_ia(n, l, t=0.85): return False, None

# --- CONSTANTES ---
FAIXAS_COMPLETAS = [
    " ", "Cinza e Branca", "Cinza", "Cinza e Preta",
    "Amarela e Branca", "Amarela", "Amarela e Preta",
    "Laranja e Branca", "Laranja", "Laranja e Preta",
    "Verde e Branca", "Verde", "Verde e Preta",
    "Azul", "Roxa", "Marrom", "Preta"
]
NIVEIS_DIFICULDADE = [1, 2, 3, 4]
MAPA_NIVEIS = {1: "🟢 Fácil", 2: "🔵 Médio", 3: "🟠 Difícil", 4: "🔴 Muito Difícil"}

def get_badge_nivel(n): return MAPA_NIVEIS.get(n, "⚪ ?")

# =========================================
# GESTÃO DE USUÁRIOS (TAB INTERNA)
# =========================================
def gestao_usuarios_tab():
    db = get_db()
    
    # 1. Carregar Listas Auxiliares (Equipes e Professores)
    users_ref = list(db.collection('usuarios').stream())
    users = [d.to_dict() | {"id": d.id} for d in users_ref]
    
    # Lista de Equipes
    equipes_ref = list(db.collection('equipes').stream())
    mapa_equipes = {d.id: d.to_dict().get('nome', 'Sem Nome') for d in equipes_ref} # ID -> Nome
    mapa_equipes_inv = {v: k for k, v in mapa_equipes.items()} # Nome -> ID
    lista_equipes = ["Sem Equipe"] + sorted(list(mapa_equipes.values()))

    # Lista de Professores (Com Vínculo de Equipe)
    profs_vinc_ref = list(db.collection('professores').stream())
    mapa_prof_equipe = {} # ProfID -> NomeEquipe
    for pv in profs_vinc_ref:
        d = pv.to_dict()
        uid = d.get('usuario_id')
        eid = d.get('equipe_id')
        if uid and eid:
            mapa_prof_equipe[uid] = mapa_equipes.get(eid, "?")

    # Monta lista de nomes de professores com a equipe entre parênteses
    profs_users = [u for u in users if u.get('tipo_usuario') == 'professor']
    
    mapa_profs_display = {} # "Nome (Equipe)" -> ID
    mapa_profs_id_to_display = {} # ID -> "Nome (Equipe)"
    
    for p in profs_users:
        pid = p['id']
        pnome = p.get('nome', 'Sem Nome')
        pequipe = mapa_prof_equipe.get(pid, "Sem Equipe")
        label = f"{pnome} ({pequipe})"
        mapa_profs_display[label] = pid
        mapa_profs_id_to_display[pid] = label

    lista_profs_formatada = ["Sem Professor"] + sorted(list(mapa_profs_display.keys()))

    if not users: st.warning("Vazio."); return
    
    # 2. Tabela Principal
    df = pd.DataFrame(users)
    c1, c2 = st.columns(2)
    filtro_nome = c1.text_input("🔍 Buscar Nome/Email/CPF:")
    filtro_tipo = c2.multiselect("Filtrar Tipo:", df['tipo_usuario'].unique() if 'tipo_usuario' in df.columns else [])

    if filtro_nome:
        termo = filtro_nome.upper()
        df = df[
            df['nome'].str.upper().str.contains(termo) | 
            df['email'].str.upper().str.contains(termo) |
            df['cpf'].str.contains(termo)
        ]
    if filtro_tipo:
        df = df[df['tipo_usuario'].isin(filtro_tipo)]

    cols_show = ['nome', 'email', 'tipo_usuario', 'faixa_atual', 'sexo']
    for c in cols_show: 
        if c not in df.columns: df[c] = "-"
    
    st.dataframe(df[cols_show], use_container_width=True, hide_index=True)
    
    st.markdown("---")
    st.subheader("🛠️ Editar Cadastro Completo")
    
    opcoes = df.to_dict('records')
    sel = st.selectbox("Selecione o usuário:", opcoes, format_func=lambda x: f"{x.get('nome')} ({x.get('tipo_usuario')})")
    
    if sel:
        # --- Lógica para buscar vínculo atual ---
        vinculo_equipe_id = None
        vinculo_prof_id = None
        
        # Busca em alunos
        if sel.get('tipo_usuario') == 'aluno':
            vincs = list(db.collection('alunos').where('usuario_id', '==', sel['id']).limit(1).stream())
            if vincs:
                d_vinc = vincs[0].to_dict()
                vinculo_equipe_id = d_vinc.get('equipe_id')
                vinculo_prof_id = d_vinc.get('professor_id')
        
        # Busca em professores
        elif sel.get('tipo_usuario') == 'professor':
            vincs = list(db.collection('professores').where('usuario_id', '==', sel['id']).limit(1).stream())
            if vincs:
                d_vinc = vincs[0].to_dict()
                vinculo_equipe_id = d_vinc.get('equipe_id')

        # --- Início do Formulário ---
        with st.form(f"edt_{sel['id']}"):
            # BLOCO 1: DADOS PESSOAIS
            st.markdown("##### 👤 Dados Pessoais")
            c1, c2 = st.columns(2)
            nm = c1.text_input("Nome Completo:", value=sel.get('nome',''))
            email = c2.text_input("E-mail:", value=sel.get('email',''))
            
            c3, c4, c5 = st.columns([1.5, 1, 1])
            cpf = c3.text_input("CPF:", value=sel.get('cpf',''))
            
            idx_s = 0
            if sel.get('sexo') in OPCOES_SEXO: idx_s = OPCOES_SEXO.index(sel.get('sexo'))
            sexo_edit = c4.selectbox("Sexo:", OPCOES_SEXO, index=idx_s)
            
            val_n = None
            if sel.get('data_nascimento'):
                try: val_n = datetime.fromisoformat(sel.get('data_nascimento')).date()
                except: pass
            nasc_edit = c5.date_input("Nascimento:", value=val_n, min_value=date(1940,1,1), max_value=date.today(), format="DD/MM/YYYY")

            # BLOCO 2: ENDEREÇO
            st.markdown("##### 📍 Endereço")
            e1, e2 = st.columns([1, 3])
            cep = e1.text_input("CEP:", value=sel.get('cep',''))
            logr = e2.text_input("Logradouro:", value=sel.get('logradouro',''))
            
            e3, e4, e5 = st.columns([1, 2, 2])
            num = e3.text_input("Número:", value=sel.get('numero',''))
            comp = e4.text_input("Complemento:", value=sel.get('complemento',''))
            bairro = e5.text_input("Bairro:", value=sel.get('bairro',''))
            e6, e7 = st
