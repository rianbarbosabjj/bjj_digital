import streamlit as st
import base64
import os
import sqlite3
import bcrypt
from config import COR_DESTAQUE, COR_TEXTO, COR_FUNDO, DB_PATH
from utils import formatar_e_validar_cpf, formatar_cep, buscar_cep

# =========================================
# 🏠 TELA INÍCIO (DO SEU PROJETO ORIGINAL)
# =========================================
def tela_inicio():
    
    # 1. 👇 FUNÇÃO DE CALLBACK PARA NAVEGAÇÃO
    def navigate_to(page_name):
        st.session_state.menu_selection = page_name

    # Logo centralizado
    logo_path = "assets/logo.png"
    if os.path.exists(logo_path):
        with open(logo_path, "rb") as f:
            logo_base64 = base64.b64encode(f.read()).decode()
        logo_html = f"<img src='data:image/png;base64,{logo_base64}' style='width:180px;max-width:200px;height:auto;margin-bottom:10px;'/>"
    else:
        logo_html = "<p style='color:red;'>Logo não encontrada.</p>"

    st.markdown(f"""
        <div style='display:flex;flex-direction:column;align-items:center;justify-content:center;margin-bottom:30px;'>
            {logo_html}
            <h2 style='color:{COR_DESTAQUE};text-align:center;'>Painel BJJ Digital</h2>
            <p style='color:{COR_TEXTO};text-align:center;font-size:1.1em;'>Bem-vindo(a), {st.session_state.usuario['nome'].title()}!</p>
        </div>
    """, unsafe_allow_html=True)

    st.markdown("---")

    # --- Cartões Principais (Para todos) ---
    col1, col2, col3 = st.columns(3)

    with col1:
        with st.container(border=True):
            st.markdown("<h3>🤼 Modo Rola</h3>", unsafe_allow_html=True) 
            st.markdown("""<p style='text-align: center; min-height: 50px;'>Treino livre com questões aleatórias de todos os temas.</p> """, unsafe_allow_html=True)
            # 2. 👇 BOTÃO DE NAVEGAÇÃO
            st.button("Acessar", key="nav_rola", on_click=navigate_to, args=("Modo Rola",), use_container_width=True)

    with col2:
        with st.container(border=True):
            st.markdown("<h3>🥋 Exame de Faixa</h3>", unsafe_allow_html=True)
            st.markdown("""<p style='text-align: center; min-height: 50px;'>Realize sua avaliação teórica oficial quando liberada.</p> """, unsafe_allow_html=True)
            # 2. 👇 BOTÃO DE NAVEGAÇÃO
            st.button("Acessar", key="nav_exame", on_click=navigate_to, args=("Exame de Faixa",), use_container_width=True)
            
    with col3:
        with st.container(border=True):
            st.markdown("<h3>🏆 Ranking</h3>", unsafe_allow_html=True)
            st.markdown("""<p style='text-align: center; min-height: 50px;'>Veja sua posição e a dos seus colegas no Modo Rola.</p> """, unsafe_allow_html=True)
            # 2. 👇 BOTÃO DE NAVEGAÇÃO
            st.button("Acessar", key="nav_ranking", on_click=navigate_to, args=("Ranking",), use_container_width=True)

    # --- Cartões de Gestão (Admin/Professor) ---
    if st.session_state.usuario["tipo"] in ["admin", "professor"]:
        st.markdown("---")
        st.markdown(f"<h2 style='color:{COR_DESTAQUE};text-align:center; margin-top:30px;'>Painel de Gestão</h2>", unsafe_allow_html=True)
        
        c1, c2, c3 = st.columns(3)
        with c1:
            with st.container(border=True):
                st.markdown("<h3>🧠 Gestão de Questões</h3>", unsafe_allow_html=True)
                st.markdown("""<p style='text-align: center; min-height: 50px;'>Adicione, edite ou remova questões dos temas.</p> """, unsafe_allow_html=True)
                # 2. 👇 BOTÃO DE NAVEGAÇÃO
                st.button("Gerenciar", key="nav_gest_questoes", on_click=navigate_to, args=("Gestão de Questões",), use_container_width=True)
        with c2:
            with st.container(border=True):
                st.markdown("<h3>🏛️ Gestão de Equipes</h3>", unsafe_allow_html=True)
                st.markdown("""<p style='text-align: center; min-height: 50px;'>Gerencie equipes, professores e alunos vinculados.</p> """, unsafe_allow_html=True)
                # 2. 👇 BOTÃO DE NAVEGAÇÃO
                st.button("Gerenciar", key="nav_gest_equipes", on_click=navigate_to, args=("Gestão de Equipes",), use_container_width=True)
        with c3:
            with st.container(border=True):
                st.markdown("<h3>📜 Gestão de Exame</h3>", unsafe_allow_html=True)
                st.markdown("""<p style='text-align: center; min-height: 50px;'>Monte as provas oficiais selecionando questões.</p> """, unsafe_allow_html=True)
                # 2. 👇 BOTÃO DE NAVEGAÇÃO
                st.button("Gerenciar", key="nav_gest_exame", on_click=navigate_to, args=("Gestão de Exame",), use_container_width=True)
                
def tela_meu_perfil(usuario_logado):
    st.markdown("<h1 style='color:#FFD700;'>👤 Meu Perfil</h1>", unsafe_allow_html=True)
    
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM usuarios WHERE id=?", (usuario_logado["id"],))
    user_data = cursor.fetchone()
    
    if not user_data:
        st.error("Erro ao carregar dados.")
        return

    with st.expander("📝 Informações Pessoais e Endereço", expanded=True):
        with st.form(key="form_edit_perfil"):
            col1, col2 = st.columns(2)
            novo_nome = col1.text_input("Nome:", value=user_data['nome'])
            novo_email = col2.text_input("Email:", value=user_data['email'])
            
            # ... (Copie aqui a lógica de CPF, CEP e Endereço do seu app.py original - função tela_meu_perfil) ...
            # Lembre-se de usar as funções importadas de `utils`
            
            if st.form_submit_button("💾 Salvar Alterações"):
                # ... (Lógica de UPDATE no banco) ...
                st.success("Dados salvos!") # Placeholder
                conn.commit()
                st.rerun()
    conn.close()
