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
# GESTÃO DE USUÁRIOS (Mantida igual)
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
                
                tipo_atual = user_data.get('tipo_usuario', 'aluno')
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
# GESTÃO DE QUESTÕES (COM FLUXO DE APROVAÇÃO)
# =========================================
def gestao_questoes():
    """Gestão de Banco de Questões no Firestore."""
    
    user = st.session_state.usuario
    tipo_user = user["tipo"]
    if tipo_user not in ["admin", "professor"]:
        st.error("Acesso negado.")
        return
    
    st.markdown("<h1 style='color:#FFD700;'>🧠 Banco de Questões</h1>", unsafe_allow_html=True)
    db = get_db()

    # --- CARREGAMENTO INICIAL ---
    docs_q = list(db.collection('questoes').stream())
    todas_questoes = []
    temas_set = set()
    
    pendentes = []
    correcoes = []
    aprovadas = []
    minhas_pendentes = []

    for doc in docs_q:
        d = doc.to_dict()
        d['id'] = doc.id
        status = d.get('status', 'aprovada') # Legado assume aprovada
        
        # Separação por Status
        if status == 'pendente':
            pendentes.append(d)
            if d.get('criado_por_id') == user['id']:
                minhas_pendentes.append(d)
        else:
            aprovadas.append(d)
            temas_set.add(d.get('tema', 'Geral'))
            # Verifica se tem pedido de correção
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
                cor_card = "#2e2e2e" if not q.get('solicitacao_correcao') else "#5c4b0b" # Destaca se tiver flag
                with st.container(border=True):
                    # Cabeçalho da Questão
                    col_txt, col_btn = st.columns([6, 1])
                    col_txt.markdown(f"**[{q.get('tema')}]** {q['pergunta']}")
                    
                    with st.expander("Ver Detalhes / Opções"):
                        st.write(f"**Opções:** {q.get('opcoes')}")
                        st.caption(f"✅ Resposta: {q.get('resposta')}")
                        if q.get('imagem'): st.image(q['imagem'], width=200)
                        
                        st.markdown("---")
                        
                        # Ações
                        c_act1, c_act2 = st.columns(2)
                        
                        # Admin pode excluir direto
                        if tipo_user == "admin":
                            if c_act2.button("🗑️ Excluir", key=f"del_{q['id']}"):
                                db.collection('questoes').document(q['id']).delete()
                                st.rerun()
                        
                        # Professor/Admin pode solicitar correção
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
                            c_act1.warning(f"Correção pendente: {q.get('motivo_correcao')} (por {q.get('solicitado_por')})")

    # -------------------------------------------------------
    # ABA 2: ADICIONAR NOVA
    # -------------------------------------------------------
    with abas[1]:
        st.markdown("### Cadastrar Nova Questão")
        if tipo_user == "professor":
            st.info("ℹ️ Suas questões ficarão como 'Pendente' até aprovação de um administrador.")
            
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
                    
                    msg = "Questão salva e aprovada!" if status_inicial == "aprovada" else "Questão enviada para aprovação!"
                    st.success(msg)
                    st.rerun()
                else:
                    st.warning("Preencha a pergunta, o tema e pelo menos 2 opções.")

    # -------------------------------------------------------
    # ABA ADMIN: APROVAR PENDENTES
    # -------------------------------------------------------
    if tipo_user == "admin":
        with abas[2]:
            st.markdown("### ✅ Aprovação de Questões")
            if not pendentes:
                st.info("Nenhuma questão pendente.")
            else:
                for q in pendentes:
                    with st.expander(f"{q['tema']} | {q['pergunta']} (Por: {q.get('criado_por')})"):
                        st.write(f"**Opções:** {q.get('opcoes')}")
                        st.caption(f"Resposta: {q.get('resposta')}")
                        
                        c_apr, c_rej = st.columns(2)
                        if c_apr.button("Aprovar", key=f"apr_{q['id']}"):
                            db.collection('questoes').document(q['id']).update({"status": "aprovada"})
                            st.success("Aprovada!")
                            st.rerun()
                        if c_rej.button("Rejeitar/Excluir", key=f"rej_{q['id']}"):
                            db.collection('questoes').document(q['id']).delete()
                            st.warning("Excluída.")
                            st.rerun()
                            
        # ABA ADMIN: CORREÇÕES
        with abas[3]:
            st.markdown("### 🔧 Solicitações de Correção")
            if not correcoes:
                st.info("Nenhuma solicitação em aberto.")
            else:
                for q in correcoes:
                    with st.container(border=True):
                        st.markdown(f"**Questão:** {q['pergunta']}")
                        st.error(f"📢 Motivo: {q.get('motivo_correcao')} (Reportado por: {q.get('solicitado_por')})")
                        
                        with st.expander("Editar e Corrigir"):
                            with st.form(key=f"fix_{q['id']}"):
                                n_perg = st.text_area("Pergunta:", value=q['pergunta'])
                                # Simplificação: Editar apenas a pergunta e resposta aqui. 
                                # Para editar opções, precisaria explodir a lista.
                                # Vamos permitir limpar a flag ou excluir.
                                
                                c_fix1, c_fix2 = st.columns(2)
                                salvar_fix = c_fix1.form_submit_button("Salvar e Marcar como Resolvido")
                                
                                if salvar_fix:
                                    db.collection('questoes').document(q['id']).update({
                                        "pergunta": n_perg,
                                        "solicitacao_correcao": False,
                                        "motivo_correcao": firestore.DELETE_FIELD
                                    })
                                    st.success("Resolvido!")
                                    st.rerun()
                                    
                        if st.button("Ignorar/Remover Flag", key=f"ign_{q['id']}"):
                             db.collection('questoes').document(q['id']).update({
                                "solicitacao_correcao": False,
                                "motivo_correcao": firestore.DELETE_FIELD
                             })
                             st.rerun()

    # -------------------------------------------------------
    # ABA PROFESSOR: MINHAS PENDENTES
    # -------------------------------------------------------
    elif tipo_user == "professor":
        with abas[2]:
            st.markdown("### ⏳ Minhas Questões em Análise")
            if not minhas_pendentes:
                st.info("Você não tem questões aguardando aprovação.")
            else:
                for q in minhas_pendentes:
                    st.info(f"[{q['tema']}] {q['pergunta']}")


# =========================================
# GESTÃO DE EXAME DE FAIXA (Mantida igual)
# =========================================
def gestao_exame_de_faixa():
    # ... (código anterior da gestão de exame, sem alterações) ...
    st.markdown("<h1 style='color:#FFD700;'>📜 Gestão de Exame</h1>", unsafe_allow_html=True)
    
    user_logado = st.session_state.usuario
    if user_logado["tipo"] not in ["admin", "professor"]:
        st.error("Acesso negado.")
        return

    tab_prova, tab_alunos = st.tabs(["📝 Montar Prova", "✅ Habilitar Alunos"])

    # ABA 1: MONTAR PROVA
    with tab_prova:
        st.subheader("Configurar Prova")
        db = get_db()
        
        faixas = ["Cinza", "Amarela", "Laranja", "Verde", "Azul", "Roxa", "Marrom", "Preta"]
        faixa = st.selectbox("Selecione a faixa:", faixas, key="sel_faixa_prova")

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

        # CARREGA APENAS QUESTÕES APROVADAS
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
                        st.caption(f"✅ Resposta: {q.get('resposta')}")
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

    # ABA 2: HABILITAR ALUNOS (Mantida igual)
    with tab_alunos:
        st.subheader("Autorizar Alunos")
        db = get_db()

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
                    nome = users_map.get(uid, "Desc")
                    eq = equipes_map.get(eid, "-")
                    hab = d.get('exame_habilitado', False)
                    
                    p_str = "Bloqueado"
                    if hab:
                        try:
                            i = d.get('exame_inicio').replace(tzinfo=None).strftime("%d/%m %H:%M")
                            f = d.get('exame_fim').replace(tzinfo=None).strftime("%d/%m %H:%M")
                            p_str = f"Lib: {i} até {f}"
                        except: p_str = "Liberado"

                    c = st.columns([3, 2, 2, 3, 2])
                    c[0].write(nome)
                    c[1].write(eq)
                    c[2].write(d.get('faixa_atual'))
                    c[3].write(p_str)
                    
                    if hab:
                        if c[4].button("Bloquear", key=f"blk_{doc.id}"):
                            db.collection('alunos').document(doc.id).update({"exame_habilitado": False})
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
```

### Agora o `views/aluno.py`

Também precisamos garantir que os alunos **só vejam questões aprovadas** quando forem treinar no Modo Rola.

Substitua a função `carregar_questoes_firestore` em **`views/aluno.py`** por esta versão filtrada:

```python
@st.cache_data(ttl=300) 
def carregar_questoes_firestore():
    db = get_db()
    todas_questoes = []
    try:
        # FILTRO: Apenas questões com status 'aprovada' ou que não tenham status (legado)
        docs_questoes = list(db.collection('questoes').stream())
        if docs_questoes:
            for d in docs_questoes:
                dados = d.to_dict()
                # Se não tiver campo 'status', assume aprovada (legado). 
                # Se tiver, só passa se for 'aprovada'.
                if dados.get('status', 'aprovada') == 'aprovada':
                    todas_questoes.append(dados)
    except: pass
    
    # ... (código de fallback local continua igual) ...
    return todas_questoes
