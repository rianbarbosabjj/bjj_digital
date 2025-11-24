import streamlit as st
import base64
import os
from config import COR_DESTAQUE, COR_TEXTO, COR_FUNDO, DB_PATH, COR_BOTAO
from utils import formatar_e_validar_cpf, formatar_cep, buscar_cep
from database import get_db 

# =========================================
# FUNÇÃO AUXILIAR DE CARTÕES
# =========================================
def render_card(titulo, descricao, texto_botao, chave_botao, pagina_destino):
    """Renderiza um cartão de navegação padronizado."""
    with st.container(border=True):
        st.markdown(f"<h3>{titulo}</h3>", unsafe_allow_html=True)
        st.markdown(f"<p style='text-align: center; min-height: 60px;'>{descricao}</p>", unsafe_allow_html=True)
        
        if st.button(texto_botao, key=chave_botao, use_container_width=True):
            st.session_state.menu_selection = pagina_destino
            st.rerun()

# =========================================
# TELA INICIAL (DASHBOARD)
# =========================================
def tela_inicio():
    logo_path = "assets/logo.png"
    if os.path.exists(logo_path):
        with open(logo_path, "rb") as f:
            logo_base64 = base64.b64encode(f.read()).decode()
        logo_html = f"<img src='data:image/png;base64,{logo_base64}' style='width:180px;max-width:200px;height:auto;margin-bottom:10px;'/>"
    else:
        logo_html = ""

    st.markdown(f"""
        <div style='display:flex;flex-direction:column;align-items:center;justify-content:center;margin-bottom:30px;'>
            {logo_html}
            <h2 style='color:{COR_DESTAQUE};text-align:center;'>Painel BJJ Digital</h2>
            <p style='color:{COR_TEXTO};text-align:center;font-size:1.1em;'>Bem-vindo(a), {st.session_state.usuario['nome'].title()}!</p>
        </div>
    """, unsafe_allow_html=True)
    st.markdown("---")
    
    col1, col2, col3 = st.columns(3)
    with col1:
        render_card("🤼 Modo Rola", "Treino livre com questões aleatórias.", "Acessar", "nav_rola", "Modo Rola")
    with col2:
        render_card("🥋 Exame de Faixa", "Realize sua avaliação teórica oficial.", "Acessar", "nav_exame", "Exame de Faixa")
    with col3:
        render_card("🏆 Ranking", "Veja sua posição no ranking.", "Acessar", "nav_ranking", "Ranking")

    raw_tipo = st.session_state.usuario.get("tipo", "aluno")
    tipo_usuario = str(raw_tipo).strip().lower()
    
    if tipo_usuario in ["admin", "professor"]:
        st.markdown("---")
        st.markdown(f"<h2 style='color:{COR_DESTAQUE};text-align:center; margin-top:30px;'>Painel de Gestão</h2>", unsafe_allow_html=True)
        
        c1, c2, c3 = st.columns(3)
        with c1: render_card("🧠 Gestão de Questões", "Edite questões dos temas.", "Gerenciar", "nav_gest_questoes", "Gestão de Questões")
        with c2: render_card("🏛️ Gestão de Equipes", "Gerencie equipes e alunos.", "Gerenciar", "nav_gest_equipes", "Gestão de Equipes")
        with c3: render_card("📜 Gestão de Exame", "Monte as provas oficiais.", "Gerenciar", "nav_gest_exame", "Gestão de Exame")

# =========================================
# TELA MEU PERFIL
# =========================================
def tela_meu_perfil(usuario_logado):
    st.markdown("<h1 style='color:#FFD700;'>👤 Meu Perfil</h1>", unsafe_allow_html=True)
    
    db = get_db()
    user_ref = db.collection('usuarios').document(usuario_logado['id'])
    user_data = user_ref.get().to_dict()
    
    if not user_data:
        st.error("Erro ao carregar dados.")
        return

    # --- ABA 1: DADOS PESSOAIS (Comum a todos) ---
    with st.expander("📝 Informações Pessoais e Endereço", expanded=True):
        with st.form(key="form_edit_perfil"):
            col1, col2 = st.columns(2)
            novo_nome = col1.text_input("Nome:", value=user_data.get('nome', ''))
            novo_email = col2.text_input("Email:", value=user_data.get('email', ''), disabled=True)
            
            if 'perf_cep' not in st.session_state: 
                st.session_state.perf_cep = user_data.get('cep', '')
                
            c_cep, c_btn = st.columns([3, 1])
            novo_cep = c_cep.text_input("CEP:", key="in_perf_cep", value=st.session_state.perf_cep)
            
            if c_btn.form_submit_button("Buscar Endereço"):
                end = buscar_cep(novo_cep)
                if end:
                    st.session_state.perf_end = end
                    st.rerun()
            
            end_base = st.session_state.get('perf_end', user_data)
            
            c1, c2 = st.columns(2)
            logr = c1.text_input("Logradouro:", value=end_base.get('logradouro',''))
            bairro = c2.text_input("Bairro:", value=end_base.get('bairro',''))
            
            c3, c4 = st.columns(2)
            cid = c3.text_input("Cidade:", value=end_base.get('cidade',''))
            uf = c4.text_input("UF:", value=end_base.get('uf',''))
            
            c5, c6 = st.columns(2)
            num = c5.text_input("Número:", value=user_data.get('numero',''))
            comp = c6.text_input("Complemento:", value=user_data.get('complemento',''))
            
            if st.form_submit_button("💾 Salvar Dados Pessoais", type="primary"):
                try:
                    user_ref.update({
                        "nome": novo_nome.upper(), "cep": novo_cep,
                        "logradouro": logr.upper(), "numero": num,
                        "complemento": comp.upper(), "bairro": bairro.upper(),
                        "cidade": cid.upper(), "uf": uf.upper()
                    })
                    st.success("Dados atualizados!")
                    st.session_state.usuario['nome'] = novo_nome.upper()
                    st.rerun()
                except Exception as e:
                    st.error(f"Erro ao salvar: {e}")

    # --- ABA 2: DADOS ESPECÍFICOS (Aluno ou Professor) ---
    tipo_usuario = str(user_data.get("tipo_usuario", "")).lower()
    
    # SE FOR ALUNO
    if tipo_usuario == 'aluno':
        alunos_query = db.collection('alunos').where('usuario_id', '==', usuario_logado['id']).stream()
        lista_alunos = list(alunos_query)
        
        if lista_alunos:
            aluno_doc = lista_alunos[0]
            aluno_data = aluno_doc.to_dict()
            aluno_doc_id = aluno_doc.id
            
            # Carrega Equipes e Professores
            eq_ref = db.collection('equipes').stream()
            lista_eq = ["Nenhuma (Vínculo Pendente)"]
            mapa_eq = {}
            nome_eq_atual = "Nenhuma (Vínculo Pendente)"
            for d in eq_ref:
                nm = d.to_dict().get('nome', '?')
                lista_eq.append(nm)
                mapa_eq[nm] = d.id
                if d.id == aluno_data.get('equipe_id'): nome_eq_atual = nm
            
            prof_ref = db.collection('usuarios').where('tipo_usuario', '==', 'professor').stream()
            lista_pf = ["Nenhum (Vínculo Pendente)"]
            mapa_pf = {}
            nome_pf_atual = "Nenhum (Vínculo Pendente)"
            for d in prof_ref:
                nm = d.to_dict().get('nome', '?')
                lista_pf.append(nm)
                mapa_pf[nm] = d.id
                if d.id == aluno_data.get('professor_id'): nome_pf_atual = nm

            try: idx_eq = lista_eq.index(nome_eq_atual)
            except: idx_eq = 0
            try: idx_pf = lista_pf.index(nome_pf_atual)
            except: idx_pf = 0
            
            faixas = ["Branca", "Cinza", "Amarela", "Laranja", "Verde", "Azul", "Roxa", "Marrom", "Preta"]
            try: idx_fx = faixas.index(aluno_data.get('faixa_atual', 'Branca'))
            except: idx_fx = 0

            with st.expander("🥋 Dados de Treino (Faixa, Equipe e Professor)", expanded=False):
                with st.form(key="form_bjj_data"):
                    st.info("Alterar equipe ou professor redefinirá seu status para 'Pendente'.")
                    
                    c_fx, c_eq = st.columns(2)
                    nova_faixa = c_fx.selectbox("Faixa Atual:", faixas, index=idx_fx)
                    nova_equipe = c_eq.selectbox("Equipe:", lista_eq, index=idx_eq)
                    novo_prof = st.selectbox("Professor:", lista_pf, index=idx_pf)
                    
                    if st.form_submit_button("💾 Atualizar Dados de Treino"):
                        eq_id_save = mapa_eq.get(nova_equipe)
                        prof_id_save = mapa_pf.get(novo_prof)
                        
                        novo_status = aluno_data.get('status_vinculo')
                        if eq_id_save != aluno_data.get('equipe_id') or prof_id_save != aluno_data.get('professor_id'):
                            novo_status = 'pendente'
                        
                        db.collection('alunos').document(aluno_doc_id).update({
                            "faixa_atual": nova_faixa, "equipe_id": eq_id_save,
                            "professor_id": prof_id_save, "status_vinculo": novo_status
                        })
                        st.success("Dados de treino atualizados!")
                        st.rerun()

    # SE FOR PROFESSOR (OU ADMIN)
    elif tipo_usuario in ['professor', 'admin']:
        # Busca vínculo de professor
        prof_query = db.collection('professores').where('usuario_id', '==', usuario_logado['id']).stream()
        lista_profs = list(prof_query)
        
        if lista_profs:
            # Edita o primeiro vínculo encontrado (para simplificar)
            prof_doc = lista_profs[0]
            prof_data = prof_doc.to_dict()
            prof_doc_id = prof_doc.id
            
            # Carrega Equipes
            eq_ref = db.collection('equipes').stream()
            lista_eq = ["Nenhuma (Vínculo Pendente)"]
            mapa_eq = {}
            nome_eq_atual = "Nenhuma (Vínculo Pendente)"
            
            for d in eq_ref:
                nm = d.to_dict().get('nome', '?')
                lista_eq.append(nm)
                mapa_eq[nm] = d.id
                if d.id == prof_data.get('equipe_id'): nome_eq_atual = nm
            
            try: idx_eq = lista_eq.index(nome_eq_atual)
            except: idx_eq = 0
            
            with st.expander("🥋 Dados de Vínculo (Equipe)", expanded=False):
                with st.form(key="form_prof_data"):
                    st.info("⚠️ Atenção: Alterar sua equipe redefinirá seu status para 'Pendente' e removerá privilégios até aprovação.")
                    
                    nova_equipe = st.selectbox("Sua Equipe:", lista_eq, index=idx_eq)
                    
                    if st.form_submit_button("💾 Atualizar Equipe"):
                        eq_id_save = mapa_eq.get(nova_equipe)
                        
                        if eq_id_save != prof_data.get('equipe_id'):
                            db.collection('professores').document(prof_doc_id).update({
                                "equipe_id": eq_id_save,
                                "status_vinculo": 'pendente',
                                "eh_responsavel": False, # Reseta privilégios por segurança
                                "pode_aprovar": False
                            })
                            st.success("Solicitação de mudança enviada! Aguarde aprovação.")
                            st.rerun()
                        else:
                            st.info("Nenhuma alteração realizada.")
