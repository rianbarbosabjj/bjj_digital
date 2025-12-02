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

    tab1, tab2 = st.tabs(["📚 Listar/Editar", "➕ Adicionar Nova"])

    with tab1:
        questoes_ref = list(db.collection('questoes').stream())
        lista_q = []
        for doc in questões_ref:
            d = doc.to_dict()
            lista_q.append({
                "id": doc.id,
                "Nível": d.get('dificuldade', 1),
                "Categoria": d.get('categoria', 'Geral'),
                "Pergunta": d.get('pergunta'),
                "Status": d.get('status', 'aprovada')
            })
            
        if not lista_q:
            st.info("Banco vazio.")
        else:
            df = pd.DataFrame(lista_q)
            try: df = df.sort_values(by=["Nível", "Categoria"])
            except: pass
            
            st.dataframe(df[["Nível", "Categoria", "Pergunta", "Status"]], use_container_width=True, hide_index=True)
            
            st.markdown("---")
            q_sel_id = st.selectbox("Selecione para Editar/Excluir:", [q['id'] for q in lista_q], format_func=lambda x: next((f"[N{item['Nível']}] {item['Pergunta'][:60]}..." for item in lista_q if item['id'] == x), x))
            
            if q_sel_id:
                q_data = db.collection('questoes').document(q_sel_id).get().to_dict()
                with st.expander("✏️ Editar Questão", expanded=True):
                    with st.form(f"edit_{q_sel_id}"):
                        enunciado = st.text_area("Pergunta:", value=q_data.get('pergunta',''))
                        c1, c2 = st.columns(2)
                        
                        val_dif = q_data.get('dificuldade', 1)
                        if not isinstance(val_dif, int): val_dif = 1
                        nv_dif = c1.selectbox("Nível de Dificuldade:", NIVEIS_DIFICULDADE, index=NIVEIS_DIFICULDADE.index(val_dif))
                        nv_cat = c2.text_input("Categoria:", value=q_data.get('categoria', 'Geral'))
                        
                        alts = q_data.get('alternativas', {})
                        if not alts and 'opcoes' in q_data:
                            ops = q_data['opcoes']
                            alts = {"A": ops[0], "B": ops[1], "C": ops[2], "D": ops[3]} if len(ops)>=4 else {}
                            
                        ca, cb = st.columns(2); cc, cd = st.columns(2)
                        rA = ca.text_input("A)", value=alts.get('A','')); rB = cb.text_input("B)", value=alts.get('B',''))
                        rC = cc.text_input("C)", value=alts.get('C','')); rD = cd.text_input("D)", value=alts.get('D',''))
                        
                        resp_atual = q_data.get('resposta_correta', 'A')
                        corr = st.selectbox("Correta:", ["A","B","C","D"], index=["A","B","C","D"].index(resp_atual) if resp_atual in ["A","B","C","D"] else 0)
                        
                        if st.form_submit_button("💾 Atualizar"):
                            db.collection('questoes').document(q_sel_id).update({
                                "pergunta": enunciado, "dificuldade": nv_dif, "categoria": nv_cat,
                                "alternativas": {"A":rA, "B":rB, "C":rC, "D":rD},
                                "resposta_correta": corr, "faixa": firestore.DELETE_FIELD
                            })
                            st.success("Atualizado!"); time.sleep(1); st.rerun()
                if st.button("🗑️ Excluir", type="primary"):
                    db.collection('questoes').document(q_sel_id).delete()
                    st.success("Deletado."); time.sleep(1); st.rerun()

    with tab2:
        with st.form("new_q"):
            st.markdown("#### Nova Questão")
            pergunta = st.text_area("Enunciado:")
            c1, c2 = st.columns(2)
            dificuldade = c1.selectbox("Nível:", NIVEIS_DIFICULDADE, help="1=Fácil ... 4=Difícil")
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
                    st.success("Sucesso!"); time.sleep(1); st.rerun()
                else: st.warning("Preencha tudo.")

# =========================================
# 3. GESTÃO DE EXAME (MONTADOR COM DETALHES)
# =========================================
def gestao_exame_de_faixa():
    st.markdown("<h1 style='color:#FFD700;'>⚙️ Montador de Exames</h1>", unsafe_allow_html=True)
    db = get_db()

    tab1, tab2 = st.tabs(["📝 Montar Prova", "✅ Autorizar Alunos"])

    # --- ABA 1: MONTAR PROVA (DETALHADO) ---
    with tab1:
        st.subheader("1. Selecione a Faixa")
        faixa_sel = st.selectbox("Prova de Faixa:", FAIXAS_COMPLETAS)
        
        # Carrega Config Atual
        configs = db.collection('config_exames').where('faixa', '==', faixa_sel).stream()
        conf_atual = {}; doc_id = None
        for d in configs: conf_atual = d.to_dict(); doc_id = d.id; break
        
        # Carrega TODAS as questões para exibir no filtro
        todas_questoes = list(db.collection('questoes').stream())
        
        # Recupera IDs já salvos para marcar como selecionados
        questoes_salvas = conf_atual.get('questoes_ids', [])
        
        st.markdown("### 2. Selecione as Questões")
        
        # --- FILTROS ---
        c_f1, c_f2 = st.columns(2)
        filtro_nivel = c_f1.multiselect("Filtrar por Nível:", NIVEIS_DIFICULDADE, default=[1,2,3,4])
        
        temas_disponiveis = sorted(list(set([d.to_dict().get('categoria', 'Geral') for d in todas_questoes])))
        filtro_tema = c_f2.multiselect("Filtrar por Tema:", temas_disponiveis, default=temas_disponiveis)
        
        # --- PREPARAR DADOS COMPLETOS PARA TABELA ---
        lista_exibicao = []
        for doc in todas_questoes:
            d = doc.to_dict()
            niv = d.get('dificuldade', 1)
            cat = d.get('categoria', 'Geral')
            
            # Aplica filtros (Visual apenas)
            if niv in filtro_nivel and cat in filtro_tema:
                is_selected = doc.id in questoes_salvas
                
                # Formata alternativas em uma string legível
                alts_str = ""
                if 'alternativas' in d and isinstance(d['alternativas'], dict):
                    alts = d['alternativas']
                    # Limita o tamanho se for muito grande para não quebrar a tabela visualmente
                    alts_str = f"A) {alts.get('A','')} | B) {alts.get('B','')} | C) {alts.get('C','')} | D) {alts.get('D','')}"
                elif 'opcoes' in d:
                    ops = d['opcoes']
                    if len(ops) >= 4:
                        alts_str = f"A) {ops[0]} | B) {ops[1]} | C) {ops[2]} | D) {ops[3]}"
                
                # Resposta Correta e Autor
                resp = d.get('resposta_correta') or d.get('correta') or "?"
                autor = d.get('criado_por', 'Sistema')

                lista_exibicao.append({
                    "Selecionar": is_selected,
                    "Nível": niv,
                    "Tema": cat,
                    "Pergunta": d.get('pergunta'),
                    "Alternativas": alts_str,  # <--- COLUNA NOVA
                    "Correta": resp,           # <--- COLUNA NOVA
                    "Autor": autor,            # <--- COLUNA NOVA
                    "ID": doc.id
                })
        
        # --- TABELA INTERATIVA ---
        if not lista_exibicao:
            st.warning("Nenhuma questão encontrada com esses filtros.")
            selecionados_finais = questoes_salvas 
        else:
            df = pd.DataFrame(lista_exibicao)
            # O data_editor agora mostra tudo
            editor = st.data_editor(
                df,
                column_config={
                    "Selecionar": st.column_config.CheckboxColumn("Usar?", width="small", default=False),
                    "Nível": st.column_config.NumberColumn("Nív.", width="small"),
                    "Tema": st.column_config.TextColumn("Tema", width="small"),
                    "Pergunta": st.column_config.TextColumn("Pergunta", width="medium"),
                    "Alternativas": st.column_config.TextColumn("Alternativas", width="large"), # Coluna larga
                    "Correta": st.column_config.TextColumn("Resp.", width="small"),
                    "Autor": st.column_config.TextColumn("Autor", width="small"),
                    "ID": None # Esconde ID
                },
                disabled=["Nível", "Tema", "Pergunta", "Alternativas", "Correta", "Autor"], # Impede edição, só seleção
                hide_index=True,
                use_container_width=True,
                key=f"editor_{faixa_sel}" 
            )
            selecionados_finais = editor[editor["Selecionar"] == True]["ID"].tolist()
            
        st.info(f"Total de questões selecionadas: **{len(selecionados_finais)}**")
        
        st.markdown("### 3. Regras de Aplicação")
        with st.form("save_conf"):
            c1, c2 = st.columns(2)
            tempo = c1.number_input("Tempo Limite (min):", 10, 180, int(conf_atual.get('tempo_limite', 45)))
            nota = c2.number_input("Aprovação Mínima (%):", 10, 100, int(conf_atual.get('aprovacao_minima', 70)))
            
            if st.form_submit_button("💾 Salvar Prova"):
                if not selecionados_finais:
                    st.error("Selecione pelo menos uma questão na tabela acima.")
                else:
                    dados = {
                        "faixa": faixa_sel,
                        "questoes_ids": selecionados_finais, 
                        "qtd_questoes": len(selecionados_finais),
                        "tempo_limite": tempo,
                        "aprovacao_minima": nota,
                        "modo_selecao": "Manual",
                        "atualizado_em": firestore.SERVER_TIMESTAMP
                    }
                    if doc_id: db.collection('config_exames').document(doc_id).update(dados)
                    else: db.collection('config_exames').add(dados)
                    st.success(f"Prova da Faixa {faixa_sel} salva com {len(selecionados_finais)} questões!"); time.sleep(1.5); st.rerun()

    # --- ABA 2: AUTORIZAR ---
    with tab2:
        with st.container(border=True):
            st.subheader("🗓️ Agendar Exame")
            c1, c2 = st.columns(2); d_ini = c1.date_input("Início:", datetime.now()); d_fim = c2.date_input("Fim:", datetime.now())
            c3, c4 = st.columns(2); h_ini = c3.time_input("Hora Ini:", dtime(0,0)); h_fim = c4.time_input("Hora Fim:", dtime(23,59))
            dt_ini = datetime.combine(d_ini, h_ini); dt_fim = datetime.combine(d_fim, h_fim)

        st.markdown("### Alunos")
        users = db.collection('usuarios').where('tipo_usuario','==','aluno').stream()
        cols = st.columns([3,2,2,2,1])
        cols[0].write("**Nome**"); cols[1].write("**Equipe**"); cols[2].write("**Exame**"); cols[3].write("**Status**"); cols[4].write("**Ação**")
        st.divider()
        
        for u in users:
            d = u.to_dict(); uid = u.id
            eq_nome = "-"
            al_ref = list(db.collection('alunos').where('usuario_id','==',uid).limit(1).stream())
            if al_ref:
                eid = al_ref[0].to_dict().get('equipe_id')
                if eid: 
                    eq = db.collection('equipes').document(eid).get()
                    if eq.exists: eq_nome = eq.to_dict().get('nome')

            c1, c2, c3, c4, c5 = st.columns([3,2,2,2,1])
            c1.write(d.get('nome'))
            c2.write(eq_nome)
            idx_f = FAIXAS_COMPLETAS.index(d.get('faixa_exame')) if d.get('faixa_exame') in FAIXAS_COMPLETAS else 0
            fx = c3.selectbox("Faixa", FAIXAS_COMPLETAS, index=idx_f, key=f"f_{uid}", label_visibility="collapsed")
            
            hab = d.get('exame_habilitado', False)
            if hab:
                c4.success("Liberado")
                if c5.button("⛔", key=f"stop_{uid}"):
                    db.collection('usuarios').document(uid).update({"exame_habilitado": False, "status_exame": "pendente", "exame_inicio": firestore.DELETE_FIELD, "exame_fim": firestore.DELETE_FIELD})
                    st.rerun()
            else:
                c4.write("⚪")
                if c5.button("✅", key=f"go_{uid}"):
                    db.collection('usuarios').document(uid).update({"exame_habilitado": True, "faixa_exame": fx, "exame_inicio": dt_ini.isoformat(), "exame_fim": dt_fim.isoformat(), "status_exame": "pendente", "status_exame_em_andamento": False})
                    st.success("OK!"); time.sleep(0.5); st.rerun()
            st.divider()
