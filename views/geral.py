import streamlit as st
import base64
import os
from config import COR_DESTAQUE, COR_TEXTO, COR_FUNDO, DB_PATH, COR_BOTAO
from utils import formatar_e_validar_cpf, formatar_cep, buscar_cep
from database import get_db 

# Função auxiliar para renderizar cartões de forma limpa e padronizada
def render_card(titulo, descricao, texto_botao, chave_botao, pagina_destino):
    with st.container(border=True):
        st.markdown(f"<h3>{titulo}</h3>", unsafe_allow_html=True)
        st.markdown(f"<p style='text-align: center; min-height: 50px;'>{descricao}</p>", unsafe_allow_html=True)
        
        if st.button(texto_botao, key=chave_botao, use_container_width=True):
            st.session_state.menu_selection = pagina_destino
            st.rerun()

def tela_inicio():
    # Header e Logo
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
    
    # --- CARTÕES PRINCIPAIS (Acesso Geral) ---
    col1, col2, col3 = st.columns(3)
    with col1:
        render_card(
            "🤼 Modo Rola",
            "Treino livre com questões aleatórias de todos os temas.",
            "Acessar", "nav_rola", "Modo Rola"
        )
    with col2:
        render_card(
            "🥋 Exame de Faixa",
            "Realize sua avaliação teórica oficial quando liberada.",
            "Acessar", "nav_exame", "Exame de Faixa"
        )
    with col3:
        render_card(
            "🏆 Ranking",
            "Veja sua posição e a dos seus colegas no Modo Rola.",
            "Acessar", "nav_ranking", "Ranking"
        )

    # --- CARTÕES DE GESTÃO (Apenas Admin/Professor) ---
    # Recupera o tipo, converte para string e minúsculo para evitar erro de compatibilidade
    raw_tipo = st.session_state.usuario.get("tipo", "aluno")
    tipo_usuario = str(raw_tipo).lower()
    
    if tipo_usuario in ["admin", "professor"]:
        st.markdown("---")
        st.markdown(f"<h2 style='color:{COR_DESTAQUE};text-align:center; margin-top:30px;'>Painel de Gestão</h2>", unsafe_allow_html=True)
        
        c1, c2, c3 = st.columns(3)
        with c1:
            render_card(
                "🧠 Gestão de Questões",
                "Adicione, edite ou remova questões dos temas.",
                "Gerenciar", "nav_gest_questoes", "Gestão de Questões"
            )
        with c2:
            render_card(
                "🏛️ Gestão de Equipes",
                "Gerencie equipes, professores e alunos vinculados.",
                "Gerenciar", "nav_gest_equipes", "Gestão de Equipes"
            )
        with c3:
            render_card(
                "📜 Gestão de Exame",
                "Monte as provas oficiais selecionando questões.",
                "Gerenciar", "nav_gest_exame", "Gestão de Exame"
            )

def tela_meu_perfil(usuario_logado):
    st.markdown("<h1 style='color:#FFD700;'>👤 Meu Perfil</h1>", unsafe_allow_html=True)
    
    # Conexão Firestore
    db = get_db()
    user_ref = db.collection('usuarios').document(usuario_logado['id'])
    user_data = user_ref.get().to_dict()
    
    if not user_data:
        st.error("Erro ao carregar dados.")
        return

    with st.expander("📝 Informações Pessoais e Endereço", expanded=True):
        with st.form(key="form_edit_perfil"):
            col1, col2 = st.columns(2)
            novo_nome = col1.text_input("Nome:", value=user_data.get('nome', ''))
            novo_email = col2.text_input("Email:", value=user_data.get('email', ''), disabled=True)
            
            # Inicializa CEP no estado se não existir
            if 'perf_cep' not in st.session_state: 
                st.session_state.perf_cep = user_data.get('cep', '')
                
            c_cep, c_btn = st.columns([3, 1])
            novo_cep = c_cep.text_input("CEP:", key="in_perf_cep", value=st.session_state.perf_cep)
            
            # Botão de busca de CEP dentro do form (usando form_submit_button secundário)
            if c_btn.form_submit_button("Buscar"):
                end = buscar_cep(novo_cep)
                if end:
                    st.session_state.perf_end = end
                    st.rerun()
            
            # Usa dados do cache de busca ou do banco
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
            
            if st.form_submit_button("💾 Salvar Alterações", type="primary"):
                try:
                    user_ref.update({
                        "nome": novo_nome.upper(),
                        "cep": novo_cep,
                        "logradouro": logr.upper(),
                        "numero": num,
                        "complemento": comp.upper(),
                        "bairro": bairro.upper(),
                        "cidade": cid.upper(),
                        "uf": uf.upper()
                    })
                    st.success("Dados atualizados!")
                    # Atualiza o nome na sessão para refletir na sidebar imediatamente
                    st.session_state.usuario['nome'] = novo_nome.upper()
                    st.rerun()
                except Exception as e:
                    st.error(f"Erro ao salvar: {e}")
