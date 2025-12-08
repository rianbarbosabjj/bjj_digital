import streamlit as st
import pandas as pd
import time
from database import get_db
from firebase_admin import firestore
# Importamos o dashboard para usar dentro da aba
from views import dashboard 

# =========================================
# FUNÇÃO: GESTÃO DE EQUIPES (NOVO FLUXO HIERÁRQUICO)
# =========================================
def gestao_equipes():
    db = get_db()
    user = st.session_state.usuario
    user_id = user['id']

    # --- 1. IDENTIFICAR O CONTEXTO DO PROFESSOR ---
    # Busca o vínculo do professor logado para saber quem ele é na hierarquia
    vinc = list(db.collection('professores').where('usuario_id', '==', user_id).where('status_vinculo', '==', 'ativo').limit(1).stream())
    
    if not vinc:
        st.error("⛔ Você não possui vínculo ativo com nenhuma equipe.")
        st.info("Solicite ao responsável da sua academia que aprove seu cadastro.")
        return

    dados_prof = vinc[0].to_dict()
    meu_equipe_id = dados_prof.get('equipe_id')
    sou_responsavel = dados_prof.get('eh_responsavel', False)
    sou_delegado = dados_prof.get('pode_aprovar', False) # Flag que permite auxiliar aprovar

    # Busca nome da equipe
    nome_equipe = "Minha Equipe"
    if meu_equipe_id:
        eq_doc = db.collection('equipes').document(meu_equipe_id).get()
        if eq_doc.exists:
            nome_equipe = eq_doc.to_dict().get('nome', 'Minha Equipe')

    # --- 2. DEFINIR NÍVEL DE PODER ---
    # Nível 3: Líder (Responsável) -> Pode tudo + Delegar
    # Nível 2: Delegado -> Pode aprovar Alunos e Professores
    # Nível 1: Auxiliar -> Pode aprovar SÓ seus alunos diretos
    nivel_poder = 1
    if sou_delegado: nivel_poder = 2
    if sou_responsavel: nivel_poder = 3

    # Cabeçalho Informativo
    st.markdown(f"### 🏛️ {nome_equipe}")
    
    badge = "⭐ Auxiliar"
    if nivel_poder == 2: badge = "⭐⭐ Professor Delegado"
    if nivel_poder == 3: badge = "⭐⭐⭐ Professor Responsável"
    
    st.caption(f"Seu Cargo: **{badge}**")

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
        
        # Filtro de Visibilidade (Tenancy)
        if nivel_poder == 1:
            # Auxiliar vê apenas alunos que o escolheram como professor direto
            q_alunos = q_alunos.where('professor_id', '==', user_id)
            msg_filtro = "Exibindo apenas alunos que selecionaram você."
        else:
            msg_filtro = "Exibindo todos os alunos pendentes da equipe."
            
        alunos_pend = list(q_alunos.stream())

        if alunos_pend:
            st.info(f"Alunos: {len(alunos_pend)} pendentes. ({msg_filtro})")
            for doc in alunos_pend:
                d = doc.to_dict()
                # Busca nome do usuario
                udoc = db.collection('usuarios').document(d['usuario_id']).get()
                nome_aluno = udoc.to_dict()['nome'] if udoc.exists else "Desconhecido"
                
                with st.container(border=True):
                    c1, c2, c3 = st.columns([0.6, 0.2, 0.2])
                    c1.markdown(f"**{nome_aluno}** (Faixa: {d.get('faixa_atual')})")
                    
                    if c2.button("✅ Aceitar", key=f"ok_al_{doc.id}"):
                        db.collection('alunos').document(doc.id).update({'status_vinculo': 'ativo'})
                        st.toast(f"{nome_aluno} aprovado!"); time.sleep(1); st.rerun()
                    
                    if c3.button("❌ Recusar", key=f"no_al_{doc.id}"):
                        db.collection('alunos').document(doc.id).delete()
                        st.toast("Recusado."); time.sleep(1); st.rerun()
        else:
            st.success("Nenhum aluno pendente.")
            if nivel_poder == 1: st.caption(msg_filtro)

        # --- B. PROFESSORES PENDENTES (Só Nível 2 e 3) ---
        if nivel_poder >= 2:
            st.divider()
            st.markdown("#### Professores Auxiliares Pendentes")
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
                            st.toast(f"{nome_prof} aceito na equipe!"); time.sleep(1); st.rerun()
                        
                        if c3.button("❌ Recusar", key=f"no_pr_{doc.id}"):
                            db.collection('professores').document(doc.id).delete()
                            st.toast("Recusado."); time.sleep(1); st.rerun()
            else:
                st.info("Nenhum professor aguardando aprovação.")

    # === ABA 2: MEMBROS ATIVOS ===
with tabs[1]:
        # --- 1. LISTA DE PROFESSORES ---
        st.markdown("#### 🥋 Quadro de Professores")
        profs_ativos = list(db.collection('professores').where('equipe_id', '==', meu_equipe_id).where('status_vinculo', '==', 'ativo').stream())
        
        lista_profs = []
        for p in profs_ativos:
            pdados = p.to_dict()
            u = db.collection('usuarios').document(pdados['usuario_id']).get()
            if u.exists:
                cargo = "Auxiliar"
                if pdados.get('eh_responsavel'): cargo = "Líder"
                elif pdados.get('pode_aprovar'): cargo = "Delegado"
                
                lista_profs.append({
                    "Nome": u.to_dict()['nome'],
                    "Função": cargo
                })
        
        if lista_profs:
            st.dataframe(pd.DataFrame(lista_profs), use_container_width=True, hide_index=True)
        else:
            st.info("Nenhum professor encontrado.")

        st.divider() # Linha divisória visual

        # --- 2. LISTA DE ALUNOS ---
        st.markdown("#### 🥋 Quadro de Alunos")
        alunos_ativos = list(db.collection('alunos').where('equipe_id', '==', meu_equipe_id).where('status_vinculo', '==', 'ativo').stream())
        
        lista_alunos = []
        for a in alunos_ativos:
            adados = a.to_dict()
            u = db.collection('usuarios').document(adados['usuario_id']).get()
            if u.exists:
                lista_alunos.append({
                    "Nome": u.to_dict()['nome'],
                    "Faixa": adados.get('faixa_atual', '-')
                })
                
        if lista_alunos:
            # Opção de filtro rápido para alunos (já que a lista pode ser grande)
            filtro = st.text_input("🔍 Buscar aluno:", key="filtro_aluno_ativo")
            df_alunos = pd.DataFrame(lista_alunos)
            
            if filtro:
                df_alunos = df_alunos[df_alunos['Nome'].str.upper().str.contains(filtro.upper())]
                
            st.dataframe(df_alunos, use_container_width=True, hide_index=True)
            st.caption(f"Total: {len(df_alunos)} alunos.")
        else:
            st.warning("Ainda não há alunos ativos nesta equipe.")

    # === ABA 3: DELEGAR PODER (SOMENTE LÍDER) ===
    if nivel_poder == 3:
        with tabs[2]:
            st.markdown("#### Gestão de Delegados")
            st.info("Delegados podem ajudar a aprovar novos alunos e professores auxiliares. Limite: 2 Delegados.")
            
            # Conta delegados atuais (excluindo o líder)
            delegados_existentes = [p for p in profs_ativos if p.to_dict().get('pode_aprovar') and not p.to_dict().get('eh_responsavel')]
            qtd_delegados = len(delegados_existentes)
            
            st.metric("Vagas de Delegado Ocupadas", f"{qtd_delegados} / 2")
            
            st.divider()
            st.subheader("Professores Auxiliares")
            
            # Lista apenas quem não é o líder para promover/rebaixar
            auxiliares = [p for p in profs_ativos if not p.to_dict().get('eh_responsavel')]
            
            if not auxiliares:
                st.warning("Não há professores auxiliares para gerenciar.")
            
            for doc in auxiliares:
                d = doc.to_dict()
                u = db.collection('usuarios').document(d['usuario_id']).get()
                nome = u.to_dict()['nome'] if u.exists else "..."
                is_delegado = d.get('pode_aprovar', False)
                
                c1, c2 = st.columns([3, 2])
                c1.write(f"🥋 {nome}")
                
                if is_delegado:
                    if c2.button("⬇️ Revogar Poder", key=f"rv_{doc.id}"):
                        db.collection('professores').document(doc.id).update({'pode_aprovar': False})
                        st.rerun()
                else:
                    # Só permite promover se houver vaga
                    btn_disabled = (qtd_delegados >= 2)
                    if c2.button("⬆️ Promover a Delegado", key=f"pm_{doc.id}", disabled=btn_disabled):
                        db.collection('professores').document(doc.id).update({'pode_aprovar': True})
                        st.rerun()
                st.divider()

# =========================================
# FUNÇÃO PRINCIPAL: PAINEL DO PROFESSOR (COM ABAS)
# =========================================
def painel_professor():
    st.markdown("<h1 style='color:#FFD770;'>👨‍🏫 Painel do Professor</h1>", unsafe_allow_html=True)
    
    if st.button("🏠 Voltar ao Início", key="btn_voltar_prof"):
        st.session_state.menu_selection = "Início"; st.rerun()

    tab1, tab2 = st.tabs(["👥 Gestão de Equipe", "📊 Estatísticas & Dashboard"])
    
    with tab1:
        gestao_equipes()
        
    with tab2:
        # Chamamos o dashboard aqui dentro
        dashboard.dashboard_professor()
