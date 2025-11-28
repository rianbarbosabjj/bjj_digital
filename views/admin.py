import streamlit as st
import pandas as pd
from datetime import datetime, time
from database import get_db
from firebase_admin import firestore

# =========================================
# GESTÃO DE USUÁRIOS (ROBUSTA)
# =========================================
def gestao_usuarios(usuario_logado):
    st.markdown("<h1 style='color:#FFD700;'>👥 Gestão de Usuários</h1>", unsafe_allow_html=True)
    db = get_db()
    
    # 1. Carrega usuários com tratamento de erro (evita crash do Pandas)
    users_ref = db.collection('usuarios').stream()
    lista_users = []
    
    for doc in users_ref:
        d = doc.to_dict()
        # Garante que todos os campos existam para o DataFrame não quebrar
        user_safe = {
            "id": doc.id,
            "nome": d.get('nome', 'Sem Nome'),
            "email": d.get('email', '-'),
            "cpf": d.get('cpf', '-'),
            "tipo_usuario": d.get('tipo_usuario', 'aluno'),
            "faixa_atual": d.get('faixa_atual', '-'),
            "auth_provider": d.get('auth_provider', 'local')
        }
        lista_users.append(user_safe)
        
    if not lista_users:
        st.warning("Nenhum usuário encontrado.")
        return

    # 2. Filtros
    filtro = st.text_input("🔍 Buscar por Nome, Email ou CPF:")
    
    df = pd.DataFrame(lista_users)
    
    if filtro:
        # Filtra ignorando maiúsculas/minúsculas
        f = filtro.upper()
        df = df[
            df['nome'].str.upper().str.contains(f) | 
            df['email'].str.upper().str.contains(f) | 
            df['cpf'].str.contains(f)
        ]

    # 3. Tabela Visual
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
    
    # 4. Área de Edição Rápida
    st.markdown("### ✏️ Editar Usuário")
    col_sel, col_btn = st.columns([3, 1])
    
    # Cria lista para o selectbox
    opcoes_usuarios = df.to_dict('records')
    usuario_selecionado = col_sel.selectbox(
        "Selecione para editar:", 
        opcoes_usuarios, 
        format_func=lambda x: f"{x['nome']} ({x['email']})"
    )
    
    if usuario_selecionado:
        with st.expander(f"Editar dados de {usuario_selecionado['nome']}", expanded=True):
            with st.form(key=f"edit_user_{usuario_selecionado['id']}"):
                c1, c2 = st.columns(2)
                novo_tipo = c1.selectbox(
                    "Perfil de Acesso:", 
                    ["aluno", "professor", "admin"], 
                    index=["aluno", "professor", "admin"].index(usuario_selecionado['tipo_usuario']) if usuario_selecionado['tipo_usuario'] in ["aluno", "professor", "admin"] else 0
                )
                nova_faixa = c2.selectbox(
                    "Faixa Atual:", 
                    ["Branca", "Cinza", "Amarela", "Laranja", "Verde", "Azul", "Roxa", "Marrom", "Preta"],
                    index=["Branca", "Cinza", "Amarela", "Laranja", "Verde", "Azul", "Roxa", "Marrom", "Preta"].index(usuario_selecionado['faixa_atual']) if usuario_selecionado['faixa_atual'] in ["Branca", "Cinza", "Amarela", "Laranja", "Verde", "Azul", "Roxa", "Marrom", "Preta"] else 0
                )
                
                if st.form_submit_button("💾 Salvar Alterações"):
                    db.collection('usuarios').document(usuario_selecionado['id']).update({
                        "tipo_usuario": novo_tipo,
                        "faixa_atual": nova_faixa
                    })
                    st.success("Usuário atualizado com sucesso!")
                    st.rerun()

# =========================================
# GESTÃO DE QUESTÕES
# =========================================
def gestao_questoes():
    st.markdown("<h1 style='color:#FFD700;'>🧠 Gestão de Questões</h1>", unsafe_allow_html=True)
    st.info("Funcionalidade de edição de banco de questões em desenvolvimento.")

# =========================================
# GESTÃO DE EXAME (CORRIGIDO E OTIMIZADO)
# =========================================
def gestao_exame_de_faixa():
    st.markdown("<h1 style='color:#FFD700;'>📜 Gestão de Exame</h1>", unsafe_allow_html=True)
    db = get_db()

    # --- 1. CONFIGURAÇÃO GERAL DE DATA/HORA ---
    with st.container(border=True):
        st.subheader("🗓️ Configurar Período do Exame")
        st.caption("Defina a data e hora que será gravada ao autorizar o aluno.")
        
        c1, c2 = st.columns(2)
        d_inicio = c1.date_input("Data Início:", datetime.now())
        d_fim = c2.date_input("Data Fim:", datetime.now())
        
        c3, c4 = st.columns(2)
        h_inicio = c3.time_input("Hora Início:", time(0, 0))
        h_fim = c4.time_input("Hora Fim:", time(23, 59))

        # Monta os objetos datetime
        dt_inicio = datetime.combine(d_inicio, h_inicio)
        dt_fim = datetime.combine(d_fim, h_fim)

    st.write("") 

    # --- 2. LISTAGEM DE ALUNOS ---
    st.subheader("Autorizar Alunos")
    
    # Busca apenas alunos
    alunos_ref = db.collection('usuarios').where('tipo_usuario', '==', 'aluno').stream()
    lista_alunos = []
    
    for doc in alunos_ref:
        d = doc.to_dict()
        d['id'] = doc.id
        
        # Busca nome da equipe (Extra)
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
        st.info("Nenhum aluno cadastrado no sistema.")
        return

    # Cabeçalho da Tabela
    cols = st.columns([3, 2, 2, 3, 1])
    cols[0].markdown("**Aluno**")
    cols[1].markdown("**Equipe**")
    cols[2].markdown("**Exame (Faixa)**")
    cols[3].markdown("**Status Atual**")
    cols[4].markdown("**Ação**")
    st.markdown("---")

    faixas_opcoes = ["Cinza", "Amarela", "Laranja", "Verde", "Azul", "Roxa", "Marrom", "Preta"]

    # Renderiza cada aluno
    for aluno in lista_alunos:
        c1, c2, c3, c4, c5 = st.columns([3, 2, 2, 3, 1])
        
        # Nome e Equipe
        c1.write(f"**{aluno.get('nome', 'Sem Nome')}**")
        c2.write(aluno['nome_equipe'])
        
        # Seletor de Faixa (Exame a ser aplicado)
        key_faixa = f"sel_fx_{aluno['id']}"
        
        # Define índice padrão do selectbox
        idx_padrao = 0
        faixa_salva = aluno.get('faixa_exame')
        if faixa_salva in faixas_opcoes:
            idx_padrao = faixas_opcoes.index(faixa_salva)
            
        faixa_selecionada = c3.selectbox("Faixa", faixas_opcoes, index=idx_padrao, key=key_faixa, label_visibility="collapsed")

        # Status Visual
        habilitado = aluno.get('exame_habilitado', False)
        status_prova = aluno.get('status_exame', 'pendente')
        
        if habilitado:
            # Mostra status bonito
            msg_status = "🟢 Liberado"
            fim_str = "?"
            
            # Tenta formatar a data de fim para mostrar
            raw_fim = aluno.get('exame_fim')
            if raw_fim:
                try:
                    # Se for string ISO
                    if isinstance(raw_fim, str): 
                        fim_fmt = datetime.fromisoformat(raw_fim).strftime('%d/%m')
                    else: # Se for timestamp/datetime
                        fim_fmt = raw_fim.strftime('%d/%m')
                    msg_status += f" (até {fim_fmt})"
                except: pass

            if status_prova == 'aprovado': msg_status = "🏆 Aprovado"
            elif status_prova == 'reprovado': msg_status = "🔴 Reprovado"
            elif status_prova == 'bloqueado': msg_status = "⛔ Bloqueado"
            
            c4.caption(msg_status)
            
            # Botão para DESABILITAR
            if c5.button("⛔", key=f"btn_off_{aluno['id']}", help="Cancelar autorização"):
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
            
            # Botão para HABILITAR (O QUE GRAVA OS DADOS)
            if c5.button("✅", key=f"btn_on_{aluno['id']}", help="Autorizar Exame"):
                
                # Grava os dados essenciais para o aluno.py funcionar
                dados_update = {
                    "exame_habilitado": True,
                    "faixa_exame": faixa_selecionada, # A faixa escolhida no dropdown
                    "exame_inicio": dt_inicio.isoformat(), # Formato ISO seguro
                    "exame_fim": dt_fim.isoformat(),
                    "status_exame": "pendente", # Reseta para ele poder fazer
                    "status_exame_em_andamento": False,
                    "motivo_bloqueio": firestore.DELETE_FIELD
                }
                
                db.collection('usuarios').document(aluno['id']).update(dados_update)
                st.toast(f"Exame liberado para {aluno.get('nome')}!")
                st.rerun()
        
        st.markdown("---")
