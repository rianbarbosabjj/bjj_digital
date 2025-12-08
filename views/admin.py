import streamlit as st
import pandas as pd
import bcrypt
import time 
import io 
from datetime import datetime, date, time as dtime 
from database import get_db, OPCOES_SEXO
from firebase_admin import firestore

# Tenta importar o dashboard
try:
    from views.dashboard_admin import render_dashboard_geral
except ImportError:
    def render_dashboard_geral(): st.warning("Dashboard não encontrado.")

# Importa utils
try:
    from utils import (
        carregar_todas_questoes, salvar_questoes, fazer_upload_midia, 
        normalizar_link_video, verificar_duplicidade_ia,
        auditoria_ia_questao, auditoria_ia_openai, IA_ATIVADA 
    )
except ImportError:
    IA_ATIVADA = False
    def carregar_todas_questoes(): return []
    def salvar_questoes(t, q): pass
    def fazer_upload_midia(f): return None
    def normalizar_link_video(u): return u
    def verificar_duplicidade_ia(n, l, t=0.85): return False, None
    def auditoria_ia_questao(p, a, c): return "Indisponível"
    def auditoria_ia_openai(p, a, c): return "Indisponível"

# --- CONSTANTES ---
FAIXAS_COMPLETAS = [" ", "Cinza e Branca", "Cinza", "Cinza e Preta", "Amarela e Branca", "Amarela", "Amarela e Preta", "Laranja e Branca", "Laranja", "Laranja e Preta", "Verde e Branca", "Verde", "Verde e Preta", "Azul", "Roxa", "Marrom", "Preta"]
NIVEIS_DIFICULDADE = [1, 2, 3, 4]
MAPA_NIVEIS = {1: "🟢 Fácil", 2: "🔵 Médio", 3: "🟠 Difícil", 4: "🔴 Muito Difícil"}

def get_badge_nivel(n): return MAPA_NIVEIS.get(n, "⚪ ?")

# ==============================================================================
# 1. GESTÃO GERAL DE USUÁRIOS (VISÃO DO ADMIN GLOBAL DO SISTEMA)
# ==============================================================================
def gestao_usuarios_geral():
    st.subheader("🌍 Visão Global de Usuários (Super Admin)")
    db = get_db()
    
    users_ref = list(db.collection('usuarios').stream())
    users = [d.to_dict() | {"id": d.id} for d in users_ref]
    
    if not users: st.warning("Vazio."); return
    
    df = pd.DataFrame(users)
    c1, c2 = st.columns(2)
    filtro = c1.text_input("🔍 Buscar Geral:")
    if filtro:
        termo = filtro.upper()
        df = df[df['nome'].astype(str).str.upper().str.contains(termo) | df['email'].astype(str).str.upper().str.contains(termo)]

    cols_show = ['nome', 'email', 'tipo_usuario', 'faixa_atual']
    for c in cols_show: 
        if c not in df.columns: df[c] = "-"
    st.dataframe(df[cols_show], use_container_width=True, hide_index=True)
    
    st.markdown("---")
    st.subheader("🛠️ Editar Cadastro (Modo Admin)")
    opcoes = df.to_dict('records')
    sel = st.selectbox("Selecione:", opcoes, format_func=lambda x: f"{x.get('nome')} ({x.get('tipo_usuario')})")
    
    if sel:
        with st.form(f"edt_geral_{sel['id']}"):
            new_nome = st.text_input("Nome", sel.get('nome'))
            new_email = st.text_input("Email", sel.get('email'))
            new_pass = st.text_input("Nova Senha (Opcional)", type="password")
            if st.form_submit_button("Salvar"):
                upd = {"nome": new_nome.upper(), "email": new_email.lower()}
                if new_pass:
                    upd["senha"] = bcrypt.hashpw(new_pass.encode(), bcrypt.gensalt()).decode()
                    upd["precisa_trocar_senha"] = True
                db.collection('usuarios').document(sel['id']).update(upd)
                st.success("Salvo!"); time.sleep(1); st.rerun()
        
        if st.button("Excluir Usuário", key=f"del_{sel['id']}"):
            db.collection('usuarios').document(sel['id']).delete()
            st.warning("Deletado."); st.rerun()

# ==============================================================================
# 2. GESTÃO DE EQUIPES (NOVO FLUXO)
# ==============================================================================
def gestao_equipes_tab():
    st.markdown("<h2 style='color:#FFD700;'>🏛️ Gestão de Equipe</h2>", unsafe_allow_html=True)
    db = get_db()
    user = st.session_state.usuario
    user_id = user['id']
    
    # Verifica se é Admin Global (Sistema)
    eh_admin_sistema = (str(user.get("tipo_usuario", "")).lower() == "admin")
    
    # --- 1. IDENTIFICAR O VÍNCULO DO USUÁRIO COM A EQUIPE ---
    meu_equipe_id = None
    sou_responsavel = False
    sou_delegado = False 
    
    if not eh_admin_sistema:
        # Busca vínculo ativo de professor
        vinc = list(db.collection('professores').where('usuario_id', '==', user_id).where('status_vinculo', '==', 'ativo').limit(1).stream())
        if vinc:
            dados_v = vinc[0].to_dict()
            meu_equipe_id = dados_v.get('equipe_id')
            sou_responsavel = dados_v.get('eh_responsavel', False)
            sou_delegado = dados_v.get('pode_aprovar', False)
        else:
            st.error("⛔ Você não está vinculado a nenhuma equipe como Professor Ativo.")
            return
    else:
        # Se for Admin Global, permite selecionar uma equipe para gerenciar (debug/suporte)
        equipes_all = list(db.collection('equipes').stream())
        opcoes_eq = {e.id: e.to_dict().get('nome') for e in equipes_all}
        meu_equipe_id = st.selectbox("Selecione a Equipe (Admin Mode):", list(opcoes_eq.keys()), format_func=lambda x: opcoes_eq[x])
        sou_responsavel = True # Admin tem poder total

    # Busca nome da equipe
    nome_equipe = "Desconhecida"
    if meu_equipe_id:
        eq_doc = db.collection('equipes').document(meu_equipe_id).get()
        if eq_doc.exists: nome_equipe = eq_doc.to_dict().get('nome')

    # --- 2. DEFINIR NÍVEL DE PERMISSÃO ---
    # Nível 3: Professor Responsável (Líder) -> Vê tudo, aprova tudo, delega poder.
    # Nível 2: Professor Auxiliar Delegado -> Vê tudo, aprova alunos e outros professores.
    # Nível 1: Professor Auxiliar Comum -> Vê alunos da sua turma, aprova seus alunos.
    
    nivel_poder = 1
    if sou_delegado: nivel_poder = 2
    if sou_responsavel or eh_admin_sistema: nivel_poder = 3

    # Exibe Banner Informativo
    cols_info = st.columns([3, 1])
    cols_info[0].info(f"Equipe: **{nome_equipe}**")
    
    badge = "⭐ Auxiliar"
    if nivel_poder == 2: badge = "⭐⭐ Delegado"
    if nivel_poder == 3: badge = "⭐⭐⭐ Responsável"
    cols_info[1].success(f"Cargo: {badge}")

    # --- 3. ABAS DE GESTÃO ---
    abas_titulos = ["⏳ Solicitações Pendentes", "👥 Membros Ativos"]
    if nivel_poder == 3: abas_titulos.append("🎖️ Gestão de Poder")
    if eh_admin_sistema: abas_titulos.append("⚙️ Admin Equipes")
    
    tabs = st.tabs(abas_titulos)

    # === ABA 1: SOLICITAÇÕES PENDENTES ===
    with tabs[0]:
        st.markdown("### 🔔 Aprovações Pendentes")
        
        # --- A. PENDÊNCIA DE ALUNOS ---
        st.markdown("#### 🥋 Alunos Aguardando")
        q_alunos = db.collection('alunos').where('status_vinculo', '==', 'pendente').where('equipe_id', '==', meu_equipe_id)
        
        # Se for Auxiliar Comum (Nível 1), SÓ vê alunos que escolheram ele especificamente
        if nivel_poder == 1:
            q_alunos = q_alunos.where('professor_id', '==', user_id)
            st.caption("Vendo apenas alunos que solicitaram entrada na **sua** turma.")
        else:
            st.caption("Vendo solicitações de alunos para **toda** a equipe.")

        alunos_pend = list(q_alunos.stream())
        
        if not alunos_pend:
            st.info("Nenhuma solicitação de aluno pendente.")
        else:
            for doc in alunos_pend:
                d = doc.to_dict()
                u_doc = db.collection('usuarios').document(d['usuario_id']).get()
                nome_aluno = u_doc.to_dict()['nome'] if u_doc.exists else "Usuário Desconhecido"
                
                with st.container(border=True):
                    c1, c2, c3 = st.columns([0.6, 0.2, 0.2])
                    c1.markdown(f"**{nome_aluno}**\n\nFaixa: {d.get('faixa_atual')}")
                    if c2.button("✅ Aprovar", key=f"ap_al_{doc.id}"):
                        db.collection('alunos').document(doc.id).update({'status_vinculo': 'ativo'})
                        st.toast(f"{nome_aluno} aprovado!"); time.sleep(1); st.rerun()
                    if c3.button("❌ Recusar", key=f"rc_al_{doc.id}"):
                        db.collection('alunos').document(doc.id).delete()
                        st.toast(f"{nome_aluno} recusado."); time.sleep(1); st.rerun()

        # --- B. PENDÊNCIA DE PROFESSORES (Só Nível 2 e 3 vê) ---
        if nivel_poder >= 2:
            st.divider()
            st.markdown("#### 🥋 Professores Auxiliares Aguardando")
            q_profs = db.collection('professores').where('status_vinculo', '==', 'pendente').where('equipe_id', '==', meu_equipe_id)
            profs_pend = list(q_profs.stream())
            
            if not profs_pend:
                st.info("Nenhuma solicitação de professor pendente.")
            else:
                for doc in profs_pend:
                    d = doc.to_dict()
                    u_doc = db.collection('usuarios').document(d['usuario_id']).get()
                    nome_prof = u_doc.to_dict()['nome'] if u_doc.exists else "Usuário Desconhecido"
                    
                    with st.container(border=True):
                        c1, c2, c3 = st.columns([0.6, 0.2, 0.2])
                        c1.markdown(f"**PROFESSOR: {nome_prof}**\n\nSolicita entrada como Auxiliar.")
                        if c2.button("✅ Autorizar", key=f"ap_pr_{doc.id}"):
                            db.collection('professores').document(doc.id).update({'status_vinculo': 'ativo'})
                            st.toast(f"Professor {nome_prof} autorizado!"); time.sleep(1); st.rerun()
                        if c3.button("❌ Recusar", key=f"rc_pr_{doc.id}"):
                            db.collection('professores').document(doc.id).delete()
                            st.toast("Solicitação recusada."); time.sleep(1); st.rerun()
        elif nivel_poder == 1:
            st.divider()
            st.info("Você não tem permissão para aprovar novos professores auxiliares.")

    # === ABA 2: MEMBROS ATIVOS ===
    with tabs[1]:
        st.markdown("### 📜 Quadro de Membros")
        col_filtro, _ = st.columns([1,1])
        filtro_nome = col_filtro.text_input("Buscar membro por nome:")
        
        lista_final = []
        
        # 1. Busca Professores da Equipe
        profs_ref = db.collection('professores').where('equipe_id', '==', meu_equipe_id).where('status_vinculo', '==', 'ativo').stream()
        for p in profs_ref:
            pdados = p.to_dict()
            udoc = db.collection('usuarios').document(pdados['usuario_id']).get()
            if udoc.exists:
                role = "Auxiliar"
                if pdados.get('eh_responsavel'): role = "Líder (Resp.)"
                elif pdados.get('pode_aprovar'): role = "Delegado"
                
                lista_final.append({
                    "Nome": udoc.to_dict()['nome'],
                    "Tipo": "Professor",
                    "Status/Faixa": role,
                    "ID": p.id
                })

        # 2. Busca Alunos da Equipe
        alunos_ref = db.collection('alunos').where('equipe_id', '==', meu_equipe_id).where('status_vinculo', '==', 'ativo').stream()
        for a in alunos_ref:
            adados = a.to_dict()
            udoc = db.collection('usuarios').document(adados['usuario_id']).get()
            if udoc.exists:
                lista_final.append({
                    "Nome": udoc.to_dict()['nome'],
                    "Tipo": "Aluno",
                    "Status/Faixa": adados.get('faixa_atual', '-'),
                    "ID": a.id
                })
        
        # Exibe Tabela
        if lista_final:
            df_membros = pd.DataFrame(lista_final)
            if filtro_nome:
                df_membros = df_membros[df_membros['Nome'].str.upper().str.contains(filtro_nome.upper())]
            
            st.dataframe(
                df_membros[['Nome', 'Tipo', 'Status/Faixa']], 
                use_container_width=True, 
                hide_index=True
            )
        else:
            st.warning("Ainda não há membros ativos nesta equipe.")

    # === ABA 3: GESTÃO DE PODER (SÓ LÍDER) ===
    if nivel_poder == 3 and "🎖️ Gestão de Poder" in abas_titulos:
        with tabs[2]:
            st.markdown("### 🎖️ Delegar Autoridade")
            st.info("""
            **Regra:** Você pode delegar até **2 Professores Auxiliares** para ajudarem na aprovação de solicitações.
            Delegados podem aprovar alunos e outros professores auxiliares.
            """)
            
            # 1. Contar quantos delegados já existem (excluindo o líder)
            q_delegados = db.collection('professores')\
                .where('equipe_id', '==', meu_equipe_id)\
                .where('pode_aprovar', '==', True)\
                .where('status_vinculo', '==', 'ativo')\
                .stream()
            
            delegados_ids = [d.id for d in q_delegados if not d.to_dict().get('eh_responsavel')]
            qtd_delegados = len(delegados_ids)
            
            st.metric("Vagas de Delegado Utilizadas", f"{qtd_delegados} / 2")

            st.divider()
            st.markdown("#### Professores Auxiliares Disponíveis")
            
            # Lista auxiliares para promover/rebaixar
            q_aux = db.collection('professores')\
                .where('equipe_id', '==', meu_equipe_id)\
                .where('status_vinculo', '==', 'ativo')\
                .stream()
            
            encontrou_auxiliar = False
            for doc in q_aux:
                d = doc.to_dict()
                if d.get('eh_responsavel'): continue # Pula o próprio líder
                
                encontrou_auxiliar = True
                uid = d.get('usuario_id')
                udoc = db.collection('usuarios').document(uid).get()
                nome = udoc.to_dict()['nome'] if udoc.exists else "Sem Nome"
                eh_del = d.get('pode_aprovar', False)
                
                c1, c2 = st.columns([3, 2])
                c1.write(f"🥋 **{nome}**")
                
                if eh_del:
                    if c2.button("⬇️ Revogar Poder", key=f"rv_{doc.id}"):
                        db.collection('professores').document(doc.id).update({'pode_aprovar': False})
                        st.toast(f"Poder de {nome} revogado."); time.sleep(1); st.rerun()
                else:
                    # Só habilita botão de promover se tiver vaga (< 2)
                    pode_promover = (qtd_delegados < 2)
                    if c2.button("⬆️ Promover a Delegado", key=f"pm_{doc.id}", disabled=not pode_promover):
                        db.collection('professores').document(doc.id).update({'pode_aprovar': True})
                        st.toast(f"{nome} agora é Delegado!"); time.sleep(1); st.rerun()
                st.divider()
            
            if not encontrou_auxiliar:
                st.warning("Não há professores auxiliares cadastrados na equipe para delegar.")

    # === ABA 4: ADMIN EQUIPES (SÓ SUPER ADMIN) ===
    if eh_admin_sistema and "⚙️ Admin Equipes" in abas_titulos:
        with tabs[3]:
            st.subheader("Criar/Excluir Equipes (Sistema)")
            with st.form("add_eq"):
                nm = st.text_input("Nome da Nova Equipe")
                desc = st.text_input("Descrição")
                if st.form_submit_button("Criar Equipe"):
                    db.collection('equipes').add({"nome": nm.upper(), "descricao": desc, "ativo": True})
                    st.success("Criada!"); st.rerun()

# ==============================================================================
# 3. GESTÃO DE QUESTÕES (MANTIDO)
# ==============================================================================
def gestao_questoes_tab():
    st.markdown("<h1 style='color:#FFD700;'>📝 Banco de Questões</h1>", unsafe_allow_html=True)
    db = get_db()
    user = st.session_state.usuario
    user_tipo = str(user.get("tipo_usuario", user.get("tipo", ""))).lower()
    if user_tipo not in ["admin", "professor"]: st.error("Acesso negado."); return

    titulos = ["📚 Listar/Editar", "➕ Adicionar Nova", "🔎 Minhas Submissões"]
    if user_tipo == "admin": titulos.append("⏳ Aprovações (Admin)")
    tabs = st.tabs(titulos)
    
    with tabs[0]:
        q_ref = list(db.collection('questoes').where('status', '==', 'aprovada').stream())
        c1, c2 = st.columns(2)
        termo = c1.text_input("🔍 Buscar (Aprovadas):")
        filt_n = c2.multiselect("Nível:", NIVEIS_DIFICULDADE)
        q_filtro = []
        for doc in q_ref:
            d = doc.to_dict(); d['id'] = doc.id
            if termo and termo.lower() not in d.get('pergunta','').lower(): continue
            if filt_n and d.get('dificuldade',1) not in filt_n: continue
            q_filtro.append(d)
        if not q_filtro: st.info("Nenhuma questão aprovada.")
        else:
            st.caption(f"{len(q_filtro)} questões ativas")
            for q in q_filtro:
                with st.container(border=True):
                    ch, cb = st.columns([5, 1])
                    bdg = get_badge_nivel(q.get('dificuldade',1))
                    ch.markdown(f"**{bdg}** | ✍️ {q.get('criado_por','?')}")
                    ch.markdown(f"##### {q.get('pergunta')}")
                    if q.get('url_imagem'): ch.image(q.get('url_imagem'), width=150)
                    if q.get('url_video'):
                        try: ch.video(normalizar_link_video(q.get('url_video')))
                        except: pass
                    with ch.expander("Alternativas"):
                        alts = q.get('alternativas', {})
                        st.write(f"A) {alts.get('A','')} | B) {alts.get('B','')} | C) {alts.get('C','')} | D) {alts.get('D','')}")
                        st.success(f"Correta: {q.get('resposta_correta')}")
                    if cb.button("✏️", key=f"ed_{q['id']}"): st.session_state['edit_q'] = q['id']
                if st.session_state.get('edit_q') == q['id']:
                    with st.container(border=True):
                        st.markdown("#### ✏️ Editando")
                        with st.form(f"f_ed_{q['id']}"):
                            perg = st.text_area("Enunciado *", value=q.get('pergunta',''))
                            if st.form_submit_button("💾 Salvar"):
                                db.collection('questoes').document(q['id']).update({"pergunta": perg})
                                st.session_state['edit_q'] = None; st.rerun()
                            if st.form_submit_button("Cancelar"): st.session_state['edit_q'] = None; st.rerun()
                        if st.button("🗑️ Deletar", key=f"del_q_{q['id']}", type="primary"):
                            db.collection('questoes').document(q['id']).delete(); st.session_state['edit_q'] = None; st.rerun()

    with tabs[1]:
        with st.form("new_q"):
            st.markdown("#### Nova Questão")
            perg = st.text_area("Enunciado *")
            c1, c2 = st.columns(2)
            dif = c1.selectbox("Nível:", NIVEIS_DIFICULDADE); cat = c2.text_input("Categoria:", "Geral")
            ca, cb = st.columns(2); cc, cd = st.columns(2)
            alt_a = ca.text_input("A) *"); alt_b = cb.text_input("B) *"); alt_c = cc.text_input("C)"); alt_d = cd.text_input("D)")
            correta = st.selectbox("Correta *", ["A","B","C","D"])
            if st.form_submit_button("💾 Cadastrar"):
                if perg and alt_a and alt_b:
                    stt = "aprovada" if user_tipo == "admin" else "pendente"
                    db.collection('questoes').add({"pergunta": perg, "dificuldade": dif, "categoria": cat, "alternativas": {"A":alt_a, "B":alt_b, "C":alt_c, "D":alt_d}, "resposta_correta": correta, "status": stt, "criado_por": user.get('nome', 'Admin')})
                    st.success("Cadastrada!"); time.sleep(1); st.rerun()
                else: st.warning("Preencha obrigatórios.")
    
    if user_tipo == "admin" and len(tabs) > 3:
         with tabs[3]:
            st.info("Painel de Aprovação (Admin)")

# ==============================================================================
# 4. GESTÃO DE EXAMES (MANTIDO)
# ==============================================================================
def gestao_exame_de_faixa_route():
    st.markdown("<h1 style='color:#FFD700;'>⚙️ Montador de Exames</h1>", unsafe_allow_html=True)
    db = get_db()
    tab1, tab2, tab3 = st.tabs(["📝 Montar Prova", "👁️ Visualizar", "✅ Autorizar Alunos"])

    with tab1:
        st.subheader("1. Selecione a Faixa")
        faixa_sel = st.selectbox("Prova de Faixa:", FAIXAS_COMPLETAS)
        if 'last_faixa_sel' not in st.session_state or st.session_state.last_faixa_sel != faixa_sel:
            configs = list(db.collection('config_exames').where('faixa', '==', faixa_sel).limit(1).stream())
            conf_atual = configs[0].to_dict() if configs else {}
            st.session_state.conf_atual = conf_atual; st.session_state.doc_id = configs[0].id if configs else None
            st.session_state.selected_ids = set(conf_atual.get('questoes_ids', []))
            st.session_state.last_faixa_sel = faixa_sel
        conf_atual = st.session_state.conf_atual
        todas = list(db.collection('questoes').where('status', '==', 'aprovada').stream())
        
        with st.container(height=300, border=True):
            for doc in todas:
                d = doc.to_dict()
                chk = st.checkbox(f"{d.get('pergunta')}", value=(doc.id in st.session_state.selected_ids), key=f"chk_{doc.id}")
                if chk: st.session_state.selected_ids.add(doc.id)
                else: st.session_state.selected_ids.discard(doc.id)
        
        st.write(f"Selecionadas: {len(st.session_state.selected_ids)}")
        if st.button("💾 Salvar Prova"):
            dados = {"faixa": faixa_sel, "questoes_ids": list(st.session_state.selected_ids), "qtd_questoes": len(st.session_state.selected_ids)}
            if st.session_state.doc_id: db.collection('config_exames').document(st.session_state.doc_id).update(dados)
            else: db.collection('config_exames').add(dados)
            st.success("Salvo!"); time.sleep(1); st.rerun()

    with tab2:
        st.subheader("Status das Provas")
        confs = db.collection('config_exames').stream()
        for c in confs:
            d = c.to_dict()
            st.success(f"{d.get('faixa')} - {d.get('qtd_questoes')} questões")

    with tab3:
        st.subheader("Autorizar Alunos")
        st.info("Utilize a aba 'Gestão de Equipe' para aprovar a entrada. Aqui você libera o exame.")

# =========================================
# CONTROLADOR PRINCIPAL
# =========================================
def gestao_questoes(): gestao_questoes_tab()
def gestao_exame_de_faixa(): gestao_exame_de_faixa_route()
def gestao_equipes(): gestao_equipes_tab()

def gestao_usuarios(usuario_logado):
    st.markdown(f"<h1 style='color:#FFD700;'>Gestão e Estatísticas</h1>", unsafe_allow_html=True)
    if st.button("🏠 Voltar ao Início", key="btn_back_admin_main"):
        st.session_state.menu_selection = "Início"; st.rerun()
    
    tipo = str(usuario_logado.get("tipo_usuario", "aluno")).lower()
    
    opcoes_menu = []
    if tipo == 'admin':
        opcoes_menu = ["👥 Usuários (Geral)", "🏛️ Gestão de Equipe", "📊 Dashboard"]
    elif tipo == 'professor':
        opcoes_menu = ["🏛️ Gestão de Equipe"]
    
    if not opcoes_menu: st.error("Acesso restrito."); return

    if len(opcoes_menu) > 1:
        menu = st.radio("", opcoes_menu, horizontal=True, label_visibility="collapsed")
    else:
        menu = opcoes_menu[0]

    st.markdown("---")
    
    if menu == "📊 Dashboard": render_dashboard_geral()
    elif menu == "👥 Usuários (Geral)": gestao_usuarios_geral()
    elif menu == "🏛️ Gestão de Equipe": gestao_equipes_tab()
