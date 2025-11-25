import streamlit as st
import pandas as pd
import bcrypt
from database import get_db
from utils import formatar_e_validar_cpf, carregar_questoes, salvar_questoes, carregar_todas_questoes
import os
import json
from datetime import datetime, time

# =========================================
# GESTÃO DE USUÁRIOS
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
        user_data = user_ref.get().to_dict()

        if not user_data:
            st.error("Usuário não encontrado.")
            return

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
                st.success("Usuário excluído.")
                st.rerun()

# =========================================
# GESTÃO DE QUESTÕES
# =========================================
def gestao_questoes():
    """Gestão de Banco de Questões (JSON)."""
    
    user = st.session_state.usuario
    if user["tipo"] not in ["admin", "professor"]:
        st.error("Acesso negado.")
        return
    
    st.markdown("<h1 style='color:#FFD700;'>🧠 Banco de Questões</h1>", unsafe_allow_html=True)

    os.makedirs("questions", exist_ok=True)
    temas_existentes = [f.replace(".json", "") for f in os.listdir("questions") if f.endswith(".json")]
    
    c1, c2 = st.columns([3, 1])
    tema_sel = c1.selectbox("Tema:", ["Novo Tema"] + temas_existentes)
    
    tema_atual = st.text_input("Nome do novo tema:") if tema_sel == "Novo Tema" else tema_sel

    questoes = carregar_questoes(tema_atual) if tema_atual else []

    with st.expander("➕ Adicionar Nova Questão", expanded=False):
        with st.form("form_add_q"):
            pergunta = st.text_area("Pergunta:")
            cols = st.columns(5)
            opts = [cols[i].text_input(f"Opção {l}") for i, l in enumerate("ABCDE")]
            resp = st.selectbox("Correta:", list("ABCDE"))
            if st.form_submit_button("Salvar"):
                if pergunta and tema_atual:
                    nova = {
                        "pergunta": pergunta,
                        "opcoes": [f"{l}) {t}" for l, t in zip("ABCDE", opts) if t],
                        "resposta": resp
                    }
                    questoes.append(nova)
                    salvar_questoes(tema_atual, questoes)
                    st.success("Salvo!")
                    st.rerun()

    st.markdown("### Questões Existentes")
    if questoes:
        for i, q in enumerate(questoes):
            with st.expander(f"{i+1}. {q['pergunta']}"):
                st.write(q['opcoes'])
                st.caption(f"Resposta: {q['resposta']}")
                if st.button("Excluir", key=f"dq_{i}"):
                    questoes.pop(i)
                    salvar_questoes(tema_atual, questoes)
                    st.rerun()

# =========================================
# GESTÃO DE EXAME DE FAIXA (ATUALIZADO)
# =========================================
def gestao_exame_de_faixa():
    st.markdown("<h1 style='color:#FFD700;'>📜 Gestão de Exame</h1>", unsafe_allow_html=True)
    
    user_logado = st.session_state.usuario
    if user_logado["tipo"] not in ["admin", "professor"]:
        st.error("Acesso negado.")
        return

    tab_prova, tab_alunos = st.tabs(["📝 Montar Prova", "✅ Habilitar Alunos"])

    # ---------------------------------------------------------
    # ABA 1: MONTAR PROVA
    # ---------------------------------------------------------
    with tab_prova:
        st.subheader("Configurar Perguntas do Exame")
        
        faixas = ["Cinza", "Amarela", "Laranja", "Verde", "Azul", "Roxa", "Marrom", "Preta"]
        faixa = st.selectbox("Selecione a faixa do exame:", faixas, key="sel_faixa_prova")

        exame_path = f"exames/faixa_{faixa.lower()}.json"
        os.makedirs("exames", exist_ok=True)
        
        try:
            with open(exame_path, "r", encoding="utf-8") as f: exame = json.load(f)
        except: exame = {"questoes": [], "faixa": faixa}

        todas = carregar_todas_questoes()
        if not todas:
            st.warning("Cadastre questões no Banco de Questões primeiro.")
        else:
            temas = sorted(list(set(q["tema"] for q in todas)))
            filtro = st.selectbox("Filtrar por tema:", ["Todos"] + temas)
            q_exibir = [q for q in todas if q["tema"] == filtro] if filtro != "Todos" else todas
            
            perguntas_no_exame = [q['pergunta'] for q in exame.get('questoes', [])]

            with st.form("add_q_exame"):
                st.markdown("#### Selecionar Questões Disponíveis")
                selecionadas = []
                
                for i, q in enumerate(q_exibir):
                    if q['pergunta'] not in perguntas_no_exame:
                        c_chk, c_det = st.columns([1, 15])
                        with c_chk:
                            checked = st.checkbox("Add", key=f"chk_{i}", label_visibility="collapsed")
                            if checked: selecionadas.append(q)
                        with c_det:
                            st.markdown(f"**[{q['tema']}]** {q['pergunta']}")
                            if 'opcoes' in q:
                                for op in q['opcoes']:
                                    st.markdown(f"<span style='color: #aaa; margin-left: 15px;'>• {op}</span>", unsafe_allow_html=True)
                            st.caption(f"✅ Gabarito: **{q.get('resposta', '?')}**")
                            st.markdown("---")
                
                if st.form_submit_button("➕ Adicionar ao Exame"):
                    if 'questoes' not in exame: exame['questoes'] = []
                    exame['questoes'].extend(selecionadas)
                    with open(exame_path, "w", encoding="utf-8") as f:
                        json.dump(exame, f, indent=4, ensure_ascii=False)
                    st.success("Questões adicionadas!")
                    st.rerun()

            st.markdown("---")
            st.markdown(f"#### Questões Atuais ({len(exame.get('questoes', []))})")
            if 'questoes' in exame and exame['questoes']:
                for i, q in enumerate(exame['questoes']):
                    with st.expander(f"{i+1}. {q['pergunta']} ({q.get('tema','?')})"):
                        if 'opcoes' in q:
                            for op in q['opcoes']: st.write(f"• {op}")
                        st.caption(f"Resposta Correta: {q.get('resposta')}")
                        if st.button("Remover Questão", key=f"rm_ex_{i}"):
                            exame['questoes'].pop(i)
                            with open(exame_path, "w", encoding="utf-8") as f:
                                json.dump(exame, f, indent=4, ensure_ascii=False)
                            st.rerun()
            else:
                st.info("Nenhuma questão adicionada.")

    # ---------------------------------------------------------
    # ABA 2: HABILITAR ALUNOS (CORRIGIDO)
    # ---------------------------------------------------------
    with tab_alunos:
        st.subheader("Autorizar Alunos para o Exame")
        db = get_db()

        # --- 1. LÓGICA DE PERMISSÃO (Recuperada) ---
        equipes_permitidas = []
        if user_logado['tipo'] == 'admin':
            equipes_permitidas = None # Admin vê tudo
        else:
            # Busca equipes onde é responsável
            q1 = db.collection('equipes').where('professor_responsavel_id', '==', user_logado['id']).stream()
            equipes_permitidas = [d.id for d in q1]
            
            # Busca equipes onde é professor vinculado
            q2 = db.collection('professores').where('usuario_id', '==', user_logado['id']).where('status_vinculo', '==', 'ativo').stream()
            for d in q2:
                eid = d.to_dict().get('equipe_id')
                if eid and eid not in equipes_permitidas:
                    equipes_permitidas.append(eid)
            
            if not equipes_permitidas:
                st.warning("Você não possui equipes vinculadas para gerenciar alunos.")
                return # Encerra aqui se não tiver equipe

        # --- 2. BUSCA ALUNOS ---
        alunos_ref = db.collection('alunos')
        if equipes_permitidas:
            # Limita a 10 para evitar erro do 'in'
            query = alunos_ref.where('equipe_id', 'in', equipes_permitidas[:10])
        else:
            query = alunos_ref # Admin

        docs_alunos = list(query.stream())
        
        if not docs_alunos:
            st.info("Nenhum aluno encontrado nas suas equipes.")
        else:
            users_map = {d.id: d.to_dict().get('nome','?') for d in db.collection('usuarios').stream()}
            equipes_map = {d.id: d.to_dict().get('nome','?') for d in db.collection('equipes').stream()}
            
            st.markdown("#### Configurar Período")
            c_ini, c_fim = st.columns(2)
            d_ini = c_ini.date_input("Início:", value=datetime.now())
            h_ini = c_ini.time_input("Hora Início:", value=time(0, 0))
            d_fim = c_fim.date_input("Fim:", value=datetime.now())
            h_fim = c_fim.time_input("Hora Fim:", value=time(23, 59))
            
            dt_inicio = datetime.combine(d_ini, h_ini)
            dt_fim = datetime.combine(d_fim, h_fim)

            if dt_inicio >= dt_fim:
                st.warning("Data fim deve ser maior que início.")

            st.markdown("---")
            
            # Cabeçalho da Tabela
            h = st.columns([3, 2, 2, 3, 2])
            h[0].markdown("**Aluno**")
            h[1].markdown("**Equipe**")
            h[2].markdown("**Faixa**")
            h[3].markdown("**Período**")
            h[4].markdown("**Ação**")
            st.markdown("---")
            
            for doc in docs_alunos:
                d = doc.to_dict()
                uid = d.get('usuario_id')
                eid = d.get('equipe_id')
                
                # Filtro extra para admin caso query traga tudo
                if equipes_permitidas is None or eid in equipes_permitidas:
                    nome_aluno = users_map.get(uid, "Desconhecido")
                    nome_equipe = equipes_map.get(eid, "Sem Equipe")
                    habilitado = d.get('exame_habilitado', False)
                    
                    # Formata datas
                    ini_salvo = d.get('exame_inicio')
                    fim_salvo = d.get('exame_fim')
                    periodo_str = "-"
                    if ini_salvo and fim_salvo:
                        try:
                            i_str = ini_salvo.replace(tzinfo=None).strftime("%d/%m %H:%M")
                            f_str = fim_salvo.replace(tzinfo=None).strftime("%d/%m %H:%M")
                            periodo_str = f"{i_str} até {f_str}"
                        except: pass

                    cols = st.columns([3, 2, 2, 3, 2])
                    cols[0].write(nome_aluno)
                    cols[1].write(nome_equipe)
                    cols[2].write(d.get('faixa_atual'))
                    cols[3].write(periodo_str)
                    
                    if habilitado:
                        if cols[4].button("⛔ Bloquear", key=f"bloq_{doc.id}"):
                            db.collection('alunos').document(doc.id).update({
                                "exame_habilitado": False, "exame_inicio": None, "exame_fim": None
                            })
                            st.rerun()
                    else:
                        if cols[4].button("✅ Habilitar", key=f"hab_{doc.id}"):
                            if dt_inicio < dt_fim:
                                db.collection('alunos').document(doc.id).update({
                                    "exame_habilitado": True, "exame_inicio": dt_inicio, "exame_fim": dt_fim
                                })
                                st.rerun()
                            else:
                                st.error("Datas inválidas.")
