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
    """Página de gerenciamento de usuários (Admin)."""
    
    # Normaliza tipo para segurança
    tipo_user = str(usuario_logado.get("tipo", "")).lower()
    
    if tipo_user != "admin":
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
        
        user_ref = db.collection('usuarios').document(user_id)
        doc_snap = user_ref.get()
        
        if not doc_snap.exists:
            st.error("Usuário não encontrado.")
            return

        user_data = doc_snap.to_dict()

        with st.expander(f"⚙️ Editar: {user_data.get('nome')}", expanded=True):
            with st.form(key="form_edit_user_admin"):
                c1, c2 = st.columns(2)
                novo_nome = c1.text_input("Nome:", value=user_data.get('nome', ''))
                novo_email = c2.text_input("Email:", value=user_data.get('email', ''))
                novo_cpf = st.text_input("CPF:", value=user_data.get('cpf', ''))
                
                tipo_atual = str(user_data.get('tipo_usuario', 'aluno')).lower()
                opcoes_tipo = ["aluno", "professor", "admin"]
                try: idx_tipo = opcoes_tipo.index(tipo_atual)
                except: idx_tipo = 0
                novo_tipo = st.selectbox("Tipo:", options=opcoes_tipo, index=idx_tipo)
                
                if st.form_submit_button("💾 Salvar"):
                    try:
                        user_ref.update({
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
                            user_ref.update({"senha": h})
                            st.success("Senha alterada.")

            st.markdown("---")
            st.warning("Zona de Perigo")
            if st.button("🗑️ Excluir Usuário"):
                user_ref.delete()
                batch = db.batch()
                for a_doc in db.collection('alunos').where('usuario_id', '==', user_id).stream():
                    batch.delete(a_doc.reference)
                for p_doc in db.collection('professores').where('usuario_id', '==', user_id).stream():
                    batch.delete(p_doc.reference)
                batch.commit()
                st.success("Usuário excluído.")
                st.rerun()

# =========================================
# GESTÃO DE QUESTÕES (COM FLUXO DE APROVAÇÃO CORRIGIDO)
# =========================================
def gestao_questoes():
    """Gestão de Banco de Questões no Firestore."""
    
    user = st.session_state.usuario
    # Normaliza tipo para evitar erro de caixa alta/baixa
    tipo_user = str(user.get("tipo", "")).lower()
    
    if tipo_user not in ["admin", "professor"]:
        st.error("Acesso negado.")
        return
    
    st.markdown("<h1 style='color:#FFD700;'>🧠 Banco de Questões</h1>", unsafe_allow_html=True)
    db = get_db()

    # --- CARREGAMENTO INICIAL ---
    docs_q = list(db.collection('questoes').stream())
    
    pendentes = []
    correcoes = []
    aprovadas = []
    minhas_pendentes = []
    temas_set = set()

    for doc in docs_q:
        d = doc.to_dict()
        d['id'] = doc.id
        # Se não tiver status, assume aprovada (legado), senão pega o status real
        status = d.get('status', 'aprovada')
        
        if status == 'pendente':
            pendentes.append(d)
            # Se eu fui quem criou, adiciona na minha lista de acompanhamento
            if d.get('criado_por_id') == user['id']:
                minhas_pendentes.append(d)
        else:
            aprovadas.append(d)
            temas_set.add(d.get('tema', 'Geral'))
            if d.get('solicitacao_correcao'):
                correcoes.append(d)

    temas_existentes = sorted(list(temas_set))
    
    # --- DEFINIÇÃO DAS ABAS ---
    titulos_abas = ["📚 Banco de Questões (Aprovadas)", "➕ Adicionar Nova"]
    
    if tipo_user == "admin":
        titulos_abas.extend([f"✅ Aprovar ({len(pendentes)})", f"🔧 Correções ({len(correcoes)})"])
    else:
        titulos_abas.append(f"⏳ Minhas Pendentes ({len(minhas_pendentes)})")
        
    abas = st.tabs(titulos_abas)

    # -------------------------------------------------------
    # ABA 1: BANCO DE QUESTÕES (APROVADAS)
    # -------------------------------------------------------
    with abas[0]:
        c1, c2 = st.columns([3, 1])
        filtro_tema = c1.selectbox("Filtrar por Tema:", ["Todos"] + temas_existentes)
        q_exibir = aprovadas
        if filtro_tema != "Todos":
            q_exibir = [q for q in aprovadas if q.get('tema') == filtro_tema]
        
        if not q_exibir:
            st.info("Nenhuma questão aprovada encontrada.")
        else:
            for q in q_exibir:
                with st.container(border=True):
                    col_txt, col_btn = st.columns([6, 1])
                    col_txt.markdown(f"**[{q.get('tema')}]** {q['pergunta']}")
                    
                    autor = q.get('criado_por', 'Desconhecido').title()
                    st.caption(f"✍️ Criado por: {autor}")
                    
                    with st.expander("Ver Detalhes / Opções"):
                        st.write(f"**Opções:** {q.get('opcoes')}")
                        st.caption(f"✅ Resposta: {q.get('resposta')}")
                        if q.get('imagem'): st.image(q['imagem'], width=200)
                        
                        st.markdown("---")
                        c_act1, c_act2 = st.columns(2)
                        
                        # ADMIN: Exclui direto
                        if tipo_user == "admin":
                            if c_act2.button("🗑️ Excluir Definitivamente", key=f"del_{q['id']}"):
                                db.collection('questoes').document(q['id']).delete()
                                st.success("Excluída!")
                                st.rerun()
                        
                        # TODOS (Prof/Admin): Solicitam correção
                        if not q.get('solicitacao_correcao'):
                            with c_act1.popover("🚩 Solicitar Correção"):
                                motivo = st.text_input("Motivo:", key=f"motivo_{q['id']}")
                                if st.button("Enviar Solicitação", key=f"send_fix_{q['id']}"):
                                    db.collection('questoes').document(q['id']).update({
                                        "solicitacao_correcao": True,
                                        "motivo_correcao": motivo,
                                        "solicitado_por": user['nome']
                                    })
                                    st.success("Enviado!")
                                    st.rerun()
                        else:
                            c_act1.warning(f"Correção pendente: {q.get('motivo_correcao')}")

    # -------------------------------------------------------
    # ABA 2: ADICIONAR NOVA
    # -------------------------------------------------------
    with abas[1]:
        st.markdown("### Cadastrar Nova Questão")
        if tipo_user == "professor":
            st.info("ℹ️ Suas questões entrarão como 'Pendente' até aprovação de um Admin.")
            
        with st.form("form_add_q"):
            c_tema1, c_tema2 = st.columns([1, 1])
            tema_sel_add = c_tema1.selectbox("Tema:", ["Novo Tema"] + temas_existentes)
            tema_novo = c_tema2.text_input("Nome do Novo Tema:") if tema_sel_add == "Novo Tema" else None
            tema_final = tema_novo if tema_novo else tema_sel_add
            
            pergunta = st.text_area("Enunciado da Pergunta:")
            
            cols = st.columns(2)
            op_a = cols[0].text_input("Opção A:")
            op_b = cols[1].text_input("Opção B:")
            op_c = cols[0].text_input("Opção C:")
            op_d = cols[1].text_input("Opção D:")
            
            correta_letra = st.selectbox("Qual a correta?", ["A", "B", "C", "D"])
            img = st.text_input("URL da Imagem (Opcional):")

            if st.form_submit_button("💾 Salvar Questão"):
                if pergunta and tema_final and op_a and op_b:
                    opcoes_raw = [op_a, op_b, op_c, op_d]
                    opcoes_limpas = [o for o in opcoes_raw if o.strip()]
                    mapa = {"A": op_a, "B": op_b, "C": op_c, "D": op_d}
                    resp_texto = mapa.get(correta_letra)
                    
                    # Regra de Status: Admin -> Aprovada / Professor -> Pendente
                    status_inicial = "aprovada" if tipo_user == "admin" else "pendente"
                    
                    nova_q = {
                        "tema": tema_final, "pergunta": pergunta, "opcoes": opcoes_limpas,
                        "resposta": resp_texto, "imagem": img, 
                        "criado_por": user['nome'], "criado_por_id": user['id'],
                        "data": firestore.SERVER_TIMESTAMP,
                        "status": status_inicial,
                        "solicitacao_correcao": False
                    }
                    db.collection('questoes').add(nova_q)
                    
                    msg = "Questão salva e APROVADA!" if status_inicial == "aprovada" else "Questão enviada para APROVAÇÃO!"
                    st.success(msg)
                    st.rerun()
                else:
                    st.warning("Preencha a pergunta, o tema e pelo menos 2 opções.")

    # -------------------------------------------------------
    # ABA 3: ADMIN - APROVAR PENDENTES
    # -------------------------------------------------------
    if tipo_user == "admin":
        with abas[2]:
            st.markdown(f"### ✅ Aprovação de Questões ({len(pendentes)})")
            if not pendentes:
                st.info("Nenhuma questão aguardando aprovação.")
            else:
                for q in pendentes:
                    with st.container(border=True):
                        st.markdown(f"**[{q.get('tema')}]** {q['pergunta']}")
                        st.caption(f"Por: {q.get('criado_por')} | Status: Pendente")
                        
                        with st.expander("Revisar"):
                            st.write(f"**Opções:** {q.get('opcoes')}")
                            st.write(f"**Resposta:** {q.get('resposta')}")
                            
                            c_apr, c_rej = st.columns(2)
                            if c_apr.button("✅ Aprovar", key=f"apr_{q['id']}"):
                                db.collection('questoes').document(q['id']).update({"status": "aprovada"})
                                st.success("Aprovada!")
                                st.rerun()
                            if c_rej.button("❌ Rejeitar", key=f"rej_{q['id']}"):
                                db.collection('questoes').document(q['id']).delete()
                                st.warning("Rejeitada e excluída.")
                                st.rerun()
                            
        # ABA 4: ADMIN - CORREÇÕES
        with abas[3]:
            st.markdown("### 🔧 Solicitações de Correção")
            if not correcoes:
                st.info("Nenhuma solicitação em aberto.")
            else:
                for q in correcoes:
                    with st.container(border=True):
                        st.markdown(f"**Questão:** {q['pergunta']}")
                        st.error(f"📢 Motivo: {q.get('motivo_correcao')} (Por: {q.get('solicitado_por')})")
                        
                        with st.expander("Editar"):
                            with st.form(key=f"fix_{q['id']}"):
                                n_perg = st.text_area("Pergunta:", value=q['pergunta'])
                                c_fix1, c_fix2 = st.columns(2)
                                salvar_fix = c_fix1.form_submit_button("Salvar e Resolver")
                                
                                if salvar_fix:
                                    db.collection('questoes').document(q['id']).update({
                                        "pergunta": n_perg,
                                        "solicitacao_correcao": False,
                                        "motivo_correcao": firestore.DELETE_FIELD
                                    })
                                    st.success("Resolvido!")
                                    st.rerun()
                                    
                        if st.button("Ignorar Flag", key=f"ign_{q['id']}"):
                             db.collection('questoes').document(q['id']).update({
                                "solicitacao_correcao": False,
                                "motivo_correcao": firestore.DELETE_FIELD
                             })
                             st.rerun()

    # -------------------------------------------------------
    # ABA 3: PROFESSOR - MINHAS PENDENTES
    # -------------------------------------------------------
    elif tipo_user == "professor":
        with abas[2]:
            st.markdown("### ⏳ Minhas Questões em Análise")
            if not minhas_pendentes:
                st.info("Você não tem questões aguardando aprovação.")
            else:
                for q in minhas_pendentes:
                    with st.container(border=True):
                        st.markdown(f"**[{q.get('tema')}]** {q['pergunta']}")
                        st.caption("Status: Aguardando Admin")

# =========================================
# GESTÃO DE EXAME DE FAIXA (Mantida igual)
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
    # ABA 1: MONTAR PROVA (Mantida igual)
    # ---------------------------------------------------------
    with tab_prova:
        st.subheader("Configurar Prova")
        db = get_db()
        
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
            
            for i, q in enumerate(q_exibir):
                if q['pergunta'] not in perguntas_ja_add:
                    c_chk, c_det = st.columns([0.5, 10])
                    with c_chk:
                        key_id = str(hash(q['pergunta']))
                        if st.checkbox("Add", key=f"chk_{key_id}", label_visibility="collapsed"):
                            selecionadas.append(q)
                    with c_det:
                        st.markdown(f"**[{q.get('tema')}]** {q['pergunta']}")
                        if 'opcoes' in q and q['opcoes']:
                            for op in q['opcoes']:
                                st.markdown(f"<span style='color: #aaaaaa; margin-left: 15px;'>• {op}</span>", unsafe_allow_html=True)
                        st.caption(f"✅ {q.get('resposta')}")
                        st.markdown("---")
            
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

        st.markdown("---")
        if questoes_na_prova:
            st.markdown(f"#### Questões nesta Prova ({len(questoes_na_prova)})")
            for i, q in enumerate(questoes_na_prova):
                with st.expander(f"{i+1}. {q['pergunta']}"):
                    st.write(q.get('opcoes'))
                    if st.button("Remover", key=f"rm_{i}"):
                        questoes_na_prova.pop(i)
                        doc_ref.update({"questoes": questoes_na_prova, "tempo_limite": novo_tempo})
                        st.rerun()
        else:
            st.info("Esta prova ainda não tem questões.")

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
                # return # (Removido para não quebrar fluxo visual, usa lógica abaixo)

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
            
            st.markdown("#### 📅 Configurar Período Disponível")
            c_ini, c_fim = st.columns(2)
            d_ini = c_ini.date_input("Início:", value=datetime.now())
            h_ini = c_ini.time_input("Hora:", value=time(0, 0))
            d_fim = c_fim.date_input("Fim:", value=datetime.now())
            h_fim = c_fim.time_input("Hora Fin:", value=time(23, 59))
            
            dt_inicio = datetime.combine(d_ini, h_ini)
            dt_fim = datetime.combine(d_fim, h_fim)

            st.markdown("---")
            st.write("Selecione a **Faixa do Exame** que o aluno irá prestar e clique em Habilitar.")
            
            # Cabeçalho Tabela
            h = st.columns([3, 2, 2, 3, 2])
            h[0].markdown("**Aluno**")
            h[1].markdown("**Equipe**")
            h[2].markdown("**Exame Para**") # Coluna de Seleção
            h[3].markdown("**Status**")
            h[4].markdown("**Ação**")
            st.markdown("---")
            
            faixas_disponiveis = ["Cinza", "Amarela", "Laranja", "Verde", "Azul", "Roxa", "Marrom", "Preta"]

            for doc in docs_alunos:
                d = doc.to_dict()
                uid = d.get('usuario_id')
                eid = d.get('equipe_id')
                
                if equipes_permitidas is None or eid in equipes_permitidas:
                    nome_aluno = users_map.get(uid, "Desconhecido")
                    nome_equipe = equipes_map.get(eid, "Sem Equipe")
                    
                    habilitado = d.get('exame_habilitado', False)
                    faixa_liberada = d.get('faixa_exame_liberado', 'Nenhuma')
                    
                    # Status Visual
                    p_str = "Bloqueado"
                    if habilitado:
                        try:
                            i = d.get('exame_inicio').replace(tzinfo=None).strftime("%d/%m")
                            f = d.get('exame_fim').replace(tzinfo=None).strftime("%d/%m")
                            p_str = f"🟢 {faixa_liberada} ({i}-{f})"
                        except: p_str = f"🟢 {faixa_liberada}"

                    c = st.columns([3, 2, 2, 3, 2])
                    c[0].write(nome_aluno)
                    c[1].write(nome_equipe)
                    
                    # Seletor de Faixa individual para este aluno
                    # Tenta prever a próxima faixa se possível, ou usa a atual + 1
                    faixa_selecionada = c[2].selectbox(
                        "Faixa", 
                        faixas_disponiveis, 
                        key=f"sel_fx_{doc.id}", 
                        label_visibility="collapsed",
                        index=0 # Padrão
                    )
                    
                    c[3].write(p_str)
                    
                    if habilitado:
                        if c[4].button("⛔ Bloquear", key=f"blk_{doc.id}"):
                            db.collection('alunos').document(doc.id).update({
                                "exame_habilitado": False,
                                "exame_inicio": None,
                                "exame_fim": None,
                                "faixa_exame_liberado": None # Limpa a faixa liberada
                            })
                            st.rerun()
                    else:
                        if c[4].button("✅ Habilitar", key=f"hab_{doc.id}"):
                            if dt_inicio < dt_fim:
                                db.collection('alunos').document(doc.id).update({
                                    "exame_habilitado": True, 
                                    "exame_inicio": dt_inicio, 
                                    "exame_fim": dt_fim,
                                    "faixa_exame_liberado": faixa_selecionada # Salva qual exame ele vai fazer
                                })
                                st.rerun()
                            else: st.error("Data Inválida")
