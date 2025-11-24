import streamlit as st
import pandas as pd
from database import get_db
from firebase_admin import firestore

# =========================================
# PAINEL DO PROFESSOR (Aprovações)
# =========================================
def painel_professor():
    st.markdown("<h1 style='color:#FFD700;'>👩‍🏫 Painel do Professor</h1>", unsafe_allow_html=True)
    db = get_db()
    user = st.session_state.usuario
    
    # 1. Descobre equipes vinculadas
    prof_query = db.collection('professores')\
        .where('usuario_id', '==', user['id'])\
        .where('status_vinculo', '==', 'ativo').stream()
        
    meus_vinculos = list(prof_query)
    
    if not meus_vinculos:
        st.warning("Você não está vinculado a nenhuma equipe como professor ativo.")
        return
    
    equipes_ids = [doc.to_dict().get('equipe_id') for doc in meus_vinculos]
    
    if not equipes_ids:
        st.info("Nenhuma equipe vinculada.")
        return

    # 2. Busca alunos pendentes
    # (Firestore 'in' aceita max 10. Se tiver mais, precisaria de loop, mas ok pro MVP)
    alunos_pend_ref = db.collection('alunos')\
        .where('equipe_id', 'in', equipes_ids[:10])\
        .where('status_vinculo', '==', 'pendente').stream()
        
    lista_pend = []
    for doc in alunos_pend_ref:
        d = doc.to_dict()
        
        u_snap = db.collection('usuarios').document(d['usuario_id']).get()
        if u_snap.exists:
            nome_aluno = u_snap.to_dict().get('nome', 'Desconhecido')
            
            eq_snap = db.collection('equipes').document(d['equipe_id']).get()
            nome_equipe = eq_snap.to_dict().get('nome', '?') if eq_snap.exists else '?'
            
            lista_pend.append({
                "id_doc": doc.id,
                "nome": nome_aluno,
                "equipe": nome_equipe,
                "faixa": d.get('faixa_atual')
            })
            
    if not lista_pend:
        st.info("Nenhuma solicitação pendente nas suas equipes.")
    else:
        st.markdown("### 🔔 Solicitações de Vínculo")
        for p in lista_pend:
            with st.container(border=True):
                c1, c2, c3 = st.columns([3, 1, 1])
                c1.markdown(f"**{p['nome']}** quer entrar na equipe **{p['equipe']}** (Faixa: {p['faixa']})")
                
                if c2.button("✅ Aprovar", key=f"ok_{p['id_doc']}"):
                    db.collection('alunos').document(p['id_doc']).update({
                        "status_vinculo": "ativo",
                        "professor_id": user['id']
                    })
                    st.success(f"{p['nome']} aprovado!")
                    st.rerun()
                    
                if c3.button("❌ Rejeitar", key=f"no_{p['id_doc']}"):
                    db.collection('alunos').document(p['id_doc']).update({"status_vinculo": "rejeitado"})
                    st.warning("Rejeitado.")
                    st.rerun()

# =========================================
# GESTÃO DE EQUIPES (COM FILTRO DE VISÃO)
# =========================================
def gestao_equipes():
    st.markdown("<h1 style='color:#FFD700;'>🏛️ Gestão de Equipes</h1>", unsafe_allow_html=True)
    db = get_db()
    
    user_logado = st.session_state.usuario
    # Normaliza o tipo para minúsculo para garantir
    tipo_logado = str(user_logado.get('tipo', '')).lower()
    is_admin = tipo_logado == 'admin'

    # --- 1. DEFINIR O ESCOPO (QUAIS EQUIPES POSSO VER?) ---
    allowed_team_ids = [] # Se None, vê tudo
    
    if is_admin:
        allowed_team_ids = None 
    else:
        # Professor: Vê onde é responsável
        q1 = db.collection('equipes').where('professor_responsavel_id', '==', user_logado['id']).stream()
        allowed_team_ids = [d.id for d in q1]
        
        # E vê onde é vinculado como professor
        q2 = db.collection('professores').where('usuario_id', '==', user_logado['id']).where('status_vinculo', '==', 'ativo').stream()
        for d in q2:
            tid = d.to_dict().get('equipe_id')
            if tid and tid not in allowed_team_ids:
                allowed_team_ids.append(tid)
                
        if not allowed_team_ids:
            st.warning("Você não possui permissão para gerenciar nenhuma equipe.")
            return

    # --- 2. CARREGAR DADOS FILTRADOS ---
    
    # Carrega Equipes Permitidas
    equipes_map = {} 
    lista_equipes = []
    
    # Se for admin, busca tudo. Se não, busca filtrado (ou filtra em memória se a lista for pequena)
    # Firestore não tem "where id in [...]" para muitos IDs, então vamos buscar tudo e filtrar no Python 
    # (para bases pequenas/médias é ok).
    all_equipes = db.collection('equipes').stream()
    
    for doc in all_equipes:
        if allowed_team_ids is None or doc.id in allowed_team_ids:
            d = doc.to_dict()
            equipes_map[doc.id] = d
            lista_equipes.append((d.get('nome', 'Sem Nome'), doc.id))

    # Descobre quais alunos pertencem a essas equipes (Para filtrar o dropdown de alunos)
    allowed_student_ids = set()
    if not is_admin and allowed_team_ids:
        # Busca alunos vinculados às equipes permitidas
        # Limitado a 10 no 'in'. Se o prof tiver >10 equipes, ideal fazer em batches.
        # Simplificação: Vamos iterar as equipes permitidas.
        for tid in allowed_team_ids:
            s_query = db.collection('alunos').where('equipe_id', '==', tid).stream()
            for s in s_query:
                allowed_student_ids.add(s.to_dict().get('usuario_id'))

    # Carrega Usuários (Mapeamento ID -> Nome e Listas para Dropdown)
    users_ref = db.collection('usuarios').stream()
    users_map = {} 
    lista_professores = [] 
    lista_alunos_dropdown = []      
    
    for doc in users_ref:
        d = doc.to_dict()
        uid = doc.id
        users_map[uid] = d
        u_tipo = str(d.get('tipo_usuario', '')).lower()
        
        # Professores: Admin vê todos, Prof vê todos (para poder adicionar colegas de apoio)
        if u_tipo in ['professor', 'admin']:
            lista_professores.append((d.get('nome'), uid))
            
        # Alunos: Admin vê todos, Prof só vê os das suas equipes
        elif u_tipo == 'aluno':
            if is_admin:
                lista_alunos_dropdown.append((d.get('nome'), uid))
            elif uid in allowed_student_ids:
                lista_alunos_dropdown.append((d.get('nome'), uid))

    # --- ABAS ---
    aba1, aba2, aba3 = st.tabs(["🏫 Equipes", "👩‍🏫 Professores", "🥋 Alunos"])

    # ----------------------------------------------------------
    # ABA 1: EQUIPES
    # ----------------------------------------------------------
    with aba1:
        st.subheader("Gerenciar Equipes")
        
        # Só Admin cria equipe ou Prof Responsável pode criar? 
        # Geralmente só Admin cria, ou Prof cria a sua. Vamos deixar liberado.
        with st.expander("➕ Cadastrar Nova Equipe"):
            nome_eq = st.text_input("Nome da equipe:")
            desc_eq = st.text_area("Descrição:")
            prof_opcoes = ["Nenhum"] + [p[0] for p in lista_professores]
            
            # Se for prof criando, já vem pré-selecionado ele mesmo
            idx_padrao = 0
            if not is_admin:
                try: idx_padrao = [p[1] for p in lista_professores].index(user_logado['id']) + 1
                except: pass
            
            prof_sel = st.selectbox("Professor Responsável:", prof_opcoes, index=idx_padrao)
            
            if st.button("Criar Equipe"):
                if nome_eq:
                    prof_resp_id = None
                    if prof_sel != "Nenhum":
                        for nome, uid in lista_professores:
                            if nome == prof_sel: prof_resp_id = uid; break
                    
                    _, new_eq_ref = db.collection('equipes').add({
                        "nome": nome_eq.upper(),
                        "descricao": desc_eq,
                        "professor_responsavel_id": prof_resp_id,
                        "ativo": True
                    })
                    
                    if prof_resp_id:
                        db.collection('professores').add({
                            "usuario_id": prof_resp_id,
                            "equipe_id": new_eq_ref.id,
                            "eh_responsavel": True, "pode_aprovar": True, "status_vinculo": "ativo"
                        })
                    st.success("Equipe criada!"); st.rerun()
                else: st.warning("Nome obrigatório.")

        st.markdown("---")
        
        # Tabela
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
                            for nome, uid in lista_professores:
                                if nome == n_prof: pid_new = uid; break
                        db.collection('equipes').document(eid).update({
                            "nome": n_nome.upper(), "descricao": n_desc, "professor_responsavel_id": pid_new
                        })
                        st.success("Salvo!"); st.rerun()
                        
                    if excluir:
                        db.collection('equipes').document(eid).delete()
                        st.warning("Excluído!"); st.rerun()

    # ----------------------------------------------------------
    # ABA 2: PROFESSORES
    # ----------------------------------------------------------
    with aba2:
        st.subheader("Equipe Técnica (Professores)")
        c1, c2 = st.columns(2)
        p_sel = c1.selectbox("Professor:", [p[0] for p in lista_professores])
        e_sel = c2.selectbox("Vincular à Equipe:", [e[0] for e in lista_equipes])
        
        if st.button("Vincular Professor"):
            pid = next(uid for nome, uid in lista_professores if nome == p_sel)
            eid = next(uid for nome, uid in lista_equipes if nome == e_sel)
            
            # Check duplicidade
            exists = list(db.collection('professores').where('usuario_id','==',pid).where('equipe_id','==',eid).stream())
            if exists: st.warning("Já vinculado.")
            else:
                db.collection('professores').add({
                    "usuario_id": pid, "equipe_id": eid, 
                    "pode_aprovar": False, "eh_responsavel": False, "status_vinculo": "ativo"
                })
                st.success("Vinculado!"); st.rerun()
        
        st.markdown("---")
        # Lista apenas professores das equipes permitidas
        vincs = db.collection('professores').stream()
        lista_v = []
        for v in vincs:
            d = v.to_dict()
            if d.get('equipe_id') in equipes_map: # Filtro de segurança
                pn = users_map.get(d.get('usuario_id'), {}).get('nome', '?')
                en = equipes_map.get(d.get('equipe_id'), {}).get('nome', '?')
                lista_v.append({"Professor": pn, "Equipe": en, "Função": "Responsável" if d.get('eh_responsavel') else "Apoio"})
        st.dataframe(pd.DataFrame(lista_v), use_container_width=True)

    # ----------------------------------------------------------
    # ABA 3: ALUNOS (FILTRADA)
    # ----------------------------------------------------------
    with aba3:
        st.subheader("Alunos da Equipe")
        
        if not lista_alunos_dropdown:
            st.info("Nenhum aluno encontrado nas suas equipes.")
        else:
            # Mostra apenas alunos que o professor TEM PERMISSÃO de ver
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
        # Lista geral filtrada
        alunos_bd = db.collection('alunos').stream()
        lista_a_bd = []
        for doc in alunos_bd:
            d = doc.to_dict()
            # Filtro Mágico: Só mostra se a equipe estiver na lista de permitidas
            if d.get('equipe_id') in equipes_map:
                anome = users_map.get(d.get('usuario_id'), {}).get('nome', '?')
                enome = equipes_map.get(d.get('equipe_id'), {}).get('nome', '?')
                lista_a_bd.append({"Aluno": anome, "Equipe": enome, "Faixa": d.get('faixa_atual')})
            
        if lista_a_bd:
            st.dataframe(pd.DataFrame(lista_a_bd), use_container_width=True)
