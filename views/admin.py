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
    st.markdown("<h1 style='color:#FFD700;'>📜 Gestão de Exame</h1>", unsafe_allow_html=True)
    
    user_logado = st.session_state.usuario
    tipo_user = str(user_logado.get("tipo", "")).lower()
    
    if tipo_user not in ["admin", "professor"]:
        st.error("Acesso negado.")
        return

    # Abas Principais
    tab_editor, tab_visualizar, tab_alunos = st.tabs(["✏️ Editor de Provas", "👁️ Visualizar Provas", "✅ Habilitar Alunos"])
    
    db = get_db()
    
    # Lista completa de faixas com subdivisões
    todas_faixas = [
        "Cinza e Branca", "Cinza", "Cinza e Preta",
        "Amarela e Branca", "Amarela", "Amarela e Preta",
        "Laranja e Branca", "Laranja", "Laranja e Preta",
        "Verde e Branca", "Verde", "Verde e Preta",
        "Azul", "Roxa", "Marrom", "Preta"
    ]

    # ---------------------------------------------------------
    # ABA 1: EDITOR (Focado em Criação/Edição)
    # ---------------------------------------------------------
    with tab_editor:
        st.subheader("Editor de Prova")
        st.caption("Selecione a faixa abaixo para adicionar ou remover questões.")
        
        # Seletor ÚNICO com todas as opções
        faixa_edit = st.selectbox("Selecione o exame:", todas_faixas, key="sel_faixa_edit")
        
        # Carrega dados
        doc_ref = db.collection('exames').document(faixa_edit)
        doc_snap = doc_ref.get()
        
        dados_prova = doc_snap.to_dict() if doc_snap.exists else {}
        questoes_atuais = dados_prova.get('questoes', [])
        tempo_atual = dados_prova.get('tempo_limite', 60)

        c_time, c_stat = st.columns([1, 3])
        novo_tempo = c_time.number_input("⏱️ Tempo Limite (min):", 10, 240, tempo_atual, 10)
        c_stat.info(f"Prova **{faixa_edit}**: {len(questoes_atuais)} questões adicionadas.")

        st.markdown("---")
        st.markdown("#### ➕ Adicionar Questões do Banco")
        
        # Carrega Banco de Questões Aprovadas
        docs_q = db.collection('questoes').where('status', '==', 'aprovada').stream()
        todas_q = [d.to_dict() for d in docs_q] 
        
        temas = sorted(list(set(q.get('tema', 'Geral') for q in todas_q)))
        filtro = st.selectbox("Filtrar Banco por Tema:", ["Todos"] + temas)
        
        q_exibir = [q for q in todas_q if q.get('tema') == filtro] if filtro != "Todos" else todas_q
        perguntas_ja_add = [q['pergunta'] for q in questoes_atuais]

        # Formulário de Adição
        with st.form("form_add_questoes"):
            selecionadas = []
            count = 0
            for i, q in enumerate(q_exibir):
                if count > 50: 
                    st.caption("... muitos resultados. Filtre por tema para ver mais."); break
                    
                if q['pergunta'] not in perguntas_ja_add:
                    c_chk, c_det = st.columns([0.5, 10])
                    with c_chk:
                        # Visualização compacta para seleção
                        ck = st.checkbox("Add", key=f"add_{i}", label_visibility="collapsed")
                        if ck: selecionadas.append(q)
                    with c_det:
                        st.markdown(f"**[{q.get('tema')}]** {q['pergunta']}")
                        # Detalhes visíveis na seleção
                        if 'opcoes' in q:
                            st.caption(f"Opções: {q.get('opcoes')}")
                        st.caption(f"✅ {q.get('resposta')} | ✍️ {q.get('criado_por', 'Admin')}")
                        st.markdown("---")
                    count += 1
            
            if st.form_submit_button("Salvar Selecionadas na Prova"):
                questoes_atuais.extend(selecionadas)
                doc_ref.set({
                    "faixa": faixa_edit,
                    "questoes": questoes_atuais,
                    "tempo_limite": novo_tempo,
                    "atualizado_em": firestore.SERVER_TIMESTAMP,
                    "atualizado_por": user_logado['nome']
                })
                st.success("Prova salva com sucesso!")
                st.rerun()

        if questoes_atuais:
            st.markdown("#### 📋 Questões na Prova Atual")
            for i, q in enumerate(questoes_atuais):
                with st.expander(f"{i+1}. {q['pergunta']}"):
                    st.write(q.get('opcoes'))
                    st.info(f"Resposta: {q.get('resposta')}")
                    if st.button("Remover da Prova", key=f"rem_{i}"):
                        questoes_atuais.pop(i)
                        doc_ref.update({"questoes": questoes_atuais, "tempo_limite": novo_tempo})
                        st.rerun()

    # ---------------------------------------------------------
    # ABA 2: VISUALIZAR (Agrupado por Cor)
    # ---------------------------------------------------------
    with tab_visualizar:
        st.subheader("Visualizar Provas Cadastradas")
        
        # Categorias de Cores para organização visual
        categorias = {
            "🔘 Cinza": ["Cinza e Branca", "Cinza", "Cinza e Preta"],
            "🟡 Amarela": ["Amarela e Branca", "Amarela", "Amarela e Preta"],
            "🟠 Laranja": ["Laranja e Branca", "Laranja", "Laranja e Preta"],
            "🟢 Verde": ["Verde e Branca", "Verde", "Verde e Preta"],
            "🔵 Azul": ["Azul"],
            "🟣 Roxa": ["Roxa"],
            "🟤 Marrom": ["Marrom"],
            "⚫ Preta": ["Preta"]
        }
        
        abas_cores = st.tabs(list(categorias.keys()))
        
        for aba, (cor_nome, lista_faixas) in zip(abas_cores, categorias.items()):
            with aba:
                for f_nome in lista_faixas:
                    d_ref = db.collection('exames').document(f_nome).get()
                    if d_ref.exists:
                        data = d_ref.to_dict()
                        q_list = data.get('questoes', [])
                        
                        with st.expander(f"✅ {f_nome} ({len(q_list)} questões)"):
                            st.caption(f"Tempo: {data.get('tempo_limite')} min | Por: {data.get('atualizado_por', 'Admin')}")
                            
                            if q_list:
                                for i, q in enumerate(q_list, 1):
                                    st.markdown(f"**{i}. {q['pergunta']}**")
                                    for op in q.get('opcoes', []):
                                        st.text(f"  • {op}")
                                    st.success(f"Resposta: {q.get('resposta')}")
                                    st.caption(f"Autor: {q.get('criado_por', 'Desconhecido')}")
                                    st.markdown("---")
                            else:
                                st.warning("Prova vazia.")
                    else:
                        st.info(f"⚠️ A prova para a faixa **{f_nome}** ainda não foi criada.")

    # ---------------------------------------------------------
    # ABA 3: HABILITAR ALUNOS (Texto Atualizado)
    # ---------------------------------------------------------
    with tab_alunos:
        st.subheader("Autorizar Alunos")
        
        equipes_permitidas = []
        if tipo_user == 'admin':
            equipes_permitidas = None 
        else:
            q1 = db.collection('equipes').where('professor_responsavel_id', '==', user_logado['id']).stream()
            equipes_permitidas = [d.id for d in q1]
            q2 = db.collection('professores').where('usuario_id', '==', user_logado['id']).where('status_vinculo', '==', 'ativo').stream()
            for d in q2:
                eid = d.to_dict().get('equipe_id')
                if eid and eid not in equipes_permitidas:
                    equipes_permitidas.append(eid)
            
            if not equipes_permitidas:
                st.warning("Sem equipes vinculadas.")
                st.stop()

        alunos_ref = db.collection('alunos')
        if equipes_permitidas:
            query = alunos_ref.where('equipe_id', 'in', equipes_permitidas[:10])
        else:
            query = alunos_ref 

        docs_alunos = list(query.stream())
        
        if not docs_alunos:
            st.info("Nenhum aluno encontrado.")
        else:
            users_map = {d.id: d.to_dict().get('nome','?') for d in db.collection('usuarios').stream()}
            equipes_map = {d.id: d.to_dict().get('nome','?') for d in db.collection('equipes').stream()}
            
            st.markdown("#### 📅 Configurar Período")
            c_ini, c_fim = st.columns(2)
            d_ini = c_ini.date_input("Início:", value=datetime.now())
            h_ini = c_ini.time_input("Hora:", value=time(0, 0))
            d_fim = c_fim.date_input("Fim:", value=datetime.now())
            h_fim = c_fim.time_input("Hora Fin:", value=time(23, 59))
            dt_inicio = datetime.combine(d_ini, h_ini); dt_fim = datetime.combine(d_fim, h_fim)

            st.markdown("---")
            h = st.columns([3, 2, 2, 3, 2])
            h[0].markdown("**Aluno**"); h[1].markdown("**Equipe**"); h[2].markdown("**Exame**"); h[3].markdown("**Status**"); h[4].markdown("**Ação**")
            
            # Lista completa para o seletor
            todas_faixas_ops = todas_faixas

            for doc in docs_alunos:
                d = doc.to_dict()
                uid = d.get('usuario_id'); eid = d.get('equipe_id')
                
                if equipes_permitidas is None or eid in equipes_permitidas:
                    nome = users_map.get(uid, "Desconhecido")
                    eq = equipes_map.get(eid, "-")
                    hab = d.get('exame_habilitado', False)
                    lib = d.get('faixa_exame_liberado', 'Nenhuma')
                    
                    # --- TEXTO DE STATUS ATUALIZADO ---
                    status_txt = "🔴 Bloqueado"
                    if hab:
                        try:
                            # Formato: liberado para realizar o exame até o dia DD/MM/AAAA
                            f_dt = d.get('exame_fim').replace(tzinfo=None).strftime("%d/%m/%Y")
                            status_txt = f"🟢 liberado para realizar o exame até o dia {f_dt}"
                        except:
                            status_txt = "🟢 Liberado"
                    
                    c = st.columns([3, 2, 2, 3, 2])
                    c[0].write(nome)
                    c[1].write(eq)
                    
                    try: idx_f = todas_faixas_ops.index(lib)
                    except: idx_f = 0
                    fx_sel = c[2].selectbox("Faixa", todas_faixas_ops, index=idx_f, key=f"s_{doc.id}", label_visibility="collapsed")
                    c[3].caption(status_txt)
                    
                    if hab:
                        if c[4].button("⛔", key=f"b_{doc.id}", help="Bloquear"):
                            db.collection('alunos').document(doc.id).update({"exame_habilitado": False})
                            st.rerun()
                    else:
                        if c[4].button("✅", key=f"l_{doc.id}", help="Liberar"):
                            db.collection('alunos').document(doc.id).update({
                                "exame_habilitado": True, "exame_inicio": dt_inicio, "exame_fim": dt_fim, "faixa_exame_liberado": fx_sel
                            })
                            st.rerun()
