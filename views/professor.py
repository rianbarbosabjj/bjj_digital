import streamlit as st
import pandas as pd
from datetime import datetime, time as dtime
import time
from firebase_admin import firestore

# ==============================================================================
# 0. CONFIGURAÇÕES LOCAIS
# ==============================================================================
FAIXAS_COMPLETAS = [
    "Branca", 
    "Cinza e Branca", "Cinza", "Cinza e Preta",
    "Amarela e Branca", "Amarela", "Amarela e Preta",
    "Laranja e Branca", "Laranja", "Laranja e Preta",
    "Verde e Branca", "Verde", "Verde e Preta",
    "Azul", "Roxa", "Marrom", "Preta"
]

NIVEIS_DIFICULDADE = [1, 2, 3, 4]

MAPA_NIVEIS = {
    1: "Fácil", 
    2: "Médio", 
    3: "Difícil", 
    4: "Mestre"
}

def get_badge_nivel(nivel):
    """Retorna um ícone visual para o nível da questão"""
    badges = {1: "🟢", 2: "🟡", 3: "🔴", 4: "💀"}
    return badges.get(nivel, "⚪")

# ==============================================================================
# 1. IMPORTAÇÕES ROBUSTAS
# ==============================================================================
try:
    from utils import get_db, fazer_upload_midia, normalizar_link_video
except ImportError:
    try:
        from database import get_db
        def fazer_upload_midia(arquivo):
            st.warning("Função de upload indisponível (utils.py não encontrado).")
            return None
        def normalizar_link_video(url): return url
    except ImportError:
        st.error("ERRO CRÍTICO: Não foi possível conectar ao banco de dados.")
        st.stop()

# ==============================================================================
# 2. COMPONENTE: GESTÃO DE PROVAS DE CURSOS
# ==============================================================================
def componente_gestao_provas():
    db = get_db()
    
    # Busca cursos
    try:
        cursos_ref = db.collection('cursos').stream()
        LISTA_CURSOS = sorted([d.to_dict().get('titulo', d.to_dict().get('nome', d.id)) for d in cursos_ref])
    except: LISTA_CURSOS = []
    
    if not LISTA_CURSOS:
        st.warning("⚠️ Nenhum curso encontrado. Cadastre um curso na aba ao lado primeiro.")
        return

    t1, t2, t3 = st.tabs(["📝 Montar Prova", "👁️ Ver Provas Criadas", "✅ Autorizar Alunos"])

    # --- ABA 1: MONTAR PROVA ---
    with t1:
        st.subheader("Configurar Prova")
        c_sel = st.selectbox("Selecione o Curso:", LISTA_CURSOS, key="prov_curso_sel")
        
        if 'last_c_sel' not in st.session_state or st.session_state.last_c_sel != c_sel:
            cfgs = list(db.collection('config_provas_cursos').where('curso_alvo', '==', c_sel).limit(1).stream())
            st.session_state.cfg_atual = cfgs[0].to_dict() if cfgs else {}
            st.session_state.cfg_id = cfgs[0].id if cfgs else None
            st.session_state.sel_ids = set(st.session_state.cfg_atual.get('questoes_ids', []))
            st.session_state.last_c_sel = c_sel
            
        q_all = list(db.collection('questoes').where('status', '==', 'aprovada').stream())
        
        col_a, col_b = st.columns(2)
        f_niv = col_a.multiselect("Filtrar Nível:", NIVEIS_DIFICULDADE, default=NIVEIS_DIFICULDADE, format_func=lambda x: MAPA_NIVEIS.get(x, str(x)), key="f_niv_p")
        cats = sorted(list(set([d.to_dict().get('categoria','Geral') for d in q_all])))
        f_tem = col_b.multiselect("Filtrar Tema:", cats, default=cats, key="f_tem_p")
        
        with st.container(height=400, border=True):
            vis = 0
            for doc in q_all:
                d = doc.to_dict(); nid = d.get('dificuldade',1); cat = d.get('categoria','Geral')
                if nid in f_niv and cat in f_tem:
                    vis+=1
                    cc, cd = st.columns([1,15])
                    chk = cc.checkbox("", doc.id in st.session_state.sel_ids, key=f"chk_p_{doc.id}")
                    if chk: st.session_state.sel_ids.add(doc.id)
                    else: st.session_state.sel_ids.discard(doc.id)
                    
                    with cd:
                        st.markdown(f"**{get_badge_nivel(nid)}** | {cat} | {d.get('pergunta')}")
                        if d.get('url_imagem'): st.image(d.get('url_imagem'), width=80)
                    st.divider()
            if vis==0: st.caption("Nenhuma questão encontrada com estes filtros.")
            
        qt = len(st.session_state.sel_ids)
        st.info(f"**{qt}** questões selecionadas para a prova de **{c_sel}**.")
        
        with st.form("save_prova"):
            c1, c2 = st.columns(2)
            tmp = c1.number_input("Tempo Limite (min)", 10, 180, int(st.session_state.cfg_atual.get('tempo_limite',60)))
            nota = c2.number_input("Aprovação Mínima (%)", 10, 100, int(st.session_state.cfg_atual.get('aprovacao_minima',70)))
            
            if st.form_submit_button("💾 Salvar Configuração da Prova"):
                if qt == 0: st.error("Selecione pelo menos uma questão.")
                else:
                    dados = {"curso_alvo": c_sel, "questoes_ids": list(st.session_state.sel_ids), "qtd_questoes": qt, "tempo_limite": tmp, "aprovacao_minima": nota, "tipo_prova": "curso", "atualizado_em": firestore.SERVER_TIMESTAMP}
                    if st.session_state.cfg_id: db.collection('config_provas_cursos').document(st.session_state.cfg_id).update(dados)
                    else: db.collection('config_provas_cursos').add(dados)
                    st.success("Prova Salva!"); time.sleep(1); st.rerun()

    # --- ABA 2: VISUALIZAR ---
    with t2:
        st.subheader("Provas Configuradas")
        all_c = list(db.collection('config_provas_cursos').stream())
        if not all_c: st.info("Nenhuma prova configurada.")
        cols = st.columns(3)
        for i, dc in enumerate(all_c):
            dd = dc.to_dict()
            with cols[i%3]:
                with st.container(border=True):
                    st.markdown(f"### 📘 {dd.get('curso_alvo')}")
                    st.caption(f"Questões: {dd.get('qtd_questoes')} | Min: {dd.get('aprovacao_minima')}%")
                    if st.button("🗑️ Excluir", key=f"del_p_{dc.id}"):
                        db.collection('config_provas_cursos').document(dc.id).delete(); st.rerun()

    # --- ABA 3: AUTORIZAR ---
    with t3:
        st.subheader("Liberar Prova")
        c1, c2 = st.columns(2)
        ini = datetime.combine(c1.date_input("Início", key="di_p"), dtime(0,0))
        fim = datetime.combine(c2.date_input("Fim", key="df_p"), dtime(23,59))
        busca = st.text_input("Buscar aluno:", key="bus_al")
        als = db.collection('usuarios').where('tipo_usuario','==','aluno').stream()
        st.markdown("---")
        h1, h2, h3, h4 = st.columns([3, 3, 2, 1])
        h1.markdown("**Nome**"); h2.markdown("**Prova**"); h3.markdown("**Status**"); h4.markdown("**Ação**")
        st.markdown("---")
        for a in als:
            ad = a.to_dict(); aid = a.id
            if busca and busca.lower() not in ad.get('nome','').lower(): continue
            ca, cb, cc, cd = st.columns([3, 3, 2, 1])
            ca.write(f"**{ad.get('nome')}**")
            curs_atv = ad.get('curso_prova_alvo','')
            try: idx = LISTA_CURSOS.index(curs_atv)
            except: idx = 0
            sel_c = cb.selectbox("Curso", LISTA_CURSOS, index=idx, key=f"s_c_{aid}", label_visibility="collapsed")
            stt = "⚪ Off"
            hab = ad.get('exame_habilitado')
            tipo = ad.get('tipo_exame') 
            if hab and tipo == 'curso':
                s = ad.get('status_exame','pendente')
                if s=='aprovado': stt="🏆 Aprovado"
                elif s=='reprovado': stt="🔴 Reprovado"
                else: stt="🟢 Liberado"
            elif hab and tipo == 'faixa': stt = "⚠️ Prova de Faixa"
            cc.write(stt)
            if hab and tipo == 'curso':
                if cd.button("⛔", key=f"b_p_{aid}"):
                    db.collection('usuarios').document(aid).update({"exame_habilitado":False}); st.rerun()
            else:
                if cd.button("✅", key=f"l_p_{aid}"):
                    db.collection('usuarios').document(aid).update({"exame_habilitado":True, "tipo_exame":"curso", "curso_prova_alvo": sel_c, "exame_inicio": ini.isoformat(), "exame_fim": fim.isoformat(), "status_exame":"pendente"}); st.rerun()
            st.divider()

# ==============================================================================
# 3. ROTA: GESTÃO DE CURSOS
# ==============================================================================
def gestao_cursos_tab():
    st.markdown("<h1 style='color:#32CD32;'>📚 Gestão Acadêmica</h1>", unsafe_allow_html=True)
    
    user = st.session_state.usuario
    # PERMISSÃO: Admin, Professor ou Delegado (se houver essa role no futuro)
    if str(user.get("tipo", "")).lower() not in ["admin", "professor", "delegado"]:
        st.error("Acesso negado.")
        return

    tab_conteudo, tab_provas = st.tabs(["📚 Conteúdo & Módulos", "🎓 Provas & Certificados"])

    # --------------------------------------------------------------------------
    # ABA 1: CONTEÚDO
    # --------------------------------------------------------------------------
    with tab_conteudo:
        db = get_db()
        user_id = user['id']
        user_nome = user['nome']
        equipe_id_prof = user.get('equipe_id') 

        st.markdown("### Conteúdo dos Cursos")
        sub_tab_list, sub_tab_add = st.tabs(["🔎 Listar e Editar", "➕ Criar Novo Curso"])

        # --- SUB-ABA: CRIAR CURSO ---
        with sub_tab_add:
            with st.form("form_novo_curso"):
                st.markdown("##### Informações Básicas")
                c1, c2 = st.columns(2)
                titulo = c1.text_input("Título do Curso *", max_chars=100)
                categoria = c2.text_input("Categoria", "Geral")
                descricao = st.text_area("Descrição Completa *", height=100)
                
                st.markdown("##### Segmentação")
                c3, c4, c5 = st.columns(3)
                faixa_minima = c3.selectbox("Faixa Mínima:", ["Nenhuma", "Branca", "Azul", "Roxa", "Marrom", "Preta"])
                duracao = c4.text_input("Duração Est.", "Não especificada")
                
                # Seletor de Visibilidade
                visibilidade_label = c5.selectbox(
                    "Quem pode ver este curso?", 
                    ["Todos (Público)", "Apenas Minha Equipe"],
                    help="Se 'Apenas Minha Equipe', somente seus alunos verão."
                )
                
                st.markdown("##### Mídia e Status")
                col_up, col_link = st.columns(2)
                up_img = col_up.file_uploader("Capa (Imagem):", type=["jpg","png", "jpeg"])
                url_capa = col_link.text_input("Ou Link da Capa:")
                ativo = st.checkbox("Curso Ativo?", value=True)

                if st.form_submit_button("💾 Criar Curso", type="primary"):
                    if not titulo or not descricao: st.error("Preencha Título e Descrição.")
                    else:
                        url_final = url_capa
                        if up_img:
                            try:
                                with st.spinner("Subindo imagem..."):
                                    res = fazer_upload_midia(up_img)
                                    if res: url_final = res
                            except: pass

                        visib_valor = "equipe" if visibilidade_label == "Apenas Minha Equipe" else "todos"
                        try:
                            novo_curso = {
                                "titulo": titulo.upper(), "descricao": descricao, "categoria": categoria,
                                "faixa_minima": faixa_minima, "duracao_estimada": duracao,
                                "url_capa": url_final, "ativo": ativo,
                                "visibilidade": visib_valor,
                                "equipe_id": equipe_id_prof,
                                "criado_por_id": user_id, "criado_por_nome": user_nome,
                                "data_criacao": firestore.SERVER_TIMESTAMP, "modulos": []
                            }
                            db.collection('cursos').add(novo_curso)
                            st.success("Curso criado!"); time.sleep(1.5); st.rerun()
                        except Exception as e: st.error(f"Erro: {e}")

        # --- SUB-ABA: LISTAR E EDITAR ---
        with sub_tab_list:
            cursos_ref = list(db.collection('cursos').stream())
            cursos_data = [d.to_dict() | {"id": d.id} for d in cursos_ref]
            
            # FILTRO DE SEGURANÇA:
            # Se for Admin ou Delegado, vê tudo.
            # Se for Professor, vê apenas o que ele criou.
            tipo_user = str(user.get("tipo")).lower()
            if tipo_user not in ["admin", "delegado"]:
                cursos_data = [c for c in cursos_data if c.get('criado_por_id') == user_id]

            filtro = st.text_input("🔍 Buscar Curso:", key="filtro_cur_main")
            if filtro:
                cursos_data = [c for c in cursos_data if filtro.upper() in c.get('titulo','').upper()]

            if not cursos_data: st.info("Nenhum curso encontrado onde você seja o instrutor responsável.")

            for i, curso in enumerate(cursos_data):
                status_icon = '🟢' if curso.get('ativo') else '🔴'
                visib = curso.get('visibilidade', 'todos')
                visib_icon = "🌍 Público" if visib == 'todos' else "🔒 Equipe"
                
                with st.expander(f"{status_icon} {curso.get('titulo')} | {visib_icon}"):
                    
                    # 1. VISUALIZAÇÃO
                    c_img, c_info = st.columns([1, 3])
                    if curso.get('url_capa'): c_img.image(curso.get('url_capa'), width=150)
                    with c_info:
                        st.caption(f"ID: {curso['id']} | Min: {curso.get('faixa_minima')} | Visibilidade: {visib.upper()}")
                        st.write(curso.get('descricao'))
                    
                    st.divider()

                    # 2. BOTÃO DE EDIÇÃO DE METADADOS (NOVO)
                    if st.button("✏️ Editar Informações Principais", key=f"btn_edit_{curso['id']}"):
                        st.session_state[f"edit_mode_{curso['id']}"] = not st.session_state.get(f"edit_mode_{curso['id']}", False)

                    # FORMULÁRIO DE EDIÇÃO (Aparece se clicado)
                    if st.session_state.get(f"edit_mode_{curso['id']}"):
                        with st.form(f"form_edit_{curso['id']}"):
                            st.markdown("#### Editando Curso")
                            nt = st.text_input("Título", value=curso.get('titulo'))
                            nd = st.text_area("Descrição", value=curso.get('descricao'))
                            nc = st.text_input("Categoria", value=curso.get('categoria'))
                            nf = st.selectbox("Faixa Mínima", ["Nenhuma", "Branca", "Azul", "Roxa", "Marrom", "Preta"], index=["Nenhuma", "Branca", "Azul", "Roxa", "Marrom", "Preta"].index(curso.get('faixa_minima', 'Nenhuma')))
                            
                            # Edição de Visibilidade
                            idx_vis = 1 if curso.get('visibilidade') == 'equipe' else 0
                            nvis = st.selectbox("Visibilidade", ["Todos (Público)", "Apenas Minha Equipe"], index=idx_vis)

                            if st.form_submit_button("💾 Salvar Alterações"):
                                vis_val = "equipe" if nvis == "Apenas Minha Equipe" else "todos"
                                db.collection('cursos').document(curso['id']).update({
                                    "titulo": nt.upper(), "descricao": nd, "categoria": nc,
                                    "faixa_minima": nf, "visibilidade": vis_val
                                })
                                st.session_state[f"edit_mode_{curso['id']}"] = False
                                st.success("Atualizado!"); time.sleep(1); st.rerun()
                        st.divider()
                    
                    # 3. MÓDULOS
                    st.subheader("🛠️ Módulos e Aulas")
                    modulos = curso.get('modulos', [])
                    if modulos:
                        st.dataframe(pd.DataFrame(modulos), use_container_width=True, hide_index=True, column_config={"titulo_modulo": "Módulo", "descricao_modulo": "Desc", "aulas": "Aulas"})
                    else: st.info("Sem módulos ainda.")

                    with st.form(f"add_mod_{curso['id']}"):
                        c_m1, c_m2 = st.columns(2)
                        mt = c_m1.text_input("Novo Módulo (Título):")
                        md = c_m2.text_input("Descrição Curta:")
                        aul = st.text_area("Aulas (uma por linha):", height=80)
                        if st.form_submit_button("➕ Adicionar/Atualizar Módulo"):
                            if mt:
                                novas_aulas = [x.strip() for x in aul.split('\n') if x.strip()]
                                novo_mod = {"titulo_modulo": mt, "descricao_modulo": md, "aulas": novas_aulas}
                                mods_atual = list(modulos)
                                idx_found = -1
                                for idx, m in enumerate(mods_atual):
                                    if m.get('titulo_modulo') == mt: idx_found = idx
                                if idx_found >= 0: mods_atual[idx_found] = novo_mod
                                else: mods_atual.append(novo_mod)
                                db.collection('cursos').document(curso['id']).update({"modulos": mods_atual})
                                st.rerun()

                    st.divider()
                    cb1, cb2, cb3 = st.columns(3)
                    if cb1.button(f"{'Desativar' if curso.get('ativo') else 'Ativar'}", key=f"togg_{curso['id']}"):
                         db.collection('cursos').document(curso['id']).update({"ativo": not curso.get('ativo')}); st.rerun()

                    if cb3.button("🗑️ Excluir Curso", key=f"del_{curso['id']}"):
                        db.collection('cursos').document(curso['id']).delete(); st.rerun()

    # --------------------------------------------------------------------------
    # ABA 2: PROVAS
    # --------------------------------------------------------------------------
    with tab_provas:
        componente_gestao_provas()


# ==============================================================================
# 4. ROTA: GESTÃO DE EXAMES DE FAIXA
# ==============================================================================
def gestao_exame_de_faixa_route():
    st.markdown("<h1 style='color:#FFD700;'>⚙️ Montador de Exames (Faixa)</h1>", unsafe_allow_html=True)
    db = get_db()
    tab1, tab2, tab3 = st.tabs(["📝 Montar Prova", "👁️ Visualizar", "✅ Autorizar Alunos"])

    with tab1:
        st.subheader("1. Selecione a Faixa")
        faixa_sel = st.selectbox("Prova de Faixa:", FAIXAS_COMPLETAS)
        if 'last_faixa_sel' not in st.session_state or st.session_state.last_faixa_sel != faixa_sel:
            configs = list(db.collection('config_exames').where('faixa', '==', faixa_sel).limit(1).stream())
            conf_atual = configs[0].to_dict() if configs else {}
            doc_id = configs[0].id if configs else None
            st.session_state.conf_atual = conf_atual; st.session_state.doc_id = doc_id
            st.session_state.selected_ids = set(conf_atual.get('questoes_ids', []))
            st.session_state.last_faixa_sel = faixa_sel
        conf_atual = st.session_state.conf_atual
        todas_questoes = list(db.collection('questoes').where('status', '==', 'aprovada').stream())
        
        st.markdown("### 2. Selecione as Questões")
        c_f1, c_f2 = st.columns(2)
        filtro_nivel = c_f1.multiselect("Filtrar Nível:", NIVEIS_DIFICULDADE, default=[1,2,3,4], format_func=lambda x: MAPA_NIVEIS.get(x, str(x)))
        cats = sorted(list(set([d.to_dict().get('categoria', 'Geral') for d in todas_questoes])))
        filtro_tema = c_f2.multiselect("Filtrar Tema:", cats, default=cats)
        
        with st.container(height=500, border=True):
            count_visible = 0
            for doc in todas_questoes:
                d = doc.to_dict(); niv = d.get('dificuldade', 1); cat = d.get('categoria', 'Geral')
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
                        st.markdown(f"**{badge}** | {cat} | {d.get('pergunta')}")
                        if d.get('url_imagem'): st.image(d.get('url_imagem'), width=150)
                    st.divider()
            if count_visible == 0: st.warning("Nada encontrado.")
        
        total_sel = len(st.session_state.selected_ids)
        st.success(f"**{total_sel}** questões selecionadas.")
        
        st.markdown("### 3. Regras")
        with st.form("save_conf"):
            c1, c2 = st.columns(2)
            tempo = c1.number_input("Tempo (min):", 10, 180, int(conf_atual.get('tempo_limite', 45)))
            nota = c2.number_input("Aprovação (%):", 10, 100, int(conf_atual.get('aprovacao_minima', 70)))
            if st.form_submit_button("💾 Salvar Prova de Faixa"):
                if total_sel > 0:
                    dados = {"faixa": faixa_sel, "questoes_ids": list(st.session_state.selected_ids), "qtd_questoes": total_sel, "tempo_limite": tempo, "aprovacao_minima": nota, "modo_selecao": "Manual", "atualizado_em": firestore.SERVER_TIMESTAMP}
                    if st.session_state.doc_id: db.collection('config_exames').document(st.session_state.doc_id).update(dados)
                    else: db.collection('config_exames').add(dados)
                    st.success("Salvo!"); time.sleep(1.5); st.rerun()
                else: st.error("Selecione questões.")

    with tab2:
        st.subheader("Exames de Faixa Ativos")
        configs_stream = db.collection('config_exames').stream()
        for doc in configs_stream:
            d = doc.to_dict()
            with st.expander(f"🥋 {d.get('faixa')}"):
                st.write(f"Questões: {d.get('qtd_questoes')} | Min: {d.get('aprovacao_minima')}%")
                if st.button("🗑️ Deletar", key=f"del_ex_{doc.id}"):
                     db.collection('config_exames').document(doc.id).delete(); st.rerun()

    with tab3:
        st.subheader("Autorizar Alunos (Faixa)")
        c1, c2 = st.columns(2)
        d_ini = c1.date_input("Início:", datetime.now(), key="d_ini_ex")
        d_fim = c2.date_input("Fim:", datetime.now(), key="d_fim_ex")
        dt_ini = datetime.combine(d_ini, dtime(0,0)); dt_fim = datetime.combine(d_fim, dtime(23,59))
        alunos_ref = db.collection('usuarios').where('tipo_usuario', '==', 'aluno').stream()
        for doc in alunos_ref:
            d = doc.to_dict(); d['id'] = doc.id
            c1, c2, c3, c4 = st.columns([3, 2, 3, 1])
            c1.write(f"**{d.get('nome')}**")
            fx_idx = 0
            if d.get('faixa_exame') in FAIXAS_COMPLETAS: fx_idx = FAIXAS_COMPLETAS.index(d.get('faixa_exame'))
            fx_sel = c2.selectbox("Faixa", FAIXAS_COMPLETAS, index=fx_idx, key=f"fx_s_{d['id']}", label_visibility="collapsed")
            status = "⚪ Off"
            hab = d.get('exame_habilitado')
            tp = d.get('tipo_exame')
            if hab and tp == 'faixa': status = "🟢 Faixa Liberada"
            elif hab and tp == 'curso': status = "⚠️ Curso Ativo"
            c3.write(status)
            if hab and tp == 'faixa':
                 if c4.button("⛔", key=f"blk_f_{d['id']}"):
                     db.collection('usuarios').document(d['id']).update({"exame_habilitado": False}); st.rerun()
            else:
                 if c4.button("✅", key=f"lib_f_{d['id']}"):
                     db.collection('usuarios').document(d['id']).update({"exame_habilitado": True, "tipo_exame": "faixa", "faixa_exame": fx_sel, "exame_inicio": dt_ini.isoformat(), "exame_fim": dt_fim.isoformat(), "status_exame": "pendente"}); st.rerun()
            st.divider()

# ==============================================================================
# 5. ROTAS AUXILIARES
# ==============================================================================
def dashboard_route():
    st.title("📊 Dashboard do Professor")
    st.info("Estatísticas gerais de alunos e cursos aparecerão aqui.")

def gestao_alunos_route():
    st.title("👥 Gestão de Alunos")
    st.info("Ferramenta de consulta e edição de alunos.")

# ==============================================================================
# 6. APP PRINCIPAL DO PROFESSOR
# ==============================================================================
def app_professor():
    with st.sidebar:
        st.image("https://cdn-icons-png.flaticon.com/512/3135/3135715.png", width=100)
        st.title("Painel Professor")
        menu = st.radio("Navegação", ["Dashboard", "Gestão de Alunos", "Gestão de Cursos", "Gestão de Exames (Faixa)", "Sair"])
        st.markdown("---")
        st.caption("Mestre Tunico v2.0")

    if menu == "Dashboard": dashboard_route()
    elif menu == "Gestão de Alunos": gestao_alunos_route()
    elif menu == "Gestão de Cursos": gestao_cursos_tab()
    elif menu == "Gestão de Exames (Faixa)": gestao_exame_de_faixa_route()
    elif menu == "Sair":
        st.session_state.logado = False
        st.rerun()

if __name__ == "__main__":
    app_professor()
