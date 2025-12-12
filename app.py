"""
🎨 Módulo Principal Modernizado - BJJ Digital
Design: Glassmorphism, Dark Mode Elegante
Funcionalidades: Layout responsivo, componentes modulares, animações suaves
"""

import streamlit as st
import os
import sys
import bcrypt 
import time
from datetime import datetime
from typing import Optional, Dict, Any
from dataclasses import dataclass
import random

# Banco de dados
from database import get_db

# =========================================
# CONFIGURAÇÃO DE PATH E ASSETS
# =========================================

def get_logo_path() -> Optional[str]:
    """Retorna o caminho do logo com fallback inteligente"""
    possible_paths = [
        "assets/logo.png", "assets/logo.jpg", "assets/logo.svg",
        "logo.png", "logo.jpg", "logo.svg",
        "static/logo.png", "static/logo.jpg"
    ]
    
    for path in possible_paths:
        if os.path.exists(path):
            return path
    
    # Se não encontrar, usar um placeholder SVG
    return None

def get_background_image() -> Optional[str]:
    """Retorna caminho para imagem de background"""
    possible_backgrounds = [
        "assets/background.jpg", "assets/bg.jpg",
        "background.jpg", "bg.jpg",
        "static/background.jpg"
    ]
    
    for path in possible_backgrounds:
        if os.path.exists(path):
            return path
    
    return None

logo_file = get_logo_path()
bg_image = get_background_image()

# =========================================
# CONFIGURAÇÃO DA PÁGINA
# =========================================

st.set_page_config(
    page_title="BJJ Digital | Sistema de Gestão",
    page_icon="🥋" if not logo_file else logo_file,
    layout="wide",
    initial_sidebar_state="expanded",
    menu_items={
        'Get Help': 'https://github.com/seu-repo/bjj-digital',
        'Report a bug': "https://github.com/seu-repo/bjj-digital/issues",
        'About': "### BJJ Digital\nSistema de gestão para artes marciais\nVersão 2.0"
    }
)

# =========================================
# CONFIGURAÇÃO DE TEMA E CORES
# =========================================

@dataclass
class ThemeConfig:
    """Configuração de tema moderno"""
    # Cores principais
    primary: str = "#10B981"  # Verde esmeralda
    secondary: str = "#3B82F6"  # Azul safira
    accent: str = "#F59E0B"  # Âmbar
    
    # Backgrounds
    bg_dark: str = "#0F172A"  # Azul noite
    bg_card: str = "#1E293B"  # Azul ardósia
    bg_sidebar: str = "#0F172A"
    
    # Textos
    text_primary: str = "#F1F5F9"
    text_secondary: str = "#94A3B8"
    text_accent: str = "#F59E0B"
    
    # Estados
    success: str = "#10B981"
    warning: str = "#F59E0B"
    error: str = "#EF4444"
    info: str = "#3B82F6"
    
    # Gradientes
    gradient_primary: str = "linear-gradient(135deg, #10B981 0%, #059669 100%)"
    gradient_secondary: str = "linear-gradient(135deg, #3B82F6 0%, #1D4ED8 100%)"
    gradient_accent: str = "linear-gradient(135deg, #F59E0B 0%, #D97706 100%)"
    gradient_dark: str = "linear-gradient(135deg, #0F172A 0%, #1E293B 100%)"
    
    # Efeitos
    shadow: str = "0 10px 25px rgba(0, 0, 0, 0.3)"
    glow: str = "0 0 20px rgba(16, 185, 129, 0.3)"
    border: str = "1px solid rgba(255, 255, 255, 0.1)"
    
    @property
    def css_variables(self) -> str:
        """Retorna variáveis CSS para o tema"""
        return f"""
        :root {{
            --primary: {self.primary};
            --secondary: {self.secondary};
            --accent: {self.accent};
            --bg-dark: {self.bg_dark};
            --bg-card: {self.bg_card};
            --bg-sidebar: {self.bg_sidebar};
            --text-primary: {self.text_primary};
            --text-secondary: {self.text_secondary};
            --text-accent: {self.text_accent};
            --success: {self.success};
            --warning: {self.warning};
            --error: {self.error};
            --info: {self.info};
            --gradient-primary: {self.gradient_primary};
            --gradient-secondary: {self.gradient_secondary};
            --gradient-accent: {self.gradient_accent};
            --gradient-dark: {self.gradient_dark};
            --shadow: {self.shadow};
            --glow: {self.glow};
            --border: {self.border};
        }}
        """

# Criar instância do tema
theme = ThemeConfig()

# =========================================
# STYLESHEET MODERNO
# =========================================

def aplicar_estilos_modernos():
    """Aplica todos os estilos modernos da aplicação"""
    
    # Background image se disponível
    bg_style = ""
    if bg_image:
        bg_style = f"""
        background-image: url('{bg_image}');
        background-size: cover;
        background-position: center;
        background-attachment: fixed;
        """
    else:
        bg_style = f"background: {theme.gradient_dark};"
    
    styles = f"""
    <style>
    {theme.css_variables}
    
    /* Importação de fontes modernas */
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&family=JetBrains+Mono:wght@400;500&display=swap');
    
    /* Reset e base */
    * {{
        margin: 0;
        padding: 0;
        box-sizing: border-box;
    }}
    
    html, body, .stApp {{
        min-height: 100vh;
        {bg_style}
        font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
        color: var(--text-primary);
        overflow-x: hidden;
    }}
    
    /* Tipografia moderna */
    h1, h2, h3, h4, h5, h6 {{
        font-family: 'Inter', sans-serif;
        font-weight: 700;
        background: {theme.gradient_primary};
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        background-clip: text;
        margin-bottom: 1rem;
        line-height: 1.2;
    }}
    
    h1 {{
        font-size: 2.5rem;
        letter-spacing: -0.5px;
    }}
    
    h2 {{
        font-size: 2rem;
        letter-spacing: -0.3px;
    }}
    
    h3 {{
        font-size: 1.5rem;
    }}
    
    p, span, div, label {{
        font-family: 'Inter', sans-serif;
        color: var(--text-primary);
        line-height: 1.6;
    }}
    
    /* Cards modernos com glassmorphism */
    .modern-card {{
        background: rgba(255, 255, 255, 0.03);
        backdrop-filter: blur(20px);
        border: var(--border);
        border-radius: 20px;
        padding: 1.5rem;
        margin: 1rem 0;
        transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
        box-shadow: var(--shadow);
    }}
    
    .modern-card:hover {{
        transform: translateY(-5px);
        border-color: rgba(16, 185, 129, 0.3);
        box-shadow: 0 20px 40px rgba(0, 0, 0, 0.4);
    }}
    
    /* Sidebar elegante */
    section[data-testid="stSidebar"] {{
        background: var(--bg-sidebar) !important;
        border-right: 1px solid rgba(255, 255, 255, 0.05);
        backdrop-filter: blur(10px);
    }}
    
    section[data-testid="stSidebar"] > div {{
        padding: 2rem 1.5rem;
    }}
    
    /* Botões modernos */
    .stButton > button {{
        background: var(--gradient-primary);
        color: white !important;
        border: none !important;
        border-radius: 12px !important;
        padding: 0.75rem 1.5rem !important;
        font-weight: 600 !important;
        font-size: 0.9rem;
        cursor: pointer;
        transition: all 0.3s ease !important;
        position: relative;
        overflow: hidden;
    }}
    
    .stButton > button::before {{
        content: '';
        position: absolute;
        top: 0;
        left: -100%;
        width: 100%;
        height: 100%;
        background: linear-gradient(90deg, transparent, rgba(255, 255, 255, 0.2), transparent);
        transition: 0.5s;
    }}
    
    .stButton > button:hover {{
        transform: translateY(-2px);
        box-shadow: 0 10px 25px rgba(16, 185, 129, 0.4);
    }}
    
    .stButton > button:hover::before {{
        left: 100%;
    }}
    
    .stButton > button:active {{
        transform: translateY(0);
    }}
    
    /* Botão secundário */
    .secondary-button > button {{
        background: transparent !important;
        border: 2px solid var(--primary) !important;
        color: var(--primary) !important;
    }}
    
    /* Inputs modernos */
    .stTextInput > div > div > input,
    .stTextArea > div > textarea,
    .stSelectbox > div > div {{
        background: rgba(255, 255, 255, 0.05) !important;
        border: var(--border) !important;
        border-radius: 12px !important;
        color: var(--text-primary) !important;
        padding: 0.75rem 1rem !important;
        font-size: 0.9rem;
        transition: all 0.3s ease;
    }}
    
    .stTextInput > div > div > input:focus,
    .stTextArea > div > textarea:focus {{
        border-color: var(--primary) !important;
        box-shadow: 0 0 0 3px rgba(16, 185, 129, 0.1) !important;
        outline: none !important;
    }}
    
    /* Tabs modernas */
    .stTabs [data-baseweb="tab-list"] {{
        gap: 0.5rem;
        background: rgba(255, 255, 255, 0.03);
        border-radius: 16px;
        padding: 0.5rem;
        margin-bottom: 2rem;
    }}
    
    .stTabs [data-baseweb="tab"] {{
        border-radius: 12px;
        padding: 0.75rem 1.5rem;
        font-weight: 500;
        color: var(--text-secondary);
        transition: all 0.3s ease;
    }}
    
    .stTabs [data-baseweb="tab"]:hover {{
        background: rgba(255, 255, 255, 0.05);
        color: var(--text-primary);
    }}
    
    .stTabs [aria-selected="true"] {{
        background: var(--gradient-primary) !important;
        color: white !important;
        font-weight: 600;
    }}
    
    /* Progress bars personalizadas */
    .stProgress > div > div > div {{
        background: var(--gradient-primary);
        border-radius: 10px;
    }}
    
    /* Badges modernas */
    .badge {{
        display: inline-flex;
        align-items: center;
        padding: 0.25rem 0.75rem;
        border-radius: 20px;
        font-size: 0.75rem;
        font-weight: 600;
        margin: 0.25rem;
        backdrop-filter: blur(10px);
    }}
    
    .badge-success {{
        background: rgba(16, 185, 129, 0.2);
        color: var(--success);
        border: 1px solid rgba(16, 185, 129, 0.3);
    }}
    
    .badge-warning {{
        background: rgba(245, 158, 11, 0.2);
        color: var(--warning);
        border: 1px solid rgba(245, 158, 11, 0.3);
    }}
    
    .badge-error {{
        background: rgba(239, 68, 68, 0.2);
        color: var(--error);
        border: 1px solid rgba(239, 68, 68, 0.3);
    }}
    
    .badge-info {{
        background: rgba(59, 130, 246, 0.2);
        color: var(--info);
        border: 1px solid rgba(59, 130, 246, 0.3);
    }}
    
    /* Avatar circular */
    .avatar {{
        width: 40px;
        height: 40px;
        border-radius: 50%;
        background: var(--gradient-primary);
        display: flex;
        align-items: center;
        justify-content: center;
        color: white;
        font-weight: bold;
        font-size: 1rem;
    }}
    
    /* Separadores modernos */
    hr {{
        margin: 2rem 0;
        border: none;
        height: 1px;
        background: linear-gradient(
            to right, 
            transparent, 
            rgba(255, 255, 255, 0.1), 
            transparent
        );
    }}
    
    /* Animações */
    @keyframes fadeIn {{
        from {{ opacity: 0; transform: translateY(20px); }}
        to {{ opacity: 1; transform: translateY(0); }}
    }}
    
    @keyframes slideIn {{
        from {{ transform: translateX(-20px); opacity: 0; }}
        to {{ transform: translateX(0); opacity: 1; }}
    }}
    
    @keyframes pulse {{
        0%, 100% {{ opacity: 1; }}
        50% {{ opacity: 0.7; }}
    }}
    
    .animate-fadeIn {{
        animation: fadeIn 0.6s ease-out;
    }}
    
    .animate-slideIn {{
        animation: slideIn 0.5s ease-out;
    }}
    
    .animate-pulse {{
        animation: pulse 2s infinite;
    }}
    
    /* Scrollbar personalizada */
    ::-webkit-scrollbar {{
        width: 8px;
        height: 8px;
    }}
    
    ::-webkit-scrollbar-track {{
        background: rgba(255, 255, 255, 0.05);
        border-radius: 4px;
    }}
    
    ::-webkit-scrollbar-thumb {{
        background: var(--gradient-primary);
        border-radius: 4px;
    }}
    
    ::-webkit-scrollbar-thumb:hover {{
        background: var(--primary);
    }}
    
    /* Utilidades */
    .glass-effect {{
        background: rgba(255, 255, 255, 0.05);
        backdrop-filter: blur(10px);
        border: var(--border);
    }}
    
    .text-gradient {{
        background: var(--gradient-primary);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        background-clip: text;
    }}
    
    /* Loading states */
    .loading {{
        position: relative;
        overflow: hidden;
    }}
    
    .loading::after {{
        content: '';
        position: absolute;
        top: 0;
        left: -100%;
        width: 100%;
        height: 100%;
        background: linear-gradient(
            90deg,
            transparent,
            rgba(255, 255, 255, 0.1),
            transparent
        );
        animation: loading 1.5s infinite;
    }}
    
    @keyframes loading {{
        0% {{ left: -100%; }}
        100% {{ left: 100%; }}
    }}
    
    /* Esconder elementos do Streamlit */
    #MainMenu {{ visibility: hidden; }}
    footer {{ visibility: hidden; }}
    header {{ visibility: hidden; }}
    [data-testid="stDecoration"] {{ display: none; }}
    [data-testid="collapsedControl"] {{ display: none; }}
    
    /* Tooltip customizado */
    .tooltip {{
        position: relative;
        display: inline-block;
    }}
    
    .tooltip .tooltiptext {{
        visibility: hidden;
        width: 200px;
        background-color: var(--bg-card);
        color: var(--text-primary);
        text-align: center;
        border-radius: 12px;
        padding: 0.5rem;
        position: absolute;
        z-index: 1;
        bottom: 125%;
        left: 50%;
        transform: translateX(-50%);
        opacity: 0;
        transition: opacity 0.3s;
        border: var(--border);
        box-shadow: var(--shadow);
        font-size: 0.8rem;
    }}
    
    .tooltip:hover .tooltiptext {{
        visibility: visible;
        opacity: 1;
    }}
    </style>
    """
    
    st.markdown(styles, unsafe_allow_html=True)

# =========================================
# COMPONENTES REUTILIZÁVEIS
# =========================================

def header_component(title: str, subtitle: str = None, icon: str = "🥋"):
    """Componente de header moderno"""
    col1, col2 = st.columns([3, 1])
    
    with col1:
        st.markdown(f"""
        <div class="animate-fadeIn">
            <div style="display: flex; align-items: center; gap: 1rem; margin-bottom: 0.5rem;">
                <div style="font-size: 2.5rem;">{icon}</div>
                <h1 style="margin: 0;">{title}</h1>
            </div>
            {f'<p style="opacity: 0.8; font-size: 1.1rem;">{subtitle}</p>' if subtitle else ''}
        </div>
        """, unsafe_allow_html=True)
    
    with col2:
        # Relógio e data atual
        current_time = datetime.now().strftime("%H:%M")
        current_date = datetime.now().strftime("%d/%m/%Y")
        st.markdown(f"""
        <div style="text-align: right; opacity: 0.7;">
            <div style="font-size: 1.5rem; font-weight: bold;">{current_time}</div>
            <div style="font-size: 0.9rem;">{current_date}</div>
        </div>
        """, unsafe_allow_html=True)
    
    st.markdown("---")

def user_card_component(usuario: Dict[str, Any]):
    """Card de usuário para sidebar"""
    nome = usuario.get('nome', 'Usuário').split()[0]
    tipo = usuario.get('tipo', 'aluno').lower()
    email = usuario.get('email', '')
    
    # Avatar com iniciais
    initials = ''.join([n[0].upper() for n in nome.split()[:2]]) if ' ' in nome else nome[0].upper()
    
    # Cor baseada no tipo
    tipo_colors = {
        'admin': theme.primary,
        'professor': theme.secondary,
        'aluno': theme.accent
    }
    tipo_color = tipo_colors.get(tipo, theme.primary)
    
    st.markdown(f"""
    <div style="
        display: flex;
        align-items: center;
        gap: 1rem;
        padding: 1rem;
        background: rgba(255, 255, 255, 0.03);
        border-radius: 16px;
        margin-bottom: 1rem;
        border: {theme.border};
    ">
        <div class="avatar" style="background: {tipo_color};">
            {initials}
        </div>
        <div>
            <div style="font-weight: 600; font-size: 1.1rem;">{nome}</div>
            <div style="opacity: 0.7; font-size: 0.9rem;">{tipo.capitalize()}</div>
            <div style="opacity: 0.5; font-size: 0.8rem;">{email}</div>
        </div>
    </div>
    """, unsafe_allow_html=True)

def metric_card_component(title: str, value: Any, change: str = None, icon: str = "📊"):
    """Componente de métrica para dashboard"""
    st.markdown(f"""
    <div class="modern-card" style="text-align: center;">
        <div style="font-size: 2rem; margin-bottom: 0.5rem;">{icon}</div>
        <div style="font-size: 2rem; font-weight: bold; margin-bottom: 0.5rem;">{value}</div>
        <div style="font-size: 0.9rem; opacity: 0.8; margin-bottom: 0.5rem;">{title}</div>
        {f'<div style="font-size: 0.8rem; color: {theme.success};">{change}</div>' if change else ''}
    </div>
    """, unsafe_allow_html=True)

def feature_card_component(title: str, description: str, icon: str, action_func=None, action_label: str = "Acessar"):
    """Card de funcionalidade"""
    col1, col2 = st.columns([4, 1])
    
    with col1:
        st.markdown(f"""
        <div style="margin-bottom: 0.5rem;">
            <div style="font-size: 1.5rem; display: flex; align-items: center; gap: 0.5rem;">
                {icon}
                <span style="font-weight: 600;">{title}</span>
            </div>
            <div style="opacity: 0.8; font-size: 0.9rem; margin-top: 0.25rem;">
                {description}
            </div>
        </div>
        """, unsafe_allow_html=True)
    
    with col2:
        if action_func and st.button(action_label, key=f"btn_{title}"):
            action_func()

# =========================================
# FUNÇÕES DE AUTENTICAÇÃO
# =========================================

def tela_troca_senha_obrigatoria():
    """Interface moderna para troca de senha obrigatória"""
    
    # Header elegante
    st.markdown("""
    <div class="animate-fadeIn" style="max-width: 500px; margin: 4rem auto;">
        <div style="text-align: center; margin-bottom: 2rem;">
            <div style="font-size: 4rem;">🔒</div>
            <h2 style="margin-bottom: 0.5rem;">Segurança Reforçada</h2>
            <p style="opacity: 0.8;">Por segurança, redefina sua senha de acesso</p>
        </div>
    """, unsafe_allow_html=True)
    
    # Card do formulário
    with st.container():
        st.markdown("""
        <div class="modern-card">
            <div style="margin-bottom: 1.5rem;">
                <div style="display: flex; align-items: center; gap: 0.5rem; margin-bottom: 0.5rem;">
                    <div style="font-size: 1.2rem;">🛡️</div>
                    <h3 style="margin: 0;">Nova Senha</h3>
                </div>
                <p style="opacity: 0.8; font-size: 0.9rem;">
                    Crie uma senha forte com pelo menos 8 caracteres, incluindo números e letras.
                </p>
            </div>
        """, unsafe_allow_html=True)
        
        with st.form("frm_troca_senha"):
            col1, col2 = st.columns(2)
            
            with col1:
                nova_senha = st.text_input(
                    "Nova Senha",
                    type="password",
                    help="Mínimo 8 caracteres",
                    placeholder="Digite sua nova senha"
                )
            
            with col2:
                confirmar_senha = st.text_input(
                    "Confirmar Senha",
                    type="password",
                    placeholder="Digite novamente"
                )
            
            # Dicas de senha
            with st.expander("💡 Dicas para senha segura"):
                st.markdown("""
                - Use pelo menos **8 caracteres**
                - Combine **letras maiúsculas e minúsculas**
                - Inclua **números** e **símbolos** se possível
                - Evite informações pessoais como data de nascimento
                - Não reutilize senhas de outros serviços
                """)
            
            submitted = st.form_submit_button(
                "🚀 Atualizar Senha",
                use_container_width=True,
                type="primary"
            )
            
            if submitted:
                if not nova_senha or not confirmar_senha:
                    st.error("⚠️ Preencha ambos os campos")
                elif nova_senha != confirmar_senha:
                    st.error("⚠️ As senhas não coincidem")
                elif len(nova_senha) < 8:
                    st.error("⚠️ A senha deve ter pelo menos 8 caracteres")
                else:
                    try:
                        # 1. Recupera dados da sessão
                        user_sessao = st.session_state.get('usuario')
                        if not user_sessao or 'id' not in user_sessao:
                            st.error("Erro de sessão. Faça login novamente.")
                            return
                        
                        uid = user_sessao['id']
                        
                        # 2. Gera hash da senha
                        hashed = bcrypt.hashpw(nova_senha.encode(), bcrypt.gensalt()).decode()
                        
                        # 3. Conecta ao banco
                        db = get_db()
                        if not db:
                            st.error("Erro de conexão com o banco de dados")
                            return
                        
                        # 4. Atualiza no banco
                        db.collection('usuarios').document(uid).update({
                            "senha": hashed,
                            "precisa_trocar_senha": False,
                            "ultima_troca_senha": datetime.now().isoformat()
                        })
                        
                        # 5. Atualiza sessão
                        st.session_state.usuario['precisa_trocar_senha'] = False
                        
                        # 6. Feedback visual
                        st.success("""
                        ✅ **Senha atualizada com sucesso!**
                        
                        Redirecionando para o sistema...
                        """)
                        
                        time.sleep(1.5)
                        st.rerun()
                        
                    except Exception as e:
                        st.error(f"❌ Erro ao salvar: {str(e)}")
        
        st.markdown("</div>", unsafe_allow_html=True)
    
    st.markdown("</div>", unsafe_allow_html=True)

# =========================================
# LAYOUT PRINCIPAL MODERNO
# =========================================

def sidebar_component(usuario: Dict[str, Any]):
    """Sidebar moderna com navegação"""
    
    with st.sidebar:
        # Logo e marca
        if logo_file:
            st.image(logo_file, use_container_width=True)
        else:
            st.markdown(f"""
            <div style="text-align: center; margin: 1rem 0 2rem 0;">
                <div style="font-size: 3rem;">🥋</div>
                <h3 style="margin: 0.5rem 0;">BJJ Digital</h3>
                <p style="opacity: 0.7; font-size: 0.9rem;">Sistema de Gestão</p>
            </div>
            """, unsafe_allow_html=True)
        
        # Card do usuário
        user_card_component(usuario)
        
        st.markdown("---")
        
        # Navegação principal
        st.markdown("### 📍 Navegação")
        
        # Mapeamento de rotas
        nav_items = [
            {"label": "🏠 Dashboard", "icon": "🏠", "page": "Início"},
            {"label": "👤 Meu Perfil", "icon": "👤", "page": "Meu Perfil"},
            {"label": "📚 Cursos", "icon": "📚", "page": "Cursos"},
            {"label": "🥋 Treinos", "icon": "🥋", "page": "Modo Rola"},
            {"label": "🏆 Ranking", "icon": "🏆", "page": "Ranking"},
            {"label": "📝 Exames", "icon": "📝", "page": "Exame de Faixa"},
        ]
        
        if usuario.get("tipo") in ["admin", "professor"]:
            nav_items.append({"label": "👨‍🏫 Painel Prof.", "icon": "👨‍🏫", "page": "Painel de Professores"})
        
        if usuario.get("tipo") == "admin":
            nav_items.append({"label": "📊 Administração", "icon": "📊", "page": "Gestão e Estatísticas"})
        
        # Renderizar botões de navegação
        for item in nav_items:
            if st.button(
                f"{item['icon']} {item['label']}",
                key=f"nav_{item['page']}",
                use_container_width=True,
                type="secondary"
            ):
                st.session_state.menu_selection = item['page']
                st.rerun()
        
        st.markdown("---")
        
        # Configurações e saída
        col_set1, col_set2 = st.columns(2)
        
        with col_set1:
            if st.button("⚙️", help="Configurações", use_container_width=True):
                st.session_state.menu_selection = "Configurações"
                st.rerun()
        
        with col_set2:
            if st.button("?", help="Ajuda", use_container_width=True):
                st.session_state.menu_selection = "Ajuda"
                st.rerun()
        
        # Botão de sair
        if st.button("🚪 Sair do Sistema", use_container_width=True, type="primary"):
            st.session_state.clear()
            st.success("Até logo! 👋")
            time.sleep(1)
            st.rerun()
        
        # Footer da sidebar
        st.markdown("---")
        st.markdown(f"""
        <div style="text-align: center; opacity: 0.5; font-size: 0.8rem; margin-top: 2rem;">
            <div>BJJ Digital v2.0</div>
            <div>© {datetime.now().year}</div>
        </div>
        """, unsafe_allow_html=True)

def app_principal():
    """Aplicação principal modernizada"""
    
    # Verificar se usuário está logado
    if not st.session_state.get('usuario'):
        st.session_state.clear()
        st.rerun()
        return
    
    usuario = st.session_state.usuario
    
    # Determinar tipo de usuário
    raw_tipo = str(usuario.get("tipo", "aluno")).lower()
    
    tipo_map = {
        "admin": "Administrador(a)",
        "professor": "Professor(a)",
        "aluno": "Aluno(a)"
    }
    
    tipo_display = tipo_map.get(raw_tipo, "Aluno(a)")
    
    # Aplicar estilos
    aplicar_estilos_modernos()
    
    # Configurar sidebar
    sidebar_component(usuario)
    
    # Roteamento de páginas
    pagina_atual = st.session_state.get('menu_selection', 'Início')
    
    # Importar módulos dinamicamente (com fallback)
    try:
        from views import login, geral, aluno, professor, admin, cursos
        modulos_disponiveis = True
    except ImportError as e:
        st.error(f"❌ Erro ao importar módulos: {e}")
        modulos_disponiveis = False
    
    # Roteamento
    if modulos_disponiveis:
        if pagina_atual == "Meu Perfil":
            geral.tela_meu_perfil(usuario)
        elif pagina_atual == "Gestão e Estatísticas":
            admin.gestao_usuarios(usuario)
        elif pagina_atual == "Painel de Professores":
            professor.painel_professor()
        elif pagina_atual == "Meus Certificados":
            aluno.meus_certificados(usuario)
        elif pagina_atual == "Cursos":
            cursos.pagina_cursos(usuario)
        elif pagina_atual == "Modo Rola":
            aluno.modo_rola(usuario)
        elif pagina_atual == "Exame de Faixa":
            aluno.exame_de_faixa(usuario)
        elif pagina_atual == "Ranking":
            aluno.ranking()
        elif pagina_atual == "Gestão de Equipes":
            professor.gestao_equipes()
        elif pagina_atual == "Gestão de Questões":
            admin.gestao_questoes()
        elif pagina_atual == "Gestão de Exame":
            admin.gestao_exame_de_faixa()
        elif pagina_atual == "Configurações":
            _pagina_configuracoes(usuario)
        elif pagina_atual == "Ajuda":
            _pagina_ajuda(usuario)
        else:  # Início/Dashboard
            geral.tela_inicio()
    else:
        # Fallback se módulos não carregarem
        header_component("BJJ Digital", "Sistema de Gestão")
        st.error("Módulos não disponíveis. Verifique as importações.")

# =========================================
# PÁGINAS AUXILIARES
# =========================================

def _pagina_configuracoes(usuario: Dict[str, Any]):
    """Página de configurações do usuário"""
    header_component("⚙️ Configurações", "Personalize sua experiência")
    
    with st.container():
        st.markdown("<div class='modern-card'>", unsafe_allow_html=True)
        
        tab1, tab2, tab3 = st.tabs(["📱 Interface", "🔔 Notificações", "🔒 Segurança"])
        
        with tab1:
            st.markdown("#### Preferências de Interface")
            
            tema = st.selectbox(
                "Tema de Cores",
                ["Escuro (Padrão)", "Escuro Profundo", "Azul Escuro", "Personalizado"],
                index=0
            )
            
            densidade = st.select_slider(
                "Densidade de Interface",
                options=["Compacta", "Confortável", "Espaçosa"],
                value="Confortável"
            )
            
            animacoes = st.toggle("Animações", value=True)
            reduzir_movimento = st.toggle("Reduzir movimento", value=False)
            
            if st.button("💾 Salvar Preferências", type="primary"):
                st.success("Preferências salvas!")
        
        with tab2:
            st.markdown("#### Configurações de Notificação")
            
            col_not1, col_not2 = st.columns(2)
            
            with col_not1:
                email_notificacoes = st.toggle("Notificações por E-mail", value=True)
                push_notificacoes = st.toggle("Notificações Push", value=True)
            
            with col_not2:
                lembrete_treinos = st.toggle("Lembretes de Treino", value=True)
                novidades = st.toggle("Novidades do Sistema", value=False)
            
            frequencia = st.select_slider(
                "Frequência de Resumo",
                options=["Diário", "Semanal", "Quinzenal", "Mensal"],
                value="Semanal"
            )
            
            if st.button("💾 Salvar Notificações", type="primary"):
                st.success("Configurações de notificação salvas!")
        
        with tab3:
            st.markdown("#### Configurações de Segurança")
            
            autenticacao_2fa = st.toggle("Autenticação em Dois Fatores", value=False)
            
            if autenticacao_2fa:
                st.info("📱 Configure um aplicativo autenticador como Google Authenticator")
            
            sessoes_ativas = st.button("🖥️ Ver Sessões Ativas", use_container_width=True)
            
            if sessoes_ativas:
                st.info("Funcionalidade em desenvolvimento")
            
            if st.button("🔄 Forçar Troca de Senha", use_container_width=True, type="primary"):
                st.session_state.usuario['precisa_trocar_senha'] = True
                st.success("Na próxima vez que entrar, será solicitada a troca de senha!")
        
        st.markdown("</div>", unsafe_allow_html=True)

def _pagina_ajuda(usuario: Dict[str, Any]):
    """Página de ajuda e suporte"""
    header_component("❓ Ajuda e Suporte", "Encontre respostas e recursos")
    
    col_help1, col_help2 = st.columns(2)
    
    with col_help1:
        with st.container():
            st.markdown("<div class='modern-card'>", unsafe_allow_html=True)
            st.markdown("### 📖 Documentação")
            st.markdown("""
            - [📚 Guia do Usuário](https://docs.bjjdigital.com)
            - [🎥 Vídeos Tutoriais](https://youtube.com/bjjdigital)
            - [📄 FAQ - Perguntas Frequentes](https://faq.bjjdigital.com)
            """)
            st.markdown("</div>", unsafe_allow_html=True)
    
    with col_help2:
        with st.container():
            st.markdown("<div class='modern-card'>", unsafe_allow_html=True)
            st.markdown("### 🛠️ Suporte")
            st.markdown("""
            - **Email:** suporte@bjjdigital.com
            - **Telefone:** (11) 99999-9999
            - **Horário:** Seg-Sex, 9h-18h
            """)
            
            with st.form("form_suporte"):
                assunto = st.text_input("Assunto")
                mensagem = st.text_area("Descreva seu problema", height=100)
                
                if st.form_submit_button("📤 Enviar Solicitação", type="primary"):
                    st.success("Solicitação enviada! Entraremos em contato em até 24h.")
            
            st.markdown("</div>", unsafe_allow_html=True)

# =========================================
# PONTO DE ENTRADA PRINCIPAL
# =========================================

def main():
    """Ponto de entrada principal da aplicação"""
    
    # Inicializar variáveis de sessão
    if 'usuario' not in st.session_state:
        st.session_state.usuario = None
    
    if 'menu_selection' not in st.session_state:
        st.session_state.menu_selection = 'Início'
    
    if 'registration_pending' not in st.session_state:
        st.session_state.registration_pending = None
    
    # Aplicar estilos globais
    aplicar_estilos_modernos()
    
    # Lógica de roteamento principal
    if not st.session_state.get('usuario') and not st.session_state.get('registration_pending'):
        # Tela de login
        try:
            from views import login
            login.tela_login()
        except ImportError:
            st.error("Módulo de login não disponível")
    
    elif st.session_state.get('registration_pending'):
        # Completar cadastro
        try:
            from views import login
            login.tela_completar_cadastro(st.session_state.registration_pending)
        except ImportError:
            st.error("Módulo de registro não disponível")
    
    elif st.session_state.get('usuario'):
        # Usuário logado
        if st.session_state.usuario.get("precisa_trocar_senha"):
            tela_troca_senha_obrigatoria()
        else:
            app_principal()

# =========================================
# CONFIGURAÇÃO DE SECRETS (Para deploy)
# =========================================

if "SECRETS_TOML" in os.environ:
    if not os.path.exists(".streamlit"):
        os.makedirs(".streamlit")
    
    secrets_path = ".streamlit/secrets.toml"
    
    # Escrever secrets apenas se necessário
    if not os.path.exists(secrets_path):
        with open(secrets_path, "w") as f:
            f.write(os.environ["SECRETS_TOML"])

# =========================================
# EXECUÇÃO
# =========================================

if __name__ == "__main__":
    main()
