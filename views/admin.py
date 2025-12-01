import streamlit as st
import pandas as pd
import bcrypt
import random
import time 
from datetime import datetime, time as dtime # CORREÇÃO CRÍTICA: 'dtime' evita conflito com o comando 'time.sleep'
from database import get_db
from firebase_admin import firestore
# Certifique-se de que essas funções existem no seu utils.py, senão o código falha
try:
    from utils import carregar_todas_questoes, salvar_questoes
except ImportError:
    # Fallback simples caso utils não tenha as funções
    def carregar_todas_questoes(): return []
    def salvar_questoes(t, q): pass

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
            "equipe": d.get('equipe', '-'),
            "status_exame": d.get('status_exame', 'N/A')
        }
        lista_users.append(user_safe)
        
    df = pd.DataFrame(lista_users)
    
    if not df.empty:
        st.dataframe(df, use_container_width=True, hide_index=True)
        
        # Mudar Tipo de Usuário
        st.subheader("Alterar Permissões")
        c1, c2, c3 = st.columns([2, 1, 1])
        user_sel = c1.selectbox("Selecionar Usuário:", df['nome'].tolist())
        novo_tipo = c2.selectbox("Novo Tipo:", ["aluno", "professor", "admin"])
        
        if c3.button("Atualizar Tipo"):
            uid = df[df['nome'] == user_sel]['id'].values[0]
            db.collection('usuarios').document(uid).update({"tipo_usuario": novo_tipo})
            st.success(f"Permissão de {user_sel} alterada para {novo_tipo}!")
            time.sleep(1) # Agora funciona sem conflito
            st.rerun()

# =========================================
# 2. GESTÃO DE QUESTÕES
# =========================================
def gestao_questoes():
    st.markdown("<h1 style='color:#FFD700;'>📝 Gestão de Questões</h1>", unsafe_allow_html=True)
    db = get_db()

    tab1, tab2 = st.tabs(["📚 Banco de Questões", "➕ Adicionar Nova"])

    # --- TAB 1: LISTAR/EDITAR ---
    with tab1:
        questoes = carregar_todas_questoes()
        
        if not questoes:
            st.info("Nenhuma questão cadastrada no banco.")
        else:
            lista_q = []
            for q in questoes:
                lista_q.append({
                    "id": q.get("id"),
                    "pergunta": q.get("pergunta"),
                    "faixa": q.get("faixa", "Geral"),
                    "resposta_correta": q.get("resposta_correta") or q.get("resposta"),
                    "status": q.get("status", "aprovada")
                })
            
            df = pd.DataFrame(lista_q)
            
            # Edição na Tabela
            st.data_editor(
                df,
                column_config={
                    "status": st.column_config.SelectboxColumn(
                        "Status", options=["aprovada", "pendente", "arquivada"]
                    )
                },
                use_container_width=True,
                hide_index=True,
                key="editor_questoes"
            )
            
            # Deletar Questão
            st.markdown("---")
            col_del, _ = st.columns([1, 3])
            q_to_del = col_del.selectbox("Selecionar para Excluir:", df["pergunta"].unique(), key="sel_del")
            if col_del.button("🗑️ Excluir Questão", type="primary"):
                try:
                    docs = db.collection('questoes').where('pergunta', '==', q_to_del).stream()
                    for doc in docs:
                        doc.reference.delete()
                    st.success("Questão excluída!")
                    time.sleep(1)
                    st.rerun()
                except Exception as e:
                    st.error(f"Erro ao excluir: {e}")

    # --- TAB 2: ADICIONAR NOVA ---
    with tab2:
        with st.form("form_add_q"):
            pergunta = st.text_area("Enunciado da Pergunta:")
            c1, c2 = st.columns(2)
            faixa = c1.selectbox("Nível da Faixa:", ["Todas"] + FAIXAS_COMPLETAS)
            categoria = c2.text_input("Categoria (ex: Regras, História):", "Geral")
            
            st.markdown("**Alternativas:**")
            alt_a = st.text_input("A)")
            alt_b = st.text_input("B)")
            alt_c = st.text_input("C)")
            alt_d = st.text_input("D)")
            
            correta = st.selectbox("Qual a correta?", ["A", "B", "C", "D"])
            
            if st.form_submit_button("💾 Salvar Questão"):
                if pergunta and alt_a and alt_b:
                    nova_q = {
                        "pergunta": pergunta,
                        "faixa": faixa,
                        "categoria": categoria,
                        "alternativas": {
                            "A": alt_a, "B": alt_b, "C": alt_c, "D": alt_d
                        },
                        "resposta_correta": correta,
                        "status": "aprovada",
                        "data_criacao": firestore.SERVER_TIMESTAMP
                    }
                    db.collection('questoes').add(nova_q)
                    st.success("Questão adicionada com sucesso!")
                    time.sleep(1)
                    st.rerun()
                else:
                    st.warning("Preencha pelo menos a pergunta e duas alternativas.")

# =========================================
# 3. GESTÃO DE EXAMES
# =========================================
def gestao_exame_de_faixa():
    st.markdown("<h1 style='color:#FFD700;'>⚙️ Configuração de Exames</h1>", unsafe_allow_html=True)
    db = get_db()
    
    st.info("Configure as regras da prova para cada faixa.")
    
    faixa_sel = st.selectbox("Selecione a Faixa para Configurar:", FAIXAS_COMPLETAS)
    
    docs = db.collection('config_exames').where('faixa', '==', faixa_sel).stream()
    config_atual = {}
    doc_id = None
    for doc in docs:
        config_atual = doc.to_dict()
        doc_id = doc.id
        break
        
    with st.form("form_config_exame"):
        c1, c2, c3 = st.columns(3)
        qtd = c1.number_input("Qtd. Questões:", min_value=5, max_value=50, value=int(config_atual.get('qtd_questoes', 10)))
        tempo = c2.number_input("Tempo (minutos):", min_value=10, max_value=180, value=int(config_atual.get('tempo_limite', 45)))
        minima = c3.number_input("Aprovação (%):", min_value=50, max_value=100, value=int(config_atual.get('aprovacao_minima', 70)))
        
        # Configurar Horários (Usando dtime para evitar conflito)
        st.markdown("---")
        st.markdown("**Horário Padrão (Opcional)**")
        ch1, ch2 = st.columns(2)
        h_ini = ch1.time_input("Início Padrão:", value=dtime(0,0)) 
        h_fim = ch2.time_input("Fim Padrão:", value=dtime(23,59))
        
        if st.form_submit_button("💾 Salvar Configuração"):
            dados = {
                "faixa": faixa_sel,
                "qtd_questoes": qtd,
                "tempo_limite": tempo,
                "aprovacao_minima": minima
            }
            if doc_id:
                db.collection('config_exames').document(doc_id).update(dados)
            else:
                db.collection('config_exames').add(dados)
            st.success(f"Regras para faixa {faixa_sel} salvas!")
            time.sleep(1)
            st.rerun()
