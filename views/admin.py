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
    # ... (Código de gestão de questões mantido igual ao anterior)
    # Repetindo a lógica essencial para garantir funcionamento
    
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
                with st.expander(f"[{q.get('tema')}] {q['pergunta']}"):
                    st.write(f"Opções: {q.get('opcoes')}")
                    st.caption(f"Resposta: {q.get('resposta')}")
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
# GESTÃO DE EXAME DE FAIXA (REFORMULADO)
# =========================================
def gestao_exame_de_faixa():
    st.markdown("<h1 style='color:#FFD700;'>📜 Gestão de Exame</h1>", unsafe_allow_html=True)
    
    user_logado = st.session_state.usuario
    tipo_user = str(user_logado.get("tipo", "")).lower()
    
    if tipo_user not in ["admin", "professor"]:
        st.error("Acesso negado.")
        return

    tab_prova, tab_alunos = st.tabs(["📝 Montar Prova", "✅ Habilitar Alunos"])

    # ---------------------------------------------------------
    # ABA 1: MONTAR PROVA
    # ---------------------------------------------------------
    with tab_prova:
        st.subheader("Editor de Exames")
        db = get_db()
        
        # Lista de faixas SEM a Branca
        faixas = ["Cinza", "Amarela", "Laranja", "Verde", "Azul", "Roxa", "Marrom", "Preta"]
        faixa = st.selectbox("Selecione a faixa para editar:", faixas, key="sel_faixa_prova")

        doc_ref = db.collection('exames').document(faixa)
        doc_prova = doc_ref.get()
        
        questoes_na_prova = []
        tempo_limite_atual = 60
        
        if doc_prova.exists:
            prova_data = doc_prova.to_dict()
            questoes_na_prova = prova_data.get('questoes', [])
            tempo_limite_atual = prova_data.get('tempo_limite', 60)

        col_tempo, col_vazia = st.columns([1, 3])
        novo_tempo = col_tempo.number_input(
            "⏱️ Tempo Limite (minutos):", 
            min_value=10, max_value=240, value=tempo_limite_atual, step=10
        )

        docs_q = db.collection('questoes').where('status', '==', 'aprovada').stream()
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
            # Limite de visualização para performance
            count = 0
            for q in q_exibir:
                if count > 100: break
                if q['pergunta'] not in perguntas_ja_add:
                    c_chk, c_det = st.columns([0.5, 10])
                    with c_chk:
                        key_id = str(hash(q['pergunta']))
                        if st.checkbox("Add", key=f"chk_{key_id}", label_visibility="collapsed"):
                            selecionadas.append(q)
                    with c_det:
                        st.markdown(f"**[{q.get('tema')}]** {q['pergunta']}")
                        if 'opcoes' in q:
                             st.caption(f"Opções: {q.get('opcoes')}")
                        st.markdown("---")
                    count += 1
            
            if st.form_submit_button("➕ Salvar Prova"):
                questoes_na_prova.extend(selecionadas)
                doc_ref.set({
                    "faixa": faixa,
                    "questoes": questoes_na_prova,
                    "tempo_limite": novo_tempo,
                    "atualizado_em": firestore.SERVER_TIMESTAMP,
                    "atualizado_por": user_logado['nome']
                })
                st.success("Prova atualizada!")
                st.rerun()

        if questoes_na_prova:
            st.info(f"Esta prova contém {len(questoes_na_prova)} questões.")
            with st.expander("Ver/Remover Questões Atuais"):
                for i, q in enumerate(questoes_na_prova):
                    c1, c2 = st.columns([5, 1])
                    c1.write(f"{i+1}. {q['pergunta']}")
                    if c2.button("🗑️", key=f"rm_{i}"):
                        questoes_na_prova.pop(i)
                        doc_ref.update({"questoes": questoes_na_prova, "tempo_limite": novo_tempo})
                        st.rerun()

        # --- VISUALIZADOR DE PROVAS SALVAS (NOVO) ---
        st.markdown("---")
        st.subheader("📂 Visualizar Provas Salvas")
        
        # Categorias de Cores para organização visual
        # (A branca foi removida conforme solicitado)
        categorias = {
            "Cinza": ["Cinza"],
            "Amarela": ["Amarela"],
            "Laranja": ["Laranja"],
            "Verde": ["Verde"],
            "Azul": ["Azul"],
            "Roxa": ["Roxa"],
            "Marrom": ["Marrom"],
            "Preta": ["Preta"]
        }
        
        abas_cores = st.tabs(list(categorias.keys()))
        
        for aba, (cor, lista_faixas) in zip(abas_cores, categorias.items()):
            with aba:
                for f_nome in lista_faixas:
                    # Busca rapida para ver se existe
                    d_ref = db.collection('exames').document(f_nome).get()
                    if d_ref.exists:
                        d_data = d_ref.to_dict()
                        q_qtd = len(d_data.get('questoes', []))
                        t_lim = d_data.get('tempo_limite', 60)
                        st.success(f"**{f_nome}:** {q_qtd} questões | {t_lim} min")
                        # Botão para carregar no editor
                        if st.button(f"Editar {f_nome}", key=f"load_{f_nome}"):
                            # Como o selectbox controla o estado, não conseguimos forçar a mudança dele 
                            # facilmente sem session_state complexo, mas o usuário pode ver que existe.
                            st.toast(f"Selecione '{f_nome}' no menu acima para editar.")
                    else:
                        st.caption(f"{f_nome}: Não criada")

    # ---------------------------------------------------------
    # ABA 2: HABILITAR ALUNOS (ATUALIZADA)
    # ---------------------------------------------------------
    with tab_alunos:
        st.subheader("Autorizar Alunos")
        db = get_db()

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
            
            # Lista completa SEM Branca
            todas_faixas_ops = faixas

            for doc in docs_alunos:
                d = doc.to_dict()
                uid = d.get('usuario_id'); eid = d.get('equipe_id')
                
                if equipes_permitidas is None or eid in equipes_permitidas:
                    nome = users_map.get(uid, "Desconhecido")
                    eq = equipes_map.get(eid, "-")
                    hab = d.get('exame_habilitado', False)
                    lib = d.get('faixa_exame_liberado', 'Nenhuma')
                    
                    # --- FORMATO DE STATUS SOLICITADO ---
                    status_txt = "🔴 Bloqueado"
                    if hab:
                        try:
                            # Formata data fim para exibição amigável
                            f_dt = d.get('exame_fim').replace(tzinfo=None).strftime("%d/%m/%Y")
                            status_txt = f"🟢 liberado para realizar o exame até o dia {f_dt}"
                        except:
                            status_txt = "🟢 Liberado (Data desconhecida)"
                    
                    c = st.columns([3, 2, 2, 3, 2])
                    c[0].write(nome)
                    c[1].write(eq)
                    
                    try: idx_f = todas_faixas_ops.index(lib)
                    except: idx_f = 0
                    
                    fx_sel = c[2].selectbox("Faixa", todas_faixas_ops, index=idx_f, key=f"s_{doc.id}", label_visibility="collapsed")
                    c[3].caption(status_txt) # Caption fica menor e mais bonito para texto longo
                    
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
