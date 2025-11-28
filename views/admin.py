import streamlit as st
import pandas as pd
from datetime import datetime, time
from database import get_db
from firebase_admin import firestore

# =========================================
# GESTÃO DE USUÁRIOS (CADASTRO/EDIÇÃO)
# =========================================
def gestao_usuarios(usuario_logado):
    st.markdown("<h1 style='color:#FFD700;'>👥 Gestão de Usuários</h1>", unsafe_allow_html=True)
    db = get_db()
    
    # Lista todos os usuários
    users = db.collection('usuarios').stream()
    lista = []
    for doc in users:
        d = doc.to_dict()
        d['id'] = doc.id
        lista.append(d)
        
    if not lista:
        st.warning("Nenhum usuário encontrado.")
        return

    df = pd.DataFrame(lista)
    
    # Filtros e Tabela
    filtro = st.text_input("Buscar por nome ou CPF:")
    if filtro:
        df = df[df['nome'].str.contains(filtro.upper(), na=False) | df['cpf'].str.contains(filtro, na=False)]
        
    st.dataframe(
        df[['nome', 'email', 'cpf', 'tipo_usuario', 'faixa_atual']], 
        use_container_width=True,
        hide_index=True
    )

# =========================================
# GESTÃO DE QUESTÕES
# =========================================
def gestao_questoes():
    st.markdown("<h1 style='color:#FFD700;'>🧠 Gestão de Questões</h1>", unsafe_allow_html=True)
    st.info("Funcionalidade de edição de banco de questões em desenvolvimento.")

# =========================================
# GESTÃO DE EXAME (AQUI ESTAVA O PROBLEMA)
# =========================================
def gestao_exame_de_faixa():
    st.markdown("<h1 style='color:#FFD700;'>📜 Gestão de Exame</h1>", unsafe_allow_html=True)
    db = get_db()

    # --- 1. CONFIGURAÇÃO GERAL DE DATA/HORA ---
    with st.container(border=True):
        st.subheader("🗓️ Configurar Período do Exame")
        c1, c2 = st.columns(2)
        d_inicio = c1.date_input("Data Início:", datetime.now())
        d_fim = c2.date_input("Data Fim:", datetime.now())
        
        c3, c4 = st.columns(2)
        h_inicio = c3.time_input("Hora Início:", time(0, 0))
        h_fim = c4.time_input("Hora Fim:", time(23, 59))

        # Monta os objetos datetime completos
        dt_inicio = datetime.combine(d_inicio, h_inicio)
        dt_fim = datetime.combine(d_fim, h_fim)

    st.write("") # Espaço

    # --- 2. LISTAGEM DE ALUNOS ---
    st.subheader("Autorizar Alunos")
    
    # Busca apenas alunos
    alunos_ref = db.collection('usuarios').where('tipo_usuario', '==', 'aluno').stream()
    lista_alunos = []
    
    for doc in alunos_ref:
        d = doc.to_dict()
        d['id'] = doc.id
        
        # Busca nome da equipe (opcional, para ficar bonito na tabela)
        nome_equipe = "Sem Equipe"
        # Tenta achar vinculo na coleção alunos
        vinculo = list(db.collection('alunos').where('usuario_id', '==', doc.id).stream())
        if vinculo:
            eq_id = vinculo[0].to_dict().get('equipe_id')
            if eq_id:
                eq_doc = db.collection('equipes').document(eq_id).get()
                if eq_doc.exists:
                    nome_equipe = eq_doc.to_dict().get('nome')
        
        d['nome_equipe'] = nome_equipe
        lista_alunos.append(d)

    if not lista_alunos:
        st.info("Nenhum aluno cadastrado.")
        return

    # Cabeçalho da "Tabela" Manual
    cols = st.columns([3, 2, 2, 3, 1])
    cols[0].markdown("**Aluno**")
    cols[1].markdown("**Equipe**")
    cols[2].markdown("**Exame (Faixa)**")
    cols[3].markdown("**Status Atual**")
    cols[4].markdown("**Ação**")
    st.markdown("---")

    faixas_opcoes = ["Cinza", "Amarela", "Laranja", "Verde", "Azul", "Roxa", "Marrom", "Preta"]

    # Renderiza cada aluno
    for aluno in lista_alunos:
        c1, c2, c3, c4, c5 = st.columns([3, 2, 2, 3, 1])
        
        # Nome e Equipe
        c1.write(f"**{aluno['nome']}**")
        c2.write(aluno['nome_equipe'])
        
        # Seletor de Faixa (Exame a ser aplicado)
        key_faixa = f"sel_fx_{aluno['id']}"
        idx_padrao = 0
        # Tenta ser inteligente e sugerir a próxima faixa (ex: se é Branca, sugere Cinza/Azul)
        # Por simplicidade, deixamos padrão ou o que já está salvo
        if aluno.get('faixa_exame') in faixas_opcoes:
            idx_padrao = faixas_opcoes.index(aluno.get('faixa_exame'))
            
        faixa_selecionada = c3.selectbox("Faixa", faixas_opcoes, index=idx_padrao, key=key_faixa, label_visibility="collapsed")

        # Status Visual
        habilitado = aluno.get('exame_habilitado', False)
        status_prova = aluno.get('status_exame', 'pendente')
        
        if habilitado:
            msg_status = f"🟢 Liberado (até {aluno.get('exame_fim', '?')})"
            if status_prova == 'aprovado': msg_status = "🏆 Aprovado"
            elif status_prova == 'reprovado': msg_status = "🔴 Reprovado"
            elif status_prova == 'bloqueado': msg_status = "⛔ Bloqueado"
            c4.caption(msg_status)
            
            # Botão para DESABILITAR
            if c5.button("⛔", key=f"btn_off_{aluno['id']}", help="Cancelar autorização"):
                db.collection('usuarios').document(aluno['id']).update({
                    "exame_habilitado": False,
                    "exame_inicio": firestore.DELETE_FIELD,
                    "exame_fim": firestore.DELETE_FIELD,
                    "faixa_exame": firestore.DELETE_FIELD,
                    "status_exame": "pendente" # Reseta status para poder fazer de novo no futuro
                })
                st.rerun()
        else:
            c4.caption("⚪ Não autorizado")
            
            # Botão para HABILITAR (O QUE GRAVA OS DADOS)
            if c5.button("✅", key=f"btn_on_{aluno['id']}", help="Autorizar Exame"):
                
                # --- AQUI ESTÁ A CORREÇÃO CRÍTICA ---
                # Gravamos TODOS os campos que o aluno.py espera
                dados_update = {
                    "exame_habilitado": True,
                    "faixa_exame": faixa_selecionada, # A faixa que o professor escolheu no dropdown
                    # Convertemos datetime para string ISO para evitar problemas de timezone/objeto
                    "exame_inicio": dt_inicio.isoformat(),
                    "exame_fim": dt_fim.isoformat(),
                    "status_exame": "pendente", # Reseta status antigo
                    "status_exame_em_andamento": False,
                    "motivo_bloqueio": firestore.DELETE_FIELD
                }
                
                db.collection('usuarios').document(aluno['id']).update(dados_update)
                st.toast(f"Exame liberado para {aluno['nome']}!")
                st.rerun()
        
        st.markdown("---")
