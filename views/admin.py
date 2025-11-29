import streamlit as st
import pandas as pd
import bcrypt
from datetime import datetime, time
from database import get_db
from firebase_admin import firestore

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
            "faixa_atual": d.get('faixa_atual', 'Branca'),
            "cep": d.get('cep', ''),
            "logradouro": d.get('logradouro', ''),
            "numero": d.get('numero', ''),
            "complemento": d.get('complemento', ''),
            "bairro": d.get('bairro', ''),
            "cidade": d.get('cidade', ''),
            "uf": d.get('uf', '')
        }
        lista_users.append(user_safe)
        
    if not lista_users:
        st.warning("Nenhum usuário encontrado.")
        return

    filtro = st.text_input("🔍 Buscar por Nome, Email ou CPF:")
    df = pd.DataFrame(lista_users)
    
    if filtro:
        f = filtro.upper()
        df = df[
            df['nome'].str.upper().str.contains(f) | 
            df['email'].str.upper().str.contains(f) | 
            df['cpf'].str.contains(f)
        ]

    st.dataframe(
        df[['nome', 'email', 'tipo_usuario', 'faixa_atual']], 
        use_container_width=True,
        hide_index=True
    )
    
    st.markdown("---")

    st.subheader("🛠️ Editar ou Excluir Usuário")
    opcoes_usuarios = df.to_dict('records')
    usuario_selecionado = st.selectbox("Selecione o usuário:", opcoes_usuarios, format_func=lambda x: f"{x['nome']} ({x['email']})")
    
    if usuario_selecionado:
        with st.expander(f"✏️ Editar dados de {usuario_selecionado['nome']}", expanded=False):
            with st.form(key=f"edit_full_{usuario_selecionado['id']}"):
                st.markdown("##### 👤 Dados Pessoais")
                c1, c2 = st.columns(2)
                novo_nome = c1.text_input("Nome:", value=usuario_selecionado['nome'])
                novo_email = c2.text_input("E-mail:", value=usuario_selecionado['email'])
                c3, c4 = st.columns(2)
                novo_cpf = c3.text_input("CPF:", value=usuario_selecionado['cpf'])
                
                tipos = ["aluno", "professor", "admin"]
                idx_t = tipos.index(usuario_selecionado['tipo_usuario']) if usuario_selecionado['tipo_usuario'] in tipos else 0
                novo_tipo = c4.selectbox("Perfil:", tipos, index=idx_t)

                idx_f = FAIXAS_COMPLETAS.index(usuario_selecionado['faixa_atual']) if usuario_selecionado['faixa_atual'] in FAIXAS_COMPLETAS else 0
                novo_faixa = st.selectbox("Faixa Atual:", FAIXAS_COMPLETAS, index=idx_f)
                
                st.markdown("---")
                st.markdown("##### 🔐 Alterar Senha")
                nova_senha_admin = st.text_input("Nova Senha:", type="password", help="Preencha apenas se quiser alterar.")
                
                st.markdown("---")
                st.markdown("##### 🏠 Endereço")
                e1, e2 = st.columns([1, 3])
                novo_cep = e1.text_input("CEP:", value=usuario_selecionado['cep'])
                novo_logr = e2.text_input("Logradouro:", value=usuario_selecionado['logradouro'])
                
                if st.form_submit_button("💾 SALVAR ALTERAÇÕES", type="primary", use_container_width=True):
                    try:
                        dados_update = {
                            "nome": novo_nome.upper(),
                            "email": novo_email.lower().strip(),
                            "cpf": novo_cpf,
                            "tipo_usuario": novo_tipo,
                            "faixa_atual": novo_faixa,
                            "cep": novo_cep,
                            "logradouro": novo_logr.upper()
                        }
                        if nova_senha_admin:
                            hashed = bcrypt.hashpw(nova_senha_admin.encode(), bcrypt.gensalt()).decode()
                            dados_update["senha"] = hashed
                            dados_update["precisa_trocar_senha"] = True
                            st.info("Senha alterada!")
                        db.collection('usuarios').document(usuario_selecionado['id']).update(dados_update)
                        st.success("Atualizado com sucesso!")
                        st.rerun()
                    except Exception as e: st.error(f"Erro: {e}")

        st.write("")
        with st.container(border=True):
            c_aviso, c_botao = st.columns([3, 1])
            c_aviso.warning(f"Deseja excluir **{usuario_selecionado['nome']}** permanentemente?")
            if c_botao.button("🗑️ EXCLUIR", key=f"del_u_{usuario_selecionado['id']}", type="primary"):
                db.collection('usuarios').document(usuario_selecionado['id']).delete()
                st.toast("Usuário excluído.")
                st.rerun()

# =========================================
# 2. GESTÃO DE QUESTÕES
# =========================================
def gestao_questoes():
    st.markdown("<h1 style='color:#FFD700;'>🧠 Banco de Questões</h1>", unsafe_allow_html=True)
    
    user = st.session_state.usuario
    tipo_user = str(user.get("tipo", "")).lower()
    
    if tipo_user not in ["admin", "professor"]:
        st.error("Acesso negado.")
        return
        
    db = get_db()
    docs_q = list(db.collection('questoes').stream())
    aprovadas = []; pendentes = []; edicoes = []; temas_set = set()

    for doc in docs_q:
        d = doc.to_dict(); d['id'] = doc.id
        status = d.get('status', 'aprovada')
        if status == 'pendente': pendentes.append(d)
        elif status == 'pendente_edicao': edicoes.append(d)
        else: aprovadas.append(d); temas_set.add(d.get('tema', 'Geral'))

    temas_existentes = sorted(list(temas_set))
    titulos = ["📚 Listar Questões", "➕ Nova Questão"]
    if tipo_user == "admin": titulos.append(f"✅ Aprovar ({len(pendentes)+len(edicoes)})")
    
    abas = st.tabs(titulos)
    
    faixas_questoes = ["Geral"] + FAIXAS_COMPLETAS

    # ABA 1: LISTAR
    with abas[0]:
        ft = st.selectbox("Filtrar por Tema:", ["Todos"] + temas_existentes)
        qx = [q for q in aprovadas if q.get('tema') == ft] if ft != "Todos" else aprovadas
        
        if not qx: st.info("Nenhuma questão encontrada.")
        else:
            st.write(f"Total: {len(qx)} questões")
            for q in qx:
                with st.container(border=True):
                    c_txt, c_btn = st.columns([5, 1])
                    c_txt.markdown(f"**[{q.get('tema')}]** {q.get('pergunta')}")
                    c_txt.caption(f"Faixa: {q.get('faixa', 'Geral')} | Autor: {q.get('criado_por')}")
                    
                    if c_btn.button("✏️", key=f"edit_btn_{q['id']}"): st.session_state[f"editing_{q['id']}"] = True
                    
                    if st.session_state.get(f"editing_{q['id']}"):
                        with st.form(key=f"form_edit_{q['id']}"):
                            st.markdown("#### ✏️ Editando")
                            e_tema = st.text_input("Tema:", value=q.get('tema'))
                            e_perg = st.text_area("Pergunta:", value=q.get('pergunta'))
                            
                            idx_fq = faixas_questoes.index(q.get('faixa', 'Geral')) if q.get('faixa', 'Geral') in faixas_questoes else 0
                            e_faixa = st.selectbox("Faixa:", faixas_questoes, index=idx_fq)
                            
                            ops = q.get('opcoes', ["","","",""])
                            while len(ops) < 4: ops.append("")
                            c1, c2 = st.columns(2)
                            e_op1 = c1.text_input("A)", value=ops[0])
                            e_op2 = c2.text_input("B)", value=ops[1])
                            e_op3 = c1.text_input("C)", value=ops[2])
                            e_op4 = c2.text_input("D)", value=ops[3])
                            
                            map_inv = {ops[0]:"A", ops[1]:"B", ops[2]:"C", ops[3]:"D"}
                            try: idx_corr = ["A","B","C","D"].index(map_inv.get(q.get('resposta'), "A"))
                            except: idx_corr = 0
                            e_correta = st.selectbox("Correta:", ["A","B","C","D"], index=idx_corr)
                            
                            justificativa = ""
                            if tipo_user != "admin": justificativa = st.text_area("Justificativa:")
                            
                            c_s, c_c = st.columns(2)
                            if c_s.form_submit_button("Salvar"):
                                ops_new = [e_op1, e_op2, e_op3, e_op4]
                                map_new = {"A": e_op1, "B": e_op2, "C": e_op3, "D": e_op4}
                                novos_dados = {
                                    "tema": e_tema, "faixa": e_faixa, "pergunta": e_perg,
                                    "opcoes": [o for o in ops_new if o.strip()],
                                    "resposta": map_new[e_correta], "correta": map_new[e_correta],
                                    "editado_por": user['nome'], "data_edicao": firestore.SERVER_TIMESTAMP
                                }
                                if tipo_user == "admin":
                                    db.collection('questoes').document(q['id']).update(novos_dados)
                                    st.success("Atualizado!")
                                else:
                                    if not justificativa: st.warning("Justifique.")
                                    else:
                                        novos_dados.update({"status": "pendente_edicao", "id_original": q['id'], "justificativa": justificativa})
                                        db.collection('questoes').add(novos_dados)
                                        st.info("Enviado para aprovação.")
                                del st.session_state[f"editing_{q['id']}"]; st.rerun()
                            if c_c.form_submit_button("Cancelar"):
                                del st.session_state[f"editing_{q['id']}"]; st.rerun()

                    with st.expander("Ver Detalhes"):
                        st.write(f"Opções: {q.get('opcoes')}")
                        st.success(f"Resposta: {q.get('resposta')}")
                        if tipo_user == "admin":
                            if st.button("🗑️ Excluir", key=f"del_q_{q['id']}"):
                                db.collection('questoes').document(q['id']).delete(); st.rerun()

    # ABA 2: CRIAR
    with abas[1]:
        st.subheader("Adicionar Nova Questão")
        with st.form("new_q"):
            c1, c2 = st.columns(2)
            tema = c1.text_input("Tema:")
            faixa = c2.selectbox("Faixa Alvo:", faixas_questoes)
            perg = st.text_area("Pergunta:")
            st.write("Alternativas:")
            c_op1, c_op2 = st.columns(2)
            op1 = c_op1.text_input("A)")
            op2 = c_op2.text_input("B)")
            c_op3, c_op4 = st.columns(2)
            op3 = c_op3.text_input("C)")
            op4 = c_op4.text_input("D)")
            resp_letra = st.selectbox("Correta:", ["A", "B", "C", "D"])
            
            if st.form_submit_button("💾 Salvar"):
                ops = [op1, op2, op3, op4]
                limpas = [o for o in ops if o.strip()]
                if len(limpas) < 2 or not tema or not perg: st.warning("Preencha corretamente.")
                else:
                    mapa = {"A": op1, "B": op2, "C": op3, "D": op4}
                    st_init = "aprovada" if tipo_user == "admin" else "pendente"
                    db.collection('questoes').add({
                        "tema": tema, "faixa": faixa, "pergunta": perg,
                        "opcoes": limpas, "resposta": mapa[resp_letra], "correta": mapa[resp_letra],
                        "status": st_init, "criado_por": user['nome'], "data": firestore.SERVER_TIMESTAMP
                    })
                    st.success("Salvo!"); st.rerun()

    # ABA 3: APROVAR
    if tipo_user == "admin" and len(abas) > 2:
        with abas[2]:
            if not pendentes and not edicoes: st.success("Nada pendente.")
            
            if pendentes:
                st.markdown("#### 🆕 Novas Questões")
                for q in pendentes:
                    with st.container(border=True):
                        st.markdown(f"**[{q.get('tema')}]** {q['pergunta']}")
                        st.caption(f"Por: {q.get('criado_por')}")
                        c1, c2 = st.columns(2)
                        if c1.button("✅ Aprovar", key=f"ok_{q['id']}"):
                            db.collection('questoes').document(q['id']).update({"status":"aprovada"}); st.rerun()
                        if c2.button("❌ Rejeitar", key=f"no_{q['id']}"):
                            db.collection('questoes').document(q['id']).delete(); st.rerun()
            
            if edicoes:
                st.markdown("#### ✏️ Edições")
                for ed in edicoes:
                    with st.container(border=True):
                        st.info(f"Justif: {ed.get('justificativa')}")
                        st.markdown(f"**Nova:** {ed.get('pergunta')}")
                        id_orig = ed.get('id_original')
                        c1, c2 = st.columns(2)
                        if c1.button("✅ Aceitar", key=f"ok_ed_{ed['id']}"):
                            dados = ed.copy(); dados.pop('id'); dados.pop('status'); dados.pop('id_original'); dados.pop('justificativa')
                            dados['status'] = 'aprovada'
                            db.collection('questoes').document(id_orig).update(dados)
                            db.collection('questoes').document(ed['id']).delete()
                            st.success("Editado!"); st.rerun()
                        if c2.button("❌ Rejeitar", key=f"no_ed_{ed['id']}"):
                            db.collection('questoes').document(ed['id']).delete(); st.rerun()

# =========================================
# 3. GESTÃO DE EXAME
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
