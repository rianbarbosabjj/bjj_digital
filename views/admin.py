import streamlit as st
import pandas as pd
import bcrypt
import random
import time 
from datetime import datetime, time as dtime 
from database import get_db
from firebase_admin import firestore

# Tenta importar do utils, se falhar define funções vazias para não quebrar
try:
    from utils import carregar_todas_questoes, salvar_questoes
except ImportError:
    def carregar_todas_questoes(): return []
    def salvar_questoes(t, q): pass

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
                        time.sleep(1)
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
                    time.sleep(1)
                    st.rerun()
                except Exception as e:
                    st.error(f"Erro ao excluir usuário: {e}")

# =========================================
# 2. GESTÃO DE QUESTÕES
# =========================================
def gestao_questoes():
    st.markdown("<h1 style='color:#FFD700;'>📝 Gestão de Questões</h1>", unsafe_allow_html=True)
    db = get_db()
    
    # Verifica permissão
    user = st.session_state.usuario
    tipo_user = str(user.get("tipo", "")).lower()
    if tipo_user not in ["admin", "professor"]:
        st.error("Acesso negado.")
        return

    tab1, tab2 = st.tabs(["📚 Banco de Questões", "➕ Adicionar Nova"])

    # --- TAB 1: LISTAR/EDITAR ---
    with tab1:
        questoes = carregar_todas_questoes()
        
        if not questoes:
            st.info("Nenhuma questão cadastrada no banco.")
        else:
            lista_q = []
            for q in questoes:
                lista_q.append({
                    "id": q.get("id"),
                    "pergunta": q.get("pergunta"),
                    "faixa": q.get("faixa", "Geral"),
                    "resposta_correta": q.get("resposta_correta") or q.get("resposta"),
                    "status": q.get("status", "aprovada")
                })
            
            df = pd.DataFrame(lista_q)
            
            # Edição na Tabela
            st.data_editor(
                df,
                column_config={
                    "status": st.column_config.SelectboxColumn(
                        "Status", options=["aprovada", "pendente", "arquivada"]
                    )
                },
                use_container_width=True,
                hide_index=True,
                key="editor_questoes"
            )
            
            # Deletar Questão
            st.markdown("---")
            col_del, _ = st.columns([1, 3])
            # Dropdown seguro
            opcoes_del = df["pergunta"].unique() if not df.empty else []
            if len(opcoes_del) > 0:
                q_to_del = col_del.selectbox("Selecionar para Excluir:", opcoes_del, key="sel_del")
                if col_del.button("🗑️ Excluir Questão", type="primary"):
                    try:
                        docs = db.collection('questoes').where('pergunta', '==', q_to_del).stream()
                        for doc in docs:
                            doc.reference.delete()
                        st.success("Questão excluída!")
                        time.sleep(1)
                        st.rerun()
                    except Exception as e:
                        st.error(f"Erro ao excluir: {e}")

    # --- TAB 2: ADICIONAR NOVA ---
    with tab2:
        with st.form("form_add_q"):
            pergunta = st.text_area("Enunciado da Pergunta:")
            c1, c2 = st.columns(2)
            faixa = c1.selectbox("Nível da Faixa:", ["Todas"] + FAIXAS_COMPLETAS)
            categoria = c2.text_input("Categoria (ex: Regras, História):", "Geral")
            
            st.markdown("**Alternativas:**")
            alt_a = st.text_input("A)")
            alt_b = st.text_input("B)")
            alt_c = st.text_input("C)")
            alt_d = st.text_input("D)")
            
            correta = st.selectbox("Qual a correta?", ["A", "B", "C", "D"])
            
            if st.form_submit_button("💾 Salvar Questão"):
                if pergunta and alt_a and alt_b:
                    nova_q = {
                        "pergunta": pergunta,
                        "faixa": faixa,
                        "categoria": categoria,
                        "alternativas": {
                            "A": alt_a, "B": alt_b, "C": alt_c, "D": alt_d
                        },
                        "resposta_correta": correta,
                        "status": "aprovada",
                        "criado_por": user.get('nome', 'Admin'),
                        "data_criacao": firestore.SERVER_TIMESTAMP
                    }
                    db.collection('questoes').add(nova_q)
                    st.success("Questão adicionada com sucesso!")
                    time.sleep(1)
                    st.rerun()
                else:
                    st.warning("Preencha pelo menos a pergunta e duas alternativas.")

# =========================================
# 3. GESTÃO DE EXAME
# =========================================
def gestao_exame_de_faixa():
    st.markdown("<h1 style='color:#FFD700;'>⚙️ Configuração de Exames</h1>", unsafe_allow_html=True)
    db = get_db()

    tab1, tab2, tab3 = st.tabs(["📝 Regras da Prova", "👁️ Visualizar", "✅ Autorizar Alunos"])

    # --- ABA 1: EDITOR DE REGRAS ---
    with tab1:
        st.subheader("Configurar Regras da Prova")
        faixa_config = st.selectbox("Selecione a Faixa:", ["Todas"] + FAIXAS_COMPLETAS, key="faixa_config")
        
        # Busca config atual
        config_ref = db.collection('config_exames').where('faixa', '==', faixa_config).stream()
        config_atual = {}
        doc_id_config = None
        for doc in config_ref:
            config_atual = doc.to_dict()
            doc_id_config = doc.id
            break
            
        with st.form("form_config_exame"):
            c1, c2, c3 = st.columns(3)
            # Default values
            def_qtd = int(config_atual.get('qtd_questoes', 10))
            def_tempo = int(config_atual.get('tempo_limite', 45))
            def_min = int(config_atual.get('aprovacao_minima', 70))
            
            qtd = c1.number_input("Qtd. Questões (Sorteio):", min_value=1, max_value=50, value=def_qtd)
            tempo = c2.number_input("Tempo (minutos):", min_value=10, max_value=180, value=def_tempo)
            nota = c3.number_input("Aprovação Mínima (%):", min_value=50, max_value=100, value=def_min)
            
            if st.form_submit_button("💾 Salvar Regras"):
                dados_config = {
                    "faixa": faixa_config, 
                    "tempo_limite": tempo, 
                    "qtd_questoes": qtd,
                    "aprovacao_minima": nota, 
                    "modo_selecao": "Aleatório", # Simplificado para evitar erro
                    "atualizado_em": firestore.SERVER_TIMESTAMP
                }
                if doc_id_config:
                    db.collection('config_exames').document(doc_id_config).update(dados_config)
                else:
                    db.collection('config_exames').add(dados_config)
                st.success(f"Regras salvas para faixa {faixa_config}!")
                time.sleep(1)
                st.rerun()

    # --- ABA 2: VISUALIZAR ---
    with tab2:
        st.info("Visualização das configurações atuais.")
        configs_stream = db.collection('config_exames').stream()
        for doc in configs_stream:
            d = doc.to_dict()
            st.markdown(f"**{d.get('faixa')}**: {d.get('qtd_questoes')} questões | {d.get('tempo_limite')} min | Mínimo {d.get('aprovacao_minima')}%")
            st.markdown("---")

    # --- ABA 3: AUTORIZAR ALUNOS ---
with tab3:
        with st.container(border=True):
            st.subheader("🗓️ Configurar Período de Exame")
            c1, c2 = st.columns(2)
            d_inicio = c1.date_input("Início:", datetime.now(), key="data_inicio_exame")
            d_fim = c2.date_input("Fim:", datetime.now(), key="data_fim_exame")
            c3, c4 = st.columns(2)
            
            h_inicio = c3.time_input("Hora Início:", dtime(0, 0), key="hora_inicio_exame")
            h_fim = c4.time_input("Hora Fim:", dtime(23, 59), key="hora_fim_exame")
            
            # Cria objetos datetime combinados
            dt_inicio = datetime.combine(d_inicio, h_inicio)
            dt_fim = datetime.combine(d_fim, h_fim)

        st.write("") 
        st.subheader("Lista de Alunos")
        
        try:
            alunos_ref = db.collection('usuarios').where('tipo_usuario', '==', 'aluno').stream()
            lista_alunos = []
            
            for doc in alunos_ref:
                d = doc.to_dict(); d['id'] = doc.id
                # Tenta buscar equipe
                vinculo = list(db.collection('alunos').where('usuario_id', '==', doc.id).limit(1).stream())
                nome_eq = "Sem Equipe"
                if vinculo:
                    try:
                        eid = vinculo[0].to_dict().get('equipe_id')
                        if eid:
                            eq_doc = db.collection('equipes').document(eid).get()
                            if eq_doc.exists: nome_eq = eq_doc.to_dict().get('nome', 'Sem Nome')
                    except: pass
                d['nome_equipe'] = nome_eq
                lista_alunos.append(d)

            if not lista_alunos: 
                st.info("Nenhum aluno cadastrado.")
            else:
                cols = st.columns([3, 2, 2, 2, 1])
                cols[0].markdown("**Aluno**")
                cols[1].markdown("**Equipe**")
                cols[2].markdown("**Exame**")
                cols[3].markdown("**Status**")
                cols[4].markdown("**Ação**")
                st.markdown("---")

                for aluno in lista_alunos:
                    aluno_id = aluno.get('id')
                    aluno_nome = aluno.get('nome', 'Sem Nome')
                    faixa_exame_atual = aluno.get('faixa_exame', 'Branca')
                    
                    c1, c2, c3, c4, c5 = st.columns([3, 2, 2, 2, 1])
                    c1.write(f"**{aluno_nome}**")
                    c2.write(aluno.get('nome_equipe'))
                    
                    idx = FAIXAS_COMPLETAS.index(faixa_exame_atual) if faixa_exame_atual in FAIXAS_COMPLETAS else 0
                    fx_sel = c3.selectbox("Faixa", FAIXAS_COMPLETAS, index=idx, key=f"fx_{aluno_id}", label_visibility="collapsed")
                    
                    habilitado = aluno.get('exame_habilitado', False)
                    status = aluno.get('status_exame', 'pendente')
                    
                    # --- RESTAURAÇÃO DA FUNCIONALIDADE DETALHADA ---
                    if habilitado:
                        msg = "🟢 Liberado"
                        try:
                            raw_fim = aluno.get('exame_fim')
                            if raw_fim:
                                if isinstance(raw_fim, str):
                                    dt_obj = datetime.fromisoformat(raw_fim.replace('Z', '+00:00'))
                                    msg += f" (até {dt_obj.strftime('%d/%m/%Y %H:%M')})"
                        except: pass
                        
                        if status == 'aprovado': msg = "🏆 Aprovado"
                        elif status == 'bloqueado': msg = "⛔ Bloqueado"
                        elif status == 'reprovado': msg = "🔴 Reprovado"
                        elif status == 'em_andamento': msg = "🟡 Em Andamento"
                        
                        c4.write(msg)
                        if c5.button("⛔", key=f"off_btn_{aluno_id}"):
                            update_data = {"exame_habilitado": False, "status_exame": "pendente"}
                            for campo in ["exame_inicio", "exame_fim", "faixa_exame", "motivo_bloqueio", "status_exame_em_andamento"]:
                                if campo in aluno: update_data[campo] = firestore.DELETE_FIELD
                            db.collection('usuarios').document(aluno_id).update(update_data)
                            st.rerun()
                    else:
                        c4.write("⚪ Não autorizado")
                        if c5.button("✅", key=f"on_btn_{aluno_id}"):
                            db.collection('usuarios').document(aluno_id).update({
                                "exame_habilitado": True,
                                "faixa_exame": fx_sel,
                                "exame_inicio": dt_inicio.isoformat(), 
                                "exame_fim": dt_fim.isoformat(),
                                "status_exame": "pendente",
                                "status_exame_em_andamento": False
                            })
                            st.success(f"Liberado!")
                            time.sleep(0.5)
                            st.rerun()
                    st.markdown("---")

        except Exception as e:
            st.error(f"Erro ao carregar lista de alunos: {e}")
