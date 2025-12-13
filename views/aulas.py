"""
BJJ Digital - Sistema de Aulas (Versão Simplificada)
Tela de placeholder enquanto desenvolvemos o sistema completo
"""

import streamlit as st

def pagina_aulas(usuario: dict):
    """Página de aulas (placeholder)"""
    
    st.markdown("""
    <style>
    .feature-card {
        background: linear-gradient(135deg, rgba(14, 45, 38, 0.8) 0%, rgba(9, 31, 26, 0.9) 100%);
        border: 1px solid rgba(255, 215, 112, 0.2);
        border-radius: 16px;
        padding: 1.5rem;
        margin: 1rem 0;
        transition: all 0.3s ease;
    }
    
    .feature-card:hover {
        border-color: #FFD770;
        transform: translateY(-4px);
    }
    
    .feature-icon {
        font-size: 2.5rem;
        margin-bottom: 1rem;
        color: #FFD770;
    }
    </style>
    """, unsafe_allow_html=True)
    
    st.markdown(f"""
    <div style="text-align: center; margin-bottom: 3rem;">
        <h1 style="color: #FFD770;">🎬 Sistema de Aulas</h1>
        <p style="opacity: 0.8;">Em desenvolvimento - Lançamento em breve!</p>
    </div>
    """, unsafe_allow_html=True)
    
    # Botão voltar
    if st.button("← Voltar para Cursos", type="secondary", use_container_width=True):
        if 'curso_atual' in st.session_state:
            del st.session_state.curso_atual
        st.rerun()
    
    st.markdown("<br>", unsafe_allow_html=True)
    
    # Cards de features
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.markdown("""
        <div class="feature-card">
            <div class="feature-icon">🎥</div>
            <h3>Aulas em Vídeo</h3>
            <p style="opacity: 0.8;">Conteúdo exclusivo em alta qualidade com demonstrações técnicas detalhadas.</p>
        </div>
        """, unsafe_allow_html=True)
    
    with col2:
        st.markdown("""
        <div class="feature-card">
            <div class="feature-icon">📖</div>
            <h3>Material Didático</h3>
            <p style="opacity: 0.8;">PDFs, e-books e infográficos para estudo aprofundado das técnicas.</p>
        </div>
        """, unsafe_allow_html=True)
    
    with col3:
        st.markdown("""
        <div class="feature-card">
            <div class="feature-icon">❓</div>
            <h3>Quizzes Interativos</h3>
            <p style="opacity: 0.8;">Teste seu conhecimento com questões sobre cada aula.</p>
        </div>
        """, unsafe_allow_html=True)
    
    # Mais features
    col4, col5, col6 = st.columns(3)
    
    with col4:
        st.markdown("""
        <div class="feature-card">
            <div class="feature-icon">📊</div>
            <h3>Acompanhamento de Progresso</h3>
            <p style="opacity: 0.8;">Veja seu desenvolvimento e receba feedback personalizado.</p>
        </div>
        """, unsafe_allow_html=True)
    
    with col5:
        st.markdown("""
        <div class="feature-card">
            <div class="feature-icon">🏆</div>
            <h3>Certificação</h3>
            <p style="opacity: 0.8;">Receba certificados ao concluir módulos e cursos completos.</p>
        </div>
        """, unsafe_allow_html=True)
    
    with col6:
        st.markdown("""
        <div class="feature-card">
            <div class="feature-icon">💬</div>
            <h3>Comunidade</h3>
            <p style="opacity: 0.8;">Interaja com outros alunos e tire dúvidas com instrutores.</p>
        </div>
        """, unsafe_allow_html=True)
    
    # Informações sobre desenvolvimento
    st.markdown("---")
    
    st.markdown("""
    <div style="background: rgba(255,215,112,0.1); padding: 2rem; border-radius: 16px; margin-top: 2rem;">
        <h3 style="color: #FFD770; margin-top: 0;">🚀 Em Desenvolvimento Ativo</h3>
        
        <p>Estamos trabalhando duro para trazer a melhor experiência de aprendizado de Jiu-Jitsu online.</p>
        
        <h4>📅 Próximas Funcionalidades:</h4>
        <ul>
            <li><strong>Fevereiro 2024:</strong> Player de vídeo com controles avançados</li>
            <li><strong>Março 2024:</strong> Sistema de progresso e certificação automática</li>
            <li><strong>Abril 2024:</strong> Comunidade e fórum de discussão</li>
            <li><strong>Maio 2024:</strong> Aplicativo mobile nativo</li>
        </ul>
        
        <p><em>Quer sugerir alguma funcionalidade? Entre em contato com nosso time!</em></p>
    </div>
    """, unsafe_allow_html=True)
    
    # Botão de suporte
    if st.button("📞 Falar com Suporte", type="primary", use_container_width=True):
        st.info("Entre em contato: suporte@bjjdigital.com.br")

# Função placeholder para navegação
def navegar_para_aulas(curso_id: str, usuario: dict):
    """Redireciona para a tela de aulas (placeholder)"""
    st.session_state.curso_atual = curso_id
    st.rerun()
