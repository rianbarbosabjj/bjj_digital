import streamlit as st
import pandas as pd
import bcrypt
import random
import time
from datetime import datetime, time as dtime
from database import get_db
from firebase_admin import firestore

try:
    from utils import carregar_todas_questoes, salvar_questoes
except ImportError:
    def carregar_todas_questoes(): return []
    def salvar_questoes(t, q): pass

FAIXAS_COMPLETAS = [
    "Cinza e Branca", "Cinza", "Cinza e Preta",
    "Amarela e Branca", "Amarela", "Amarela e Preta",
    "Laranja e Branca", "Laranja", "Laranja e Preta",
    "Verde e Branca", "Verde", "Verde e Preta",
    "Azul", "Roxa", "Marrom", "Preta"
]

NIVEIS_DIFICULDADE = [1, 2, 3, 4]

# =========================================
# HELPER: BADGES DE DIFICULDADE
# =========================================
def get_badge_nivel(nivel):
    cores = {1: "🟢 Fácil", 2: "🔵 Médio", 3: "🟠 Difícil", 4: "🔴 Muito Difícil"}
    return cores.get(nivel, "⚪ Nível ?")

# =========================================
# 1. GESTÃO DE USUÁRIOS
# =========================================
def gestao_usuarios(usuario_logado):
    if st.button("🏠 Voltar ao Início", key="btn_voltar_adm"):
        st.session_state.menu_selection = "Início"; st.rerun()

    st.markdown("<h1 style='color:#FFD700;'>👥 Gestão de Usuários</h1>", unsafe_allow_html=True)
    db = get_db()
    users = [d.to_dict() | {"id": d.id} for d in db.collection('usuarios').stream()]
    if not users: st.warning("Vazio."); return
    df = pd.DataFrame(users)
    cols = ['nome', 'email', 'tipo_usuario', 'faixa_atual']
    for c in cols:
        if c not in df.columns: df[c] = "-"
    st.dataframe(df[cols], use_container_width=True, hide_index=True)
    st.markdown("---")
    st.subheader("🛠️ Editar")
    sel = st.selectbox("Usuário:", users, format_func=lambda x: f"{x.get('nome')} ({x.get('email')})")
    if sel:
        with st.form(f"edt_{sel['id']}"):
            nm = st.text_input("Nome:", value=sel.get('nome',''))
            tp = st.selectbox("Tipo:", ["aluno","professor","admin"], index=["aluno","professor","admin"].index(sel.get('tipo_usuario','aluno')))
            fx = st.selectbox("Faixa Atual:", ["Branca"] + FAIXAS_COMPLETAS, index=(["Branca"] + FAIXAS_COMPLETAS).index(sel.get('faixa_atual', 'Branca')) if sel.get('faixa_atual') in FAIXAS_COMPLETAS else 0)
            pwd = st.text_input("Nova Senha (opcional):", type="password")
            if st.form_submit_button("Salvar"):
                upd = {"nome": nm.upper(), "tipo_usuario": tp, "faixa_atual": fx}
                if pwd: upd["senha"] = bcrypt.hashpw(pwd.encode(), bcrypt.gensalt()).decode(); upd["precisa_trocar_senha"] = True
                db.collection('usuarios').document(sel['id']).update(upd)
                st.success("Salvo!"); time.sleep(1); st.rerun()
        if st.button("🗑️ Excluir Usuário", key=f"del_{sel['id']}"):
            db.collection('usuarios').document(sel['id']).delete()
            st.warning("Excluído."); time.sleep(1); st.rerun()

# =========================================
# 2. GESTÃO DE QUESTÕES
# =========================================
def gestao_questoes():
    st.markdown("<h1 style='color:#FFD700;'>📝 Banco de Questões</h1>", unsafe_allow_html=True)
    db = get_db()
    
    user = st.session_state.usuario
    if str(user.get("tipo", "")).lower() not in ["admin", "professor"]:
        st.error("Acesso negado."); return

    MAPA_NIVEIS = {
        1: "🟢 Fácil", 2: "🔵 Médio", 
        3: "🟠 Difícil", 4: "🔴 Muito Difícil"
    }

    tab1, tab2 = st.tabs(["📚 Listar/Editar", "➕ Adicionar Nova"])

    # --- LISTAR (CARDS) ---
    with tab1:
        questoes_ref = list(db.collection('questoes').stream())
        
        c_f1, c_f2 = st.columns(2)
        termo = c_f1.text_input("🔍 Buscar no enunciado:")
        filtro_n = c_f2.multiselect("Filtrar Nível:", NIVEIS_DIFICULDADE, format_func=lambda x: MAPA_NIVEIS.get(x, str(x)))

        questoes_filtradas = []
        for doc in questoes_ref:
            d = doc.to_dict()
            d['id'] = doc.id
            if termo and termo.lower() not in d.get('pergunta','').lower(): continue
            if filtro_n and d.get('dificuldade', 1) not in filtro_n: continue
            questoes_filtradas.append(d)
            
        if not questoes_filtradas:
            st.info("Nenhuma questão encontrada.")
        else:
            st.caption(f"Exibindo {len(questoes_filtradas)} questões")
            for q in questoes_filtradas:
                with st.container(border=True):
                    c_head, c_btn = st.columns([5, 1])
                    nivel_val = q.get('dificuldade', 1)
                    nivel_texto = MAPA_NIVEIS.get(nivel_val, "⚪ Nível ?")
                    cat = q.get('categoria', 'Geral')
                    autor = q.get('criado_por', 'Desconhecido')
                    
                    # --- AQUI: Autor no Banco de Questões ---
                    c_head.markdown(f"**{nivel_texto}** | *{cat}* | ✍️ {autor}")
                    c_head.markdown(f"##### {q.get('pergunta')}")
                    
                    with c_head.expander("👁️ Ver Detalhes (Alternativas)"):
                        alts = q.get('alternativas', {})
                        if not alts and 'opcoes' in q:
                            ops = q['opcoes']
                            alts = {"A": ops[0], "B": ops[1], "C": ops[2], "D": ops[3]} if len(ops)>=4 else {}
                        
                        st.markdown(f"**A)** {alts.get('A','')} | **B)** {alts.get('B','')}")
                        st.markdown(f"**C)** {alts.get('C','')} | **D)** {alts.get('D','')}")
                        resp = q.get('resposta_correta') or q.get('correta') or "?"
                        st.success(f"**Correta:** {resp}")

                    if c_btn.button("✏️", key=f"btn_edit_{q['id']}"):
                        st.session_state[f"editing_q"] = q['id']

                # FORMULÁRIO DE EDIÇÃO
                if st.session_state.get("editing_q") == q['id']:
                    with st.container(border=True):
                        st.markdown("#### ✏️ Editando")
                        with st.form(f"form_edit_{q['id']}"):
                            enunciado = st.text_area("Pergunta:", value=q.get('pergunta',''))
                            c1, c2 = st.columns(2)
                            val_dif = q.get('dificuldade', 1)
                            if not isinstance(val_dif, int): val_dif = 1
                            nv_dif = c1.selectbox("Nível de Dificuldade:", NIVEIS_DIFICULDADE, index=NIVEIS_DIFICULDADE.index(val_dif) if val_dif in NIVEIS_DIFICULDADE else 0, format_func=lambda x: MAPA_NIVEIS.get(x, str(x)))
                            nv_cat = c2.text_input("Categoria:", value=q.get('categoria', 'Geral'))
                            
                            alts = q.get('alternativas', {})
                            if not alts and 'opcoes' in q:
                                ops = q['opcoes']
                                alts = {"A": ops[0], "B": ops[1], "C": ops[2], "D": ops[3]} if len(ops)>=4 else {}
                                
                            ca, cb = st.columns(2); cc, cd = st.columns(2)
                            rA = ca.text_input("A)", value=alts.get('A','')); rB = cb.text_input("B)", value=alts.get('B',''))
                            rC = cc.text_input("C)", value=alts.get('C','')); rD = cd.text_input("D)", value=alts.get('D',''))
                            
                            resp_atual = q.get('resposta_correta', 'A')
                            corr = st.selectbox("Correta:", ["A","B","C","D"], index=["A","B","C","D"].index(resp_atual) if resp_atual in ["A","B","C","D"] else 0)
                            
                            cols = st.columns(2)
                            if cols[0].form_submit_button("💾 Salvar Alterações"):
                                db.collection('questoes').document(q['id']).update({
                                    "pergunta": enunciado, "dificuldade": nv_dif, "categoria": nv_cat,
                                    "alternativas": {"A":rA, "B":rB, "C":rC, "D":rD},
                                    "resposta_correta": corr, "faixa": firestore.DELETE_FIELD
                                })
                                st.session_state["editing_q"] = None
                                st.success("Atualizado!"); time.sleep(1); st.rerun()
                            
                            if cols[1].form_submit_button("Cancelar"):
                                st.session_state["editing_q"] = None
                                st.rerun()
                                
                        if st.button("🗑️ Deletar Questão", key=f"del_q_{q['id']}", type="primary"):
                            db.collection('questoes').document(q['id']).delete()
                            st.session_state["editing_q"] = None
                            st.success("Deletado."); st.rerun()

    # --- CRIAR ---
    with tab2:
        with st.form("form_criar_nova_questao_v2"):
            st.markdown("#### Nova Questão")
            pergunta = st.text_area("Enunciado:")
            c1, c2 = st.columns(2)
            dificuldade = c1.selectbox("Nível de Dificuldade:", NIVEIS_DIFICULDADE, format_func=lambda x: MAPA_NIVEIS.get(x, str(x)))
            categoria = c2.text_input("Categoria:", "Geral")
            st.markdown("**Alternativas:**")
            ca, cb = st.columns(2); cc, cd = st.columns(2)
            alt_a = ca.text_input("A)"); alt_b = cb.text_input("B)")
            alt_c = cc.text_input("C)"); alt_d = cd.text_input("D)")
            correta = st.selectbox("Correta:", ["A", "B", "C", "D"])
            
            if st.form_submit_button("💾 Cadastrar"):
                if pergunta and alt_a and alt_b:
                    db.collection('questoes').add({
                        "pergunta": pergunta, "dificuldade": dificuldade, "categoria": categoria,
                        "alternativas": {"A": alt_a, "B": alt_b, "C": alt_c, "D": alt_d},
                        "resposta_correta": correta, "status": "aprovada",
                        "criado_por": user.get('nome', 'Admin'), "data_criacao": firestore.SERVER_TIMESTAMP
                    })
                    st.success("Questão cadastrada!"); time.sleep(1); st.rerun()
                else: st.warning("Preencha o enunciado e pelo menos 2 alternativas.")


# =========================================
# 3. GESTÃO DE EXAME
# =========================================
def gestao_exame_de_faixa():
    st.markdown("<h1 style='color:#FFD700;'>⚙️ Montador de Exames</h1>", unsafe_allow_html=True)
    db = get_db()

    tab1, tab2, tab3 = st.tabs(["📝 Criar e Editar Prova", "👁️ Visualizar Provas", "✅ Autorizar Alunos"])

    # --- ABA 1: CRIAR/EDITAR ---
    with tab1:
        st.subheader("1. Selecione a Faixa")
        faixa_sel = st.selectbox("Prova de Faixa:", FAIXAS_COMPLETAS)
        
        if 'last_faixa_sel' not in st.session_state or st.session_state.last_faixa_sel != faixa_sel:
            configs = db.collection('config_exames').where('faixa', '==', faixa_sel).stream()
            conf_atual = {}; doc_id = None
            for d in configs: conf_atual = d.to_dict(); doc_id = d.id; break
            
            st.session_state.conf_atual = conf_atual
            st.session_state.doc_id = doc_id
            st.session_state.selected_ids = set(conf_atual.get('questoes_ids', []))
            st.session_state.last_faixa_sel = faixa_sel
        
        conf_atual = st.session_state.conf_atual
        todas_questoes = list(db.collection('questoes').stream())
        
        st.markdown("### 2. Selecione as Questões (Cards)")
        c_f1, c_f2 = st.columns(2)
        filtro_nivel = c_f1.multiselect("Filtrar por Nível:", NIVEIS_DIFICULDADE, default=[1,2,3,4])
        cats = sorted(list(set([d.to_dict().get('categoria', 'Geral') for d in todas_questoes])))
        filtro_tema = c_f2.multiselect("Filtrar por Tema:", cats, default=cats)
        
        with st.container(height=500, border=True):
            count_visible = 0
            for doc in todas_questoes:
                d = doc.to_dict()
                niv = d.get('dificuldade', 1)
                cat = d.get('categoria', 'Geral')
                autor = d.get('criado_por', 'Desconhecido')
                
                if niv in filtro_nivel and cat in filtro_tema:
                    count_visible += 1
                    c_chk, c_content = st.columns([1, 15])
                    is_checked = doc.id in st.session_state.selected_ids
                    
                    def update_selection(qid=doc.id):
                        if st.session_state[f"chk_{qid}"]: st.session_state.selected_ids.add(qid)
                        else: st.session_state.selected_ids.discard(qid)

                    c_chk.checkbox("", value=is_checked, key=f"chk_{doc.id}", on_change=update_selection)
                    with c_content:
                        badge = get_badge_nivel(niv)
                        # --- AQUI: Autor no Card de Seleção ---
                        st.markdown(f"**{badge}** | {cat} | ✍️ {autor}")
                        st.markdown(f"{d.get('pergunta')}")
                        with st.expander("Ver Detalhes"):
                            st.info(f"✅ Correta: {d.get('resposta_correta') or 'A'}")
                    st.divider()
            
            if count_visible == 0: st.warning("Nenhuma questão corresponde aos filtros atuais.")

        # --- BARRA DE STATUS DA SELEÇÃO (COM BOTÃO DE LIMPAR) ---
        total_sel = len(st.session_state.selected_ids)
        c_res1, c_res2 = st.columns([3, 1])
        c_res1.success(f"**{total_sel}** questões selecionadas para a prova de **{faixa_sel}**.")
        
        if total_sel > 0:
            if c_res2.button("🗑️ Limpar Seleção", key="btn_limpar_sel"):
                st.session_state.selected_ids = set()
                st.rerun()
        
        st.markdown("### 3. Regras de Aplicação")
        with st.form("save_conf"):
            c1, c2 = st.columns(2)
            tempo = c1.number_input("Tempo Limite (min):", 10, 180, int(conf_atual.get('tempo_limite', 45)))
            nota = c2.number_input("Aprovação Mínima (%):", 10, 100, int(conf_atual.get('aprovacao_minima', 70)))
            
            if st.form_submit_button("💾 Salvar Prova"):
                if total_sel == 0:
                    st.error("Selecione pelo menos uma questão.")
                else:
                    dados = {
                        "faixa": faixa_sel,
                        "questoes_ids": list(st.session_state.selected_ids), 
                        "qtd_questoes": total_sel,
                        "tempo_limite": tempo,
                        "aprovacao_minima": nota,
                        "modo_selecao": "Manual",
                        "atualizado_em": firestore.SERVER_TIMESTAMP
                    }
                    
                    # BLINDAGEM CONTRA ERRO NOTFOUND
                    try:
                        if st.session_state.doc_id:
                            db.collection('config_exames').document(st.session_state.doc_id).update(dados)
                            st.success(f"Prova da Faixa {faixa_sel} ATUALIZADA com sucesso!")
                        else:
                            db.collection('config_exames').add(dados)
                            st.success(f"Prova da Faixa {faixa_sel} CRIADA com sucesso!")
                    except Exception:
                        ref = db.collection('config_exames').add(dados)
                        st.session_state.doc_id = ref[1].id
                        st.success(f"Prova da Faixa {faixa_sel} RECRIADA com sucesso!")
                    
                    time.sleep(1.5); st.rerun()

    # --- ABA 2: VISUALIZAR E EXCLUIR ---
    with tab2:
        st.subheader("Status das Provas Cadastradas")
        all_q_docs = list(db.collection('questoes').stream())
        mapa_questoes_completo = {doc.id: doc.to_dict() for doc in all_q_docs}

        configs_stream = db.collection('config_exames').stream()
        mapa_configs = {}
        for doc in configs_stream:
            d = doc.to_dict(); d['id'] = doc.id 
            mapa_configs[d.get('faixa')] = d

        categorias = {
            "🔘 Cinza": ["Cinza e Branca", "Cinza", "Cinza e Preta"],
            "🟡 Amarela": ["Amarela e Branca", "Amarela", "Amarela e Preta"],
            "🟠 Laranja": ["Laranja e Branca", "Laranja", "Laranja e Preta"],
            "🟢 Verde": ["Verde e Branca", "Verde", "Verde e Preta"],
            "🔵 Azul": ["Azul"], "🟣 Roxa": ["Roxa"], "🟤 Marrom": ["Marrom"], "⚫ Preta": ["Preta"]
        }

        abas_cores = st.tabs(list(categorias.keys()))
        for aba, (cor_nome, lista_faixas) in zip(abas_cores, categorias.items()):
            with aba:
                for f_nome in lista_faixas:
                    data = mapa_configs.get(f_nome)
                    if data:
                        modo = data.get('modo_selecao', 'Sorteio')
                        qtd = data.get('qtd_questoes', 0)
                        tempo = data.get('tempo_limite', 0)
                        nota = data.get('aprovacao_minima', 0)
                        
                        with st.expander(f"✅ {f_nome} ({modo} | {qtd} questões)"):
                            st.caption(f"⏱️ Tempo: {tempo} min | 🎯 Mínimo: {nota}%")
                            
                            # --- LISTAGEM DIRETA DAS QUESTÕES (SEM BOTÃO TOGGLE) ---
                            if modo == "🖐️ Manual (Fixa)" and data.get('questoes_ids'):
                                ids = data.get('questoes_ids', [])
                                st.markdown("---")
                                st.markdown("#### 📋 Questões Selecionadas")
                                for i, q_id in enumerate(ids, 1):
                                    q_data = mapa_questoes_completo.get(q_id)
                                    if q_data:
                                        st.markdown(f"**{i}. {q_data.get('pergunta')}**")
                                        # --- AQUI: Autor na Visualização da Prova Pronta ---
                                        autor_q = q_data.get('criado_por', 'Desconhecido')
                                        st.caption(f"Correta: {q_data.get('resposta_correta')} | ✍️ {autor_q}")
                                    else: st.error(f"{i}. Questão deletada (ID: {q_id})")
                                    st.divider()
                            elif modo == "🎲 Aleatório (Sorteio)":
                                st.info(f"Sorteio aleatório de {qtd} questões.")
                            
                            st.markdown("---")
                            if st.button("🗑️ Excluir Prova", key=f"del_proof_{data['id']}"):
                                db.collection('config_exames').document(data['id']).delete()
                                if 'doc_id' in st.session_state and st.session_state.doc_id == data['id']:
                                    st.session_state.doc_id = None
                                st.warning(f"Prova de {f_nome} excluída.")
                                time.sleep(1); st.rerun()
                    else: st.warning(f"⚠️ {f_nome} não configurada.")

    # --- ABA 3: AUTORIZAR ---
    with tab3:
        with st.container(border=True):
            st.subheader("🗓️ Configurar Período")
            c1, c2 = st.columns(2)
            d_inicio = c1.date_input("Início:", datetime.now(), key="data_inicio_exame")
            d_fim = c2.date_input("Fim:", datetime.now(), key="data_fim_exame")
            c3, c4 = st.columns(2)
            h_inicio = c3.time_input("Hora Início:", dtime(0, 0), key="hora_inicio_exame")
            h_fim = c4.time_input("Hora Fim:", dtime(23, 59), key="hora_fim_exame")
            dt_inicio = datetime.combine(d_inicio, h_inicio)
            dt_fim = datetime.combine(d_fim, h_fim)

        st.write(""); st.subheader("Lista de Alunos")
        try:
            alunos_ref = db.collection('usuarios').where('tipo_usuario', '==', 'aluno').stream()
            lista_alunos = []
            for doc in alunos_ref:
                d = doc.to_dict(); d['id'] = doc.id
                nome_eq = "Sem Equipe"
                try:
                    vinculo = list(db.collection('alunos').where('usuario_id', '==', doc.id).limit(1).stream())
                    if vinculo:
                        eid = vinculo[0].to_dict().get('equipe_id')
                        eq_doc = db.collection('equipes').document(eid).get()
                        if eq_doc.exists: nome_eq = eq_doc.to_dict().get('nome', 'Sem Nome')
                except: pass
                d['nome_equipe'] = nome_eq
                lista_alunos.append(d)

            if not lista_alunos: st.info("Nenhum aluno cadastrado.")
            else:
                cols = st.columns([3, 2, 2, 3, 1])
                cols[0].markdown("**Aluno**")
                cols[1].markdown("**Equipe**")
                cols[2].markdown("**Exame**")
                cols[3].markdown("**Status**")
                cols[4].markdown("**Ação**")
                st.markdown("---")

                for aluno in lista_alunos:
                    try:
                        aluno_id = aluno.get('id', 'unknown')
                        aluno_nome = aluno.get('nome', 'Sem Nome')
                        faixa_exame_atual = aluno.get('faixa_exame', '')
                        
                        c1, c2, c3, c4, c5 = st.columns([3, 2, 2, 3, 1])
                        c1.write(f"**{aluno_nome}**")
                        c2.write(aluno.get('nome_equipe', 'Sem Equipe'))
                        
                        idx = FAIXAS_COMPLETAS.index(faixa_exame_atual) if faixa_exame_atual in FAIXAS_COMPLETAS else 0
                        fx_sel = c3.selectbox("Faixa", FAIXAS_COMPLETAS, index=idx, key=f"fx_select_{aluno_id}", label_visibility="collapsed")
                        
                        habilitado = aluno.get('exame_habilitado', False)
                        status = aluno.get('status_exame', 'pendente')
                        
                        msg_status = "⚪ Não autorizado"
                        if status == 'aprovado': msg_status = "🏆 Aprovado"
                        elif status == 'reprovado': msg_status = "🔴 Reprovado"
                        elif status == 'bloqueado': msg_status = "⛔ Bloqueado"
                        elif habilitado:
                            msg_status = "🟢 Liberado"
                            try:
                                raw_fim = aluno.get('exame_fim')
                                if raw_fim:
                                    dt_obj = datetime.fromisoformat(raw_fim.replace('Z', '+00:00')) if isinstance(raw_fim, str) else raw_fim
                                    msg_status += f" (até {dt_obj.strftime('%d/%m %H:%M')})"
                            except: pass
                            if status == 'em_andamento': msg_status = "🟡 Em Andamento"

                        c4.write(msg_status)
                        
                        if habilitado:
                            if c5.button("⛔", key=f"off_btn_{aluno_id}"):
                                update_data = {"exame_habilitado": False, "status_exame": "pendente"}
                                for k in ["exame_inicio", "exame_fim", "faixa_exame", "motivo_bloqueio", "status_exame_em_andamento"]:
                                    if k in aluno: update_data[k] = firestore.DELETE_FIELD
                                db.collection('usuarios').document(aluno_id).update(update_data)
                                st.rerun()
                        else:
                            if c5.button("✅", key=f"on_btn_{aluno_id}"):
                                db.collection('usuarios').document(aluno_id).update({
                                    "exame_habilitado": True, "faixa_exame": fx_sel,
                                    "exame_inicio": dt_inicio.isoformat(), "exame_fim": dt_fim.isoformat(),
                                    "status_exame": "pendente", "status_exame_em_andamento": False
                                })
                                st.success("Liberado!"); time.sleep(0.5); st.rerun()
                        st.markdown("---")
                    except Exception as e: st.error(f"Erro: {e}")
        except: st.error("Erro ao carregar alunos.")
