import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime

# CSS moderno para a tabela
st.markdown("""
<style>
    /* Container principal */
    .exams-container {
        background: linear-gradient(135deg, #f5f7fa 0%, #c3cfe2 100%);
        border-radius: 20px;
        padding: 1.5rem;
        margin: 1rem 0;
        box-shadow: 0 8px 32px rgba(0, 0, 0, 0.1);
        border: 1px solid rgba(255, 255, 255, 0.2);
    }
    
    /* Título da seção */
    .section-title {
        font-size: 1.5rem;
        font-weight: 700;
        color: #2d3748;
        margin-bottom: 1.5rem;
        display: flex;
        align-items: center;
        gap: 0.5rem;
    }
    
    /* Badges de status */
    .status-badge {
        padding: 0.25rem 0.75rem;
        border-radius: 20px;
        font-size: 0.75rem;
        font-weight: 600;
        display: inline-flex;
        align-items: center;
        gap: 0.25rem;
    }
    
    .approved {
        background: linear-gradient(135deg, #34d399 0%, #059669 100%);
        color: white;
    }
    
    .rejected {
        background: linear-gradient(135deg, #f87171 0%, #dc2626 100%);
        color: white;
    }
    
    /* Cards dos exames */
    .exam-card {
        background: white;
        border-radius: 16px;
        padding: 1.25rem;
        margin: 0.75rem 0;
        box-shadow: 0 4px 6px rgba(0, 0, 0, 0.05);
        border: 1px solid #e2e8f0;
        transition: all 0.3s ease;
        cursor: pointer;
    }
    
    .exam-card:hover {
        transform: translateY(-3px);
        box-shadow: 0 8px 25px rgba(0, 0, 0, 0.1);
        border-color: #667eea;
    }
    
    /* Cabeçalho do card */
    .exam-header {
        display: flex;
        justify-content: space-between;
        align-items: flex-start;
        margin-bottom: 1rem;
    }
    
    .student-name {
        font-size: 1.1rem;
        font-weight: 700;
        color: #2d3748;
    }
    
    .exam-date {
        font-size: 0.85rem;
        color: #718096;
        background: #f7fafc;
        padding: 0.25rem 0.75rem;
        border-radius: 12px;
    }
    
    /* Corpo do card */
    .exam-details {
        display: flex;
        gap: 1.5rem;
        flex-wrap: wrap;
    }
    
    .detail-item {
        display: flex;
        flex-direction: column;
        gap: 0.25rem;
    }
    
    .detail-label {
        font-size: 0.75rem;
        color: #718096;
        text-transform: uppercase;
        letter-spacing: 0.5px;
    }
    
    .detail-value {
        font-size: 1rem;
        font-weight: 600;
        color: #2d3748;
    }
    
    /* Indicador de faixa */
    .belt-indicator {
        padding: 0.5rem 1rem;
        border-radius: 12px;
        font-weight: 600;
        font-size: 0.85rem;
        text-align: center;
        min-width: 120px;
    }
    
    .belt-white-gray {
        background: linear-gradient(135deg, #f3f4f6 0%, #9ca3af 100%);
        color: #374151;
    }
    
    .belt-black {
        background: linear-gradient(135deg, #1f2937 0%, #111827 100%);
        color: white;
    }
    
    .belt-blue {
        background: linear-gradient(135deg, #3b82f6 0%, #1d4ed8 100%);
        color: white;
    }
    
    .belt-purple {
        background: linear-gradient(135deg, #8b5cf6 0%, #7c3aed 100%);
        color: white;
    }
    
    .belt-brown {
        background: linear-gradient(135deg, #92400e 0%, #78350f 100%);
        color: white;
    }
    
    /* Barra de progresso da nota */
    .grade-progress {
        height: 8px;
        background: #e5e7eb;
        border-radius: 4px;
        overflow: hidden;
        margin-top: 0.5rem;
    }
    
    .grade-fill {
        height: 100%;
        border-radius: 4px;
    }
    
    .grade-100 {
        background: linear-gradient(90deg, #10b981 0%, #059669 100%);
        width: 100%;
    }
    
    .grade-90 {
        background: linear-gradient(90deg, #10b981 0%, #059669 100%);
        width: 90%;
    }
    
    .grade-80 {
        background: linear-gradient(90deg, #f59e0b 0%, #d97706 100%);
        width: 80%;
    }
    
    .grade-70 {
        background: linear-gradient(90deg, #f59e0b 0%, #d97706 100%);
        width: 70%;
    }
    
    /* Visualização em grid */
    .exams-grid {
        display: grid;
        grid-template-columns: repeat(auto-fit, minmax(350px, 1fr));
        gap: 1rem;
        margin-top: 1rem;
    }
    
    /* Botão de ação */
    .action-button {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
        border: none;
        padding: 0.75rem 1.5rem;
        border-radius: 12px;
        font-weight: 600;
        cursor: pointer;
        transition: all 0.3s ease;
        display: inline-flex;
        align-items: center;
        gap: 0.5rem;
        margin-top: 1rem;
    }
    
    .action-button:hover {
        transform: translateY(-2px);
        box-shadow: 0 6px 20px rgba(102, 126, 234, 0.3);
    }
</style>
""", unsafe_allow_html=True)

def create_exam_card(name, belt, grade, approved, date, index):
    """Cria um card individual para cada exame"""
    
    # Mapeia cores de faixa
    belt_colors = {
        "Cinza e Branca": "belt-white-gray",
        "Branca": "belt-white-gray",
        "Azul": "belt-blue",
        "Roxa": "belt-purple",
        "Marrom": "belt-brown",
        "Preta": "belt-black",
    }
    
    belt_class = belt_colors.get(belt, "belt-white-gray")
    
    # Determina classe da nota
    if grade == 100:
        grade_class = "grade-100"
    elif grade >= 90:
        grade_class = "grade-90"
    elif grade >= 80:
        grade_class = "grade-80"
    else:
        grade_class = "grade-70"
    
    status_text = "Aprovado" if approved else "Reprovado"
    status_class = "approved" if approved else "rejected"
    status_icon = "✅" if approved else "❌"
    
    return f"""
    <div class="exam-card">
        <div class="exam-header">
            <div>
                <span class="student-name">{name}</span>
            </div>
            <span class="exam-date">{date}</span>
        </div>
        
        <div class="exam-details">
            <div class="detail-item">
                <span class="detail-label">Faixa</span>
                <div class="belt-indicator {belt_class}">
                    {belt}
                </div>
            </div>
            
            <div class="detail-item">
                <span class="detail-label">Nota Final</span>
                <span class="detail-value">{grade}%</span>
                <div class="grade-progress">
                    <div class="grade-fill {grade_class}"></div>
                </div>
            </div>
            
            <div class="detail-item">
                <span class="detail-label">Status</span>
                <span class="status-badge {status_class}">
                    {status_icon} {status_text}
                </span>
            </div>
        </div>
    </div>
    """

def create_exams_table():
    """Cria a tabela moderna de exames"""
    
    # Dados de exemplo (substitua pelos seus dados reais)
    exams_data = [
        {
            "name": "IRBOSA DE OLIVEIRA",
            "belt": "Cinza e Branca",
            "grade": 100.0,
            "approved": True,
            "date": "30/11/2024"
        },
        {
            "name": "IRBOSA DE OLIVEIRA",
            "belt": "Cinza e Branca",
            "grade": 100.0,
            "approved": True,
            "date": "30/11/2024"
        },
        {
            "name": "IRBOSA DE OLIVEIRA",
            "belt": "Cinza e Branca",
            "grade": 100.0,
            "approved": True,
            "date": "30/11/2024"
        },
        {
            "name": "IREM",
            "belt": "Preta",
            "grade": 100.0,
            "approved": True,
            "date": "28/11/2024"
        },
        {
            "name": "IREM",
            "belt": "Preta",
            "grade": 100.0,
            "approved": True,
            "date": "28/11/2024"
        }
    ]
    
    # Container principal
    st.markdown('<div class="exams-container">', unsafe_allow_html=True)
    
    # Cabeçalho da seção
    st.markdown(
        '<div class="section-title">📋 ÚLTIMOS 5 EXAMES REALIZADOS</div>',
        unsafe_allow_html=True
    )
    
    # Filtros rápidos
    col1, col2, col3, col4 = st.columns([2, 2, 2, 1])
    
    with col1:
        st.selectbox("Filtrar por faixa", ["Todas", "Cinza e Branca", "Preta", "Azul", "Roxa", "Marrom"], key="filter_belt")
    
    with col2:
        st.selectbox("Filtrar por status", ["Todos", "Aprovados", "Reprovados"], key="filter_status")
    
    with col3:
        st.selectbox("Ordenar por", ["Data ↓", "Data ↑", "Nota ↓", "Nota ↑"], key="sort_by")
    
    with col4:
        st.button("🔄", help="Atualizar dados")
    
    # Cards dos exames
    st.markdown('<div class="exams-grid">', unsafe_allow_html=True)
    
    for i, exam in enumerate(exams_data):
        card_html = create_exam_card(
            name=exam["name"],
            belt=exam["belt"],
            grade=exam["grade"],
            approved=exam["approved"],
            date=exam["date"],
            index=i
        )
        st.markdown(card_html, unsafe_allow_html=True)
    
    st.markdown('</div>', unsafe_allow_html=True)
    
    # Estatísticas resumidas
    st.markdown("---")
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.metric("📊 Média de Notas", "100%", "0%")
    
    with col2:
        st.metric("✅ Taxa de Aprovação", "100%", "0%")
    
    with col3:
        st.metric("🥋 Faixa Mais Comum", "Cinza e Branca", "3 exames")
    
    # Botão de ação
    st.markdown(
        """
        <div style="text-align: center; margin-top: 2rem;">
            <button class="action-button" onclick="alert('Ver todos os exames')">
                📊 Ver Todos os Exames
            </button>
        </div>
        """,
        unsafe_allow_html=True
    )
    
    st.markdown('</div>', unsafe_allow_html=True)

def main():
    """Função principal"""
    st.set_page_config(
        page_title="Exames BJJ Digital",
        page_icon="🥋",
        layout="wide"
    )
    
    # Título da página
    st.markdown("""
        <div style="text-align: center; margin-bottom: 2rem;">
            <h1 style="font-size: 2.5rem; color: #2d3748; margin-bottom: 0.5rem;">
                🥋 BJJ Digital - Exames
            </h1>
            <p style="color: #718096; font-size: 1.1rem;">
                Monitoramento de desempenho e aprovação em exames
            </p>
        </div>
    """, unsafe_allow_html=True)
    
    # Criar a tabela moderna
    create_exams_table()
    
    # Sidebar com informações adicionais
    with st.sidebar:
        st.markdown("### 📈 Estatísticas Globais")
        st.metric("Total de Exames", "156")
        st.metric("Aprovação Global", "92%", "3% ↗️")
        st.metric("Exames Este Mês", "24")
        
        st.markdown("---")
        
        st.markdown("### 🎯 Metas")
        st.progress(85, text="Meta de Aprovação: 85% alcançado")
        st.progress(70, text="Exames/Mês: 70% da meta")
        
        st.markdown("---")
        
        st.markdown("### 🔔 Próximos Exames")
        st.info("**15/12** - Exame de Faixa Azul")
        st.info("**18/12** - Exame de Graduação")
        st.info("**20/12** - Exame Especial")

if __name__ == "__main__":
    main()
