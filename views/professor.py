import streamlit as st
import pandas as pd
import time
from database import get_db
from firebase_admin import firestore
# Importamos o dashboard para usar dentro da aba
from views import dashboard 

# =========================================
# HELPER: DECORAR FAIXAS E CARGOS
# =========================================
def get_faixa_decorada(faixa):
    """Adiciona emojis combinados para representar faixas mistas e sólidas"""
    f = str(faixa).lower().strip()
    
    # 1. Faixas Mistas (Infantil/Juvenil) - Verificamos estas PRIMEIRO
    if "cinza" in f and "branca" in f: return f"🔘⚪ {faixa}"
    if "cinza" in f and "preta" in f:  return f"🔘⚫ {faixa}"
    
    if "amarela" in f and "branca" in f: return f"🟡⚪ {faixa}"
    if "amarela" in f and "preta" in f:  return f"🟡⚫ {faixa}"
    
    if "laranja" in f and "branca" in f: return f"🟠⚪ {faixa}"
    if "laranja" in f and "preta" in f:  return f"🟠⚫ {faixa}"
    
    if "verde" in f and "branca" in f: return f"🟢⚪ {faixa}"
    if "verde" in f and "preta" in f:  return f"🟢⚫ {faixa}"

    # 2. Faixas Sólidas
    if "branca" in f: return f"⚪ {faixa}"
    if "cinza" in f:  return f"🔘 {faixa}"
    if "amarela" in f: return f"🟡 {faixa}"
    if "laranja" in f: return f"🟠 {faixa}"
    if "verde" in f:  return f"🟢 {faixa}"
    if "azul" in f:   return f"🔵 {faixa}"
    if "roxa" in f:   return f"🟣 {faixa}"
    if "marrom" in f: return f"🟤 {faixa}"
    if "preta" in f:  return f"⚫ {faixa}"

    # Fallback
    return f"🥋 {faixa}"

def get_cargo_decorado(cargo):
    if cargo == "Líder": return "👑 Professor Responsável"
    if cargo == "Delegado": return "🛡️ Professor Delegado"
    return "🥋 Professor Adjunto"

# =========================================
# FUNÇÃO: GESTÃO DE EQUIPES (COM TOTAIS)
# =========================================
def gestao_equipes():
    db = get_db()
    user = st.session_state.usuario
    user_id = user['id']

    # --- 1. IDENTIFICAR O CONTEXTO DO PROFESSOR ---
    vinc = list(db.collection('professores').where('usuario_id', '==', user_id).where('status_vinculo', '==', 'ativo').limit(1).stream())
    
    if not vinc:
        st.error("⛔ Você não possui vínculo ativo com nenhuma equipe.")
        return

    dados_prof = vinc[0].to_dict()
    meu_equipe_id = dados_prof.get('equipe_id')
    sou_responsavel = dados_prof.get('eh_responsavel', False)
    sou_delegado = dados_prof.get('pode_aprovar', False) 

    # Busca nome da equipe
    nome_equipe = "Minha Equipe"
    if meu_equipe_id:
        eq_doc = db.collection('equipes').document(meu_equipe_id).get()
        if eq_doc.exists:
            nome_equipe = eq_doc.to_dict().get('nome', 'Minha Equipe')

    # --- 2. DEFINIR NÍVEL DE PODER ---
    nivel_poder = 1
    if sou_delegado: nivel_poder = 2
    if sou_responsavel: nivel_poder = 3

    # Cabeçalho
    st.markdown(f"### 🏛️ {nome_equipe}")
    col_info1, col_info2 = st.columns([3, 1])
    col_info1.caption("Painel de Gestão de Membros e Aprovações")
    
    badge = "⭐ Auxiliar"
    if nivel_poder == 2: badge = "⭐⭐ Delegado"
    if nivel_poder == 3: badge = "⭐⭐⭐ Responsável"
    col_info2.markdown(f"**Cargo:** {badge}")

    # --- 3. ABAS DE GESTÃO ---
    abas = ["⏳ Aprovações", "👥 Membros Ativos"]
    if nivel_poder == 3:
        abas.append("🎖️ Delegar Poder")
    
    tabs = st.tabs(abas)

    # === ABA 1: APROVAÇÕES PENDENTES ===
    with tabs[0]:
        st.markdown("#### Solicitações de Entrada")
        
        # A. ALUNOS
        q_alunos = db.collection('alunos').where('equipe_id', '==', meu_equipe_id).where('status_vinculo', '==', 'pendente')
        if nivel_poder == 1:
            q_alunos = q_alunos.where('professor_id', '==', user_id)
            msg_filtro = "Seus alunos diretos"
        else:
            msg_filtro = "Todos da equipe"
            
        alunos_pend = list(q_alunos.stream())

        if alunos_pend:
            st.info(f"Alunos Pendentes: {len(alunos_pend)} ({msg_filtro})")
            for doc in alunos_pend:
                d = doc.to_dict()
                udoc = db.collection('usuarios').document(d['usuario_id']).get()
                nome_aluno = udoc.to_dict()['nome'] if udoc.exists else "Desconhecido"
                
                with st.container(border=True):
                    c1, c2, c3 = st.columns([0.6, 0.2, 0.2])
                    c1.markdown(f"**{nome_aluno}**\n\n{get_faixa_decorada(d.get('faixa_atual'))}")
                    if c2.button("✅ Aceitar", key=f"ok_al_{doc.id}"):
                        db.collection('alunos').document(doc.id).update({'status_vinculo': 'ativo'})
                        st.toast(f"{nome_aluno} aprovado!"); time.sleep(1); st.rerun()
                    if c3.button("❌ Recusar", key=f"no_al_{doc.id}"):
                        db.collection('alunos').document(doc.id).delete()
                        st.toast("Recusado."); time.sleep(1); st.rerun()
        else:
            st.success("Nenhuma pendência de aluno.")

        # B. PROFESSORES
        if nivel_poder >= 2:
            st.divider()
            st.markdown("#### Professores Pendentes")
            q_profs = db.collection('professores').where('equipe_id', '==', meu_equipe_id).where('status_vinculo', '==', 'pendente')
            profs_pend = list(q_profs.stream())
            
            if profs_pend:
                for doc in profs_pend:
                    d = doc.to_dict()
                    udoc = db.collection('usuarios').document(d['usuario_id']).get()
                    nome_prof = udoc.to_dict()['nome'] if udoc.exists else "Desconhecido"
                    
                    with st.container(border=True):
                        c1, c2, c3 = st.columns([0.6, 0.2, 0.2])
                        c1.markdown(f"**PROFESSOR: {nome_prof}**")
                        if c2.button("✅ Aceitar", key=f"ok_pr_{doc.id}"):
                            db.collection('professores').document(doc.id).update({'status_vinculo': 'ativo'})
                            st.toast("Aceito!"); time.sleep(1); st.rerun()
                        if c3.button("❌ Recusar", key=f"no_pr_{doc.id}"):
                            db.collection('professores').document(doc.id).delete()
                            st.toast("Recusado."); time.sleep(1); st.rerun()

    # === ABA 2: MEMBROS ATIVOS (COM TOTAIS) ===
    with tabs[1]:
        # 1. BUSCAR DADOS (Queries)
        # Fazemos a busca antes para poder contar e exibir os totais no topo
        profs_ativos = list(db.collection('professores').where('equipe_id', '==', meu_equipe_id).where('status_vinculo', '==', 'ativo').stream())
        alunos_ativos = list(db.collection('alunos').where('equipe_id', '==', meu_equipe_id).where('status_vinculo', '==', 'ativo').stream())

        # 2. EXIBIR TOTAIS (Métricas)
        c_tot1, c_tot2 = st.columns(2)
        c_tot1.metric("👨‍🏫 Total Professores", len(profs_ativos))
        c_tot2.metric("🥋 Total Alunos", len(alunos_ativos))
        
        st.divider()

        # 3. TABELA DE PROFESSORES
        st.markdown("#### 🥋 Quadro de Professores")
        
        lista_profs = []
        for p in profs_ativos:
            pdados = p.to_dict()
            u = db.collection('usuarios').document(pdados['usuario_id']).get()
            if u.exists:
                cargo_raw = "Auxiliar"
                if pdados.get('eh_responsavel'): cargo_raw = "Líder"
                elif pdados.get('pode_aprovar'): cargo_raw = "Delegado"
                
                lista_profs.append({
                    "Nome": u.to_dict()['nome'],
                    "Cargo": get_cargo_decorado(cargo_raw)
                })
        
        if lista_profs:
            st.dataframe(
                pd.DataFrame(lista_profs),
                use_container_width=True,
                hide_index=True,
                column_config={
                    "Nome": st.column_config.TextColumn("Professor", width="large"),
                    "Cargo": st.column_config.TextColumn("Função / Nível", width="medium"),
                }
            )
        else:
            st.info("Nenhum professor encontrado.")

        st.markdown("---")

        # 4. TABELA DE ALUNOS
        c_titulo, c_busca = st.columns([1, 1])
        c_titulo.markdown("#### 🥋 Quadro de Alunos")
        filtro = c_busca.text_input("🔍 Buscar aluno:", placeholder="Digite o nome...", label_visibility="collapsed")
        
        lista_alunos = []
        for a in alunos_ativos:
            adados = a.to_dict()
            u = db.collection('usuarios').document(adados['usuario_id']).get()
            if u.exists:
                nome_real = u.to_dict()['nome']
                # Filtro visual
                if filtro and filtro.upper() not in nome_real.upper():
                    continue

                lista_alunos.append({
                    "Nome": nome_real,
                    "Faixa": get_faixa_decorada(adados.get('faixa_atual', '-'))
                })
                
        if lista_alunos:
            df_alunos = pd.DataFrame(lista_alunos).sort_values(by="Nome")
            st.dataframe(
                df_alunos,
                use_container_width=True,
                hide_index=True,
                height=400,
                column_config={
                    "Nome": st.column_config.TextColumn("Aluno", width="large"),
                    "Faixa": st.column_config.TextColumn("Graduação Atual", width="medium"),
                }
            )
            if filtro:
                st.caption(f"Exibindo {len(df_alunos)} alunos filtrados.")
        else:
            if filtro: st.warning("Nenhum aluno encontrado.")
            else: st.warning("Ainda não há alunos ativos.")

    # === ABA 3: DELEGAR PODER ===
    if nivel_poder == 3:
        with tabs[2]:
            st.markdown("#### Gestão de Delegados")
            st.info("Limite: 2 Delegados.")
            
            profs_ativos_del = list(db.collection('professores').where('equipe_id', '==', meu_equipe_id).where('status_vinculo', '==', 'ativo').stream())
            delegados_existentes = [p for p in profs_ativos_del if p.to_dict().get('pode_aprovar') and not p.to_dict().get('eh_responsavel')]
            
            st.metric("Vagas Utilizadas", f"{len(delegados_existentes)} / 2")
            st.divider()
            
            auxiliares = [p for p in profs_ativos_del if not p.to_dict().get('eh_responsavel')]
            
            if not auxiliares:
                st.warning("Sem auxiliares disponíveis.")
            
            for doc in auxiliares:
                d = doc.to_dict()
                u = db.collection('usuarios').document(d['usuario_id']).get()
                nome = u.to_dict()['nome'] if u.exists else "..."
                is_delegado = d.get('pode_aprovar', False)
                
                c1, c2 = st.columns([3, 2])
                c1.write(f"🥋 {nome}")
                
                if is_delegado:
                    if c2.button("⬇️ Revogar", key=f"rv_{doc.id}"):
                        db.collection('professores').document(doc.id).update({'pode_aprovar': False})
                        st.rerun()
                else:
                    btn_disabled = (len(delegados_existentes) >= 2)
                    if c2.button("⬆️ Promover", key=f"pm_{doc.id}", disabled=btn_disabled):
                        db.collection('professores').document(doc.id).update({'pode_aprovar': True})
                        st.rerun()
                st.divider()

# ==============================================================================
# GESTÃO DE CURSOS (ROTA PRINCIPAL)
# Substitua a função antiga por esta completa
# ==============================================================================
def gestao_cursos_route():
    st.markdown("<h1 style='color:#32CD32;'>📚 Gestão Acadêmica</h1>", unsafe_allow_html=True)
    
    # Verificação de Permissão
    user = st.session_state.usuario
    if str(user.get("tipo", "")).lower() not in ["admin", "professor"]:
        st.error("Acesso negado.")
        return

    # --- AQUI ESTÁ A MÁGICA: DIVIDIMOS EM DUAS GRANDES ABAS ---
    tab_conteudo, tab_provas = st.tabs(["📚 Conteúdo & Módulos", "🎓 Provas & Certificados"])

    # ==========================================================================
    # ABA 1: CONTEÚDO (O SEU CÓDIGO VAI AQUI, FOCADO EM CURSO E MÓDULOS)
    # ==========================================================================
    with tab_conteudo:
        db = get_db()
        user_id = user['id']
        user_nome = user['nome']

        # Sub-abas para organizar a criação e edição
        st.markdown("### Conteúdo dos Cursos")
        sub_tab_list, sub_tab_add = st.tabs(["🔎 Listar e Editar", "➕ Criar Novo Curso"])

        # --- SUB-ABA: CRIAR CURSO ---
        with sub_tab_add:
            with st.form("form_novo_curso"):
                c1, c2 = st.columns(2)
                titulo = c1.text_input("Título do Curso *", max_chars=100)
                categoria = c2.text_input("Categoria", "Geral")
                descricao = st.text_area("Descrição Completa *", height=100)
                
                c3, c4 = st.columns(2)
                faixa_minima = c3.selectbox("Faixa Mínima:", ["Nenhuma", "Branca", "Azul", "Roxa", "Marrom", "Preta"])
                duracao = c4.text_input("Duração Estimada", "Não especificada")
                
                st.markdown("---")
                col_up, col_link = st.columns(2)
                up_img = col_up.file_uploader("Capa (Imagem):", type=["jpg","png", "jpeg"])
                url_capa = col_link.text_input("Ou Link da Capa:")
                ativo = st.checkbox("Curso Ativo?", value=True)

                if st.form_submit_button("💾 Criar Curso", type="primary"):
                    if not titulo or not descricao:
                        st.error("Título e Descrição são obrigatórios.")
                    else:
                        # Lógica de Upload (simplificada para o exemplo)
                        url_final = url_capa
                        if up_img:
                            try:
                                from utils import fazer_upload_midia
                                with st.spinner("Subindo imagem..."):
                                    url_final = fazer_upload_midia(up_img) or url_capa
                            except: pass

                        try:
                            novo_curso = {
                                "titulo": titulo.upper(), "descricao": descricao, "categoria": categoria,
                                "faixa_minima": faixa_minima, "duracao_estimada": duracao,
                                "url_capa": url_final, "ativo": ativo,
                                "criado_por_id": user_id, "criado_por_nome": user_nome,
                                "data_criacao": firestore.SERVER_TIMESTAMP, "modulos": []
                            }
                            db.collection('cursos').add(novo_curso)
                            st.success("Curso criado!"); time.sleep(1); st.rerun()
                        except Exception as e: st.error(f"Erro: {e}")

        # --- SUB-ABA: LISTAR E EDITAR ---
        with sub_tab_list:
            # Filtros e Busca
            cursos_ref = list(db.collection('cursos').stream())
            cursos_data = [d.to_dict() | {"id": d.id} for d in cursos_ref]
            
            # Filtra se não for admin
            if str(user.get("tipo")).lower() != "admin":
                cursos_data = [c for c in cursos_data if c.get('criado_por_id') == user_id]

            filtro = st.text_input("🔍 Buscar Curso:", key="filtro_cur_main")
            if filtro:
                cursos_data = [c for c in cursos_data if filtro.upper() in c.get('titulo','').upper()]

            if not cursos_data: st.info("Nenhum curso encontrado.")

            for i, curso in enumerate(cursos_data):
                status_icon = '🟢' if curso.get('ativo') else '🔴'
                with st.expander(f"{status_icon} {curso.get('titulo')} ({curso.get('categoria')})"):
                    
                    # 1. Dados Básicos e Imagem
                    c_img, c_info = st.columns([1, 3])
                    if curso.get('url_capa'): c_img.image(curso.get('url_capa'), width=150)
                    with c_info:
                        st.caption(f"ID: {curso['id']} | Min: {curso.get('faixa_minima')}")
                        st.write(curso.get('descricao'))
                    
                    st.divider()
                    
                    # 2. Gestão de Módulos (Seu código original de módulos vem aqui)
                    st.subheader("🛠️ Módulos e Aulas")
                    modulos = curso.get('modulos', [])
                    
                    # Exibe tabela simples dos módulos
                    if modulos:
                        st.dataframe(pd.DataFrame(modulos), use_container_width=True, hide_index=True, 
                                   column_config={"titulo_modulo": "Módulo", "descricao_modulo": "Desc", "aulas": "Aulas"})
                    else: st.info("Sem módulos ainda.")

                    # Formulário rápido de adicionar módulo
                    with st.form(f"add_mod_{curso['id']}"):
                        c_m1, c_m2 = st.columns(2)
                        mt = c_m1.text_input("Novo Módulo (Título):")
                        md = c_m2.text_input("Descrição Curta:")
                        aul = st.text_area("Aulas (uma por linha):", height=80)
                        
                        if st.form_submit_button("➕ Adicionar/Atualizar Módulo"):
                            if mt:
                                novas_aulas = [x.strip() for x in aul.split('\n') if x.strip()]
                                novo_mod = {"titulo_modulo": mt, "descricao_modulo": md, "aulas": novas_aulas}
                                
                                # Lógica simples: se já existe com mesmo nome, atualiza. Se não, adiciona.
                                mods_atual = list(modulos)
                                idx_found = -1
                                for idx, m in enumerate(mods_atual):
                                    if m.get('titulo_modulo') == mt: idx_found = idx
                                
                                if idx_found >= 0: mods_atual[idx_found] = novo_mod
                                else: mods_atual.append(novo_mod)
                                
                                db.collection('cursos').document(curso['id']).update({"modulos": mods_atual})
                                st.rerun()

                    st.divider()
                    
                    # 3. Botões de Ação Gerais
                    cb1, cb2, cb3 = st.columns(3)
                    if cb1.button("🗑️ Excluir Curso", key=f"del_{curso['id']}"):
                        db.collection('cursos').document(curso['id']).delete(); st.rerun()
                    
                    # (OBS: Removemos o bloco de PROVAS daqui de dentro, pois ele agora tem a aba própria)

    # ==========================================================================
    # ABA 2: PROVAS E CERTIFICADOS (CHAMA O COMPONENTE NOVO)
    # ==========================================================================
    with tab_provas:
        # Aqui chamamos aquela função que você colou no final do arquivo
        componente_gestao_provas()
# ==============================================================================
# COLE ISSO NO FINAL DO ARQUIVO PROFESSOR.PY
# Esta é a lógica das provas, transformada em um componente.
# ==============================================================================
def componente_gestao_provas():
    db = get_db()
    
    # Busca cursos
    try:
        cursos_ref = db.collection('cursos').stream()
        LISTA_CURSOS = sorted([d.to_dict().get('titulo', d.to_dict().get('nome', d.id)) for d in cursos_ref])
    except: LISTA_CURSOS = []
    
    if not LISTA_CURSOS:
        st.warning("Cadastre um curso na aba ao lado primeiro.")
        return

    # Sub-abas internas da gestão de provas
    t1, t2, t3 = st.tabs(["📝 Montar Prova", "👁️ Ver Provas", "✅ Autorizar Alunos"])

    # --- ABA 1: MONTAR ---
    with t1:
        c_sel = st.selectbox("Selecione o Curso:", LISTA_CURSOS, key="prov_curso_sel")
        
        # Carrega dados
        if 'last_c_sel' not in st.session_state or st.session_state.last_c_sel != c_sel:
            cfgs = list(db.collection('config_provas_cursos').where('curso_alvo', '==', c_sel).limit(1).stream())
            st.session_state.cfg_atual = cfgs[0].to_dict() if cfgs else {}
            st.session_state.cfg_id = cfgs[0].id if cfgs else None
            st.session_state.sel_ids = set(st.session_state.cfg_atual.get('questoes_ids', []))
            st.session_state.last_c_sel = c_sel
            
        # Busca Questões
        q_all = list(db.collection('questoes').where('status', '==', 'aprovada').stream())
        
        # Filtros
        col_a, col_b = st.columns(2)
        # Tenta usar niveis globais ou padrao
        try: l_niv = NIVEIS_DIFICULDADE; m_niv = MAPA_NIVEIS
        except: l_niv = [1,2,3,4]; m_niv = {1:'Fácil', 2:'Médio', 3:'Difícil', 4:'Mestre'}
        
        f_niv = col_a.multiselect("Nível:", l_niv, default=l_niv, format_func=lambda x: m_niv.get(x, str(x)), key="f_niv_p")
        cats = sorted(list(set([d.to_dict().get('categoria','Geral') for d in q_all])))
        f_tem = col_b.multiselect("Tema:", cats, default=cats, key="f_tem_p")
        
        # Lista
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
                        st.markdown(f"**{cat}** | {d.get('pergunta')}")
                        if d.get('url_imagem'): st.image(d.get('url_imagem'), width=80)
                    st.divider()
            if vis==0: st.caption("Nada encontrado.")
            
        qt = len(st.session_state.sel_ids)
        st.info(f"{qt} questões selecionadas.")
        
        with st.form("save_prova"):
            c1, c2 = st.columns(2)
            tmp = c1.number_input("Tempo (min)", 10, 180, int(st.session_state.cfg_atual.get('tempo_limite',60)))
            nota = c2.number_input("Min. Aprovação (%)", 10, 100, int(st.session_state.cfg_atual.get('aprovacao_minima',70)))
            if st.form_submit_button("💾 Salvar Prova"):
                dados = {"curso_alvo": c_sel, "questoes_ids": list(st.session_state.sel_ids), "qtd_questoes": qt, "tempo_limite": tmp, "aprovacao_minima": nota, "tipo_prova": "curso", "atualizado_em": firestore.SERVER_TIMESTAMP}
                if st.session_state.cfg_id: db.collection('config_provas_cursos').document(st.session_state.cfg_id).update(dados)
                else: db.collection('config_provas_cursos').add(dados)
                st.success("Salvo!"); time.sleep(1); st.rerun()

    # --- ABA 2: VISUALIZAR ---
    with t2:
        st.caption("Provas Configuradas")
        all_c = list(db.collection('config_provas_cursos').stream())
        if not all_c: st.info("Nenhuma prova ainda.")
        cols = st.columns(3)
        for i, dc in enumerate(all_c):
            dd = dc.to_dict()
            with cols[i%3]:
                with st.container(border=True):
                    st.markdown(f"**{dd.get('curso_alvo')}**")
                    st.caption(f"{dd.get('qtd_questoes')} questões | {dd.get('tempo_limite')}min")
                    if st.button("🗑️", key=f"del_p_{dc.id}"):
                        db.collection('config_provas_cursos').document(dc.id).delete(); st.rerun()

    # --- ABA 3: AUTORIZAR ---
    with t3:
        st.caption("Liberar Alunos")
        c1, c2 = st.columns(2)
        ini = datetime.combine(c1.date_input("Início", key="di_p"), dtime(0,0))
        fim = datetime.combine(c2.date_input("Fim", key="df_p"), dtime(23,59))
        
        busca = st.text_input("Buscar aluno:", key="bus_al")
        als = db.collection('usuarios').where('tipo_usuario','==','aluno').stream()
        
        for a in als:
            ad = a.to_dict(); aid = a.id
            if busca and busca.lower() not in ad.get('nome','').lower(): continue
            
            # Linha Aluno
            ca, cb, cc, cd = st.columns([3, 3, 2, 1])
            ca.write(f"**{ad.get('nome')}**")
            
            # Select Curso
            curs_atv = ad.get('curso_prova_alvo','')
            try: idx = LISTA_CURSOS.index(curs_atv)
            except: idx = 0
            sel_c = cb.selectbox("Curso", LISTA_CURSOS, index=idx, key=f"s_c_{aid}", label_visibility="collapsed")
            
            # Status
            stt = "⚪"
            if ad.get('exame_habilitado') and ad.get('tipo_exame') == 'curso':
                s = ad.get('status_exame','pendente')
                if s=='aprovado': stt="🏆 OK"
                elif s=='reprovado': stt="🔴 Ruim"
                else: stt="🟢 On"
            cc.write(stt)
            
            # Ação
            if ad.get('exame_habilitado') and ad.get('tipo_exame') == 'curso':
                if cd.button("⛔", key=f"b_p_{aid}"):
                    db.collection('usuarios').document(aid).update({"exame_habilitado":False}); st.rerun()
            else:
                if cd.button("✅", key=f"l_p_{aid}"):
                    db.collection('usuarios').document(aid).update({
                        "exame_habilitado":True, "tipo_exame":"curso", "curso_prova_alvo": sel_c,
                        "exame_inicio": ini.isoformat(), "exame_fim": fim.isoformat(),
                        "status_exame":"pendente", "status_exame_em_andamento": False
                    }); st.rerun()
            st.divider()
            
# =========================================
# FUNÇÃO PRINCIPAL: PAINEL DO PROFESSOR (ATUALIZADA)
# =========================================
def painel_professor():
    st.markdown("<h1 style='color:#FFD770;'>👨‍🏫 Painel do Professor</h1>", unsafe_allow_html=True)
    
    if st.button("🏠 Voltar ao Início", key="btn_voltar_prof"):
        st.session_state.menu_selection = "Início"; st.rerun()

    # Note que agora temos 3 abas, a Gestão de Cursos é a segunda.
    tab1, tab2, tab3 = st.tabs(["👥 Gestão de Equipe", "📚 Gestão de Cursos", "📊 Estatísticas & Dashboard"])
    
    with tab1:
        gestao_equipes()
               
    with tab2:
        dashboard.dashboard_professor()
