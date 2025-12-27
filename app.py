# main/app.py
import streamlit as st
import os
import sys
import bcrypt 
import time
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

    div.stRadio > div[role="radiogroup"] > label > div:first-child {{
        border-color: {COR_DESTAQUE} !important;
        background-color: transparent !important;
    }}
    div.stRadio > div[role="radiogroup"] > label > div:first-child > div {{
        background-color: {COR_DESTAQUE} !important;
    }}

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
    section[data-testid="stSidebar"] svg, [data-testid="collapsedControl"] svg {{
        fill: {COR_DESTAQUE} !important;
        color: {COR_DESTAQUE} !important;
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

    input, textarea, select, div[data-testid="stSelectbox"] > div {{ 
        background-color: rgba(255, 255, 255, 0.05) !important;
        color: white !important;
        border: 1px solid rgba(255, 255, 255, 0.2) !important; 
        border-radius: 8px !important;
    }}
    .stTextInput input, .stTextArea textarea {{ color: white !important; }}
    
    #MainMenu {{visibility: hidden;}}
    footer {{visibility: hidden;}}
    [data-testid="stDecoration"] {{display: none;}}
    header[data-testid="stHeader"] {{ background-color: transparent !important; z-index: 1; }}
    /* ============== ÁREA DE CURSOS MODERNA ============== */
    
    /* GRID DE CURSOS RESPONSIVO */
    .cursos-grid {{
        display: grid;
        grid-template-columns: repeat(auto-fill, minmax(350px, 1fr));
        gap: 24px;
        margin: 30px 0;
    }}
    
    /* CARD MODERNO */
    .curso-card-moderno {{
        background: linear-gradient(145deg, rgba(255,255,255,0.05), rgba(255,255,255,0.02));
        border: 1px solid rgba(255, 215, 112, 0.15);
        border-radius: 20px;
        padding: 25px;
        position: relative;
        overflow: hidden;
        transition: all 0.4s cubic-bezier(0.4, 0, 0.2, 1);
        backdrop-filter: blur(10px);
    }}
    
    .curso-card-moderno:hover {{
        transform: translateY(-8px);
        border-color: {COR_DESTAQUE};
        box-shadow: 0 25px 50px rgba(0,0,0,0.4),
                    inset 0 1px 0 rgba(255,255,255,0.1);
    }}
    
    .curso-card-moderno::before {{
        content: '';
        position: absolute;
        top: 0;
        left: 0;
        width: 100%;
        height: 5px;
        background: linear-gradient(90deg, {COR_BOTAO}, {COR_HOVER});
        border-radius: 20px 20px 0 0;
    }}
    
    /* BADGES */
    .badge-curso {{
        display: inline-block;
        padding: 6px 14px;
        border-radius: 20px;
        font-size: 0.8rem;
        font-weight: 700;
        margin-right: 8px;
        margin-bottom: 12px;
        letter-spacing: 0.5px;
    }}
    
    .badge-gratuito {{
        background: linear-gradient(135deg, #078B6C, #056853);
        color: white;
        box-shadow: 0 4px 12px rgba(7, 139, 108, 0.3);
    }}
    
    .badge-premium {{
        background: linear-gradient(135deg, #FFD770, #FFC107);
        color: #0e2d26;
        box-shadow: 0 4px 12px rgba(255, 215, 112, 0.3);
    }}
    
    .badge-andamento {{
        background: rgba(255, 215, 112, 0.15);
        color: #FFD770;
        border: 1px solid rgba(255, 215, 112, 0.3);
    }}
    
    /* TÍTULO E DESCRIÇÃO */
    .titulo-curso {{
        font-size: 1.4rem;
        font-weight: 700;
        background: linear-gradient(135deg, #FFF, {COR_DESTAQUE});
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        margin: 15px 0 10px 0;
        line-height: 1.3;
    }}
    
    .descricao-curso {{
        color: rgba(255,255,255,0.7);
        font-size: 0.95rem;
        line-height: 1.6;
        margin-bottom: 20px;
        display: -webkit-box;
        -webkit-line-clamp: 3;
        -webkit-box-orient: vertical;
        overflow: hidden;
    }}
    
    /* PROGRESS BAR ANIMADO */
    .progresso-container {{
        height: 10px;
        background: rgba(255,255,255,0.08);
        border-radius: 10px;
        overflow: hidden;
        margin: 20px 0;
        position: relative;
    }}
    
    .progresso-bar {{
        height: 100%;
        background: linear-gradient(90deg, {COR_BOTAO}, {COR_HOVER});
        border-radius: 10px;
        position: relative;
        transition: width 1s ease-out;
    }}
    
    .progresso-bar::after {{
        content: '';
        position: absolute;
        top: 0;
        left: 0;
        right: 0;
        bottom: 0;
        background: linear-gradient(
            90deg,
            transparent,
            rgba(255,255,255,0.4),
            transparent
        );
        animation: shimmer 2.5s infinite;
    }}
    
    @keyframes shimmer {{
        0% {{ transform: translateX(-100%); }}
        100% {{ transform: translateX(100%); }}
    }}
    
    /* METADADOS */
    .metadados-curso {{
        display: flex;
        justify-content: space-between;
        color: rgba(255,255,255,0.6);
        font-size: 0.85rem;
        margin-top: 15px;
    }}
    
    .metadado-item {{
        display: flex;
        align-items: center;
        gap: 6px;
    }}
    
    /* BOTÕES MODERNOS */
    .btn-curso {{
        width: 100%;
        padding: 14px;
        border-radius: 12px;
        border: none;
        font-weight: 700;
        font-size: 1rem;
        cursor: pointer;
        transition: all 0.3s;
        margin-top: 15px;
        display: flex;
        align-items: center;
        justify-content: center;
        gap: 10px;
    }}
    
    .btn-continuar {{
        background: linear-gradient(135deg, {COR_BOTAO}, #056853);
        color: white;
    }}
    
    .btn-continuar:hover {{
        background: linear-gradient(135deg, {COR_HOVER}, #FFC107);
        transform: scale(1.02);
        box-shadow: 0 10px 20px rgba(255, 215, 112, 0.3);
    }}
    
    .btn-comprar {{
        background: linear-gradient(135deg, #FFD770, #FFC107);
        color: #0e2d26;
        font-weight: 800;
    }}
    
    .btn-comprar:hover {{
        transform: scale(1.05);
        box-shadow: 0 12px 24px rgba(255, 215, 112, 0.4);
    }}
    
    /* HERO SECTION */
    .hero-cursos {{
        background: linear-gradient(135deg, 
            rgba(7, 139, 108, 0.25), 
            rgba(5, 104, 83, 0.15));
        border-radius: 24px;
        padding: 50px 40px;
        margin-bottom: 40px;
        text-align: center;
        border: 1px solid rgba(255, 215, 112, 0.2);
        position: relative;
        overflow: hidden;
    }}
    
    .hero-cursos::before {{
        content: '';
        position: absolute;
        top: -50%;
        left: -50%;
        width: 200%;
        height: 200%;
        background: radial-gradient(
            circle,
            rgba(255, 215, 112, 0.1) 0%,
            transparent 70%
        );
        z-index: -1;
    }}
    
    /* TABS MODERNAS */
    .stTabs [data-baseweb="tab-list"] {{
        gap: 10px;
        background: transparent;
        border-bottom: 2px solid rgba(255,255,255,0.1);
    }}
    
    .stTabs [data-baseweb="tab"] {{
        background: rgba(255,255,255,0.05);
        border-radius: 12px 12px 0 0;
        padding: 14px 28px;
        color: rgba(255,255,255,0.8);
        border: 1px solid rgba(255,255,255,0.1);
        border-bottom: none;
        font-weight: 500;
        transition: all 0.3s;
    }}
    
    .stTabs [data-baseweb="tab"]:hover {{
        background: rgba(255, 215, 112, 0.1);
        color: {COR_DESTAQUE};
    }}
    
    .stTabs [aria-selected="true"] {{
        background: linear-gradient(135deg, {COR_BOTAO}, #056853) !important;
        color: white !important;
        font-weight: 700;
        border-color: {COR_BOTAO} !important;
        position: relative;
    }}
    
    .stTabs [aria-selected="true"]::after {{
        content: '';
        position: absolute;
        bottom: -2px;
        left: 0;
        width: 100%;
        height: 3px;
        background: {COR_HOVER};
    }}
    
    /* ESTADO VAZIO */
    .empty-state {{
        text-align: center;
        padding: 60px 20px;
        background: rgba(255,255,255,0.02);
        border-radius: 20px;
        border: 2px dashed rgba(255,255,255,0.1);
        margin: 40px 0;
    }}
    
    .empty-state-icon {{
        font-size: 4rem;
        opacity: 0.3;
        margin-bottom: 20px;
    }}
    
    /* FILTROS MODERNOS */
    .filtros-container {{
        background: rgba(255,255,255,0.03);
        border-radius: 16px;
        padding: 20px;
        margin: 20px 0;
        border: 1px solid rgba(255,255,255,0.1);
    }}
    
    /* RESPONSIVIDADE */
    @media (max-width: 768px) {{
        .cursos-grid {{
            grid-template-columns: 1fr;
            gap: 20px;
        }}
        
        .curso-card-moderno {{
            padding: 20px;
        }}
        
        .hero-cursos {{
            padding: 30px 20px;
        }}
    }}
    
    /* PLAYER DE AULA MODERNO */
    .player-container {{
        background: linear-gradient(145deg, rgba(14,45,38,0.95), rgba(7,139,108,0.15));
        border-radius: 20px;
        border: 1px solid rgba(255,215,112,0.2);
        padding: 30px;
        margin-bottom: 30px;
        position: relative;
    }}
    
    .player-header {{
        display: flex;
        justify-content: space-between;
        align-items: center;
        margin-bottom: 25px;
    }}
    
    .player-title {{
        font-size: 1.8rem;
        color: {COR_DESTAQUE};
        font-weight: 700;
    }}
    
    .conteudo-aula {{
        background: rgba(255,255,255,0.03);
        border-radius: 15px;
        padding: 25px;
        margin-top: 25px;
        border: 1px solid rgba(255,255,255,0.1);
    }}

    /* TABS ESPECÍFICAS PARA CURSOS */
div[data-testid="stTabs"] {
    background: transparent;
}

div[data-testid="stTabs"] > div > div {
    overflow: visible;
}

/* ANIMAÇÃO DE ENTRADA */
@keyframes fadeInUp {
    from {
        opacity: 0;
        transform: translateY(20px);
    }
    to {
        opacity: 1;
        transform: translateY(0);
    }
}

.curso-card-moderno {
    animation: fadeInUp 0.6s ease-out;
}

/* LOADING SKELETON */
.skeleton {
    background: linear-gradient(90deg, 
        rgba(255,255,255,0.05) 25%, 
        rgba(255,255,255,0.1) 50%, 
        rgba(255,255,255,0.05) 75%);
    background-size: 200% 100%;
    animation: loading 1.5s infinite;
    border-radius: 12px;
}

@keyframes loading {
    0% { background-position: 200% 0; }
    100% { background-position: -200% 0; }
}

/* TOOLTIPS */
.tooltip {
    position: relative;
    display: inline-block;
}

.tooltip .tooltiptext {
    visibility: hidden;
    background: rgba(0,0,0,0.8);
    color: white;
    text-align: center;
    padding: 8px 12px;
    border-radius: 8px;
    position: absolute;
    z-index: 1000;
    bottom: 125%;
    left: 50%;
    transform: translateX(-50%);
    white-space: nowrap;
}

.tooltip:hover .tooltiptext {
    visibility: visible;
}

/* BOTÃO FLUTUANTE */
.floating-btn {
    position: fixed;
    bottom: 30px;
    right: 30px;
    width: 60px;
    height: 60px;
    border-radius: 50%;
    background: linear-gradient(135deg, #FFD770, #FFC107);
    color: #0e2d26;
    border: none;
    font-size: 24px;
    cursor: pointer;
    box-shadow: 0 8px 25px rgba(255, 215, 112, 0.4);
    z-index: 1000;
    display: flex;
    align-items: center;
    justify-content: center;
    transition: all 0.3s;
}

.floating-btn:hover {
    transform: scale(1.1);
    box-shadow: 0 12px 30px rgba(255, 215, 112, 0.6);
}
</style>
""", unsafe_allow_html=True)

if "SECRETS_TOML" in os.environ:
    if not os.path.exists(".streamlit"): os.makedirs(".streamlit")
    with open(".streamlit/secrets.toml", "w") as f: f.write(os.environ["SECRETS_TOML"])

try:
    from streamlit_option_menu import option_menu
    # --- CORREÇÃO AQUI: Removemos 'cursos' da lista ---
    from views import login, geral, aluno, professor, admin
    from views.painel_aluno import render_painel_aluno 
    # --- CORREÇÃO AQUI: Adicionamos o import que faltava ---
    from views.cursos_professor import pagina_cursos_professor

except ImportError as e:
    st.error(f"❌ Erro crítico nas importações: {e}")
    st.stop()

def handle_javascript_events():
    """Processa eventos enviados do JavaScript"""
    
    # Criar componente para receber mensagens
    js_receiver = """
    <script>
    // Enviar mensagem quando a página carregar
    window.onload = function() {
        window.parent.postMessage({
            type: 'STREAMLIT_READY',
            data: { ready: true }
        }, '*');
    };
    
    // Handler para mensagens do Streamlit
    window.addEventListener('message', function(event) {
        if (event.data.type === 'STREAMLIT_COMMAND') {
            // Processar comandos do Streamlit
            console.log('Streamlit command:', event.data.data);

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
                            user_sessao = st.session_state.get('usuario')
                            if not user_sessao or 'id' not in user_sessao:
                                st.error("Erro de Sessão: Usuário não identificado.")
                                return

                            uid = user_sessao['id']
                            hashed = bcrypt.hashpw(ns.encode(), bcrypt.gensalt()).decode()
                            
                            db = get_db()
                            if not db:
                                st.error("Erro de conexão com o banco.")
                                return

                            db.collection('usuarios').document(uid).update({
                                "senha": hashed, 
                                "precisa_trocar_senha": False
                            })
                            
                            st.success("Sucesso! Entrando...")
                            st.session_state.usuario['precisa_trocar_senha'] = False
                            time.sleep(1)
                            st.rerun()
                            
                        except Exception as e: 
                            st.error(f"Erro ao salvar: {e}") 
                    else: st.error("Senhas não conferem.")

def app_principal():
    if not st.session_state.get('usuario'):
        st.session_state.clear(); st.rerun(); return

    usuario = st.session_state.usuario
    raw_tipo = str(usuario.get("tipo", "aluno")).lower()
    
    if "admin" in raw_tipo: tipo_code = "admin"
    elif "professor" in raw_tipo: tipo_code = "professor"
    else: tipo_code = "aluno"

    label_tipo = raw_tipo.capitalize()
    if tipo_code == "admin": label_tipo = "Administrador(a)"
    elif tipo_code == "professor": label_tipo = "Professor(a)"
    elif tipo_code == "aluno": label_tipo = "Aluno(a)"

    def nav(pg): st.session_state.menu_selection = pg

    with st.sidebar:
        if logo_file: st.image(logo_file, use_container_width=True)
        st.markdown(f"<h3 style='color:{COR_DESTAQUE}; margin:0;'>{usuario['nome'].split()[0]}</h3>", unsafe_allow_html=True)
        
        st.markdown(f"<p style='text-align:center; color:#aaa; font-size: 0.9em;'>{label_tipo}</p>", unsafe_allow_html=True)
        st.markdown("---")
        
        if st.button("👤 Meu Perfil", use_container_width=True): nav("Meu Perfil")

        # Botão direto para a nova área
        if st.button("📚 Meus Cursos", use_container_width=True): nav("Meus Cursos")
        
        if tipo_code in ["admin", "professor"]:
            if st.button("🥋 Painel Prof.", use_container_width=True): nav("Painel de Professores")
        
        if tipo_code != "admin": 
            if st.button("🏅 Meus Certificados", use_container_width=True): nav("Meus Certificados")
        
        if tipo_code == "admin":
            if st.button("📊 Gestão e Estatísticas", use_container_width=True): nav("Gestão e Estatísticas")
            
        st.markdown("<br>", unsafe_allow_html=True)
        if st.button("🚪 Sair", use_container_width=True):
            st.session_state.clear(); st.rerun()

    if "menu_selection" not in st.session_state: st.session_state.menu_selection = "Início"
    pg = st.session_state.menu_selection

    # --- Rotas que NÃO mostram o menu horizontal ---
    if pg == "Início": 
        geral.tela_inicio()
        return  # <--- RETORNA AQUI. NÃO DESENHA O MENU ABAIXO.

    if pg == "Meu Perfil": geral.tela_meu_perfil(usuario); return
    if pg == "Gestão e Estatísticas": admin.gestao_usuarios(usuario); return
    if pg == "Painel de Professores": professor.painel_professor(); return
    if pg == "Meus Certificados": aluno.meus_certificados(usuario); return 
    
    # -----------------------------------------------

    # --- MENU DE OPÇÕES (Só desenha se não for Início) ---
    ops, icns = [], []
    
    if tipo_code in ["admin", "professor"]:
        # Removemos "Início" do menu horizontal para não ficar redundante
        ops = ["Modo Rola", "Cursos", "Exame de Faixa", "Ranking", "Gestão de Questões", "Gestão de Equipes", "Gestão de Exame"]
        icns = ["people", "book", "journal", "trophy", "list-task", "building", "file-earmark"]
    else:
        ops = ["Modo Rola", "Cursos", "Exame de Faixa", "Ranking"]
        icns = ["people", "book", "journal", "trophy"]

    try: idx = ops.index(pg)
    except: idx = 0
    
    # Renderiza o menu
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

    # --- TRAVA DE SEGURANÇA (Páginas Ocultas) ---
    # Páginas que existem mas não estão no menu horizontal
    paginas_ocultas = ["Meus Cursos", "Área do Aluno", "Início"]

    if menu != pg:
        # Se estamos numa página oculta e o menu retornou a opção padrão (agora Modo Rola),
        # ignoramos a atualização para não expulsar o usuário da página.
        if pg in paginas_ocultas:
            pass
        else:
            st.session_state.menu_selection = menu
            st.rerun()

    # --- ROTEAMENTO FINAL ---
    if pg == "Modo Rola": 
        aluno.modo_rola(usuario)
        
    elif pg == "Cursos":
        if tipo_code == "aluno":
            render_painel_aluno(usuario) 
        else:
            # Chama a função que importamos agora corretamente
            pagina_cursos_professor(usuario)
            
    elif pg == "Meus Cursos" or pg == "Área do Aluno": 
        render_painel_aluno(usuario) 
            
    elif pg == "Exame de Faixa": 
        aluno.exame_de_faixa(usuario)
    elif pg == "Ranking": 
        aluno.ranking()
    elif pg == "Gestão de Equipes": 
        professor.gestao_equipes()
    elif pg == "Gestão de Questões": 
        admin.gestao_questoes()
    elif pg == "Gestão de Exame": 
        admin.gestao_exame_de_faixa()

if __name__ == "__main__":
    if not st.session_state.get('usuario') and not st.session_state.get('registration_pending'):
        login.tela_login()
    elif st.session_state.get('registration_pending'):
        login.tela_completar_cadastro(st.session_state.registration_pending)
    elif st.session_state.get('usuario'):
        if st.session_state.usuario.get("precisa_trocar_senha"): tela_troca_senha_obrigatoria()
        else: app_principal()
