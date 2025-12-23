"""
BJJ Digital - Componentes Visuais Modernos
Componentes reutilizáveis com design atualizado
"""

import streamlit as st
from config import COR_DESTAQUE, COR_TEXTO, COR_FUNDO, COR_BOTAO, COR_HOVER

# =========================================
# ESTILOS GLOBAIS MODERNOS
# =========================================
def aplicar_estilos_modernos():
    """Aplica estilos CSS modernos ao BJJ Digital"""
    st.markdown(f"""
    <style>
    /* ===== TYPOGRAPHY & SPACING ===== */
    h1, h2, h3, h4, h5, h6 {{
        font-family: 'Poppins', sans-serif;
        font-weight: 700;
        color: {COR_DESTAQUE} !important;
        margin-bottom: 1rem;
    }}
    
    h1 {{ font-size: 2.5rem; letter-spacing: -0.5px; }}
    h2 {{ font-size: 2rem; }}
    h3 {{ font-size: 1.75rem; }}
    
    /* ===== CONTAINERS & CARDS ===== */
    .modern-card {{
        background: linear-gradient(135deg, rgba(14, 45, 38, 0.8) 0%, rgba(9, 31, 26, 0.9) 100%);
        border: 1px solid rgba(255, 215, 112, 0.2);
        border-radius: 16px;
        padding: 1.5rem;
        margin-bottom: 1rem;
        transition: all 0.3s ease;
        backdrop-filter: blur(10px);
        box-shadow: 0 8px 32px rgba(0, 0, 0, 0.3);
    }}
    
    .modern-card:hover {{
        border-color: {COR_DESTAQUE};
        transform: translateY(-4px);
        box-shadow: 0 12px 40px rgba(255, 215, 112, 0.15);
    }}
    
    /* ===== BADGES ===== */
    .badge {{
        display: inline-block;
        padding: 0.25rem 0.75rem;
        border-radius: 20px;
        font-size: 0.75rem;
        font-weight: 600;
        text-transform: uppercase;
        letter-spacing: 0.5px;
        margin-right: 0.5rem;
        margin-bottom: 0.5rem;
    }}
    
    .badge-primary {{
        background: linear-gradient(135deg, {COR_BOTAO} 0%, #056853 100%);
        color: white;
    }}
    
    .badge-success {{
        background: linear-gradient(135deg, #10B981 0%, #059669 100%);
        color: white;
    }}
    
    .badge-warning {{
        background: linear-gradient(135deg, #F59E0B 0%, #D97706 100%);
        color: white;
    }}
    
    .badge-info {{
        background: linear-gradient(135deg, #3B82F6 0%, #1D4ED8 100%);
        color: white;
    }}
    
    .badge-gold {{
        background: linear-gradient(135deg, {COR_DESTAQUE} 0%, #D4AF37 100%);
        color: #0e2d26;
        font-weight: 700;
    }}
    
    /* ===== PROGRESS BARS ===== */
    .progress-container {{
        background: rgba(255, 255, 255, 0.05);
        border-radius: 10px;
        height: 12px;
        overflow: hidden;
        margin: 0.5rem 0;
    }}
    
    .progress-fill {{
        height: 100%;
        background: linear-gradient(90deg, {COR_BOTAO} 0%, {COR_DESTAQUE} 100%);
        border-radius: 10px;
        transition: width 0.5s ease;
    }}
    
    /* ===== BUTTONS ===== */
    .btn-modern {{
        background: linear-gradient(135deg, {COR_BOTAO} 0%, #056853 100%) !important;
        color: white !important;
        border: none !important;
        border-radius: 12px !important;
        padding: 0.75rem 1.5rem !important;
        font-weight: 600 !important;
        transition: all 0.3s ease !important;
        box-shadow: 0 4px 15px rgba(7, 139, 108, 0.3) !important;
    }}
    
    .btn-modern:hover {{
        background: linear-gradient(135deg, {COR_HOVER} 0%, #E6B91E 100%) !important;
        transform: translateY(-2px) !important;
        box-shadow: 0 8px 25px rgba(255, 215, 112, 0.4) !important;
        color: #0e2d26 !important;
    }}
    
    .btn-outline-gold {{
        background: transparent !important;
        color: {COR_DESTAQUE} !important;
        border: 2px solid {COR_DESTAQUE} !important;
        border-radius: 12px !important;
        padding: 0.75rem 1.5rem !important;
        font-weight: 600 !important;
        transition: all 0.3s ease !important;
    }}
    
    .btn-outline-gold:hover {{
        background: {COR_DESTAQUE} !important;
        color: #0e2d26 !important;
        transform: translateY(-2px);
    }}
    
    /* ===== AVATARS ===== */
    .avatar {{
        width: 48px;
        height: 48px;
        border-radius: 50%;
        background: linear-gradient(135deg, {COR_BOTAO} 0%, {COR_DESTAQUE} 100%);
        display: flex;
        align-items: center;
        justify-content: center;
        color: white;
        font-weight: bold;
        font-size: 1.25rem;
    }}
    
    /* ===== COURSE CARD ===== */
    .course-card {{
        background: linear-gradient(135deg, rgba(14, 45, 38, 0.9) 0%, rgba(9, 31, 26, 0.95) 100%);
        border: 1px solid rgba(255, 215, 112, 0.15);
        border-radius: 20px;
        padding: 1.5rem;
        transition: all 0.3s ease;
        height: 100%;
        display: flex;
        flex-direction: column;
    }}
    
    .course-card:hover {{
        border-color: {COR_DESTAQUE};
        transform: translateY(-6px);
        box-shadow: 0 20px 60px rgba(0, 0, 0, 0.4);
    }}
    
    .course-card-header {{
        display: flex;
        justify-content: space-between;
        align-items: start;
        margin-bottom: 1rem;
    }}
    
    .course-card-icon {{
        font-size: 2.5rem;
        margin-bottom: 1rem;
        text-align: center;
    }}
    
    /* ===== STATS CARDS ===== */
    .stats-card {{
        background: rgba(255, 255, 255, 0.03);
        border: 1px solid rgba(255, 255, 255, 0.05);
        border-radius: 16px;
        padding: 1.5rem;
        text-align: center;
        transition: all 0.3s ease;
    }}
    
    .stats-card:hover {{
        background: rgba(255, 255, 255, 0.05);
        border-color: {COR_DESTAQUE};
    }}
    
    .stats-value {{
        font-size: 2.5rem;
        font-weight: 700;
        background: linear-gradient(135deg, {COR_DESTAQUE} 0%, #FFFFFF 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        margin: 0.5rem 0;
    }}
    
    .stats-label {{
        color: rgba(255, 255, 255, 0.7);
        font-size: 0.9rem;
        text-transform: uppercase;
        letter-spacing: 1px;
    }}
    
    /* ===== LESSON CARD ===== */
    .lesson-card {{
        background: rgba(255, 255, 255, 0.02);
        border: 1px solid rgba(255, 255, 255, 0.08);
        border-radius: 14px;
        padding: 1.25rem;
        margin-bottom: 1rem;
        transition: all 0.3s ease;
        display: flex;
        align-items: center;
        gap: 1rem;
    }}
    
    .lesson-card.completed {{
        border-color: {COR_BOTAO};
        background: rgba(7, 139, 108, 0.1);
    }}
    
    .lesson-card.current {{
        border-color: {COR_DESTAQUE};
        background: rgba(255, 215, 112, 0.1);
        box-shadow: 0 0 20px rgba(255, 215, 112, 0.1);
    }}
    
    .lesson-card:hover {{
        border-color: {COR_DESTAQUE};
        transform: translateX(5px);
    }}
    
    .lesson-number {{
        width: 40px;
        height: 40px;
        border-radius: 50%;
        background: linear-gradient(135deg, {COR_BOTAO} 0%, #056853 100%);
        display: flex;
        align-items: center;
        justify-content: center;
        color: white;
        font-weight: bold;
        flex-shrink: 0;
    }}
    
    .lesson-card.completed .lesson-number {{
        background: linear-gradient(135deg, #10B981 0%, #059669 100%);
    }}
    
    .lesson-card.current .lesson-number {{
        background: linear-gradient(135deg, {COR_DESTAQUE} 0%, #D4AF37 100%);
        color: #0e2d26;
    }}
    
    /* ===== RESPONSIVE ===== */
    @media (max-width: 768px) {{
        .course-card {{
            margin-bottom: 1rem;
        }}
        
        .stats-card {{
            margin-bottom: 1rem;
        }}
    }}
    
    </style>
    """, unsafe_allow_html=True)

# =========================================
# COMPONENTES REUTILIZÁVEIS
# =========================================

def badge(texto, tipo="primary"):
    """Renderiza um badge colorido"""
    tipo_classes = {
        "primary": "badge-primary",
        "success": "badge-success",
        "warning": "badge-warning",
        "info": "badge-info",
        "gold": "badge-gold"
    }
    classe = tipo_classes.get(tipo, "badge-primary")
    st.markdown(f'<span class="badge {classe}">{texto}</span>', unsafe_allow_html=True)

def progress_bar(percentual, label=None):
    """Barra de progresso moderna"""
    html = f"""
    <div class="progress-container">
        <div class="progress-fill" style="width: {percentual}%"></div>
    </div>
    """
    if label:
        st.markdown(f"<small>{label}: {percentual}%</small>", unsafe_allow_html=True)
    st.markdown(html, unsafe_allow_html=True)

def stats_card(valor, label, icon=None):
    """Card de estatísticas"""
    icon_html = f'<div style="font-size: 2rem; margin-bottom: 0.5rem;">{icon}</div>' if icon else ''
    
    st.markdown(f"""
    <div class="stats-card">
        {icon_html}
        <div class="stats-value">{valor}</div>
        <div class="stats-label">{label}</div>
    </div>
    """, unsafe_allow_html=True)

def course_card(titulo, descricao, icon="📚", badges=None, acao=None, acao_texto="Acessar"):
    """Card de curso moderno"""
    badges_html = ""
    if badges:
        for b in badges:
            badges_html += f'<span class="badge badge-primary">{b}</span>'
    
    acao_html = ""
    if acao:
        acao_html = f"""
        <div style="margin-top: auto; padding-top: 1rem;">
            <button class="btn-modern" onclick="{acao}" style="width: 100%;">{acao_texto}</button>
        </div>
        """
    
    st.markdown(f"""
    <div class="course-card">
        <div class="course-card-icon">{icon}</div>
        <h4 style="margin: 0 0 0.5rem 0;">{titulo}</h4>
        <div style="margin-bottom: 1rem; opacity: 0.8; flex-grow: 1;">{descricao}</div>
        <div style="margin-bottom: 1rem;">{badges_html}</div>
        {acao_html}
    </div>
    """, unsafe_allow_html=True)

def lesson_card(numero, titulo, duracao, concluido=False, atual=False, acao=None):
    """Card de aula/modulo"""
    classe = "lesson-card"
    if concluido:
        classe += " completed"
    if atual:
        classe += " current"
    
    status_icon = "✅" if concluido else "▶️" if atual else "⏳"
    status_text = "Concluído" if concluido else "Em andamento" if atual else "Pendente"
    
    acao_html = ""
    if acao and not concluido:
        acao_html = f"""
        <div style="margin-left: auto;">
            <button class="btn-modern" onclick="{acao}" style="padding: 0.5rem 1rem !important; font-size: 0.9rem !important;">
                {status_icon} {status_text}
            </button>
        </div>
        """
    
    st.markdown(f"""
    <div class="{classe}">
        <div class="lesson-number">{numero}</div>
        <div style="flex-grow: 1;">
            <div style="font-weight: 600; margin-bottom: 0.25rem;">{titulo}</div>
            <div style="font-size: 0.85rem; opacity: 0.7;">{duracao} • {status_text}</div>
        </div>
        {acao_html}
    </div>
    """, unsafe_allow_html=True)

def empty_state(icon, titulo, descricao):
    """Estado vazio estilizado"""
    st.markdown(f"""
    <div style="text-align: center; padding: 4rem 2rem; border-radius: 20px; background: rgba(255,255,255,0.02); border: 2px dashed rgba(255,215,112,0.2);">
        <div style="font-size: 4rem; margin-bottom: 1rem; opacity: 0.5;">{icon}</div>
        <h3 style="color: {COR_DESTAQUE};">{titulo}</h3>
        <p style="opacity: 0.7; max-width: 400px; margin: 0 auto;">{descricao}</p>
    </div>
    """, unsafe_allow_html=True)
