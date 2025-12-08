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
    """Adiciona um emoji colorido baseado na faixa"""
    f = str(faixa).lower()
    if "branca" in f: return f"⚪ {faixa}"
    if "cinza" in f: return f"🔘 {faixa}"
    if "amarela" in f: return f"🟡 {faixa}"
    if "laranja" in f: return f"🟠 {faixa}"
    if "verde" in f: return f"🟢 {faixa}"
    if "azul" in f: return f"🔵 {faixa}"
    if "roxa" in f: return f"🟣 {faixa}"
    if "marrom" in f: return f"🟤 {faixa}"
    if "preta" in f: return f"⚫ {faixa}"
    return f"🥋 {faixa}"

def get_cargo_decorado(cargo):
    if cargo == "Líder": return "👑 Líder (Responsável)"
    if cargo == "Delegado": return "🛡️ Delegado"
    return "🥋 Auxiliar"

# =========================================
# FUNÇÃO: GESTÃO DE EQUIPES (FLUXO COMPLETO)
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

    # Cabeçalho Informativo Estilizado
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
        
        # --- A. ALUNOS PENDENTES ---
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

        # --- B. PROFESSORES PENDENTES ---
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

    # === ABA 2: MEMBROS ATIVOS (MELHORADA) ===
    with tabs[1]:
        # --- 1. TABELA DE PROFESSORES ---
        st.markdown("#### 🥋 Quadro de Professores")
        profs_ativos = list(db.collection('professores').where('equipe_id', '==', meu_equipe_id).where('status_vinculo', '==', 'ativo').stream())
        
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
                    "Cargo": get_cargo_decorado(cargo_raw) # Aplica decoração
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

        st.markdown("---") # Divisória

        # --- 2. TABELA DE ALUNOS ---
        c_titulo, c_busca = st.columns([1, 1])
        c_titulo.markdown("#### 🥋 Quadro de Alunos")
        filtro = c_busca.text_input("🔍 Buscar aluno:", placeholder="Digite o nome...", label_visibility="collapsed")
        
        alunos_ativos = list(db.collection('alunos').where('equipe_id', '==', meu_equipe_id).where('status_vinculo', '==', 'ativo').stream())
        
        lista_alunos = []
        for a in alunos_ativos:
            adados = a.to_dict()
            u = db.collection('usuarios').document(adados['usuario_id']).get()
            if u.exists:
                # Normaliza o nome para busca
                nome_real = u.to_dict()['nome']
                # Aplica o filtro antes de processar para ganhar performance visual
                if filtro and filtro.upper() not in nome_real.upper():
                    continue

                lista_alunos.append({
                    "Nome": nome_real,
                    "Faixa": get_faixa_decorada(adados.get('faixa_atual', '-')) # Aplica cor
                })
                
        if lista_alunos:
            df_alunos = pd.DataFrame(lista_alunos)
            # Ordenar por nome
            df_alunos = df_alunos.sort_values(by="Nome")
            
            st.dataframe(
                df_alunos,
                use_container_width=True,
                hide_index=True,
                height=400, # Altura fixa para scrollar se tiver muitos alunos
                column_config={
                    "Nome": st.column_config.TextColumn("Aluno", width="large"),
                    "Faixa": st.column_config.TextColumn("Graduação Atual", width="medium"),
                }
            )
            st.caption(f"Total listado: {len(df_alunos)} alunos.")
        else:
            if filtro:
                st.warning("Nenhum aluno encontrado com esse nome.")
            else:
                st.warning("Ainda não há alunos ativos nesta equipe.")

    # === ABA 3: DELEGAR PODER ===
    if nivel_poder == 3:
        with tabs[2]:
            st.markdown("#### Gestão de Delegados")
            st.info("Limite: 2 Delegados.")
            
            profs_ativos = list(db.collection('professores').where('equipe_id', '==', meu_equipe_id).where('status_vinculo', '==', 'ativo').stream())
            delegados_existentes = [p for p in profs_ativos if p.to_dict().get('pode_aprovar') and not p.to_dict().get('eh_responsavel')]
            
            st.metric("Vagas Utilizadas", f"{len(delegados_existentes)} / 2")
            st.divider()
            
            auxiliares = [p for p in profs_ativos if not p.to_dict().get('eh_responsavel')]
            
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

# =========================================
# FUNÇÃO PRINCIPAL: PAINEL DO PROFESSOR
# =========================================
def painel_professor():
    st.markdown("<h1 style='color:#FFD770;'>👨‍🏫 Painel do Professor</h1>", unsafe_allow_html=True)
    
    if st.button("🏠 Voltar ao Início", key="btn_voltar_prof"):
        st.session_state.menu_selection = "Início"; st.rerun()

    tab1, tab2 = st.tabs(["👥 Gestão de Equipe", "📊 Estatísticas & Dashboard"])
    
    with tab1:
        gestao_equipes()
        
    with tab2:
        dashboard.dashboard_professor()
