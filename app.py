import streamlit as st
import os
import sys
import bcrypt 
from database import get_db

def get_logo_path():
    if os.path.exists("assets/logo.jpg"): return "assets/logo.jpg"
    if os.path.exists("logo.jpg"): return "logo.jpg"
    if os.path.exists("assets/logo.png"): return "assets/logo.png"
    if os.path.exists("logo.png"): return "logo.png"
    return None

logo_file = get_logo_path()

st.set_page_config(
    page_title="BJJ Digital", 
    page_icon=logo_file, 
    layout="wide",
    initial_sidebar_state="expanded" 
)

try:
    from config import COR_FUNDO, COR_TEXTO, COR_DESTAQUE, COR_BOTAO, COR_HOVER
except ImportError:
    COR_FUNDO = "#0e2d26"
    COR_TEXTO = "#FFFFFF"
    COR_DESTAQUE = "#FFD770"
    COR_BOTAO = "#078B6C"
    COR_HOVER = "#FFD770"

st.markdown(f"""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Poppins:wght@300;400;600;700&display=swap');

    html, body, [class*="css"], .stMarkdown, p, label, .stCaption, span {{
        font-family: 'Poppins', sans-serif;
        color: {COR_TEXTO} !important;
    }}

    .stApp {{
        background-color: {COR_FUNDO} !important;
        background-image: radial-gradient(circle at 50% 0%, #164036 0%, #0e2d26 70%) !important;
    }}
    
    hr {{
        margin: 2em 0 !important;
        border: 0 !important;
        height: 1px !important;
        background-image: linear-gradient(to right, rgba(255, 255, 255, 0), rgba(255, 255, 255, 0.5), rgba(255, 255, 255, 0)) !important;
    }}

    /* --- ESTILO DO RADIO BUTTON (Dourado) --- */
    div.stRadio > div[role="radiogroup"] > label > div:first-child {{
        border-color: {COR_DESTAQUE} !important;
        background-color: transparent !important;
    }}
    div.stRadio > div[role="radiogroup"] > label > div:first-child > div {{
        background-color: {COR_DESTAQUE} !important;
    }}
    /* --------------------------------------- */

    h1, h2, h3, h4, h5, h6 {{ 
        color: {COR_DESTAQUE} !important; 
        text-align: center !important; 
        font-weight: 700 !important; 
        text-transform: uppercase;
        letter-spacing: 1px;
    }}

    section[data-testid="stSidebar"] {{
        background-color: #091f1a !important; 
        border-right: 1px solid rgba(255, 215, 112, 0.15);
        box-shadow: 5px 0 15px rgba(0,0,0,0.3);
    }}
    section[data-testid="stSidebar"] svg {{
        fill: {COR_DESTAQUE} !important;
        color: {COR_DESTAQUE} !important;
    }}

    /* --- HEADER ESCONDIDO COM BOTÃO DA SIDEBAR CUSTOMIZADO --- */
    /* Esconde completamente o header padrão do Streamlit */
    header[data-testid="stHeader"] {{
        display: none !important;
        visibility: hidden !important;
        height: 0 !important;
        padding: 0 !important;
        margin: 0 !important;
    }}
    
    /* Remove o botão original da sidebar que está dentro do header */
    [data-testid="collapsedControl"] {{
        display: none !important;
    }}
    
    /* BOTÃO HAMBURGUER CUSTOMIZADO */
    .custom-sidebar-toggle {{
        position: fixed !important;
        top: 15px !important;
        left: 15px !important;
        z-index: 999999 !important;
        background-color: rgba(9, 31, 26, 0.9) !important;
        border-radius: 8px !important;
        border: 1px solid rgba(255, 215, 112, 0.3) !important;
        padding: 8px 10px !important;
        box-shadow: 0 4px 15px rgba(0, 0, 0, 0.5) !important;
        backdrop-filter: blur(5px) !important;
        transition: all 0.3s ease !important;
        cursor: pointer !important;
        display: flex !important;
        align-items: center !important;
        justify-content: center !important;
    }}
    
    .custom-sidebar-toggle:hover {{
        background-color: rgba(255, 215, 112, 0.15) !important;
        border-color: {COR_HOVER} !important;
        transform: scale(1.05) !important;
        box-shadow: 0 6px 20px rgba(255, 215, 112, 0.3) !important;
    }}
    
    /* Ícone hamburguer personalizado (três traços) */
    .custom-sidebar-toggle::before {{
        content: "☰";
        color: {COR_DESTAQUE} !important;
        font-size: 24px !important;
        font-weight: bold !important;
        line-height: 1 !important;
        transition: all 0.3s ease !important;
    }}
    
    .custom-sidebar-toggle:hover::before {{
        color: {COR_HOVER} !important;
        transform: scale(1.1) !important;
    }}
    
    /* Ícone quando a sidebar está aberta (X) */
    .custom-sidebar-toggle.open::before {{
        content: "✕";
        font-size: 20px !important;
    }}

    /* Ajusta o padding do conteúdo para compensar a falta do header */
    .block-container {{
        padding-top: 1.5rem !important;
    }}
    
    /* Responsividade para tablets e celulares */
    @media (max-width: 768px) {{
        .custom-sidebar-toggle {{
            top: 10px !important;
            left: 10px !important;
            padding: 10px 12px !important;
            min-width: 48px !important;
            min-height: 48px !important;
        }}
        
        .custom-sidebar-toggle::before {{
            font-size: 26px !important;
        }}
        
        .custom-sidebar-toggle.open::before {{
            font-size: 22px !important;
        }}
        
        .block-container {{
            padding-top: 2.5rem !important;
        }}
    }}
    
    @media (max-width: 480px) {{
        .custom-sidebar-toggle {{
            top: 8px !important;
            left: 8px !important;
            padding: 8px 10px !important;
            min-width: 44px !important;
            min-height: 44px !important;
        }}
        
        .custom-sidebar-toggle::before {{
            font-size: 22px !important;
        }}
        
        .custom-sidebar-toggle.open::before {{
            font-size: 18px !important;
        }}
    }}

    div[data-testid="stVerticalBlock"] > div[data-testid="stContainer"], 
    div[data-testid="stForm"] {{
        background-color: rgba(0, 0, 0, 0.3) !important; 
        border: 1px solid rgba(255, 215, 112, 0.2) !important; 
        border-radius: 12px; 
        padding: 20px;
        box-shadow: 0 4px 10px rgba(0,0,0,0.2); 
        margin-bottom: 20px;
    }}
    
    .streamlit-expanderHeader {{
        background-color: rgba(255, 255, 255, 0.05) !important;
        color: {COR_DESTAQUE} !important;
        border: 1px solid {COR_DESTAQUE} !important;
        border-radius: 8px;
    }}
    .streamlit-expanderHeader svg {{
        fill: {COR_TEXTO} !important; 
        color: {COR_TEXTO} !important;
    }}

    div.stButton > button, div.stFormSubmitButton > button {{ 
        background: linear-gradient(135deg, {COR_BOTAO} 0%, #056853 100%) !important; 
        color: white !important; 
        border: 1px solid rgba(255,255,255,0.1) !important; 
        padding: 0.6em 1.5em !important; 
        font-weight: 600 !important;
        border-radius: 8px !important; 
        transition: all 0.3s ease !important;
    }}
    div.stButton > button:hover {{ 
        background: {COR_HOVER} !important; 
        color: #0e2d26 !important; 
        transform: translateY(-2px);
        box-shadow: 0 4px 12px rgba(255, 215, 112, 0.3);
    }}

    input, textarea, select, div[data-baseweb="select"] > div {{
        background-color: rgba(255, 255, 255, 0.05) !important;
        color: white !important;
        border: 1px solid rgba(255, 255, 255, 0.2) !important; 
        border-radius: 8px !important;
    }}
    .stTextInput input, .stTextArea textarea {{ color: white !important; }}
    
    /* --- MENU SUPERIOR (Option Menu) ESTILIZADO --- */
    .st-emotion-cache-1v7f65g {{
        background: linear-gradient(135deg, rgba(14, 45, 38, 0.9) 0%, rgba(9, 31, 26, 0.9) 100%) !important;
        backdrop-filter: blur(10px) !important;
        border: 1px solid rgba(255, 215, 112, 0.15) !important;
        border-radius: 50px !important;
        box-shadow: 0 8px 32px rgba(0, 0, 0, 0.3) !important;
        margin: 20px auto !important;
        max-width: 95% !important;
        padding: 0 !important;
    }}
    
    .st-emotion-cache-1v7f65g .st-ae .st-af {{
        color: rgba(255, 255, 255, 0.7) !important; 
        background: transparent !important;
        border: 1px solid transparent !important;
        transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1) !important;
    }}
    
    .st-emotion-cache-1v7f65g .st-ae .st-af:hover {{
        color: {COR_DESTAQUE} !important; 
        background: rgba(255, 215, 112, 0.1) !important;
        border: 1px solid rgba(255, 215, 112, 0.3) !important;
        transform: translateY(-2px) !important;
    }}
    
    .st-emotion-cache-1v7f65g .st-ae .st-ag {{
        background: linear-gradient(135deg, {COR_DESTAQUE} 0%, #ffedb3 100%) !important; 
        color: {COR_FUNDO} !important; 
        font-weight: 700 !important;
        box-shadow: 0 5px 20px rgba(255, 215, 112, 0.4) !important;
        border: none !important;
        animation: pulse 2s infinite !important;
    }}
    
    @keyframes pulse {{
        0% {{ box-shadow: 0 5px 20px rgba(255, 215, 112, 0.4); }}
        50% {{ box-shadow: 0 5px 25px rgba(255, 215, 112, 0.6); }}
        100% {{ box-shadow: 0 5px 20px rgba(255, 215, 112, 0.4); }}
    }}
    
    #MainMenu {{visibility: hidden;}}
    footer {{visibility: hidden;}}
    [data-testid="stDecoration"] {{display: none;}}

</style>
""", unsafe_allow_html=True)

# Adiciona o botão hamburguer customizado com JavaScript
st.markdown("""
<script>
// Aguarda o DOM carregar
document.addEventListener('DOMContentLoaded', function() {
    // Cria o botão hamburguer customizado
    const toggleButton = document.createElement('div');
    toggleButton.className = 'custom-sidebar-toggle';
    toggleButton.title = 'Abrir/Fechar Menu';
    
    // Adiciona ao corpo do documento
    document.body.appendChild(toggleButton);
    
    // Função para alternar a sidebar
    function toggleSidebar() {
        // Encontra o botão original do Streamlit
        const originalButton = document.querySelector('[data-testid="collapsedControl"] button');
        if (originalButton) {
            // Simula o clique no botão original
            originalButton.click();
            
            // Alterna a classe para mudar o ícone
            const sidebar = document.querySelector('section[data-testid="stSidebar"]');
            if (sidebar && sidebar.getAttribute('aria-expanded') === 'true') {
                toggleButton.classList.add('open');
            } else {
                toggleButton.classList.remove('open');
            }
        }
    }
    
    // Adiciona evento de clique ao botão customizado
    toggleButton.addEventListener('click', toggleSidebar);
    
    // Verifica o estado inicial da sidebar
    setTimeout(function() {
        const sidebar = document.querySelector('section[data-testid="stSidebar"]');
        if (sidebar && sidebar.getAttribute('aria-expanded') === 'true') {
            toggleButton.classList.add('open');
        }
    }, 500);
});
</script>
""", unsafe_allow_html=True)

if "SECRETS_TOML" in os.environ:
    if not os.path.exists(".streamlit"): os.makedirs(".streamlit")
    with open(".streamlit/secrets.toml", "w") as f: f.write(os.environ["SECRETS_TOML"])

try:
    from streamlit_option_menu import option_menu
    from views import login, geral, aluno, professor, admin
except ImportError as e:
    st.error(f"❌ Erro crítico nas importações: {e}")
    st.stop()

def tela_troca_senha_obrigatoria():
    c1, c2, c3 = st.columns([1, 2, 1])
    with c2:
        if logo_file:
            cl, cc, cr = st.columns([1, 1, 1])
            with cc: st.image(logo_file, use_container_width=True)
        st.write("") 
        with st.container(border=True):
            st.markdown("<h3>🔒 Troca de Senha</h3>", unsafe_allow_html=True)
            st.warning("Por segurança, redefina sua senha.")
            with st.form("frm_troca"):
                ns = st.text_input("Nova Senha:", type="password")
                cs = st.text_input("Confirmar:", type="password")
                if st.form_submit_button("Atualizar", use_container_width=True):
                    if ns and ns == cs:
                        try:
                            uid = st.session_state.usuario['id']
                            hashed = bcrypt.hashpw(ns.encode(), bcrypt.gensalt()).decode()
                            db = get_db()
                            db.collection('usuarios').document(uid).update({"senha": hashed, "precisa_trocar_senha": False})
                            st.success("Sucesso! Entrando..."); st.session_state.usuario['precisa_trocar_senha'] = False; st.rerun()
                        except: st.error("Erro ao salvar.")
                    else: st.error("Senhas não conferem.")

def app_principal():
    if not st.session_state.get('usuario'):
        st.session_state.clear(); st.rerun(); return

    usuario = st.session_state.usuario
    tipo = str(usuario.get("tipo", "aluno")).lower()

    def nav(pg): st.session_state.menu_selection = pg

    with st.sidebar:
        if logo_file: st.image(logo_file, use_container_width=True)
        st.markdown(f"<h3 style='color:{COR_DESTAQUE}; margin:0;'>{usuario['nome'].split()[0]}</h3>", unsafe_allow_html=True)
        st.markdown(f"<p style='text-align:center; color:#aaa; font-size: 0.9em;'>{tipo.capitalize()}</p>", unsafe_allow_html=True)
        st.markdown("---")
        
        if st.button("👤 Meu Perfil", use_container_width=True): nav("Meu Perfil")
        if tipo != "admin":
            if st.button("🏅 Meus Certificados", use_container_width=True): nav("Meus Certificados")
        if tipo in ["admin", "professor"]:
            if st.button("🥋 Painel Prof.", use_container_width=True): nav("Painel do Professor")
        if tipo == "admin":
            if st.button("🔑 Gestão Usuários", use_container_width=True): nav("Gestão de Usuários")
            
        st.markdown("<br>", unsafe_allow_html=True)
        if st.button("🚪 Sair", use_container_width=True):
            st.session_state.clear(); st.rerun()

    if "menu_selection" not in st.session_state: st.session_state.menu_selection = "Início"
    pg = st.session_state.menu_selection

    if pg == "Meu Perfil": geral.tela_meu_perfil(usuario); return
    if pg == "Gestão de Usuários": admin.gestao_usuarios(usuario); return
    if pg == "Painel do Professor": professor.painel_professor(); return
    if pg == "Meus Certificados": aluno.meus_certificados(usuario); return 
    if pg == "Início": geral.tela_inicio(); return

    ops, icns = [], []
    if tipo in ["admin", "professor"]:
        ops = ["Início", "Modo Rola", "Exame de Faixa", "Ranking", "Gestão de Questões", "Gestão de Equipes", "Gestão de Exame"]
        icns = ["house", "people", "journal", "trophy", "list-task", "building", "file-earmark"]
    else:
        ops = ["Início", "Modo Rola", "Exame de Faixa", "Ranking"]
        icns = ["house", "people", "journal", "trophy"]

    try: idx = ops.index(pg)
    except: idx = 0
    
    menu = option_menu(
        menu_title=None, 
        options=ops, 
        icons=icns, 
        default_index=idx, 
        orientation="horizontal",
        styles={
            "container": {
                "padding": "5px 10px", 
                "background-color": COR_FUNDO, 
                "margin": "0px auto",
                "border-radius": "12px", 
                "border": "1px solid rgba(255, 215, 112, 0.15)", 
                "box-shadow": "0 4px 15px rgba(0,0,0,0.3)",
                "width": "100%",      
                "max-width": "100%",  
                "display": "flex",    
                "justify-content": "space-between" 
            },
            "icon": {
                "color": COR_DESTAQUE, 
                "font-size": "16px",
                "font-weight": "bold"
            }, 
            "nav-link": {
                "font-size": "14px", 
                "text-align": "center", 
                "margin": "0px 2px",  
                "color": "rgba(255, 255, 255, 0.8)",
                "font-weight": "400",
                "border-radius": "8px",
                "transition": "0.3s",
                "width": "100%",      
                "flex-grow": "1",     
                "display": "flex",
                "justify-content": "center",
                "align-items": "center"
            },
            "nav-link-selected": {
                "background-color": COR_DESTAQUE, 
                "color": "#0e2d26", 
                "font-weight": "700",
                "box-shadow": "0px 2px 8px rgba(0,0,0,0.2)",
            },
        }
    )

    if menu != pg:
        if pg == "Meus Certificados" and menu == "Início": pass 
        else:
            st.session_state.menu_selection = menu
            st.rerun()

    if pg == "Modo Rola": aluno.modo_rola(usuario)
    elif pg == "Exame de Faixa": aluno.exame_de_faixa(usuario)
    elif pg == "Ranking": aluno.ranking()
    elif pg == "Gestão de Equipes": professor.gestao_equipes()
    elif pg == "Gestão de Questões": admin.gestao_questoes()
    elif pg == "Gestão de Exame": admin.gestao_exame_de_faixa()

if __name__ == "__main__":
    if not st.session_state.get('usuario') and not st.session_state.get('registration_pending'):
        login.tela_login()
    elif st.session_state.get('registration_pending'):
        login.tela_completar_cadastro(st.session_state.registration_pending)
    elif st.session_state.get('usuario'):
        if st.session_state.usuario.get("precisa_trocar_senha"): tela_troca_senha_obrigatoria()
        else: app_principal()
