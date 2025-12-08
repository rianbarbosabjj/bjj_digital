import streamlit as st
import pandas as pd
from datetime import datetime, date
from database import get_db, OPCOES_SEXO
from firebase_admin import firestore

def card(titulo, icone, desc, texto_botao, key_btn, acao=None):
    with st.container(border=True):
        st.markdown(f"<h3 style='text-align:center;'>{icone} {titulo}</h3>", unsafe_allow_html=True)
        st.markdown(f"<p style='text-align:center; min-height:40px;'>{desc}</p>", unsafe_allow_html=True)
        if st.button(texto_botao, key=key_btn, use_container_width=True):
            if acao: acao()

def tela_inicio():
    if not st.session_state.get('usuario'): return
    
    u = st.session_state.usuario
    # Tenta pegar 'tipo_usuario' ou 'tipo' para garantir compatibilidade
    tipo = str(u.get("tipo_usuario", u.get("tipo", "aluno"))).lower()
    nome = u.get("nome", "Visitante").split()[0]

    st.markdown(f"<h2 style='text-align:center; color:#FFD700;'>PAINEL BJJ DIGITAL</h2>", unsafe_allow_html=True)
    st.markdown(f"<p style='text-align:center;'>Bem-vindo(a), {nome}!</p>", unsafe_allow_html=True)
    st.markdown("---")

    # Funções de navegação internas
    def ir_rola(): st.session_state.menu_selection = "Modo Rola"; st.rerun()
    def ir_exame(): st.session_state.menu_selection = "Exame de Faixa"; st.rerun()
    def ir_ranking(): st.session_state.menu_selection = "Ranking"; st.rerun()
    
    # Funções Admin/Prof
    def ir_questoes(): st.session_state.menu_selection = "Gestão de Questões"; st.rerun()
    def ir_gestao_equipes_tab((): st.session_state.menu_selection = "Gestão de Equipe"; st.rerun()
    def ir_montar_exame(): st.session_state.menu_selection = "Gestão de Exame"; st.rerun()

    # --- CARDS ALUNO (TODOS VEEM) ---
    c1, c2, c3 = st.columns(3)
    with c1: card("MODO ROLA", "🤼", "Treino livre.", "Acessar", "btn_rola", ir_rola)
    with c2: card("EXAME DE FAIXA", "🥋", "Avaliação teórica.", "Acessar", "btn_exame", ir_exame)
    with c3: card("RANKING", "🏆", "Posição no ranking.", "Acessar", "btn_rank", ir_ranking)

    # --- CARDS GESTÃO (SÓ PROF/ADMIN) ---
    if tipo in ["admin", "professor"]:
        st.markdown("<h3 style='text-align:center; margin-top:30px; color:#FFD700;'>GESTÃO</h3>", unsafe_allow_html=True)
        g1, g2, g3 = st.columns(3)
        with g1: card("QUESTÕES", "🧠", "Editar banco.", "Gerenciar", "btn_quest", ir_questoes)
        with g2: card("EQUIPES", "🏛️", "Gerenciar equipes.", "Gerenciar", "btn_team", ir_equipes)
        with g3: card("EXAMES", "📜", "Montar provas.", "Gerenciar", "btn_montar", ir_montar_exame)

def tela_meu_perfil(usuario_sessao):
    st.title("👤 Meu Perfil")
    db = get_db()
    
    # 1. Carrega dados frescos do banco
    uid = usuario_sessao['id']
    doc_ref = db.collection('usuarios').document(uid)
    doc = doc_ref.get()
    
    if not doc.exists:
        st.error("Erro ao carregar perfil."); return
    
    u_db = doc.to_dict()
    tipo_user = u_db.get('tipo_usuario', 'aluno')

    # 2. Carrega Dados de Equipes e Professores
    try:
        # Carrega todas as equipes
        equipes_ref = list(db.collection('equipes').stream())
        mapa_equipes = {d.id: d.to_dict() for d in equipes_ref} # ID -> Dados da Equipe
        lista_nomes_equipes = sorted([d['nome'] for d in mapa_equipes.values()])
        mapa_nomes_equipes_inv = {d['nome']: eid for eid, d in mapa_equipes.items()}

        # Carrega nomes de todos os usuários que são professores
        profs_users_ref = list(db.collection('usuarios').where('tipo_usuario', '==', 'professor').stream())
        mapa_nomes_profs = {p.id: p.to_dict().get('nome', 'Sem Nome') for p in profs_users_ref}
        mapa_nomes_profs_inv = {v: k for k, v in mapa_nomes_profs.items()}

        # Carrega vínculos de professores (para saber quem é de qual equipe)
        vincs_p = list(db.collection('professores').where('status_vinculo', '==', 'ativo').stream())
        
        # Estrutura: { equipe_id: [ {'nome': 'Fulano', 'uid': '123', 'tipo': 'Responsável'} ] }
        profs_por_equipe = {}
        
        for v in vincs_p:
            d = v.to_dict()
            eid = d.get('equipe_id')
            pid = d.get('usuario_id')
            
            if eid and pid in mapa_nomes_profs:
                if eid not in profs_por_equipe: profs_por_equipe[eid] = []
                
                # Define o papel
                papel = "Auxiliar"
                if d.get('eh_responsavel'): papel = "Responsável"
                elif d.get('pode_aprovar'): papel = "Delegado"
                
                label_prof = f"{mapa_nomes_profs[pid]} ({papel})"
                profs_por_equipe[eid].append({'label': label_prof, 'uid': pid, 'nome_puro': mapa_nomes_profs[pid]})

    except Exception as e:
        st.error(f"Erro ao carregar listas auxiliares: {e}")
        return

    # 3. Identifica Vínculo Atual do Usuário
    equipe_atual_nome = "Sem Equipe"
    prof_atual_nome = "Sem Professor"
    doc_vinculo_id = None
    eid_atual = None
    
    col_vinculo = 'alunos' if tipo_user == 'aluno' else 'professores'
    q_vinc = list(db.collection(col_vinculo).where('usuario_id', '==', uid).limit(1).stream())
    
    if q_vinc:
        d_vinc = q_vinc[0].to_dict()
        doc_vinculo_id = q_vinc[0].id
        
        eid_atual = d_vinc.get('equipe_id')
        if eid_atual in mapa_equipes:
            equipe_atual_nome = mapa_equipes[eid_atual].get('nome', 'Sem Nome')
        
        if tipo_user == 'aluno':
            pid_atual = d_vinc.get('professor_id')
            if pid_atual in mapa_nomes_profs:
                prof_atual_nome = mapa_nomes_profs[pid_atual]

    # --- SESSÃO 1: DADOS PESSOAIS (DENTRO DO FORM) ---
    with st.form("form_perfil"):
        st.markdown("##### 📝 Dados Pessoais")
        c1, c2 = st.columns(2)
        novo_nome = c1.text_input("Nome Completo", value=u_db.get('nome',''))
        novo_email = c2.text_input("E-mail", value=u_db.get('email',''))
        
        c3, c4 = st.columns(2)
        c3.text_input("CPF (Não editável)", value=u_db.get('cpf',''), disabled=True)
        val_nasc = None
        if u_db.get('data_nascimento'):
            try: val_nasc = datetime.fromisoformat(u_db.get('data_nascimento')).date()
            except: pass
        c4.date_input("Data de Nascimento (Não editável)", value=val_nasc, disabled=True)

        c5, c6 = st.columns(2)
        idx_sexo = 0
        if u_db.get('sexo') in OPCOES_SEXO: idx_sexo = OPCOES_SEXO.index(u_db.get('sexo'))
        novo_sexo = c5.selectbox("Sexo", OPCOES_SEXO, index=idx_sexo)
        
        st.markdown("##### 📍 Endereço")
        e1, e2 = st.columns([1, 3])
        novo_cep = e1.text_input("CEP", value=u_db.get('cep',''))
        novo_logr = e2.text_input("Logradouro", value=u_db.get('logradouro',''))
        e3, e4, e5 = st.columns([1, 2, 2])
        novo_num = e3.text_input("Número", value=u_db.get('numero',''))
        novo_comp = e4.text_input("Complemento", value=u_db.get('complemento',''))
        novo_bairro = e5.text_input("Bairro", value=u_db.get('bairro',''))
        e6, e7 = st.columns(2)
        novo_cid = e6.text_input("Cidade", value=u_db.get('cidade',''))
        novo_uf = e7.text_input("UF", value=u_db.get('uf',''))

        submit_dados = st.form_submit_button("💾 Salvar Dados Pessoais", type="primary")

    if submit_dados:
        try:
            db.collection('usuarios').document(uid).update({
                "nome": novo_nome.upper(),
                "email": novo_email.lower().strip(),
                "sexo": novo_sexo,
                "cep": novo_cep, "logradouro": novo_logr.upper(),
                "numero": novo_num, "complemento": novo_comp.upper(),
                "bairro": novo_bairro.upper(), "cidade": novo_cid.upper(), "uf": novo_uf.upper()
            })
            st.session_state.usuario['nome'] = novo_nome # Atualiza sessão visual
            st.success("✅ Dados atualizados!")
            time.sleep(1)
            st.rerun()
        except Exception as e:
            st.error(f"Erro ao salvar dados: {e}")

    # --- SESSÃO 2: VÍNCULOS E ACADEMIA (FORA DO FORM PARA SER DINÂMICO) ---
    st.markdown("---")
    st.markdown("##### 🥋 Academia e Vínculos")
    
    col_v1, col_v2 = st.columns(2)
    
    # 1. Seleção de Equipe (Dinâmico)
    idx_eq = 0
    if equipe_atual_nome in lista_nomes_equipes:
        idx_eq = lista_nomes_equipes.index(equipe_atual_nome)
    
    # Adiciona opção "Sem Equipe" se não tiver
    opcoes_equipe = ["Sem Equipe"] + lista_nomes_equipes
    idx_eq_final = idx_eq + 1 if equipe_atual_nome in lista_nomes_equipes else 0
    
    nova_equipe = col_v1.selectbox("Minha Equipe:", opcoes_equipe, index=idx_eq_final, key="sel_eq_perfil")
    
    # 2. Lógica de Professor (Depende da Equipe Selecionada)
    id_nova_equipe = mapa_nomes_equipes_inv.get(nova_equipe)
    
    novo_prof_uid = None
    
    if tipo_user == 'aluno':
        lista_profs_display = ["Sem Professor"]
        mapa_profs_display = {} # Label -> UID
        
        # Se tem equipe selecionada, carrega os profs dela
        if id_nova_equipe and id_nova_equipe in profs_por_equipe:
            for p in profs_por_equipe[id_nova_equipe]:
                lista_profs_display.append(p['label'])
                mapa_profs_display[p['label']] = p['uid']
        
        # Tenta achar o index do professor atual na nova lista
        idx_prof = 0
        # Precisamos ver se o prof atual está na lista formatada (com (Responsável) etc)
        prof_atual_label_match = None
        if prof_atual_nome != "Sem Professor":
            for label in lista_profs_display:
                if prof_atual_nome in label: # Match parcial pelo nome
                    prof_atual_label_match = label
                    break
        
        if prof_atual_label_match:
            idx_prof = lista_profs_display.index(prof_atual_label_match)
            
        prof_selecionado_label = col_v2.selectbox("Professor(a):", lista_profs_display, index=idx_prof, key="sel_prof_perfil")
        novo_prof_uid = mapa_profs_display.get(prof_selecionado_label)

    elif tipo_user == 'professor':
        # Professor só vê quem é o responsável da equipe selecionada
        if id_nova_equipe:
            resp_id = mapa_equipes[id_nova_equipe].get('professor_responsavel_id')
            nome_resp = mapa_nomes_profs.get(resp_id, "Não definido")
            col_v2.info(f"Professor Responsável: {nome_resp}")
        else:
            col_v2.info("Selecione uma equipe.")

    # Botão para salvar Vínculo separado
    if st.button("💾 Atualizar Vínculo", type="secondary"):
        try:
            # Verifica mudanças
            mudou = False
            dados_update = {}
            
            # Se mudou equipe, status volta pra pendente
            if id_nova_equipe != eid_atual:
                mudou = True
                dados_update['equipe_id'] = id_nova_equipe
                dados_update['status_vinculo'] = 'pendente' if id_nova_equipe else 'inativo'
            
            if tipo_user == 'aluno':
                # Se mudou professor (mesmo na mesma equipe)
                # Verifica ID, pois o nome pode ter mudado visualmente
                pid_atual_db = d_vinc.get('professor_id') if q_vinc else None
                if novo_prof_uid != pid_atual_db:
                    mudou = True
                    dados_update['professor_id'] = novo_prof_uid
            
            if mudou:
                if doc_vinculo_id:
                    db.collection(col_vinculo).document(doc_vinculo_id).update(dados_update)
                else:
                    # Cria novo
                    dados_update['usuario_id'] = uid
                    if tipo_user == 'aluno': dados_update['faixa_atual'] = u_db.get('faixa_atual','Branca')
                    db.collection(col_vinculo).add(dados_update)
                
                st.success("✅ Vínculo atualizado! Aguarde aprovação.")
                time.sleep(1.5)
                st.rerun()
            else:
                st.info("Nenhuma alteração no vínculo.")
                
        except Exception as e:
            st.error(f"Erro ao atualizar vínculo: {e}")
