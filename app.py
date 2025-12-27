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

# No app.py, no st.markdown CSS, ADICIONE:

st.markdown(f"""
<style>
    /* ===== NOVOS ESTILOS MODERNOS ===== */
    
    /* 1. CARDS DE CURSO MODERNOS */
    .curso-card {{
        background: linear-gradient(145deg, rgba(255,255,255,0.05), rgba(255,255,255,0.02));
        border: 1px solid rgba(255, 215, 112, 0.15);
        border-radius: 16px;
        padding: 24px;
        margin-bottom: 20px;
        backdrop-filter: blur(10px);
        transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
        position: relative;
        overflow: hidden;
    }}
    
    .curso-card:hover {{
        transform: translateY(-5px);
        border-color: {COR_DESTAQUE};
        box-shadow: 0 20px 40px rgba(0,0,0,0.3), 
                    0 0 0 1px rgba(255, 215, 112, 0.1);
    }}
    
    .curso-card::before {{
        content: '';
        position: absolute;
        top: 0;
        left: 0;
        width: 100%;
        height: 4px;
        background: linear-gradient(90deg, {COR_BOTAO}, {COR_HOVER});
        border-radius: 16px 16px 0 0;
    }}
    
    /* 2. BADGES MODERNOS */
    .badge {{
        display: inline-block;
        padding: 4px 12px;
        border-radius: 20px;
        font-size: 0.75rem;
        font-weight: 600;
        margin-right: 8px;
        margin-bottom: 8px;
    }}
    
    .badge-free {{
        background: linear-gradient(135deg, #078B6C, #056853);
        color: white;
    }}
    
    .badge-premium {{
        background: linear-gradient(135deg, #FFD770, #FFC107);
        color: #0e2d26;
    }}
    
    .badge-progress {{
        background: rgba(255, 215, 112, 0.1);
        color: #FFD770;
        border: 1px solid rgba(255, 215, 112, 0.3);
    }}
    
    /* 3. BOTÕES MODERNOS */
    .btn-modern {{
        background: linear-gradient(135deg, {COR_BOTAO} 0%, #056853 100%);
        color: white;
        border: none;
        padding: 12px 24px;
        border-radius: 12px;
        font-weight: 600;
        cursor: pointer;
        transition: all 0.3s;
        display: inline-flex;
        align-items: center;
        justify-content: center;
        gap: 8px;
    }}
    
    .btn-modern:hover {{
        background: linear-gradient(135deg, {COR_HOVER} 0%, #FFC107 100%);
        transform: scale(1.05);
        box-shadow: 0 10px 20px rgba(255, 215, 112, 0.2);
    }}
    
    .btn-outline {{
        background: transparent;
        color: {COR_DESTAQUE};
        border: 2px solid {COR_DESTAQUE};
    }}
    
    .btn-outline:hover {{
        background: {COR_DESTAQUE};
        color: #0e2d26;
    }}
    
    /* 4. PROGRESS BAR MODERNO */
    .progress-container {{
        height: 8px;
        background: rgba(255,255,255,0.1);
        border-radius: 10px;
        overflow: hidden;
        margin: 15px 0;
    }}
    
    .progress-bar {{
        height: 100%;
        background: linear-gradient(90deg, {COR_BOTAO}, {COR_HOVER});
        border-radius: 10px;
        transition: width 1s ease-in-out;
        position: relative;
    }}
    
    .progress-bar::after {{
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
        animation: shimmer 2s infinite;
    }}
    
    @keyframes shimmer {{
        0% {{ transform: translateX(-100%); }}
        100% {{ transform: translateX(100%); }}
    }}
    
    /* 5. CARDS DE MÓDULO */
    .modulo-card {{
        background: rgba(255,255,255,0.03);
        border-left: 4px solid {COR_DESTAQUE};
        border-radius: 0 12px 12px 0;
        padding: 20px;
        margin: 15px 0;
    }}
    
    .aula-item {{
        padding: 12px;
        margin: 8px 0;
        background: rgba(255,255,255,0.02);
        border-radius: 8px;
        border: 1px solid rgba(255,255,255,0.05);
        transition: all 0.2s;
    }}
    
    .aula-item:hover {{
        background: rgba(255,215,112,0.05);
        border-color: rgba(255,215,112,0.2);
    }}
    
    /* 6. NOVO LAYOUT DE GRID */
    .grid-container {{
        display: grid;
        grid-template-columns: repeat(auto-fill, minmax(350px, 1fr));
        gap: 24px;
        margin: 30px 0;
    }}
    
    /* 7. TYPOGRAPHY MODERNA */
    .curso-title {{
        font-size: 1.5rem;
        font-weight: 700;
        background: linear-gradient(135deg, #FFF, {COR_DESTAQUE});
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        margin-bottom: 10px;
    }}
    
    .curso-desc {{
        color: rgba(255,255,255,0.7);
        line-height: 1.6;
        font-size: 0.95rem;
    }}
    
    /* 8. HERO SECTION */
    .hero-section {{
        background: linear-gradient(135deg, rgba(7, 139, 108, 0.2), rgba(5, 104, 83, 0.1));
        border-radius: 20px;
        padding: 40px;
        margin-bottom: 40px;
        text-align: center;
        border: 1px solid rgba(255, 215, 112, 0.1);
    }}
    
    /* 9. ICONES ANIMADOS */
    .icon-spin {{
        animation: spin 2s linear infinite;
    }}
    
    @keyframes spin {{
        0% {{ transform: rotate(0deg); }}
        100% {{ transform: rotate(360deg); }}
    }}
    
    /* 10. RESPONSIVIDADE */
    @media (max-width: 768px) {{
        .grid-container {{
            grid-template-columns: 1fr;
        }}
        
        .curso-card {{
            padding: 16px;
        }}
    }}
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
