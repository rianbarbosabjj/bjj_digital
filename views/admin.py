import streamlit as st
import pandas as pd
import bcrypt
import random
from datetime import datetime, time
import time as time_lib  # CORREÇÃO: Renomeado para evitar conflito com o 'time' do datetime
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
            df['nome'].str.upper().str.contains(f, na=False) | 
            df['email'].str.upper().str.contains(f, na=False) | 
            df['cpf'].str.contains(f, na=False)
        ]

    st.dataframe(
        df[['nome', 'email', 'tipo_usuario', 'faixa_atual']], 
        use_container_width=True,
        hide_index=True
    )
    
    st.markdown("---")

    st.subheader("🛠️ Editar ou Excluir Usuário")
    if df.empty:
        st.warning("Nenhum usuário encontrado para editar.")
        return
        
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
                novo_numero = st.text_input("Número:", value=usuario_selecionado.get('numero', ''))
                novo_complemento = st.text_input("Complemento:", value=usuario_selecionado.get('complemento', ''))
                e3, e4, e5 = st.columns(3)
                novo_bairro = e3.text_input("Bairro:", value=usuario_selecionado.get('bairro', ''))
                novo_cidade = e4.text_input("Cidade:", value=usuario_selecionado.get('cidade', ''))
                novo_uf = e5.text_input("UF:", value=usuario_selecionado.get('uf', ''))
                
                if st.form_submit_button("💾 SALVAR ALTERAÇÕES", type="primary", use_container_width=True):
                    try:
                        dados_update = {
                            "nome": novo_nome.upper(),
                            "email": novo_email.lower().strip(),
                            "cpf": novo_cpf,
                            "tipo_usuario": novo_tipo,
                            "faixa_atual": novo_faixa,
                            "cep": novo_cep,
                            "logradouro": novo_logr.upper(),
                            "numero": novo_numero,
                            "complemento": novo_complemento,
                            "bairro": novo_bairro.upper(),
                            "cidade": novo_cidade.upper(),
                            "uf": novo_uf.upper()
                        }
                        if nova_senha_admin:
                            hashed = bcrypt.hashpw(nova_senha_admin.encode(), bcrypt.gensalt()).decode()
                            dados_update["senha"] = hashed
                            dados_update["precisa_trocar_senha"] = True
                            st.info("Senha alterada!")
                        db.collection('usuarios').document(usuario_selecionado['id']).update(dados_update)
                        st.success("Atualizado com sucesso!")
                        st.rerun()
                    except Exception as e: 
                        st.error(f"Erro: {e}")

        st.write("")
        with st.container(border=True):
            c_aviso, c_botao = st.columns([3, 1])
            c_aviso.warning(f"Deseja excluir **{usuario_selecionado['nome']}** permanentemente?")
            if c_botao.button("🗑️ EXCLUIR", key=f"del_u_{usuario_selecionado['id']}", type="primary"):
                try:
                    db.collection('usuarios').document(usuario_selecionado['id']).delete()
                    st.toast("Usuário excluído.")
                    st.rerun()
                except Exception as e:
                    st.error(f"Erro ao excluir usuário: {e}")

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
        ft = st.selectbox("Filtrar por Tema:", ["Todos"] + temas_existentes, key="filtro_tema")
        qx = [q for q in aprovadas if q.get('tema') == ft] if ft != "Todos" else aprovadas
        
        if not qx: 
            st.info("Nenhuma questão encontrada.")
        else:
            st.write(f"Total: {len(qx)} questões")
            for q in qx:
                with st.container(border=True):
                    c_txt, c_btn = st.columns([5, 1])
                    c_txt.markdown(f"**[{q.get('tema')}]** {q.get('pergunta')}")
                    c_txt.caption(f"Faixa: {q.get('faixa', 'Geral')} | Autor: {q.get('criado_por')}")
                    
                    if c_btn.button("✏️", key=f"edit_btn_{q['id']}"): 
                        st.session_state[f"editing_{q['id']}"] = True
                    
                    if st.session_state.get(f"editing_{q['id']}"):
                        with st.form(key=f"form_edit_{q['id']}"):
                            st.markdown("#### ✏️ Editando")
                            e_tema = st.text_input("Tema:", value=q.get('tema'), key=f"tema_{q['id']}")
                            e_perg = st.text_area("Pergunta:", value=q.get('pergunta'), key=f"perg_{q['id']}")
                            
                            idx_fq = faixas_questoes.index(q.get('faixa', 'Geral')) if q.get('faixa', 'Geral') in faixas_questoes else 0
                            e_faixa = st.selectbox("Faixa:", faixas_questoes, index=idx_fq, key=f"faixa_{q['id']}")
                            
                            ops = q.get('opcoes', ["","","",""])
                            while len(ops) < 4: ops.append("")
                            c1, c2 = st.columns(2)
                            e_op1 = c1.text_input("A)", value=ops[0], key=f"op1_{q['id']}")
                            e_op2 = c2.text_input("B)", value=ops[1], key=f"op2_{q['id']}")
                            e_op3 = c1.text_input("C)", value=ops[2], key=f"op3_{q['id']}")
                            e_op4 = c2.text_input("D)", value=ops[3], key=f"op4_{q['id']}")
                            
                            # Corrigindo a lógica para encontrar a resposta correta
                            resposta_correta = q.get('resposta', '')
                            ops_atual = [e_op1, e_op2, e_op3, e_op4]
                            letra_correta = None
                            for i, op in enumerate(ops_atual):
                                if op == resposta_correta:
                                    letra_correta = ["A", "B", "C", "D"][i]
                                    break
                            
                            idx_corr = ["A", "B", "C", "D"].index(letra_correta) if letra_correta in ["A", "B", "C", "D"] else 0
                            e_correta = st.selectbox("Correta:", ["A","B","C","D"], index=idx_corr, key=f"corr_{q['id']}")
                            
                            justificativa = ""
                            if tipo_user != "admin": 
                                justificativa = st.text_area("Justificativa:", key=f"just_{q['id']}")
                            
                            c_s, c_c = st.columns(2)
                            if c_s.form_submit_button("Salvar"):
                                ops_new = [e_op1, e_op2, e_op3, e_op4]
                                map_new = {"A": e_op1, "B": e_op2, "C": e_op3, "D": e_op4}
                                novos_dados = {
                                    "tema": e_tema, 
                                    "faixa": e_faixa, 
                                    "pergunta": e_perg,
                                    "opcoes": [o for o in ops_new if o.strip()],
                                    "resposta": map_new[e_correta], 
                                    "correta": map_new[e_correta],
                                    "editado_por": user['nome'], 
                                    "data_edicao": firestore.SERVER_TIMESTAMP
                                }
                                if tipo_user == "admin":
                                    try:
                                        db.collection('questoes').document(q['id']).update(novos_dados)
                                        st.success("Atualizado!")
                                    except Exception as e:
                                        st.error(f"Erro ao atualizar: {e}")
                                else:
                                    if not justificativa: 
                                        st.warning("Justifique a edição.")
                                    else:
                                        novos_dados.update({
                                            "status": "pendente_edicao", 
                                            "id_original": q['id'], 
                                            "justificativa": justificativa
                                        })
                                        try:
                                            db.collection('questoes').add(novos_dados)
                                            st.info("Enviado para aprovação.")
                                        except Exception as e:
                                            st.error(f"Erro ao enviar para aprovação: {e}")
                                del st.session_state[f"editing_{q['id']}"]
                                st.rerun()
                            if c_c.form_submit_button("Cancelar"):
                                del st.session_state[f"editing_{q['id']}"]
                                st.rerun()

                    with st.expander("Ver Detalhes", key=f"det_{q['id']}"):
                        st.write(f"Opções: {q.get('opcoes')}")
                        st.success(f"Resposta: {q.get('resposta')}")
                        if tipo_user == "admin":
                            if st.button("🗑️ Excluir", key=f"del_q_{q['id']}"):
                                try:
                                    db.collection('questoes').document(q['id']).delete()
                                    st.rerun()
                                except Exception as e:
                                    st.error(f"Erro ao excluir: {e}")

    # ABA 2: CRIAR
    with abas[1]:
        st.subheader("Adicionar Nova Questão")
        with st.form("new_q"):
            c1, c2 = st.columns(2)
            tema = c1.text_input("Tema:", key="novo_tema")
            faixa = c2.selectbox("Faixa Alvo:", faixas_questoes, key="nova_faixa")
            perg = st.text_area("Pergunta:", key="nova_perg")
            st.write("Alternativas:")
            c_op1, c_op2 = st.columns(2)
            op1 = c_op1.text_input("A)", key="nova_op1")
            op2 = c_op2.text_input("B)", key="nova_op2")
            c_op3, c_op4 = st.columns(2)
            op3 = c_op3.text_input("C)", key="nova_op3")
            op4 = c_op4.text_input("D)", key="nova_op4")
            resp_letra = st.selectbox("Correta:", ["A", "B", "C", "D"], key="nova_resp")
            
            if st.form_submit_button("💾 Salvar"):
                ops = [op1, op2, op3, op4]
                limpas = [o for o in ops if o.strip()]
                if len(limpas) < 2 or not tema or not perg: 
                    st.warning("Preencha corretamente: Tema, Pergunta e pelo menos 2 alternativas.")
                else:
                    mapa = {"A": op1, "B": op2, "C": op3, "D": op4}
                    st_init = "aprovada" if tipo_user == "admin" else "pendente"
                    try:
                        db.collection('questoes').add({
                            "tema": tema, 
                            "faixa": faixa, 
                            "pergunta": perg,
                            "opcoes": limpas, 
                            "resposta": mapa[resp_letra], 
                            "correta": mapa[resp_letra],
                            "status": st_init, 
                            "criado_por": user['nome'], 
                            "data": firestore.SERVER_TIMESTAMP
                        })
                        st.success("Salvo!")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Erro ao salvar: {e}")

    # ABA 3: APROVAR
    if tipo_user == "admin" and len(abas) > 2:
        with abas[2]:
            if not pendentes and not edicoes: 
                st.success("Nada pendente.")
            
            if pendentes:
                st.markdown("#### 🆕 Novas Questões")
                for q in pendentes:
                    with st.container(border=True):
                        st.markdown(f"**[{q.get('tema')}]** {q['pergunta']}")
                        st.caption(f"Por: {q.get('criado_por')}")
                        c1, c2 = st.columns(2)
                        if c1.button("✅ Aprovar", key=f"ok_{q['id']}"):
                            try:
                                db.collection('questoes').document(q['id']).update({"status":"aprovada"})
                                st.rerun()
                            except Exception as e:
                                st.error(f"Erro ao aprovar: {e}")
                        if c2.button("❌ Rejeitar", key=f"no_{q['id']}"):
                            try:
                                db.collection('questoes').document(q['id']).delete()
                                st.rerun()
                            except Exception as e:
                                st.error(f"Erro ao rejeitar: {e}")
            
            if edicoes:
                st.markdown("#### ✏️ Edições")
                for ed in edicoes:
                    with st.container(border=True):
                        st.info(f"Justif: {ed.get('justificativa')}")
                        st.markdown(f"**Nova:** {ed.get('pergunta')}")
                        id_orig = ed.get('id_original')
                        c1, c2 = st.columns(2)
                        if c1.button("✅ Aceitar", key=f"ok_ed_{ed['id']}"):
                            try:
                                dados = ed.copy()
                                dados.pop('id')
                                dados.pop('status')
                                dados.pop('id_original')
                                dados.pop('justificativa')
                                dados['status'] = 'aprovada'
                                db.collection('questoes').document(id_orig).update(dados)
                                db.collection('questoes').document(ed['id']).delete()
                                st.success("Editado!")
                                st.rerun()
                            except Exception as e:
                                st.error(f"Erro ao aceitar edição: {e}")
                        if c2.button("❌ Rejeitar", key=f"no_ed_{ed['id']}"):
                            try:
                                db.collection('questoes').document(ed['id']).delete()
                                st.rerun()
                            except Exception as e:
                                st.error(f"Erro ao rejeitar edição: {e}")

# =========================================
# 3. GESTÃO DE EXAME
# =========================================
def gestao_exame_de_faixa():
    st.markdown("<h1 style='color:#FFD700;'>📜 Gestão de Exame</h1>", unsafe_allow_html=True)
    db = get_db()

    tab1, tab2, tab3 = st.tabs(["📝 Criar e Editar Provas", "👁️ Visualizar Provas", "👥 Autorizar Alunos"])

    # --- ABA 1: EDITOR DE PROVAS ---
    with tab1:
        st.subheader("Configurar Regras da Prova")
        faixa_config = st.selectbox("Selecione a Faixa:", ["Todas"] + FAIXAS_COMPLETAS, key="faixa_config")
        
        config_ref = db.collection('config_exames').where('faixa', '==', faixa_config).stream()
        config_atual = {}
        doc_id_config = None
        for doc in config_ref:
            config_atual = doc.to_dict()
            doc_id_config = doc.id
            break
            
        # Busca Questões (CORREÇÃO DE ID)
        if faixa_config == "Todas":
            snapshots = list(db.collection('questoes').where('status', '==', 'aprovada').stream())
        else:
            s1 = list(db.collection('questoes').where('faixa', '==', faixa_config).where('status', '==', 'aprovada').stream())
            s2 = list(db.collection('questoes').where('faixa', '==', 'Geral').where('status', '==', 'aprovada').stream())
            snapshots = s1 + s2

        questoes_map = {}
        for doc in snapshots:
            d = doc.to_dict(); d['id'] = doc.id
            questoes_map[doc.id] = d
        lista_questoes_obj = list(questoes_map.values())
            
        qtd_disponivel = len(lista_questoes_obj)
        st.info(f"Questões disponíveis: **{qtd_disponivel}**")
        
        modo_atual = config_atual.get('modo_selecao', "🎲 Aleatório (Sorteio)")
        modo_selecao = st.radio("Modo de Seleção:", ["🎲 Aleatório (Sorteio)", "🖐️ Manual (Fixa)"], 
                               index=0 if "Aleatório" in modo_atual else 1, key="modo_selecao")
        
        questoes_escolhidas_manual = []
        qtd_final = 0
        
        if modo_selecao == "🖐️ Manual (Fixa)":
            if qtd_disponivel == 0:
                st.warning("Não há questões para selecionar.")
            else:
                st.markdown("##### Selecione as questões:")
                ids_salvos = set()
                if config_atual.get('questoes'):
                    for q_salva in config_atual['questoes']:
                        if q_salva.get('id'): 
                            ids_salvos.add(q_salva.get('id'))
                        else: 
                            # Para compatibilidade com versões antigas
                            ids_salvos.add(q_salva.get('pergunta'))

                with st.container(height=400):
                    for i, q in enumerate(lista_questoes_obj):
                        is_checked = (q.get('id') in ids_salvos) or (q.get('pergunta') in ids_salvos)
                        c_chk, c_txt = st.columns([0.5, 10])
                        # Chave única
                        selecionado = c_chk.checkbox("", value=is_checked, key=f"chk_{faixa_config}_{q.get('id','no_id')}_{i}")
                        if selecionado: 
                            questoes_escolhidas_manual.append(q)
                        with c_txt:
                            st.markdown(f"**{q.get('pergunta')}**")
                            st.caption(f"✅ {q.get('resposta')} | Autor: {q.get('criado_por', '?')}")
                            st.markdown("---")
                qtd_final = len(questoes_escolhidas_manual)
                st.success(f"**{qtd_final}** questões selecionadas.")
        
        st.markdown("---")
        c1, c2, c3 = st.columns(3)
        tempo = c1.number_input("⏱️ Tempo (min):", min_value=10, value=int(config_atual.get('tempo_limite', 45)), key="tempo_exame")
        nota = c3.number_input("✅ Nota Mínima (%):", min_value=50, max_value=100, 
                              value=int(config_atual.get('aprovacao_minima', 70)), key="nota_minima")
        
        if modo_selecao == "🎲 Aleatório (Sorteio)":
            max_val = max(qtd_disponivel, 1)
            val_padrao = int(config_atual.get('qtd_questoes', min(10, max_val)))
            qtd_final = c2.number_input("📝 Qtd. Questões:", min_value=1, max_value=max_val, 
                                       value=min(val_padrao, max_val), key="qtd_questoes")
        else:
            c2.text_input("📝 Qtd. Questões:", value=qtd_final, disabled=True, key="qtd_manual")

        st.write("")
        if st.button("💾 Salvar Configuração", type="primary", key="salvar_config"):
            dados_config = {
                "faixa": faixa_config, 
                "tempo_limite": tempo, 
                "qtd_questoes": qtd_final,
                "aprovacao_minima": nota, 
                "modo_selecao": modo_selecao,
                "atualizado_em": firestore.SERVER_TIMESTAMP
            }
            if modo_selecao == "🖐️ Manual (Fixa)":
                if not questoes_escolhidas_manual: 
                    st.error("Selecione pelo menos uma questão para o modo manual.")
                else:
                    dados_config['questoes'] = questoes_escolhidas_manual
                    if doc_id_config:
                        db.collection('config_exames').document(doc_id_config).update(dados_config)
                    else:
                        db.collection('config_exames').add(dados_config)
                    st.success(f"Salvo para Faixa {faixa_config}!")
                    time_lib.sleep(1) # CORREÇÃO: Usando a biblioteca renomeada
                    st.rerun()
            else:
                dados_config['questoes'] = [] 
                if doc_id_config:
                    db.collection('config_exames').document(doc_id_config).update(dados_config)
                else:
                    db.collection('config_exames').add(dados_config)
                st.success(f"Salvo para Faixa {faixa_config}!")
                time_lib.sleep(1) # CORREÇÃO: Usando a biblioteca renomeada
                st.rerun()

    # --- ABA 2: VISUALIZAR PROVAS (VISUAL COLORIDO RESTAURADO) ---
    with tab2:
        st.subheader("Status das Provas Cadastradas")
        
        # Carrega configurações da coleção nova
        configs_stream = db.collection('config_exames').stream()
        mapa_configs = {}
        for doc in configs_stream:
            d = doc.to_dict()
            mapa_configs[d.get('faixa')] = d

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
                    data = mapa_configs.get(f_nome)
                    
                    if data:
                        # Prova Configurada
                        modo = data.get('modo_selecao', 'Sorteio')
                        qtd = data.get('qtd_questoes', 0)
                        tempo = data.get('tempo_limite', 0)
                        nota = data.get('aprovacao_minima', 0)
                        
                        with st.expander(f"✅ {f_nome} ({modo} | {qtd} questões)"):
                            st.caption(f"⏱️ Tempo: {tempo} min | 🎯 Mínimo: {nota}%")
                            
                            # Se for Manual, mostra as questões detalhadas
                            if modo == "🖐️ Manual (Fixa)" and data.get('questoes'):
                                for i, q in enumerate(data['questoes'], 1):
                                    st.markdown(f"**{i}. {q.get('pergunta')}**")
                                    st.caption(f"Resposta: {q.get('resposta')}")
                                    st.markdown("---")
                            elif modo == "🎲 Aleatório (Sorteio)":
                                st.info(f"Esta prova sorteia {qtd} questões do banco '{f_nome}' e 'Geral' no momento do exame.")
                    else:
                        st.warning(f"⚠️ A prova para a faixa **{f_nome}** ainda não foi configurada.")

    # --- ABA 3: AUTORIZAR ALUNOS ---
    with tab3:
        with st.container(border=True):
            st.subheader("🗓️ Configurar Período")
            c1, c2 = st.columns(2)
            d_inicio = c1.date_input("Início:", datetime.now(), key="data_inicio_exame")
            d_fim = c2.date_input("Fim:", datetime.now(), key="data_fim_exame")
            c3, c4 = st.columns(2)
            
            # AGORA FUNCIONA: O 'time' aqui refere-se à classe do datetime, pois renomeamos o import da biblioteca
            h_inicio = c3.time_input("Hora Início:", time(0, 0), key="hora_inicio_exame")
            h_fim = c4.time_input("Hora Fim:", time(23, 59), key="hora_fim_exame")
            
            dt_inicio = datetime.combine(d_inicio, h_inicio)
            dt_fim = datetime.combine(d_fim, h_fim)

        st.write("") 
        st.subheader("Lista de Alunos")
        
        try:
            # Buscar alunos
            alunos_ref = db.collection('usuarios').where('tipo_usuario', '==', 'aluno').stream()
            lista_alunos = []
            
            for doc in alunos_ref:
                d = doc.to_dict()
                d['id'] = doc.id
                
                # Buscar equipe do aluno - com tratamento de erro
                nome_eq = "Sem Equipe"
                try:
                    vinculo = list(db.collection('alunos').where('usuario_id', '==', doc.id).limit(1).stream())
                    if vinculo:
                        eid = vinculo[0].to_dict().get('equipe_id')
                        if eid:
                            eq_doc = db.collection('equipes').document(eid).get()
                            if eq_doc.exists:
                                nome_eq = eq_doc.to_dict().get('nome', 'Sem Nome')
                except Exception as e:
                    st.error(f"Erro ao buscar equipe: {e}")
                
                d['nome_equipe'] = nome_eq
                lista_alunos.append(d)

            if not lista_alunos: 
                st.info("Nenhum aluno cadastrado no sistema.")
            else:
                # Cabeçalho da tabela
                cols = st.columns([3, 2, 2, 3, 1])
                cols[0].markdown("**Aluno**")
                cols[1].markdown("**Equipe**")
                cols[2].markdown("**Exame**")
                cols[3].markdown("**Status**")
                cols[4].markdown("**Ação**")
                st.markdown("---")

                # Lista de alunos
                for aluno in lista_alunos:
                    try:
                        # Garantir que temos os dados necessários
                        aluno_id = aluno.get('id', 'unknown')
                        aluno_nome = aluno.get('nome', 'Sem Nome')
                        faixa_exame_atual = aluno.get('faixa_exame', '')
                        
                        c1, c2, c3, c4, c5 = st.columns([3, 2, 2, 3, 1])
                        
                        # Coluna 1: Nome do aluno
                        c1.write(f"**{aluno_nome}**")
                        
                        # Coluna 2: Equipe
                        c2.write(aluno.get('nome_equipe', 'Sem Equipe'))
                        
                        # Coluna 3: Seletor de faixa para exame
                        idx = 0
                        if faixa_exame_atual and faixa_exame_atual in FAIXAS_COMPLETAS:
                            idx = FAIXAS_COMPLETAS.index(faixa_exame_atual)
                        
                        fx_sel = c3.selectbox(
                            "Faixa", 
                            FAIXAS_COMPLETAS, 
                            index=idx, 
                            key=f"fx_select_{aluno_id}",
                            label_visibility="collapsed"
                        )
                        
                        # Coluna 4: Status
                        habilitado = aluno.get('exame_habilitado', False)
                        status = aluno.get('status_exame', 'pendente')
                        
                        if habilitado:
                            # Aluno habilitado para exame
                            msg = "🟢 Liberado"
                            try:
                                raw_fim = aluno.get('exame_fim')
                                if raw_fim:
                                    if isinstance(raw_fim, str):
                                        dt_obj = datetime.fromisoformat(raw_fim.replace('Z', '+00:00'))
                                        msg += f" (até {dt_obj.strftime('%d/%m/%Y %H:%M')})"
                                    elif hasattr(raw_fim, 'strftime'):
                                        msg += f" (até {raw_fim.strftime('%d/%m/%Y %H:%M')})"
                            except Exception as e:
                                st.error(f"Erro ao processar data: {e}")
                            
                            # Status específicos
                            if status == 'aprovado': 
                                msg = "🏆 Aprovado"
                            elif status == 'bloqueado': 
                                msg = "⛔ Bloqueado"
                            elif status == 'reprovado': 
                                msg = "🔴 Reprovado"
                            elif status == 'em_andamento':
                                msg = "🟡 Em Andamento"
                            
                            c4.write(msg)
                            
                            # Coluna 5: Botão desabilitar
                            if c5.button("⛔", key=f"off_btn_{aluno_id}"):
                                try:
                                    update_data = {
                                        "exame_habilitado": False,
                                        "status_exame": "pendente"
                                    }
                                    # Remover campos opcionais se existirem
                                    campos_para_remover = [
                                        "exame_inicio", "exame_fim", "faixa_exame", 
                                        "motivo_bloqueio", "status_exame_em_andamento"
                                    ]
                                    
                                    for campo in campos_para_remover:
                                        if campo in aluno:
                                            update_data[campo] = firestore.DELETE_FIELD
                                    
                                    db.collection('usuarios').document(aluno_id).update(update_data)
                                    st.success(f"Exame desabilitado para {aluno_nome}")
                                    st.rerun()
                                except Exception as e:
                                    st.error(f"Erro ao desabilitar: {e}")
                        else:
                            # Aluno não habilitado
                            c4.write("⚪ Não autorizado")
                            
                            # Coluna 5: Botão habilitar
                            if c5.button("✅", key=f"on_btn_{aluno_id}"):
                                try:
                                    db.collection('usuarios').document(aluno_id).update({
                                        "exame_habilitado": True,
                                        "faixa_exame": fx_sel,
                                        "exame_inicio": firestore.SERVER_TIMESTAMP,
                                        "exame_fim": dt_fim.isoformat(),
                                        "status_exame": "pendente",
                                        "status_exame_em_andamento": False
                                    })
                                    st.success(f"Exame habilitado para {aluno_nome} até {dt_fim.strftime('%d/%m/%Y %H:%M')}")
                                    st.rerun()
                                except Exception as e:
                                    st.error(f"Erro ao habilitar: {e}")
                        
                        st.markdown("---")
                        
                    except Exception as e:
                        st.error(f"Erro ao processar aluno {aluno.get('nome', 'Unknown')}: {str(e)}")
                        st.markdown("---")
                        
        except Exception as e:
            st.error(f"Erro ao carregar lista de alunos: {str(e)}")
            st.info("Verifique a conexão com o banco de dados.")
