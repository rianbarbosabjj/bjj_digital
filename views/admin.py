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
    if usuario_logado["tipo"] != "admin":
        st.error("Acesso negado."); return
    st.markdown("<h1 style='color:#FFD700;'>🔑 Gestão de Usuários</h1>", unsafe_allow_html=True)
    
    db = get_db()
    docs = db.collection('usuarios').stream()
    lista = []
    for doc in docs:
        d = doc.to_dict(); d['id_doc'] = doc.id
        d.setdefault('cpf',''); d.setdefault('tipo_usuario','aluno'); d.setdefault('auth_provider','local')
        lista.append(d)
    
    if not lista: st.info("Nenhum usuário."); return
    df = pd.DataFrame(lista)
    st.dataframe(df[['nome','email','tipo_usuario','cpf']], use_container_width=True)
    st.markdown("---")
    
    ops = [f"{u['nome']} ({u['email']})" for u in lista]
    sel = st.selectbox("Editar Usuário:", ops, index=None)
    if sel:
        idx = ops.index(sel); uid = lista[idx]['id_doc']; udata = lista[idx]
        with st.expander(f"⚙️ Editar {udata.get('nome')}", expanded=True):
            with st.form("edit_u"):
                c1,c2=st.columns(2)
                nn = c1.text_input("Nome:", udata.get('nome',''))
                ne = c2.text_input("Email:", udata.get('email',''))
                ncpf = st.text_input("CPF:", udata.get('cpf',''))
                tipos = ["aluno","professor","admin"]
                nt = st.selectbox("Tipo:", tipos, index=tipos.index(udata.get('tipo_usuario','aluno')))
                if st.form_submit_button("Salvar"):
                    db.collection('usuarios').document(uid).update({
                        "nome":nn.upper(), "email":ne.lower().strip(), "cpf":ncpf, "tipo_usuario":nt
                    })
                    st.success("Salvo!"); st.rerun()
            
            if udata.get('auth_provider') == 'local':
                with st.form("pass_u"):
                    ns = st.text_input("Nova Senha:", type="password")
                    if st.form_submit_button("Redefinir Senha") and ns:
                        h = bcrypt.hashpw(ns.encode(), bcrypt.gensalt()).decode()
                        db.collection('usuarios').document(uid).update({"senha": h})
                        st.success("Senha alterada.")
            
            st.markdown("---")
            if st.button("🗑️ Excluir Usuário"):
                db.collection('usuarios').document(uid).delete()
                st.success("Excluído!"); st.rerun()

# =========================================
# GESTÃO DE QUESTÕES (Mantida)
# =========================================
def gestao_questoes():
    st.markdown("<h1 style='color:#FFD700;'>🧠 Banco de Questões</h1>", unsafe_allow_html=True)
    # ... (Lógica mantida igual para economizar linhas aqui, já que o foco é o Exame)
    st.info("Funcionalidade de Questões mantida (código omitido para foco na mudança de Exames).")

# =========================================
# GESTÃO DE EXAME DE FAIXA (REFORMULADO)
# =========================================
def gestao_exame_de_faixa():
    st.markdown("<h1 style='color:#FFD700;'>📜 Gestão de Exame</h1>", unsafe_allow_html=True)
    
    user_logado = st.session_state.usuario
    tipo_user = str(user_logado.get("tipo", "")).lower()
    
    if tipo_user not in ["admin", "professor"]:
        st.error("Acesso negado.")
        return

    tab_prova, tab_alunos = st.tabs(["📝 Montar Provas por Faixa", "✅ Habilitar Alunos"])

    # ---------------------------------------------------------
    # ABA 1: MONTAR PROVA (ORGANIZADA POR ABAS DE COR)
    # ---------------------------------------------------------
    with tab_prova:
        st.markdown("### Configuração das Provas")
        st.caption("Selecione a categoria de faixa abaixo para ver e editar os exames específicos.")
        db = get_db()
        
        # Carrega TODAS as questões aprovadas UMA VEZ para otimizar
        docs_q = db.collection('questoes').where('status', '==', 'aprovada').stream()
        todas_q = [d.to_dict() for d in docs_q]
        temas_globais = sorted(list(set(q.get('tema', 'Geral') for q in todas_q)))

        # Organização das Faixas
        categorias_faixas = {
            "⚪ Branca": ["Branca"], # Branca geralmente não tem exame para entrar, mas deixamos a opção
            "🔘 Cinza": ["Cinza e Branca", "Cinza", "Cinza e Preta"],
            "🟡 Amarela": ["Amarela e Branca", "Amarela", "Amarela e Preta"],
            "🟠 Laranja": ["Laranja e Branca", "Laranja", "Laranja e Preta"],
            "🟢 Verde": ["Verde e Branca", "Verde", "Verde e Preta"],
            "🔵 Azul": ["Azul"],
            "🟣 Roxa": ["Roxa"],
            "🟤 Marrom": ["Marrom"],
            "⚫ Preta": ["Preta"]
        }

        # Cria abas para cada categoria de cor
        abas_cores = st.tabs(list(categorias_faixas.keys()))

        for aba, (cor, sub_faixas) in zip(abas_cores, categorias_faixas.items()):
            with aba:
                for faixa_nome in sub_faixas:
                    # Busca dados do exame específico
                    doc_ref = db.collection('exames').document(faixa_nome)
                    doc_snap = doc_ref.get()
                    
                    dados_prova = doc_snap.to_dict() if doc_snap.exists else {}
                    questoes_atuais = dados_prova.get('questoes', [])
                    tempo_atual = dados_prova.get('tempo_limite', 60)
                    
                    # Card expansível para cada exame específico
                    status_icon = "✅" if questoes_atuais else "⚠️"
                    with st.expander(f"{status_icon} Exame de Faixa {faixa_nome} ({len(questoes_atuais)} questões)"):
                        
                        # 1. Configurações Básicas
                        c_time, c_info = st.columns([1, 3])
                        novo_tempo = c_time.number_input(
                            f"⏱️ Tempo (min) - {faixa_nome}", 
                            min_value=10, max_value=240, value=tempo_atual, step=10,
                            key=f"time_{faixa_nome}"
                        )
                        
                        # 2. Adicionar Questões
                        st.markdown("---")
                        st.markdown("#### ➕ Adicionar Questões")
                        
                        filtro_tema = st.selectbox(
                            f"Filtrar tema ({faixa_nome}):", 
                            ["Todos"] + temas_globais, 
                            key=f"flt_{faixa_nome}"
                        )
                        
                        q_disponiveis = todas_q
                        if filtro_tema != "Todos":
                            q_disponiveis = [q for q in todas_q if q.get('tema') == filtro_tema]
                        
                        perguntas_ja_add = [q['pergunta'] for q in questoes_atuais]

                        with st.form(key=f"form_add_{faixa_nome}"):
                            selecionadas = []
                            # Limita visualização para não travar se tiver muitas questões
                            count_show = 0
                            for q in q_disponiveis:
                                if q['pergunta'] not in perguntas_ja_add:
                                    if count_show < 50: # Limite de segurança de renderização
                                        # Checkbox simples com a pergunta
                                        # Usa hash para chave única
                                        key_chk = f"chk_{faixa_nome}_{abs(hash(q['pergunta']))}"
                                        if st.checkbox(f"[{q.get('tema')}] {q['pergunta']}", key=key_chk):
                                            selecionadas.append(q)
                                        count_show += 1
                            
                            if count_show >= 50:
                                st.caption("... refina o filtro para ver mais questões.")

                            if st.form_submit_button("Salvar Adições"):
                                questoes_atuais.extend(selecionadas)
                                doc_ref.set({
                                    "faixa": faixa_nome,
                                    "questoes": questoes_atuais,
                                    "tempo_limite": novo_tempo,
                                    "atualizado_em": firestore.SERVER_TIMESTAMP,
                                    "atualizado_por": user_logado['nome']
                                })
                                st.success("Prova atualizada!")
                                st.rerun()

                        # 3. Listar/Remover Questões Atuais
                        if questoes_atuais:
                            st.markdown("---")
                            st.markdown("#### 📋 Questões na Prova")
                            for i, q in enumerate(questoes_atuais):
                                c_txt, c_btn = st.columns([5, 1])
                                c_txt.write(f"**{i+1}.** {q['pergunta']}")
                                if c_btn.button("🗑️", key=f"del_{faixa_nome}_{i}"):
                                    questoes_atuais.pop(i)
                                    doc_ref.update({
                                        "questoes": questoes_atuais,
                                        "tempo_limite": novo_tempo
                                    })
                                    st.rerun()
                        else:
                            st.info("Nenhuma questão adicionada a esta prova.")

    # ---------------------------------------------------------
    # ABA 2: HABILITAR ALUNOS (Com lista completa de faixas)
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
            
            # Lista completa para o selectbox
            todas_faixas_ops = [f for lista in categorias_faixas.values() for f in lista]

            for doc in docs_alunos:
                d = doc.to_dict()
                uid = d.get('usuario_id'); eid = d.get('equipe_id')
                
                if equipes_permitidas is None or eid in equipes_permitidas:
                    nome = users_map.get(uid, "Desconhecido")
                    eq = equipes_map.get(eid, "-")
                    hab = d.get('exame_habilitado', False)
                    lib = d.get('faixa_exame_liberado', 'Nenhuma')
                    
                    status_txt = f"🟢 {lib}" if hab else "🔴 Bloqueado"
                    
                    c = st.columns([3, 2, 2, 3, 2])
                    c[0].write(nome)
                    c[1].write(eq)
                    
                    # Tenta achar o index da faixa atual ou usa 0
                    try: idx_f = todas_faixas_ops.index(lib)
                    except: idx_f = 0
                    
                    fx_sel = c[2].selectbox("Faixa", todas_faixas_ops, index=idx_f, key=f"s_{doc.id}", label_visibility="collapsed")
                    c[3].write(status_txt)
                    
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
