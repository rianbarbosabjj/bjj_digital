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
# GESTÃO DE USUÁRIOS (Mantida)
# =========================================
def gestao_usuarios(usuario_logado):
    if usuario_logado["tipo"] != "admin":
        st.error("Acesso negado."); return
    st.markdown("<h1 style='color:#FFD700;'>🔑 Gestão de Usuários</h1>", unsafe_allow_html=True)
    
    db = get_db()
    docs = db.collection('usuarios').stream()
    lista = []
    for doc in docs:
        d = doc.to_dict(); d['id_doc'] = doc.id
        d.setdefault('cpf',''); d.setdefault('tipo_usuario','aluno'); d.setdefault('auth_provider','local')
        lista.append(d)
    
    if not lista: st.info("Nenhum usuário."); return
    df = pd.DataFrame(lista)
    st.dataframe(df[['nome','email','tipo_usuario','cpf']], use_container_width=True)
    st.markdown("---")
    
    ops = [f"{u['nome']} ({u['email']})" for u in lista]
    sel = st.selectbox("Editar Usuário:", ops, index=None)
    if sel:
        idx = ops.index(sel); uid = lista[idx]['id_doc']; udata = lista[idx]
        with st.expander(f"⚙️ Editar {udata.get('nome')}", expanded=True):
            with st.form("edit_u"):
                c1,c2=st.columns(2)
                nn = c1.text_input("Nome:", udata.get('nome',''))
                ne = c2.text_input("Email:", udata.get('email',''))
                ncpf = st.text_input("CPF:", udata.get('cpf',''))
                tipos = ["aluno","professor","admin"]
                nt = st.selectbox("Tipo:", tipos, index=tipos.index(udata.get('tipo_usuario','aluno')))
                if st.form_submit_button("Salvar"):
                    db.collection('usuarios').document(uid).update({
                        "nome":nn.upper(), "email":ne.lower().strip(), "cpf":ncpf, "tipo_usuario":nt
                    })
                    st.success("Salvo!"); st.rerun()
            
            if udata.get('auth_provider') == 'local':
                with st.form("pass_u"):
                    ns = st.text_input("Nova Senha:", type="password")
                    if st.form_submit_button("Redefinir Senha") and ns:
                        h = bcrypt.hashpw(ns.encode(), bcrypt.gensalt()).decode()
                        db.collection('usuarios').document(uid).update({"senha": h})
                        st.success("Senha alterada.")
            
            st.markdown("---")
            if st.button("🗑️ Excluir Usuário"):
                db.collection('usuarios').document(uid).delete()
                # Limpeza de vínculos (batch)
                batch = db.batch()
                for a_doc in db.collection('alunos').where('usuario_id', '==', uid).stream():
                    batch.delete(a_doc.reference)
                for p_doc in db.collection('professores').where('usuario_id', '==', uid).stream():
                    batch.delete(p_doc.reference)
                batch.commit()
                st.success("Excluído!"); st.rerun()

# =========================================
# GESTÃO DE QUESTÕES (Mantida)
# =========================================
def gestao_questoes():
    st.markdown("<h1 style='color:#FFD700;'>🧠 Banco de Questões</h1>", unsafe_allow_html=True)
    
    user = st.session_state.usuario
    tipo_user = str(user.get("tipo", "")).lower()
    if tipo_user not in ["admin", "professor"]:
        st.error("Acesso negado."); return
        
    db = get_db()
    docs_q = list(db.collection('questoes').stream())
    aprovadas = []; pendentes = []; temas_set = set()

    for doc in docs_q:
        d = doc.to_dict(); d['id'] = doc.id
        status = d.get('status', 'aprovada')
        if status == 'pendente': pendentes.append(d)
        else:
            aprovadas.append(d)
            temas_set.add(d.get('tema', 'Geral'))

    temas_existentes = sorted(list(temas_set))
    
    titulos_abas = ["📚 Banco de Questões", "➕ Nova Questão"]
    if tipo_user == "admin": titulos_abas.append(f"✅ Aprovar ({len(pendentes)})")
    
    abas = st.tabs(titulos_abas)
    
    # Aba 1: Listar
    with abas[0]:
        ft = st.selectbox("Filtrar Tema:", ["Todos"] + temas_existentes)
        qx = [q for q in aprovadas if q.get('tema') == ft] if ft != "Todos" else aprovadas
        if not qx: st.info("Nada encontrado.")
        else:
            for q in qx:
                with st.container(border=True):
                    col_txt, col_btn = st.columns([6, 1])
                    col_txt.markdown(f"**[{q.get('tema')}]** {q['pergunta']}")
                    autor = q.get('criado_por', 'Desconhecido').title()
                    st.caption(f"✍️ Criado por: {autor}")
                    
                    with st.expander("Ver Detalhes"):
                        st.write(f"**Opções:** {q.get('opcoes')}")
                        st.caption(f"✅ Resposta: {q.get('resposta')}")
                        if tipo_user == "admin" and st.button("Excluir", key=f"del_{q['id']}"):
                            db.collection('questoes').document(q['id']).delete(); st.rerun()

    # Aba 2: Criar
    with abas[1]:
        with st.form("new_q"):
            tema = st.text_input("Tema:")
            perg = st.text_area("Pergunta:")
            ops = [st.text_input(f"Opção {x}") for x in "ABCD"]
            resp = st.selectbox("Correta:", "ABCD")
            if st.form_submit_button("Salvar"):
                op_limpas = [o for o in ops if o.strip()]
                if len(op_limpas) >= 2:
                    mapa = dict(zip("ABCD", ops))
                    st_init = "aprovada" if tipo_user == "admin" else "pendente"
                    db.collection('questoes').add({
                        "tema": tema, "pergunta": perg, "opcoes": op_limpas,
                        "resposta": mapa[resp], "status": st_init,
                        "criado_por": user['nome'], "data": firestore.SERVER_TIMESTAMP
                    })
                    st.success("Salvo!"); st.rerun()
                else: st.warning("Preencha tudo.")

    # Aba 3: Aprovar
    if tipo_user == "admin" and len(abas) > 2:
        with abas[2]:
            for q in pendentes:
                st.write(f"**{q['pergunta']}**"); st.caption(f"Por: {q.get('criado_por')}")
                c1,c2 = st.columns(2)
                if c1.button("✅", key=f"ok_{q['id']}"):
                    db.collection('questoes').document(q['id']).update({"status":"aprovada"}); st.rerun()
                if c2.button("❌", key=f"no_{q['id']}"):
                    db.collection('questoes').document(q['id']).delete(); st.rerun()

# =========================================
# GESTÃO DE EXAME DE FAIXA (REFORMULADO COM CORES)
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
    
    # Listas de Faixas
    faixas = ["Cinza", "Amarela", "Laranja", "Verde", "Azul", "Roxa", "Marrom", "Preta"]

    # ---------------------------------------------------------
    # ABA 1: EDITOR (Focado em Criação/Edição)
    # ---------------------------------------------------------
    with tab_editor:
        st.subheader("Editor de Prova")
        
        # Seletor ÚNICO para focar na edição
        faixa_edit = st.selectbox("Selecione a faixa para criar/editar:", faixas, key="sel_faixa_edit")
        
        # Carrega dados
        doc_ref = db.collection('exames').document(faixa_edit)
        doc_snap = doc_ref.get()
        
        dados_prova = doc_snap.to_dict() if doc_snap.exists else {}
        questoes_atuais = dados_prova.get('questoes', [])
        tempo_atual = dados_prova.get('tempo_limite', 60)

        # Configurações
        c_time, c_stat = st.columns([1, 3])
        novo_tempo = c_time.number_input("⏱️ Tempo Limite (min):", 10, 240, tempo_atual, 10)
        c_stat.info(f"Esta prova contém atualmente **{len(questoes_atuais)} questões**.")

        st.markdown("---")
        st.markdown("#### ➕ Adicionar Questões")
        
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
            # Limita exibição para performance
            for i, q in enumerate(q_exibir):
                if count > 50: 
                    st.caption("... muitos resultados. Filtre por tema para ver mais."); break
                    
                if q['pergunta'] not in perguntas_ja_add:
                    # Visualização compacta para seleção
                    ck = st.checkbox(f"**[{q.get('tema')}]** {q['pergunta']}", key=f"add_{i}")
                    if ck: selecionadas.append(q)
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

        # Lista de Questões na Prova (Gerenciamento)
        if questoes_atuais:
            st.markdown("---")
            st.markdown("#### 📋 Questões na Prova Atual")
            for i, q in enumerate(questoes_atuais):
                c_txt, c_btn = st.columns([6, 1])
                c_txt.markdown(f"**{i+1}.** {q['pergunta']}")
                if c_btn.button("🗑️", key=f"rem_{i}", help="Remover da prova"):
                    questoes_atuais.pop(i)
                    doc_ref.update({"questoes": questoes_atuais, "tempo_limite": novo_tempo})
                    st.rerun()

    # ---------------------------------------------------------
    # ABA 2: VISUALIZAR (Com Abas Coloridas)
    # ---------------------------------------------------------
    with tab_visualizar:
        st.subheader("Visualizar Provas Cadastradas")
        st.caption("Consulte aqui o conteúdo das provas já criadas.")
        
        # Categorias de Cores para organização visual com ícones
        categorias = {
            "🔘 Cinza": ["Cinza"],
            "🟡 Amarela": ["Amarela"],
            "🟠 Laranja": ["Laranja"],
            "🟢 Verde": ["Verde"],
            "🔵 Azul": ["Azul"],
            "🟣 Roxa": ["Roxa"],
            "🟤 Marrom": ["Marrom"],
            "⚫ Preta": ["Preta"]
        }
        
        abas_cores = st.tabs(list(categorias.keys()))
        
        for aba, (cor_nome, lista_faixas) in zip(abas_cores, categorias.items()):
            with aba:
                for f_nome in lista_faixas:
                    # Busca dados (apenas leitura)
                    d_ref = db.collection('exames').document(f_nome).get()
                    if d_ref.exists:
                        data = d_ref.to_dict()
                        q_list = data.get('questoes', [])
                        
                        st.success(f"**Status:** ✅ Prova Criada | **Tempo:** {data.get('tempo_limite')} min")
                        st.caption(f"Atualizado por: {data.get('atualizado_por', 'Admin')}")
                        
                        if q_list:
                            for i, q in enumerate(q_list, 1):
                                with st.expander(f"{i}. {q['pergunta']}"):
                                    for op in q.get('opcoes', []):
                                        st.text(f"• {op}")
                                    st.caption(f"Resposta: {q.get('resposta')}")
                        else:
                            st.warning("Prova criada mas sem questões.")
                    else:
                        st.info(f"A prova para a faixa **{f_nome}** ainda não foi criada.")
                        st.markdown("Vá na aba **'✏️ Editor de Provas'** para criar.")

    # ---------------------------------------------------------
    # ABA 3: HABILITAR ALUNOS (Mantida)
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
            
            todas_faixas_ops = faixas

            for doc in docs_alunos:
                d = doc.to_dict()
                uid = d.get('usuario_id'); eid = d.get('equipe_id')
                
                if equipes_permitidas is None or eid in equipes_permitidas:
                    nome = users_map.get(uid, "Desconhecido")
                    eq = equipes_map.get(eid, "-")
                    hab = d.get('exame_habilitado', False)
                    lib = d.get('faixa_exame_liberado', 'Nenhuma')
                    
                    status_txt = "🔴 Bloqueado"
                    if hab:
                        try:
                            f_dt = d.get('exame_fim').replace(tzinfo=None).strftime("%d/%m/%Y")
                            status_txt = f"🟢 liberado para realizar o exame até o dia {f_dt}"
                        except: status_txt = "🟢 Liberado"
                    
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
