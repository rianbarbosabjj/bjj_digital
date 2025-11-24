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
    
    # 1. Descobre quais equipes este professor lidera ou apoia
    # Precisamos buscar na coleção 'professores' onde usuario_id == id_do_logado
    # e o status é 'ativo'
    prof_query = db.collection('professores')\
        .where('usuario_id', '==', user['id'])\
        .where('status_vinculo', '==', 'ativo').stream()
        
    meus_vinculos = list(prof_query)
    
    if not meus_vinculos:
        st.warning("Você não está vinculado a nenhuma equipe como professor ativo.")
        return
    
    # Lista de IDs das equipes que ele gerencia
    equipes_ids = [doc.to_dict().get('equipe_id') for doc in meus_vinculos]
    
    if not equipes_ids:
        st.info("Nenhuma equipe vinculada.")
        return

    # 2. Busca alunos pendentes nessas equipes
    # Nota: O operador 'in' do Firestore suporta até 10 valores.
    # Se tiver mais que 10 equipes, precisaria de lógica extra, mas para este caso serve.
    alunos_pend_ref = db.collection('alunos')\
        .where('equipe_id', 'in', equipes_ids)\
        .where('status_vinculo', '==', 'pendente').stream()
        
    lista_pend = []
    for doc in alunos_pend_ref:
        d = doc.to_dict()
        
        # Busca dados do aluno (Nome)
        # O ideal seria ter o nome desnormalizado no documento do aluno, 
        # mas vamos buscar na coleção usuarios para garantir dados frescos.
        u_snap = db.collection('usuarios').document(d['usuario_id']).get()
        if u_snap.exists:
            nome_aluno = u_snap.to_dict().get('nome', 'Desconhecido')
            
            # Busca nome da equipe
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
                    # Atualiza o status do aluno
                    db.collection('alunos').document(p['id_doc']).update({
                        "status_vinculo": "ativo",
                        "professor_id": user['id'] # Vincula a quem aprovou (opcional)
                    })
                    st.success(f"{p['nome']} aprovado!")
                    st.rerun()
                    
                if c3.button("❌ Rejeitar", key=f"no_{p['id_doc']}"):
                    db.collection('alunos').document(p['id_doc']).update({"status_vinculo": "rejeitado"})
                    st.warning("Rejeitado.")
                    st.rerun()

# =========================================
# GESTÃO DE EQUIPES
# =========================================
def gestao_equipes():
    st.markdown("<h1 style='color:#FFD700;'>🏛️ Gestão de Equipes</h1>", unsafe_allow_html=True)
    db = get_db()

    # --- PREPARAÇÃO DOS DADOS (Cache local para evitar muitas leituras) ---
    # Carrega todos os usuários para mapear ID -> Nome
    users_ref = db.collection('usuarios').stream()
    users_map = {} # {id: {'nome': 'X', 'tipo': 'professor'}}
    
    lista_professores = [] # Para dropdowns
    lista_alunos = []      # Para dropdowns
    
    for doc in users_ref:
        d = doc.to_dict()
        uid = doc.id
        users_map[uid] = d
        if d.get('tipo_usuario') == 'professor' or d.get('tipo_usuario') == 'admin':
            lista_professores.append((d.get('nome'), uid))
        elif d.get('tipo_usuario') == 'aluno':
            lista_alunos.append((d.get('nome'), uid))
            
    # Carrega todas as equipes
    equipes_ref = db.collection('equipes').stream()
    equipes_map = {} # {id: {'nome': 'X', ...}}
    lista_equipes = []
    
    for doc in equipes_ref:
        d = doc.to_dict()
        eid = doc.id
        equipes_map[eid] = d
        lista_equipes.append((d.get('nome'), eid))

    # --- ABAS ---
    aba1, aba2, aba3 = st.tabs(["🏫 Equipes", "👩‍🏫 Professores", "🥋 Alunos"])

    # ----------------------------------------------------------
    # ABA 1: CRIAÇÃO E EDIÇÃO DE EQUIPES
    # ----------------------------------------------------------
    with aba1:
        st.subheader("Cadastrar nova equipe")
        nome_eq = st.text_input("Nome da equipe:")
        desc_eq = st.text_area("Descrição:")
        
        # Selectbox de professor responsável
        prof_opcoes = ["Nenhum"] + [p[0] for p in lista_professores]
        prof_sel = st.selectbox("Professor Responsável:", prof_opcoes)
        
        if st.button("➕ Criar Equipe"):
            if nome_eq:
                # Resolve ID do professor
                prof_resp_id = None
                if prof_sel != "Nenhum":
                    # Busca o ID baseado no nome selecionado
                    for nome, uid in lista_professores:
                        if nome == prof_sel:
                            prof_resp_id = uid
                            break
                
                # Cria equipe
                _, new_eq_ref = db.collection('equipes').add({
                    "nome": nome_eq,
                    "descricao": desc_eq,
                    "professor_responsavel_id": prof_resp_id,
                    "ativo": True
                })
                
                # Se tem responsável, cria vínculo na tabela professores também
                if prof_resp_id:
                    db.collection('professores').add({
                        "usuario_id": prof_resp_id,
                        "equipe_id": new_eq_ref.id,
                        "eh_responsavel": True,
                        "pode_aprovar": True,
                        "status_vinculo": "ativo"
                    })
                    
                st.success(f"Equipe '{nome_eq}' criada!")
                st.rerun()
            else:
                st.warning("Nome obrigatório.")

        st.markdown("---")
        st.subheader("Equipes Existentes")
        
        # Monta tabela para exibição
        dados_tabela = []
        for eid, data in equipes_map.items():
            pid = data.get('professor_responsavel_id')
            pnome = users_map.get(pid, {}).get('nome', 'Nenhum') if pid else 'Nenhum'
            dados_tabela.append({
                "Equipe": data.get('nome'),
                "Descrição": data.get('descricao'),
                "Responsável": pnome,
                "ID_Equipe": eid # Escondido no dataframe se quiser, mas útil para lógica
            })
            
        if dados_tabela:
            df = pd.DataFrame(dados_tabela)
            st.dataframe(df[['Equipe', 'Descrição', 'Responsável']], use_container_width=True)
            
            # Edição / Exclusão
            st.markdown("### Gerenciar Equipe")
            eq_to_edit = st.selectbox("Selecione para editar:", [d['Equipe'] for d in dados_tabela])
            
            if eq_to_edit:
                # Recupera dados originais
                item = next(i for i in dados_tabela if i['Equipe'] == eq_to_edit)
                eid = item['ID_Equipe']
                original = equipes_map[eid]
                
                with st.expander(f"Editar {eq_to_edit}", expanded=True):
                    n_nome = st.text_input("Novo nome:", value=original.get('nome'))
                    n_desc = st.text_area("Nova descrição:", value=original.get('descricao'))
                    
                    # Recupera índice do prof atual
                    p_atual = item['Responsável']
                    try: idx_p = prof_opcoes.index(p_atual)
                    except: idx_p = 0
                    n_prof = st.selectbox("Novo Responsável:", prof_opcoes, index=idx_p, key="edit_prof_resp")
                    
                    c1, c2 = st.columns(2)
                    if c1.button("💾 Salvar"):
                        # Resolve ID
                        pid_new = None
                        if n_prof != "Nenhum":
                            for nome, uid in lista_professores:
                                if nome == n_prof: 
                                    pid_new = uid; break
                        
                        db.collection('equipes').document(eid).update({
                            "nome": n_nome, "descricao": n_desc, "professor_responsavel_id": pid_new
                        })
                        st.success("Atualizado!")
                        st.rerun()
                        
                    if c2.button("🗑️ Excluir"):
                        db.collection('equipes').document(eid).delete()
                        st.warning("Excluído.")
                        st.rerun()

    # ----------------------------------------------------------
    # ABA 2: PROFESSORES (Apoio)
    # ----------------------------------------------------------
    with aba2:
        st.subheader("Vincular Professor de Apoio")
        
        c1, c2 = st.columns(2)
        p_sel = c1.selectbox("Professor:", [p[0] for p in lista_professores], key="sel_prof_apoio")
        e_sel = c2.selectbox("Equipe:", [e[0] for e in lista_equipes], key="sel_eq_apoio")
        
        if st.button("📎 Vincular"):
            pid = next(uid for nome, uid in lista_professores if nome == p_sel)
            eid = next(uid for nome, uid in lista_equipes if nome == e_sel)
            
            # Verifica se já existe
            exists = list(db.collection('professores')
                          .where('usuario_id', '==', pid)
                          .where('equipe_id', '==', eid).stream())
            
            if exists:
                st.warning("Vínculo já existe.")
            else:
                db.collection('professores').add({
                    "usuario_id": pid, "equipe_id": eid, 
                    "pode_aprovar": False, "eh_responsavel": False, 
                    "status_vinculo": "ativo"
                })
                st.success("Vinculado!")
                st.rerun()
        
        st.markdown("---")
        st.subheader("Professores Vinculados")
        # Lista todos os vínculos
        vincs = db.collection('professores').stream()
        lista_v = []
        for v in vincs:
            d = v.to_dict()
            pn = users_map.get(d.get('usuario_id'), {}).get('nome', '?')
            en = equipes_map.get(d.get('equipe_id'), {}).get('nome', '?')
            lista_v.append({"Professor": pn, "Equipe": en, "Status": d.get('status_vinculo')})
            
        if lista_v:
            st.dataframe(pd.DataFrame(lista_v), use_container_width=True)

    # ----------------------------------------------------------
    # ABA 3: ALUNOS
    # ----------------------------------------------------------
    with aba3:
        st.subheader("Gerenciar Vínculo de Aluno")
        
        a_sel = st.selectbox("Aluno:", [a[0] for a in lista_alunos], key="sel_aluno_gest")
        eq_aluno_sel = st.selectbox("Nova Equipe:", [e[0] for e in lista_equipes], key="sel_eq_aluno")
        
        if st.button("Atualizar Vínculo do Aluno"):
            aid = next(uid for nome, uid in lista_alunos if nome == a_sel)
            eid = next(uid for nome, uid in lista_equipes if nome == eq_aluno_sel)
            
            # Verifica se aluno já tem registro na coleção 'alunos'
            aluno_docs = list(db.collection('alunos').where('usuario_id', '==', aid).stream())
            
            if aluno_docs:
                # Update no primeiro encontrado
                doc_id = aluno_docs[0].id
                db.collection('alunos').document(doc_id).update({
                    "equipe_id": eid,
                    "status_vinculo": "ativo" # Força ativo pois foi o admin/prof que mudou
                })
                st.success(f"Aluno {a_sel} movido para {eq_aluno_sel}.")
            else:
                # Cria novo
                db.collection('alunos').add({
                    "usuario_id": aid,
                    "equipe_id": eid,
                    "faixa_atual": "Branca", # Default
                    "status_vinculo": "ativo"
                })
                st.success(f"Aluno {a_sel} vinculado a {eq_aluno_sel}.")
            st.rerun()

        st.markdown("---")
        st.subheader("Alunos Vinculados")
        
        # Busca alunos
        alunos_bd = db.collection('alunos').stream()
        lista_a_bd = []
        for doc in alunos_bd:
            d = doc.to_dict()
            anome = users_map.get(d.get('usuario_id'), {}).get('nome', '?')
            enome = equipes_map.get(d.get('equipe_id'), {}).get('nome', '?')
            lista_a_bd.append({"Aluno": anome, "Equipe": enome, "Status": d.get('status_vinculo')})
            
        if lista_a_bd:
            st.dataframe(pd.DataFrame(lista_a_bd), use_container_width=True)
