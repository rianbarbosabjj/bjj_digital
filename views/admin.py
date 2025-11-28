import streamlit as st
import pandas as pd
import bcrypt
from datetime import datetime, time
from database import get_db
from firebase_admin import firestore

# =========================================
# GESTÃO DE USUÁRIOS (EDITAR + EXCLUIR)
# =========================================
def gestao_usuarios(usuario_logado):
    st.markdown("<h1 style='color:#FFD700;'>👥 Gestão de Usuários</h1>", unsafe_allow_html=True)
    db = get_db()
    
    # 1. Carrega usuários
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
            "auth_provider": d.get('auth_provider', 'local'),
            # Endereço
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

    # 2. Filtros
    filtro = st.text_input("🔍 Buscar por Nome, Email ou CPF:")
    df = pd.DataFrame(lista_users)
    
    if filtro:
        f = filtro.upper()
        df = df[
            df['nome'].str.upper().str.contains(f) | 
            df['email'].str.upper().str.contains(f) | 
            df['cpf'].str.contains(f)
        ]

    # 3. Tabela Resumo
    st.dataframe(
        df[['nome', 'email', 'tipo_usuario', 'faixa_atual']], 
        use_container_width=True,
        hide_index=True,
        column_config={
            "nome": "Nome",
            "email": "E-mail",
            "tipo_usuario": "Perfil",
            "faixa_atual": "Faixa"
        }
    )
    
    st.markdown("---")

    # 4. SELEÇÃO PARA AÇÃO
    st.subheader("🛠️ Ações de Cadastro")
    
    opcoes_usuarios = df.to_dict('records')
    usuario_selecionado = st.selectbox(
        "Selecione o usuário para Editar ou Excluir:", 
        opcoes_usuarios, 
        format_func=lambda x: f"{x['nome']} ({x['email']})"
    )
    
    if usuario_selecionado:
        # --- ÁREA DE EDIÇÃO ---
        with st.expander(f"✏️ Editar dados de {usuario_selecionado['nome']}", expanded=False):
            with st.form(key=f"edit_full_{usuario_selecionado['id']}"):
                
                # Bloco 1: Dados Pessoais
                st.markdown("##### 👤 Dados Pessoais e Acesso")
                c1, c2 = st.columns(2)
                novo_nome = c1.text_input("Nome Completo:", value=usuario_selecionado['nome'])
                novo_email = c2.text_input("E-mail:", value=usuario_selecionado['email'])
                
                c3, c4 = st.columns(2)
                novo_cpf = c3.text_input("CPF:", value=usuario_selecionado['cpf'])
                
                tipos_possiveis = ["aluno", "professor", "admin"]
                idx_tipo = tipos_possiveis.index(usuario_selecionado['tipo_usuario']) if usuario_selecionado['tipo_usuario'] in tipos_possiveis else 0
                novo_tipo = c4.selectbox("Perfil de Acesso:", tipos_possiveis, index=idx_tipo)

                faixas_possiveis = ["Branca", "Cinza", "Amarela", "Laranja", "Verde", "Azul", "Roxa", "Marrom", "Preta"]
                idx_faixa = faixas_possiveis.index(usuario_selecionado['faixa_atual']) if usuario_selecionado['faixa_atual'] in faixas_possiveis else 0
                novo_faixa = st.selectbox("Faixa Atual:", faixas_possiveis, index=idx_faixa)
                
                st.markdown("---")
                
                # Bloco 2: Segurança
                st.markdown("##### 🔐 Segurança (Redefinição de Senha)")
                st.caption("Deixe em branco para manter a senha atual.")
                nova_senha_admin = st.text_input("Nova Senha:", type="password", help="Se preencher, a senha do usuário será alterada.")
                
                st.markdown("---")
                
                # Bloco 3: Endereço
                st.markdown("##### 🏠 Endereço")
                e1, e2 = st.columns([1, 3])
                novo_cep = e1.text_input("CEP:", value=usuario_selecionado['cep'])
                novo_logr = e2.text_input("Logradouro:", value=usuario_selecionado['logradouro'])
                
                e3, e4, e5 = st.columns([1, 2, 1])
                novo_num = e3.text_input("Número:", value=usuario_selecionado['numero'])
                novo_comp = e4.text_input("Complemento:", value=usuario_selecionado['complemento'])
                novo_bairro = e5.text_input("Bairro:", value=usuario_selecionado['bairro'])
                
                e6, e7 = st.columns(2)
                novo_cid = e6.text_input("Cidade:", value=usuario_selecionado['cidade'])
                novo_uf = e7.text_input("UF:", value=usuario_selecionado['uf'])

                st.markdown("---")
                
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
                            "numero": novo_num,
                            "complemento": novo_comp.upper(),
                            "bairro": novo_bairro.upper(),
                            "cidade": novo_cid.upper(),
                            "uf": novo_uf.upper()
                        }
                        
                        if nova_senha_admin:
                            hashed = bcrypt.hashpw(nova_senha_admin.encode(), bcrypt.gensalt()).decode()
                            dados_update["senha"] = hashed
                            dados_update["precisa_trocar_senha"] = True
                            st.info("Senha alterada com sucesso.")

                        db.collection('usuarios').document(usuario_selecionado['id']).update(dados_update)
                        st.success(f"Cadastro de {novo_nome} atualizado!")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Erro ao atualizar: {e}")

        # --- ÁREA DE EXCLUSÃO (ZONA DE PERIGO) ---
        st.write("")
        with st.container(border=True):
            st.markdown("#### 🗑️ Zona de Perigo")
            c_aviso, c_botao = st.columns([3, 1])
            
            c_aviso.warning(f"Atenção: Deseja excluir permanentemente o usuário **{usuario_selecionado['nome']}**? Essa ação não pode ser desfeita.")
            
            if c_botao.button("EXCLUIR USUÁRIO", key=f"del_user_{usuario_selecionado['id']}", type="primary"):
                try:
                    # Exclui o documento do usuário
                    db.collection('usuarios').document(usuario_selecionado['id']).delete()
                    
                    # Opcional: Aqui você poderia excluir documentos vinculados (alunos/professores) se quisesse limpar tudo
                    # Mas apenas deletar o usuário já impede o login
                    
                    st.toast(f"Usuário {usuario_selecionado['nome']} excluído com sucesso!")
                    st.rerun()
                except Exception as e:
                    st.error(f"Erro ao excluir: {e}")

# =========================================
# GESTÃO DE QUESTÕES
# =========================================
def gestao_exame_de_faixa():
    st.markdown("<h1 style='color:#FFD700;'>📜 Gestão de Exame</h1>", unsafe_allow_html=True)
    
    user_logado = st.session_state.usuario
    tipo_user = str(user_logado.get("tipo", "")).lower()
    
    if tipo_user not in ["admin", "professor"]:
        st.error("Acesso negado.")
        return

    tab_editor, tab_visualizar, tab_alunos = st.tabs(["✏️ Editor de Provas", "👁️ Visualizar Provas", "✅ Habilitar Alunos"])
    
    db = get_db()
    
    todas_faixas = [
        "Cinza e Branca", "Cinza", "Cinza e Preta",
        "Amarela e Branca", "Amarela", "Amarela e Preta",
        "Laranja e Branca", "Laranja", "Laranja e Preta",
        "Verde e Branca", "Verde", "Verde e Preta",
        "Azul", "Roxa", "Marrom", "Preta"
    ]

    # ---------------------------------------------------------
    # ABA 1: EDITOR (Visualização Rica)
    # ---------------------------------------------------------
    with tab_editor:
        st.subheader("Editor de Prova")
        
        faixa_edit = st.selectbox("Selecione a faixa para criar/editar:", todas_faixas, key="sel_faixa_edit")
        
        doc_ref = db.collection('exames').document(faixa_edit)
        doc_snap = doc_ref.get()
        
        dados_prova = doc_snap.to_dict() if doc_snap.exists else {}
        questoes_atuais = dados_prova.get('questoes', [])
        tempo_atual = dados_prova.get('tempo_limite', 10)

        c_time, c_stat = st.columns([1, 3])
        novo_tempo = c_time.number_input("⏱️ Tempo Limite (min):", 10, 240, tempo_atual, 10)
        c_stat.info(f"Esta prova contém atualmente **{len(questoes_atuais)} questões**.")

        st.markdown("---")
        st.markdown("#### ➕ Adicionar Questões do Banco")
        
        docs_q = db.collection('questoes').where('status', '==', 'aprovada').stream()
        todas_q = [d.to_dict() for d in docs_q] 
        
        temas = sorted(list(set(q.get('tema', 'Geral') for q in todas_q)))
        filtro = st.selectbox("Filtrar Banco por Tema:", ["Todos"] + temas)
        
        q_exibir = [q for q in todas_q if q.get('tema') == filtro] if filtro != "Todos" else todas_q
        perguntas_ja_add = [q['pergunta'] for q in questoes_atuais]

        with st.form("form_add_questoes"):
            selecionadas = []
            count = 0
            for i, q in enumerate(q_exibir):
                if count > 100: break # Paginação simples
                
                if q['pergunta'] not in perguntas_ja_add:
                    # LAYOUT DETALHADO NA SELEÇÃO
                    st.markdown(f"**{i+1}. [{q.get('tema')}]** {q['pergunta']}")
                    
                    # Alternativas
                    if q.get('opcoes'):
                        for op in q['opcoes']:
                            st.caption(f"• {op}")
                    
                    # Metadados
                    c_meta1, c_meta2, c_meta3 = st.columns([3, 2, 1])
                    c_meta1.markdown(f"✅ **Gabarito:** {q.get('resposta')}")
                    c_meta2.caption(f"✍️ **Autor:** {q.get('criado_por', 'Desconhecido')}")
                    
                    # Checkbox
                    ck = c_meta3.checkbox("Selecionar", key=f"add_{i}")
                    if ck: selecionadas.append(q)
                    
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
                    st.info(f"Resposta: {q.get('resposta')} | Autor: {q.get('criado_por')}")
                    if st.button("Remover da Prova", key=f"rem_{i}"):
                        questoes_atuais.pop(i)
                        doc_ref.update({"questoes": questoes_atuais, "tempo_limite": novo_tempo})
                        st.rerun()


# =========================================
# GESTÃO DE EXAME
# =========================================
def gestao_exame_de_faixa():
    st.markdown("<h1 style='color:#FFD700;'>📜 Gestão de Exame</h1>", unsafe_allow_html=True)
    db = get_db()

    with st.container(border=True):
        st.subheader("🗓️ Configurar Período do Exame")
        c1, c2 = st.columns(2)
        d_inicio = c1.date_input("Data Início:", datetime.now())
        d_fim = c2.date_input("Data Fim:", datetime.now())
        c3, c4 = st.columns(2)
        h_inicio = c3.time_input("Hora Início:", time(0, 0))
        h_fim = c4.time_input("Hora Fim:", time(23, 59))
        dt_inicio = datetime.combine(d_inicio, h_inicio)
        dt_fim = datetime.combine(d_fim, h_fim)

    st.write("") 

    st.subheader("Autorizar Alunos")
    alunos_ref = db.collection('usuarios').where('tipo_usuario', '==', 'aluno').stream()
    lista_alunos = []
    
    for doc in alunos_ref:
        d = doc.to_dict()
        d['id'] = doc.id
        nome_equipe = "Sem Equipe"
        vinculo = list(db.collection('alunos').where('usuario_id', '==', doc.id).limit(1).stream())
        if vinculo:
            eq_id = vinculo[0].to_dict().get('equipe_id')
            if eq_id:
                eq_doc = db.collection('equipes').document(eq_id).get()
                if eq_doc.exists:
                    nome_equipe = eq_doc.to_dict().get('nome')
        d['nome_equipe'] = nome_equipe
        lista_alunos.append(d)

    if not lista_alunos:
        st.info("Nenhum aluno cadastrado.")
        return

    cols = st.columns([3, 2, 2, 3, 1])
    cols[0].markdown("**Aluno**")
    cols[1].markdown("**Equipe**")
    cols[2].markdown("**Exame (Faixa)**")
    cols[3].markdown("**Status Atual**")
    cols[4].markdown("**Ação**")
    st.markdown("---")

    faixas_opcoes = ["Cinza", "Amarela", "Laranja", "Verde", "Azul", "Roxa", "Marrom", "Preta"]

    for aluno in lista_alunos:
        c1, c2, c3, c4, c5 = st.columns([3, 2, 2, 3, 1])
        c1.write(f"**{aluno.get('nome', 'Sem Nome')}**")
        c2.write(aluno['nome_equipe'])
        
        key_faixa = f"sel_fx_{aluno['id']}"
        idx_padrao = 0
        faixa_salva = aluno.get('faixa_exame')
        if faixa_salva in faixas_opcoes:
            idx_padrao = faixas_opcoes.index(faixa_salva)
            
        faixa_selecionada = c3.selectbox("Faixa", faixas_opcoes, index=idx_padrao, key=key_faixa, label_visibility="collapsed")

        habilitado = aluno.get('exame_habilitado', False)
        status_prova = aluno.get('status_exame', 'pendente')
        
        if habilitado:
            msg_status = "🟢 Liberado"
            raw_fim = aluno.get('exame_fim')
            if raw_fim:
                try:
                    if isinstance(raw_fim, str): 
                        fim_fmt = datetime.fromisoformat(raw_fim).strftime('%d/%m')
                    else: 
                        fim_fmt = raw_fim.strftime('%d/%m')
                    msg_status += f" (até {fim_fmt})"
                except: pass

            if status_prova == 'aprovado': msg_status = "🏆 Aprovado"
            elif status_prova == 'reprovado': msg_status = "🔴 Reprovado"
            elif status_prova == 'bloqueado': msg_status = "⛔ Bloqueado"
            
            c4.caption(msg_status)
            
            if c5.button("⛔", key=f"btn_off_{aluno['id']}", help="Cancelar"):
                db.collection('usuarios').document(aluno['id']).update({
                    "exame_habilitado": False,
                    "exame_inicio": firestore.DELETE_FIELD,
                    "exame_fim": firestore.DELETE_FIELD,
                    "faixa_exame": firestore.DELETE_FIELD,
                    "status_exame": "pendente",
                    "motivo_bloqueio": firestore.DELETE_FIELD
                })
                st.rerun()
        else:
            c4.caption("⚪ Não autorizado")
            if c5.button("✅", key=f"btn_on_{aluno['id']}", help="Autorizar"):
                dados_update = {
                    "exame_habilitado": True,
                    "faixa_exame": faixa_selecionada,
                    "exame_inicio": dt_inicio.isoformat(),
                    "exame_fim": dt_fim.isoformat(),
                    "status_exame": "pendente",
                    "status_exame_em_andamento": False,
                    "motivo_bloqueio": firestore.DELETE_FIELD
                }
                db.collection('usuarios').document(aluno['id']).update(dados_update)
                st.toast(f"Exame liberado para {aluno.get('nome')}!")
                st.rerun()
        st.markdown("---")
