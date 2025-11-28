import streamlit as st
import pandas as pd
import bcrypt
from datetime import datetime, time
from database import get_db
from firebase_admin import firestore

# =========================================
# 1. GESTÃO DE USUÁRIOS (COMPLETA)
# =========================================
def gestao_usuarios(usuario_logado):
    st.markdown("<h1 style='color:#FFD700;'>👥 Gestão de Usuários</h1>", unsafe_allow_html=True)
    db = get_db()
    
    # Carrega usuários
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
                faixas = ["Cinza e Branca", "Cinza", "Cinza e Preta", "Amarela e Branca","Amarela","Amarela e Preta", "Laranja e Branca","Laranja","Laranja e Preta", "Verde e Branca","Verde","Verde e Preta", "Azul", "Roxa", "Marrom", "Preta"]
                idx_f = faixas.index(usuario_selecionado['faixa_atual']) if usuario_selecionado['faixa_atual'] in faixas else 0
                novo_faixa = st.selectbox("Faixa Atual:", faixas, index=idx_f)
                
                st.markdown("---")
                st.markdown("##### 🔐 Alterar Senha (Opcional)")
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
# 2. GESTÃO DE QUESTÕES (CORRIGIDO)
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
    aprovadas = []; pendentes = []; temas_set = set()

    for doc in docs_q:
        d = doc.to_dict(); d['id'] = doc.id
        status = d.get('status', 'aprovada')
        if status == 'pendente': pendentes.append(d)
        else: aprovadas.append(d); temas_set.add(d.get('tema', 'Geral'))

    temas_existentes = sorted(list(temas_set))
    titulos = ["📚 Listar Questões", "➕ Nova Questão"]
    if tipo_user == "admin": titulos.append(f"✅ Aprovar ({len(pendentes)})")
    
    abas = st.tabs(titulos)
    
    # --- ABA 1: LISTAR ---
    with abas[0]:
        ft = st.selectbox("Filtrar por Tema:", ["Todos"] + temas_existentes)
        qx = [q for q in aprovadas if q.get('tema') == ft] if ft != "Todos" else aprovadas
        
        if not qx: st.info("Nenhuma questão encontrada.")
        else:
            st.write(f"Total: {len(qx)} questões")
            for q in qx:
                with st.container(border=True):
                    st.markdown(f"**[{q.get('tema')}]** {q.get('pergunta')}")
                    st.caption(f"Faixa: {q.get('faixa', 'Geral')} | Autor: {q.get('criado_por')}")
                    with st.expander("Ver Detalhes"):
                        st.write(f"Opções: {q.get('opcoes')}")
                        st.success(f"Resposta: {q.get('resposta')}")
                        if tipo_user == "admin":
                            if st.button("Excluir", key=f"del_q_{q['id']}"):
                                db.collection('questoes').document(q['id']).delete(); st.rerun()

    # --- ABA 2: CRIAR (CORREÇÃO DA VARIÁVEL c_op3) ---
    with abas[1]:
        st.subheader("Adicionar Nova Questão")
        with st.form("new_q"):
            c1, c2 = st.columns(2)
            tema = c1.text_input("Tema:")
            faixa = c2.selectbox("Faixa Alvo:", ["Geral","Branca", "Cinza e Branca", "Cinza", "Cinza e Preta", "Amarela e Branca","Amarela","Amarela e Preta", "Laranja e Branca","Laranja","Laranja e Preta", "Verde e Branca","Verde","Verde e Preta", "Azul", "Roxa", "Marrom", "Preta""])
            perg = st.text_area("Pergunta:")
            
            st.write("Alternativas:")
            c_op1, c_op2 = st.columns(2)
            op1 = c_op1.text_input("A)")
            op2 = c_op2.text_input("B)")
            
            # CORREÇÃO AQUI: Definindo explicitamente as colunas antes de usar
            c_op3, c_op4 = st.columns(2)
            op3 = c_op3.text_input("C)")
            op4 = c_op4.text_input("D)")
            
            resp_letra = st.selectbox("Correta:", ["A", "B", "C", "D"])
            
            if st.form_submit_button("💾 Salvar"):
                ops = [op1, op2, op3, op4]
                limpas = [o for o in ops if o.strip()]
                if len(limpas) < 2 or not tema or not perg:
                    st.warning("Preencha corretamente.")
                else:
                    mapa = {"A": op1, "B": op2, "C": op3, "D": op4}
                    st_init = "aprovada" if tipo_user == "admin" else "pendente"
                    db.collection('questoes').add({
                        "tema": tema, "faixa": faixa, "pergunta": perg,
                        "opcoes": limpas, "resposta": mapa[resp_letra],
                        "correta": mapa[resp_letra], "status": st_init,
                        "criado_por": user['nome'], "data": firestore.SERVER_TIMESTAMP
                    })
                    st.success("Questão salva!"); st.rerun()

    # --- ABA 3: APROVAR ---
    if tipo_user == "admin" and len(abas) > 2:
        with abas[2]:
            if not pendentes: st.success("Nada pendente.")
            for q in pendentes:
                with st.container(border=True):
                    st.write(f"**{q['pergunta']}**")
                    c1, c2 = st.columns(2)
                    if c1.button("✅ Aprovar", key=f"ok_{q['id']}"):
                        db.collection('questoes').document(q['id']).update({"status":"aprovada"}); st.rerun()
                    if c2.button("❌ Rejeitar", key=f"no_{q['id']}"):
                        db.collection('questoes').document(q['id']).delete(); st.rerun()

# =========================================
# 3. GESTÃO DE EXAME (LIBERAÇÃO)
# =========================================
def gestao_exame_de_faixa():
    st.markdown("<h1 style='color:#FFD700;'>📜 Gestão de Exame</h1>", unsafe_allow_html=True)
    db = get_db()

    with st.container(border=True):
        st.subheader("🗓️ Configurar Período")
        c1, c2 = st.columns(2)
        d_inicio = c1.date_input("Início:", datetime.now())
        d_fim = c2.date_input("Fim:", datetime.now())
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
        d = doc.to_dict(); d['id'] = doc.id
        nome_eq = "Sem Equipe"
        vinculo = list(db.collection('alunos').where('usuario_id', '==', doc.id).limit(1).stream())
        if vinculo:
            eid = vinculo[0].to_dict().get('equipe_id')
            if eid:
                eq = db.collection('equipes').document(eid).get()
                if eq.exists: nome_eq = eq.to_dict().get('nome')
        d['nome_equipe'] = nome_eq
        lista_alunos.append(d)

    if not lista_alunos: st.info("Sem alunos."); return

    cols = st.columns([3, 2, 2, 3, 1])
    cols[0].markdown("**Aluno**"); cols[1].markdown("**Equipe**"); cols[2].markdown("**Exame**"); cols[3].markdown("**Status**"); cols[4].markdown("**Ação**")
    st.markdown("---")

    faixas = ["Cinza", "Amarela", "Laranja", "Verde", "Azul", "Roxa", "Marrom", "Preta"]

    for aluno in lista_alunos:
        c1, c2, c3, c4, c5 = st.columns([3, 2, 2, 3, 1])
        c1.write(f"**{aluno.get('nome')}**")
        c2.write(aluno['nome_equipe'])
        
        idx = 0
        if aluno.get('faixa_exame') in faixas: idx = faixas.index(aluno.get('faixa_exame'))
        fx_sel = c3.selectbox("Faixa", faixas, index=idx, key=f"fx_{aluno['id']}", label_visibility="collapsed")

        habilitado = aluno.get('exame_habilitado', False)
        status = aluno.get('status_exame', 'pendente')
        
        if habilitado:
            msg = "🟢 Liberado"
            if status == 'aprovado': msg = "🏆 Aprovado"
            elif status == 'bloqueado': msg = "⛔ Bloqueado"
            elif status == 'reprovado': msg = "🔴 Reprovado"
            c4.caption(msg)
            if c5.button("⛔", key=f"off_{aluno['id']}"):
                db.collection('usuarios').document(aluno['id']).update({
                    "exame_habilitado": False, "exame_inicio": firestore.DELETE_FIELD,
                    "exame_fim": firestore.DELETE_FIELD, "faixa_exame": firestore.DELETE_FIELD,
                    "status_exame": "pendente", "motivo_bloqueio": firestore.DELETE_FIELD
                })
                st.rerun()
        else:
            c4.caption("⚪ Não autorizado")
            if c5.button("✅", key=f"on_{aluno['id']}"):
                db.collection('usuarios').document(aluno['id']).update({
                    "exame_habilitado": True, "faixa_exame": fx_sel,
                    "exame_inicio": dt_inicio.isoformat(), "exame_fim": dt_fim.isoformat(),
                    "status_exame": "pendente", "status_exame_em_andamento": False,
                    "motivo_bloqueio": firestore.DELETE_FIELD
                })
                st.toast(f"Liberado para {aluno.get('nome')}!")
                st.rerun()
        st.markdown("---")
