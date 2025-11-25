import streamlit as st
import pandas as pd
from database import get_db
from firebase_admin import firestore

# =========================================
# PAINEL DO PROFESSOR (Aprovações de Alunos e Professores)
# =========================================
def painel_professor():
    st.markdown("<h1 style='color:#FFD700;'>👩‍🏫 Painel do Professor</h1>", unsafe_allow_html=True)
    db = get_db()
    user = st.session_state.usuario
    
    # 1. Descobre equipes onde sou ATIVO (Responsável ou Apoio Aprovado)
    prof_query = db.collection('professores')\
        .where('usuario_id', '==', user['id'])\
        .where('status_vinculo', '==', 'ativo').stream()
        
    meus_vinculos = list(prof_query)
    
    if not meus_vinculos:
        st.warning("Você não está vinculado a nenhuma equipe como professor ativo.")
        return
    
    # Lista de IDs das equipes que eu gerencio/participo
    equipes_ids = [doc.to_dict().get('equipe_id') for doc in meus_vinculos]
    
    if not equipes_ids:
        st.info("Nenhuma equipe vinculada.")
        return

    # --- SEÇÃO 1: APROVAR ALUNOS ---
    # Firestore 'in' limita a 10 ids.
    alunos_pend_ref = db.collection('alunos')\
        .where('equipe_id', 'in', equipes_ids[:10])\
        .where('status_vinculo', '==', 'pendente').stream()
        
    lista_pend_alunos = []
    for doc in alunos_pend_ref:
        d = doc.to_dict()
        u_snap = db.collection('usuarios').document(d['usuario_id']).get()
        if u_snap.exists:
            nome_aluno = u_snap.to_dict().get('nome', 'Desconhecido')
            eq_snap = db.collection('equipes').document(d['equipe_id']).get()
            nome_equipe = eq_snap.to_dict().get('nome', '?') if eq_snap.exists else '?'
            
            lista_pend_alunos.append({
                "id_doc": doc.id,
                "nome": nome_aluno,
                "equipe": nome_equipe,
                "faixa": d.get('faixa_atual')
            })

    # --- SEÇÃO 2: APROVAR PROFESSORES (NOVO!) ---
    profs_pend_ref = db.collection('professores')\
        .where('equipe_id', 'in', equipes_ids[:10])\
        .where('status_vinculo', '==', 'pendente').stream()
        
    lista_pend_profs = []
    for doc in profs_pend_ref:
        d = doc.to_dict()
        # Evita listar a si mesmo se houver algum erro de base
        if d.get('usuario_id') == user['id']:
            continue
            
        u_snap = db.collection('usuarios').document(d['usuario_id']).get()
        if u_snap.exists:
            nome_prof = u_snap.to_dict().get('nome', 'Desconhecido')
            eq_snap = db.collection('equipes').document(d['equipe_id']).get()
            nome_equipe = eq_snap.to_dict().get('nome', '?') if eq_snap.exists else '?'
            
            lista_pend_profs.append({
                "id_doc": doc.id,
                "nome": nome_prof,
                "equipe": nome_equipe
            })

    # --- RENDERIZAÇÃO ---
    
    if not lista_pend_alunos and not lista_pend_profs:
        st.info("Nenhuma solicitação pendente (Alunos ou Professores) nas suas equipes.")
    
    # Renderiza Alunos
    if lista_pend_alunos:
        st.markdown("### 🥋 Solicitações de Alunos")
        for p in lista_pend_alunos:
            with st.container(border=True):
                c1, c2, c3 = st.columns([3, 1, 1])
                c1.markdown(f"**{p['nome']}** quer entrar na equipe **{p['equipe']}** (Faixa: {p['faixa']})")
                
                if c2.button("✅ Aprovar", key=f"ok_aluno_{p['id_doc']}"):
                    db.collection('alunos').document(p['id_doc']).update({
                        "status_vinculo": "ativo",
                        "professor_id": user['id']
                    })
                    st.success(f"Aluno {p['nome']} aprovado!")
                    st.rerun()
                    
                if c3.button("❌ Rejeitar", key=f"no_aluno_{p['id_doc']}"):
                    db.collection('alunos').document(p['id_doc']).update({"status_vinculo": "rejeitado"})
                    st.warning("Rejeitado.")
                    st.rerun()

    # Renderiza Professores
    if lista_pend_profs:
        st.markdown("---")
        st.markdown("### 👨‍🏫 Solicitações de Professores (Apoio)")
        for p in lista_pend_profs:
            with st.container(border=True):
                c1, c2, c3 = st.columns([3, 1, 1])
                c1.markdown(f"**{p['nome']}** quer ser professor auxiliar na equipe **{p['equipe']}**")
                
                if c2.button("✅ Aprovar", key=f"ok_prof_{p['id_doc']}"):
                    db.collection('professores').document(p['id_doc']).update({
                        "status_vinculo": "ativo",
                        "pode_aprovar": False, # Padrão: Auxiliar não aprova outros (segurança)
                        "eh_responsavel": False
                    })
                    st.success(f"Professor {p['nome']} aprovado!")
                    st.rerun()
                    
                if c3.button("❌ Rejeitar", key=f"no_prof_{p['id_doc']}"):
                    db.collection('professores').document(p['id_doc']).update({"status_vinculo": "rejeitado"})
                    st.warning("Rejeitado.")
                    st.rerun()

# =========================================
# GESTÃO DE EQUIPES (COM FILTRO DE VISÃO)
# =========================================
def gestao_equipes():
    st.markdown("<h1 style='color:#FFD700;'>🏛️ Gestão de Equipes</h1>", unsafe_allow_html=True)
    db = get_db()
    
    user_logado = st.session_state.usuario
    tipo_logado = str(user_logado.get('tipo', '')).lower()
    is_admin = tipo_logado == 'admin'

    # --- 1. DEFINIR O ESCOPO ---
    allowed_team_ids = [] 
    
    if is_admin:
        allowed_team_ids = None 
    else:
        q1 = db.collection('equipes').where('professor_responsavel_id', '==', user_logado['id']).stream()
        allowed_team_ids = [d.id for d in q1]
        
        q2 = db.collection('professores').where('usuario_id', '==', user_logado['id']).where('status_vinculo', '==', 'ativo').stream()
        for d in q2:
            tid = d.to_dict().get('equipe_id')
            if tid and tid not in allowed_team_ids:
                allowed_team_ids.append(tid)
                
        if not allowed_team_ids:
            st.warning("Você não possui permissão para gerenciar nenhuma equipe.")
            return

    # --- 2. CARREGAR DADOS ---
    equipes_map = {} 
    lista_equipes = [] # (Nome, ID)
    all_equipes = db.collection('equipes').stream()
    
    for doc in all_equipes:
        if allowed_team_ids is None or doc.id in allowed_team_ids:
            d = doc.to_dict()
            equipes_map[doc.id] = d
            lista_equipes.append((d.get('nome', 'Sem Nome'), doc.id))

    allowed_student_ids = set()
    if not is_admin and allowed_team_ids:
        for tid in allowed_team_ids:
            s_query = db.collection('alunos').where('equipe_id', '==', tid).stream()
            for s in s_query:
                allowed_student_ids.add(s.to_dict().get('usuario_id'))

    users_ref = db.collection('usuarios').stream()
    users_map = {} 
    lista_professores_geral = [] 
    lista_alunos_dropdown = []   
    
    for doc in users_ref:
        d = doc.to_dict()
        uid = doc.id
        users_map[uid] = d
        u_tipo = str(d.get('tipo_usuario', '')).lower()
        
        if u_tipo in ['professor', 'admin']:
            lista_professores_geral.append((d.get('nome'), uid))
        elif u_tipo == 'aluno':
            if is_admin:
                lista_alunos_dropdown.append((d.get('nome'), uid))
            elif uid in allowed_student_ids:
                lista_alunos_dropdown.append((d.get('nome'), uid))

    # Busca Professores Pendentes por Equipe (Para a Aba 2)
    pendentes_por_equipe = {}
    q_pend = db.collection('professores').where('status_vinculo', '==', 'pendente').stream()
    for doc in q_pend:
        d = doc.to_dict()
        eid = d.get('equipe_id')
        uid = d.get('usuario_id')
        if eid in equipes_map and uid in users_map:
            if eid not in pendentes_por_equipe:
                pendentes_por_equipe[eid] = []
            nome_prof = users_map[uid].get('nome', 'Desconhecido')
            pendentes_por_equipe[eid].append((nome_prof, doc.id))

    # --- ABAS ---
    aba1, aba2, aba3 = st.tabs(["🏫 Equipes", "👩‍🏫 Professores (Apoio)", "🥋 Alunos"])

    # ABA 1: EQUIPES
    with aba1:
        st.subheader("Gerenciar Equipes")
        with st.expander("➕ Cadastrar Nova Equipe"):
            nome_eq = st.text_input("Nome da equipe:")
            desc_eq = st.text_area("Descrição:")
            prof_opcoes = ["Nenhum"] + [p[0] for p in lista_professores_geral]
            idx_padrao = 0
            if not is_admin:
                try: idx_padrao = [p[1] for p in lista_professores_geral].index(user_logado['id']) + 1
                except: pass
            prof_sel = st.selectbox("Professor Responsável:", prof_opcoes, index=idx_padrao)
            if st.button("Criar Equipe"):
                if nome_eq:
                    prof_resp_id = None
                    if prof_sel != "Nenhum":
                        for nome, uid in lista_professores_geral:
                            if nome == prof_sel: prof_resp_id = uid; break
                    _, new_eq_ref = db.collection('equipes').add({
                        "nome": nome_eq.upper(), "descricao": desc_eq, "professor_responsavel_id": prof_resp_id, "ativo": True
                    })
                    if prof_resp_id:
                        db.collection('professores').add({
                            "usuario_id": prof_resp_id, "equipe_id": new_eq_ref.id,
                            "eh_responsavel": True, "pode_aprovar": True, "status_vinculo": "ativo"
                        })
                    st.success("Equipe criada!"); st.rerun()
                else: st.warning("Nome obrigatório.")
        
        st.markdown("---")
        dados_tabela = []
        for eid, data in equipes_map.items():
            pid = data.get('professor_responsavel_id')
            pnome = users_map.get(pid, {}).get('nome', 'Nenhum') if pid else 'Nenhum'
            dados_tabela.append({"Equipe": data.get('nome'), "Descrição": data.get('descricao'), "Responsável": pnome, "ID": eid})
        if dados_tabela:
            df = pd.DataFrame(dados_tabela)
            st.dataframe(df[['Equipe', 'Descrição', 'Responsável']], use_container_width=True)
            eq_to_edit = st.selectbox("Editar Equipe:", [d['Equipe'] for d in dados_tabela])
            if eq_to_edit:
                item = next(i for i in dados_tabela if i['Equipe'] == eq_to_edit)
                eid = item['ID']
                original = equipes_map[eid]
                with st.form(key=f"form_eq_{eid}"):
                    n_nome = st.text_input("Nome:", value=original.get('nome'))
                    n_desc = st.text_area("Descrição:", value=original.get('descricao'))
                    p_atual = item['Responsável']
                    try: idx_p = prof_opcoes.index(p_atual)
                    except: idx_p = 0
                    n_prof = st.selectbox("Responsável:", prof_opcoes, index=idx_p)
                    c1, c2 = st.columns(2)
                    salvar = c1.form_submit_button("💾 Salvar")
                    excluir = c2.form_submit_button("🗑️ Excluir")
                    if salvar:
                        pid_new = None
                        if n_prof != "Nenhum":
                            for nome, uid in lista_professores_geral:
                                if nome == n_prof: pid_new = uid; break
                        db.collection('equipes').document(eid).update({
                            "nome": n_nome.upper(), "descricao": n_desc, "professor_responsavel_id": pid_new
                        })
                        st.success("Salvo!"); st.rerun()
                    if excluir:
                        db.collection('equipes').document(eid).delete()
                        st.warning("Excluído!"); st.rerun()

    # ----------------------------------------------------------
    # ABA 2: PROFESSORES (Apoio - TOTALMENTE FILTRADO)
    # ----------------------------------------------------------
    with aba2:
        st.subheader("Gerenciar Professores da Equipe")
        
        if not lista_equipes:
            st.warning("Nenhuma equipe encontrada.")
        else:
            # 1. Seletor Principal de Equipe
            e_sel = st.selectbox("Selecione a Equipe:", [e[0] for e in lista_equipes], key="sel_eq_prof_gest")
            eid_sel = next((eid for nome, eid in lista_equipes if nome == e_sel), None)
            
            st.markdown("---")
            
            # 2. Aprovação de Pendentes (FILTRADO PELA EQUIPE SELECIONADA)
            st.markdown("#### ⏳ Aprovar Novos Professores")
            lista_pendentes_dropdown = []
            mapa_pendentes = {}
            
            if eid_sel and eid_sel in pendentes_por_equipe:
                for p_nome, p_doc_id in pendentes_por_equipe[eid_sel]:
                    lista_pendentes_dropdown.append(p_nome)
                    mapa_pendentes[p_nome] = p_doc_id
            
            if not lista_pendentes_dropdown:
                st.info(f"Nenhum professor pendente em {e_sel}.")
            else:
                c1, c2 = st.columns([3, 1])
                p_sel = c1.selectbox("Professor Pendente:", lista_pendentes_dropdown, key="sel_prof_pend")
                if c2.button("✅ Aprovar"):
                    doc_id_vinculo = mapa_pendentes.get(p_sel)
                    if doc_id_vinculo:
                        db.collection('professores').document(doc_id_vinculo).update({
                            "status_vinculo": "ativo",
                            "pode_aprovar": False, 
                            "eh_responsavel": False
                        })
                        st.success(f"Aprovado!"); st.rerun()
            
            st.markdown("---")
            
            # 3. Lista de Ativos (FILTRADO PELA EQUIPE SELECIONADA)
            st.markdown(f"#### ✅ Professores Vinculados a {e_sel}")
            
            vincs_ativos = db.collection('professores')\
                .where('equipe_id', '==', eid_sel)\
                .where('status_vinculo', '==', 'ativo').stream()
            
            lista_ativos = []
            for v in vincs_ativos:
                d = v.to_dict()
                uid = d.get('usuario_id')
                if uid in users_map:
                    nome_p = users_map[uid].get('nome')
                    func = "Responsável" if d.get('eh_responsavel') else "Apoio"
                    lista_ativos.append({"Nome": nome_p, "Função": func, "ID_Doc": v.id, "Eh_Resp": d.get('eh_responsavel')})
            
            if not lista_ativos:
                st.info("Apenas o responsável está vinculado.")
            else:
                c1, c2, c3 = st.columns([3, 2, 2])
                c1.markdown("**Professor**")
                c2.markdown("**Função**")
                c3.markdown("**Ação**")
                
                for item in lista_ativos:
                    c1, c2, c3 = st.columns([3, 2, 2])
                    c1.write(item['Nome'])
                    c2.write(item['Função'])
                    
                    if not item['Eh_Resp']:
                        if c3.button("Desvincular", key=f"del_prof_{item['ID_Doc']}"):
                            db.collection('professores').document(item['ID_Doc']).delete()
                            st.success("Desvinculado!")
                            st.rerun()
                    else:
                        c3.caption("Principal")

    # ABA 3: ALUNOS (Mantida)
    with aba3:
        st.subheader("Alunos da Equipe")
        if not lista_alunos_dropdown:
            st.info("Nenhum aluno encontrado.")
        else:
            a_sel = st.selectbox("Selecione o Aluno:", [a[0] for a in lista_alunos_dropdown])
            eq_aluno_sel = st.selectbox("Mover para Equipe:", [e[0] for e in lista_equipes])
            if st.button("Atualizar Aluno"):
                aid = next(uid for nome, uid in lista_alunos_dropdown if nome == a_sel)
                eid = next(uid for nome, uid in lista_equipes if nome == eq_aluno_sel)
                aluno_docs = list(db.collection('alunos').where('usuario_id', '==', aid).stream())
                if aluno_docs:
                    db.collection('alunos').document(aluno_docs[0].id).update({"equipe_id": eid})
                    st.success(f"Aluno movido!"); st.rerun()
        st.markdown("---")
        alunos_bd = db.collection('alunos').stream()
        lista_a_bd = []
        for doc in alunos_bd:
            d = doc.to_dict()
            if d.get('equipe_id') in equipes_map:
                anome = users_map.get(d.get('usuario_id'), {}).get('nome', '?')
                enome = equipes_map.get(d.get('equipe_id'), {}).get('nome', '?')
                lista_a_bd.append({"Aluno": anome, "Equipe": enome, "Faixa": d.get('faixa_atual')})
            
        if lista_a_bd:
            st.dataframe(pd.DataFrame(lista_a_bd), use_container_width=True)
