import streamlit as st
import pandas as pd
import bcrypt
from database import get_db
from utils import formatar_e_validar_cpf, carregar_questoes, salvar_questoes, carregar_todas_questoes
import os
import json
from datetime import datetime, time
from firebase_admin import firestore

# =========================================
# GESTÃO DE USUÁRIOS
# =========================================
def gestao_usuarios(usuario_logado):
    """Página de gerenciamento de usuários (Admin)."""
    
    if usuario_logado["tipo"] != "admin":
        st.error("Acesso negado. Esta página é restrita aos administradores.")
        return

    st.markdown("<h1 style='color:#FFD700;'>🔑 Gestão de Usuários</h1>", unsafe_allow_html=True)
    db = get_db()
    
    docs = db.collection('usuarios').stream()
    lista_usuarios = []
    
    for doc in docs:
        d = doc.to_dict()
        d['id_doc'] = doc.id
        d.setdefault('cpf', '')
        d.setdefault('tipo_usuario', 'aluno')
        d.setdefault('auth_provider', 'local')
        lista_usuarios.append(d)
        
    if not lista_usuarios:
        st.info("Nenhum usuário encontrado.")
        return

    df = pd.DataFrame(lista_usuarios)
    
    st.subheader("Visão Geral")
    cols = [c for c in ['nome', 'email', 'tipo_usuario', 'cpf', 'auth_provider'] if c in df.columns]
    st.dataframe(df[cols], use_container_width=True)
    st.markdown("---")

    st.subheader("Gerenciar Usuário")
    opcoes_selecao = [f"{u['nome']} ({u['email']})" for u in lista_usuarios]
    selecionado_str = st.selectbox("Selecione:", options=opcoes_selecao, index=None)

    if selecionado_str:
        index_selecionado = opcoes_selecao.index(selecionado_str)
        user_id = lista_usuarios[index_selecionado]['id_doc']
        user_data = lista_usuarios[index_selecionado]

        with st.expander(f"⚙️ Editar: {user_data.get('nome')}", expanded=True):
            with st.form(key="form_edit_user_admin"):
                c1, c2 = st.columns(2)
                novo_nome = c1.text_input("Nome:", value=user_data.get('nome', ''))
                novo_email = c2.text_input("Email:", value=user_data.get('email', ''))
                novo_cpf = st.text_input("CPF:", value=user_data.get('cpf', ''))
                
                tipo_atual = user_data.get('tipo_usuario', 'aluno')
                opcoes_tipo = ["aluno", "professor", "admin"]
                try: idx_tipo = opcoes_tipo.index(tipo_atual)
                except: idx_tipo = 0
                novo_tipo = st.selectbox("Tipo:", options=opcoes_tipo, index=idx_tipo)
                
                if st.form_submit_button("💾 Salvar"):
                    try:
                        db.collection('usuarios').document(user_id).update({
                            "nome": novo_nome.upper(), "email": novo_email.lower().strip(),
                            "cpf": novo_cpf, "tipo_usuario": novo_tipo
                        })
                        st.success("Atualizado!")
                        st.rerun()
                    except Exception as e: st.error(f"Erro: {e}")

            if user_data.get('auth_provider') == 'local':
                st.markdown("---")
                with st.form(key="form_reset_pass"):
                    n_senha = st.text_input("Nova Senha:", type="password")
                    if st.form_submit_button("Redefinir Senha"):
                        if n_senha:
                            h = bcrypt.hashpw(n_senha.encode(), bcrypt.gensalt()).decode()
                            db.collection('usuarios').document(user_id).update({"senha": h})
                            st.success("Senha alterada.")

            st.markdown("---")
            st.warning("Zona de Perigo")
            if st.button("🗑️ Excluir Usuário"):
                db.collection('usuarios').document(user_id).delete()
                # Limpeza de vínculos (batch)
                batch = db.batch()
                for a_doc in db.collection('alunos').where('usuario_id', '==', user_id).stream():
                    batch.delete(a_doc.reference)
                for p_doc in db.collection('professores').where('usuario_id', '==', user_id).stream():
                    batch.delete(p_doc.reference)
                batch.commit()
                st.success("Usuário excluído.")
                st.rerun()

# =========================================
# GESTÃO DE QUESTÕES (FIRESTORE)
# =========================================
def gestao_questoes():
    """Gestão de Banco de Questões no Firestore."""
    
    user = st.session_state.usuario
    if user["tipo"] not in ["admin", "professor"]:
        st.error("Acesso negado.")
        return
    
    st.markdown("<h1 style='color:#FFD700;'>🧠 Banco de Questões</h1>", unsafe_allow_html=True)
    db = get_db()

    # 1. Carregar questões existentes
    docs_q = list(db.collection('questoes').stream())
    todas_questoes = []
    temas_set = set()
    
    for doc in docs_q:
        d = doc.to_dict()
        d['id'] = doc.id
        todas_questoes.append(d)
        temas_set.add(d.get('tema', 'Geral'))
        
    temas_existentes = sorted(list(temas_set))
    
    # 2. Seleção de Tema
    c1, c2 = st.columns([3, 1])
    tema_sel = c1.selectbox("Filtrar/Adicionar Tema:", ["Novo Tema"] + temas_existentes)
    
    tema_atual = tema_sel
    if tema_sel == "Novo Tema":
        tema_atual = c2.text_input("Nome do novo tema:")

    # 3. Formulário de Adição
    with st.expander("➕ Adicionar Nova Questão", expanded=False):
        with st.form("form_add_q"):
            pergunta = st.text_area("Pergunta:")
            cols = st.columns(2)
            op_a = cols[0].text_input("Opção A (Correta):")
            op_b = cols[1].text_input("Opção B:")
            cols2 = st.columns(2)
            op_c = cols2[0].text_input("Opção C:")
            op_d = cols2[1].text_input("Opção D:")
            
            correta_letra = st.selectbox("Qual a correta?", ["A", "B", "C", "D"])
            img = st.text_input("URL da Imagem (Opcional):")

            if st.form_submit_button("Salvar"):
                if pergunta and tema_atual and op_a and op_b:
                    opcoes_raw = [op_a, op_b, op_c, op_d]
                    opcoes_limpas = [o for o in opcoes_raw if o.strip()]
                    
                    mapa = {"A": op_a, "B": op_b, "C": op_c, "D": op_d}
                    resp_texto = mapa.get(correta_letra)
                    
                    if not resp_texto:
                        st.error("A opção correta não pode estar vazia.")
                    else:
                        nova_q = {
                            "tema": tema_atual,
                            "pergunta": pergunta,
                            "opcoes": opcoes_limpas,
                            "resposta": resp_texto,
                            "imagem": img,
                            "criado_por": user['nome'],
                            "data": firestore.SERVER_TIMESTAMP
                        }
                        db.collection('questoes').add(nova_q)
                        st.success("Salvo!")
                        st.rerun()
                else:
                    st.warning("Preencha a pergunta e pelo menos 2 opções.")

    # 4. Listagem e Exclusão
    st.markdown(f"### Questões do tema: {tema_atual}")
    questoes_filtradas = [q for q in todas_questoes if q.get('tema') == tema_atual]
    
    if not questoes_filtradas:
        st.info("Nenhuma questão neste tema.")
    else:
        for q in questoes_filtradas:
            with st.expander(f"{q['pergunta']}"):
                st.write(f"**Opções:** {q.get('opcoes')}")
                st.caption(f"✅ Resposta: {q.get('resposta')}")
                if st.button("🗑️ Excluir", key=f"del_{q['id']}"):
                    db.collection('questoes').document(q['id']).delete()
                    st.rerun()

# =========================================
# GESTÃO DE EXAME DE FAIXA (ATUALIZADO COM TEMPO)
# =========================================
def gestao_exame_de_faixa():
    st.markdown("<h1 style='color:#FFD700;'>📜 Gestão de Exame</h1>", unsafe_allow_html=True)
    
    user_logado = st.session_state.usuario
    if user_logado["tipo"] not in ["admin", "professor"]:
        st.error("Acesso negado.")
        return

    tab_prova, tab_alunos = st.tabs(["📝 Montar Prova", "✅ Habilitar Alunos"])

    # ---------------------------------------------------------
    # ABA 1: MONTAR PROVA
    # ---------------------------------------------------------
    with tab_prova:
        st.subheader("Configurar Perguntas e Tempo")
        db = get_db()
        
        faixas = ["Cinza", "Amarela", "Laranja", "Verde", "Azul", "Roxa", "Marrom", "Preta"]
        faixa = st.selectbox("Selecione a faixa:", faixas, key="sel_faixa_prova")

        doc_ref = db.collection('exames').document(faixa)
        doc_prova = doc_ref.get()
        
        questoes_na_prova = []
        tempo_limite_atual = 60 # Default 60 min
        
        if doc_prova.exists:
            prova_data = doc_prova.to_dict()
            questoes_na_prova = prova_data.get('questoes', [])
            tempo_limite_atual = prova_data.get('tempo_limite', 60)

        # --- CONFIGURAÇÃO DE TEMPO ---
        col_tempo, col_vazia = st.columns([1, 3])
        novo_tempo = col_tempo.number_input(
            "⏱️ Tempo Limite (minutos):", 
            min_value=10, max_value=240, value=tempo_limite_atual, step=10,
            help="Tempo total para o aluno responder todas as questões."
        )

        # Carrega todas as questões para seleção
        docs_q = db.collection('questoes').stream()
        todas_q = [d.to_dict() for d in docs_q]
        
        temas = sorted(list(set(q.get('tema', 'Geral') for q in todas_q)))
        filtro = st.selectbox("Filtrar banco por tema:", ["Todos"] + temas)
        
        q_exibir = todas_q
        if filtro != "Todos":
            q_exibir = [q for q in todas_q if q.get('tema') == filtro]
            
        perguntas_ja_add = [q['pergunta'] for q in questoes_na_prova]

        with st.form("add_q_exame"):
            st.markdown("#### Selecionar Questões do Banco")
            selecionadas = []
            
            for i, q in enumerate(q_exibir):
                if q['pergunta'] not in perguntas_ja_add:
                    c_chk, c_det = st.columns([0.5, 10])
                    with c_chk:
                        key_id = str(hash(q['pergunta']))
                        if st.checkbox("Add", key=f"chk_{key_id}", label_visibility="collapsed"):
                            selecionadas.append(q)
                    with c_det:
                        st.markdown(f"**[{q.get('tema')}]** {q['pergunta']}")
                        
                        # --- VISUALIZAÇÃO DETALHADA ---
                        # Exibe todas as alternativas
                        if 'opcoes' in q and q['opcoes']:
                            for op in q['opcoes']:
                                st.markdown(f"<span style='color: #aaaaaa; margin-left: 15px;'>• {op}</span>", unsafe_allow_html=True)
                        
                        # Exibe a resposta correta destacada
                        resp_correta = q.get('resposta', 'Não definida')
                        st.markdown(f"<span style='color: #4CAF50; font-weight: bold; margin-left: 15px;'>✅ Resposta: {resp_correta}</span>", unsafe_allow_html=True)
                        
                        st.markdown("---")
            
            # Botão Salvar agora atualiza Questões E Tempo
            if st.form_submit_button("➕ Salvar Prova (Questões e Tempo)"):
                questoes_na_prova.extend(selecionadas)
                
                doc_ref.set({
                    "faixa": faixa,
                    "questoes": questoes_na_prova,
                    "tempo_limite": novo_tempo, # <--- SALVA O TEMPO
                    "atualizado_em": firestore.SERVER_TIMESTAMP,
                    "atualizado_por": user_logado['nome']
                })
                st.success(f"Prova atualizada! Tempo definido: {novo_tempo} min.")
                st.rerun()

        st.markdown("---")
        st.markdown(f"#### Questões nesta Prova ({len(questoes_na_prova)})")
        
        if questoes_na_prova:
            for i, q in enumerate(questoes_na_prova):
                with st.expander(f"{i+1}. {q['pergunta']}"):
                    st.write(q.get('opcoes'))
                    st.caption(f"Resp: {q.get('resposta')}")
                    if st.button("Remover", key=f"rm_{i}"):
                        questoes_na_prova.pop(i)
                        doc_ref.update({
                            "questoes": questoes_na_prova,
                            "tempo_limite": novo_tempo 
                        })
                        st.rerun()
        else:
            st.info("Esta prova ainda não tem questões.")

    # ---------------------------------------------------------
    # ABA 2: HABILITAR ALUNOS
    # ---------------------------------------------------------
    with tab_alunos:
        st.subheader("Autorizar Alunos")
        
        equipes_permitidas = []
        if user_logado['tipo'] == 'admin':
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
            
            st.markdown("#### Configurar Período Disponível")
            c_ini, c_fim = st.columns(2)
            d_ini = c_ini.date_input("Início:", value=datetime.now())
            h_ini = c_ini.time_input("Hora:", value=time(0, 0))
            d_fim = c_fim.date_input("Fim:", value=datetime.now())
            h_fim = c_fim.time_input("Hora Fin:", value=time(23, 59))
            
            dt_inicio = datetime.combine(d_ini, h_ini)
            dt_fim = datetime.combine(d_fim, h_fim)

            st.markdown("---")
            
            h = st.columns([3, 2, 2, 3, 2])
            h[0].markdown("**Aluno**")
            h[1].markdown("**Equipe**")
            h[2].markdown("**Faixa**")
            h[3].markdown("**Status/Data**")
            h[4].markdown("**Ação**")
            
            for doc in docs_alunos:
                d = doc.to_dict()
                uid = d.get('usuario_id')
                eid = d.get('equipe_id')
                
                if equipes_permitidas is None or eid in equipes_permitidas:
                    nome = users_map.get(uid, "Desconhecido")
                    eq = equipes_map.get(eid, "-")
                    hab = d.get('exame_habilitado', False)
                    
                    p_str = "Bloqueado"
                    if hab:
                        try:
                            i = d.get('exame_inicio').replace(tzinfo=None).strftime("%d/%m")
                            f = d.get('exame_fim').replace(tzinfo=None).strftime("%d/%m")
                            p_str = f"Lib: {i}-{f}"
                        except: p_str = "Liberado"

                    c = st.columns([3, 2, 2, 3, 2])
                    c[0].write(nome)
                    c[1].write(eq)
                    c[2].write(d.get('faixa_atual'))
                    c[3].write(p_str)
                    
                    if hab:
                        if c[4].button("Bloquear", key=f"blk_{doc.id}"):
                            db.collection('alunos').document(doc.id).update({
                                "exame_habilitado": False, "exame_inicio": None, "exame_fim": None
                            })
                            st.rerun()
                    else:
                        if c[4].button("Liberar", key=f"lib_{doc.id}"):
                            if dt_inicio < dt_fim:
                                db.collection('alunos').document(doc.id).update({
                                    "exame_habilitado": True, 
                                    "exame_inicio": dt_inicio, 
                                    "exame_fim": dt_fim
                                })
                                st.rerun()
                            else: st.error("Data Inválida")
