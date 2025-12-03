import streamlit as st
import firebase_admin
from firebase_admin import credentials, firestore
import json
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime

# Configuração da página com design moderno
st.set_page_config(
    page_title="BJJ Digital Dashboard",
    page_icon="🥋",
    layout="wide",
    initial_sidebar_state="expanded"
)

# CSS personalizado para modernização
st.markdown("""
<style>
    /* Estilos principais */
    .main-header {
        font-size: 2.8rem;
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        font-weight: 800;
        margin-bottom: 0.5rem;
    }
    
    .sub-header {
        color: #666;
        font-size: 1.1rem;
        margin-bottom: 2rem;
    }
    
    /* Cards modernos */
    .metric-card {
        background: white;
        border-radius: 16px;
        padding: 1.5rem;
        box-shadow: 0 4px 20px rgba(0, 0, 0, 0.08);
        border: 1px solid #e0e0e0;
        transition: transform 0.3s ease;
    }
    
    .metric-card:hover {
        transform: translateY(-5px);
        box-shadow: 0 8px 30px rgba(0, 0, 0, 0.12);
    }
    
    .metric-value {
        font-size: 2.5rem;
        font-weight: 700;
        color: #333;
        margin: 0.5rem 0;
    }
    
    .metric-label {
        font-size: 0.9rem;
        color: #666;
        text-transform: uppercase;
        letter-spacing: 0.5px;
    }
    
    /* Botões modernos */
    .stButton > button {
        border-radius: 12px;
        padding: 0.5rem 1.5rem;
        font-weight: 600;
        transition: all 0.3s ease;
        border: none;
    }
    
    .stButton > button:hover {
        transform: translateY(-2px);
        box-shadow: 0 5px 15px rgba(0, 0, 0, 0.1);
    }
    
    /* Sidebar estilizada */
    [data-testid="stSidebar"] {
        background: linear-gradient(135deg, #f5f7fa 0%, #c3cfe2 100%);
    }
    
    /* Tabelas modernas */
    .dataframe {
        border-radius: 12px;
        overflow: hidden;
        box-shadow: 0 4px 20px rgba(0, 0, 0, 0.08);
    }
    
    /* Badges */
    .badge {
        display: inline-block;
        padding: 0.25rem 0.75rem;
        border-radius: 20px;
        font-size: 0.85rem;
        font-weight: 600;
        margin: 0.2rem;
    }
    
    .badge-success {
        background: linear-gradient(135deg, #34d399 0%, #059669 100%);
        color: white;
    }
    
    .badge-warning {
        background: linear-gradient(135deg, #fbbf24 0%, #f59e0b 100%);
        color: white;
    }
    
    .badge-danger {
        background: linear-gradient(135deg, #f87171 0%, #dc2626 100%);
        color: white;
    }
    
    /* Separador moderno */
    .stSeparator {
        background: linear-gradient(to right, transparent, #667eea, transparent);
        height: 2px;
        margin: 2rem 0;
    }
    
    /* Avatar/BJJ icon */
    .avatar {
        width: 50px;
        height: 50px;
        border-radius: 50%;
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        display: flex;
        align-items: center;
        justify-content: center;
        color: white;
        font-size: 1.5rem;
        margin: 0 auto;
    }
</style>
""", unsafe_allow_html=True)

def get_db():
    """
    Conexão ESTRITA com o banco 'bjj-digital'.
    Corrigido para usar o parâmetro 'database_id'.
    """
    # 1. Inicializa o App (se ainda não estiver rodando)
    if not firebase_admin._apps:
        try:
            key_dict = None
            
            # Procura as credenciais
            if "firebase" in st.secrets:
                key_dict = dict(st.secrets["firebase"])
            elif "textkey" in st.secrets:
                if isinstance(st.secrets["textkey"], str):
                    key_dict = json.loads(st.secrets["textkey"])
                else:
                    key_dict = dict(st.secrets["textkey"])
            elif "project_id" in st.secrets:
                key_dict = dict(st.secrets)

            if key_dict is None:
                st.error("❌ Credenciais não encontradas no secrets.toml")
                st.stop()

            cred = credentials.Certificate(key_dict)
            firebase_admin.initialize_app(cred)

        except Exception as e:
            st.error(f"❌ Erro ao iniciar Firebase App: {e}")
            st.stop()

    # 2. Conecta ESPECIFICAMENTE ao banco 'bjj-digital'
    try:
        # CORREÇÃO AQUI: Mudamos de 'database' para 'database_id'
        db = firestore.client(database_id='bjj-digital')
        return db
    except TypeError:
        # Fallback: Se a biblioteca for muito antiga e não aceitar parâmetros
        return firestore.client()
    except Exception as e:
        st.error(f"❌ Não foi possível conectar ao banco 'bjj-digital'. Erro: {e}")
        st.stop()

# ========== COMPONENTES VISUAIS MODERNOS ==========

def create_metric_card(title, value, icon="📊", change=None):
    """Cria um card de métrica moderno"""
    col1, col2 = st.columns([1, 3])
    with col1:
        st.markdown(f'<div class="avatar">{icon}</div>', unsafe_allow_html=True)
    with col2:
        st.markdown(f'<div class="metric-label">{title}</div>', unsafe_allow_html=True)
        st.markdown(f'<div class="metric-value">{value}</div>', unsafe_allow_html=True)
        if change:
            arrow = "↗️" if change > 0 else "↘️"
            color = "#34d399" if change > 0 else "#f87171"
            st.markdown(f'<div style="color: {color}; font-size: 0.9rem;">{arrow} {abs(change)}% desde o último mês</div>', unsafe_allow_html=True)

def create_stats_section():
    """Seção de estatísticas principais"""
    st.markdown('<div class="main-header">🥋 BJJ Digital Dashboard</div>', unsafe_allow_html=True)
    st.markdown('<div class="sub-header">Monitoramento em tempo real • Análise de desempenho • Gestão inteligente</div>', unsafe_allow_html=True)
    
    # Cards de métricas
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        with st.container():
            st.markdown('<div class="metric-card">', unsafe_allow_html=True)
            create_metric_card("Alunos Ativos", "142", "👤", 5.2)
            st.markdown('</div>', unsafe_allow_html=True)
    
    with col2:
        with st.container():
            st.markdown('<div class="metric-card">', unsafe_allow_html=True)
            create_metric_card("Aulas Hoje", "8", "🥋", 12.5)
            st.markdown('</div>', unsafe_allow_html=True)
    
    with col3:
        with st.container():
            st.markdown('<div class="metric-card">', unsafe_allow_html=True)
            create_metric_card("Faturamento", "R$ 12.5K", "💰", 8.3)
            st.markdown('</div>', unsafe_allow_html=True)
    
    with col4:
        with st.container():
            st.markdown('<div class="metric-card">', unsafe_allow_html=True)
            create_metric_card("Novos Alunos", "7", "⭐", 16.7)
            st.markdown('</div>', unsafe_allow_html=True)

def create_charts_section():
    """Seção de gráficos modernos"""
    st.markdown("## 📈 Análise de Desempenho")
    
    col1, col2 = st.columns(2)
    
    with col1:
        # Gráfico de linhas
        st.markdown("### Frequência Mensal")
        data = {
            'Mês': ['Jan', 'Fev', 'Mar', 'Abr', 'Mai', 'Jun'],
            'Frequência': [120, 135, 148, 142, 155, 168],
            'Meta': [130, 130, 130, 130, 130, 130]
        }
        df = pd.DataFrame(data)
        
        fig = go.Figure()
        fig.add_trace(go.Scatter(
            x=df['Mês'], 
            y=df['Frequência'],
            mode='lines+markers',
            name='Frequência Real',
            line=dict(color='#667eea', width=3),
            marker=dict(size=8)
        ))
        fig.add_trace(go.Scatter(
            x=df['Mês'], 
            y=df['Meta'],
            mode='lines',
            name='Meta',
            line=dict(color='#f87171', width=2, dash='dash')
        ))
        fig.update_layout(
            plot_bgcolor='white',
            paper_bgcolor='white',
            height=300,
            margin=dict(l=20, r=20, t=30, b=20)
        )
        st.plotly_chart(fig, use_container_width=True)
    
    with col2:
        # Gráfico de pizza
        st.markdown("### Distribuição de Faixas")
        data = {
            'Faixa': ['Branca', 'Azul', 'Roxa', 'Marrom', 'Preta'],
            'Quantidade': [45, 38, 28, 18, 13]
        }
        df = pd.DataFrame(data)
        
        fig = px.pie(
            df, 
            values='Quantidade', 
            names='Faixa',
            color_discrete_sequence=px.colors.sequential.RdBu,
            hole=0.4
        )
        fig.update_traces(
            textposition='inside',
            textinfo='percent+label',
            marker=dict(line=dict(color='white', width=2))
        )
        fig.update_layout(
            plot_bgcolor='white',
            paper_bgcolor='white',
            height=300,
            margin=dict(l=20, r=20, t=30, b=20),
            showlegend=False
        )
        st.plotly_chart(fig, use_container_width=True)

def create_data_table():
    """Tabela de dados moderna"""
    st.markdown("## 📋 Alunos Recentes")
    
    # Dados de exemplo
    data = {
        'Nome': ['Carlos Silva', 'Ana Santos', 'Pedro Costa', 'Mariana Lima', 'João Oliveira'],
        'Faixa': ['Azul', 'Branca', 'Roxa', 'Azul', 'Branca'],
        'Matrícula': ['2023-001', '2023-002', '2023-003', '2023-004', '2023-005'],
        'Status': ['Ativo', 'Ativo', 'Ativo', 'Inativo', 'Ativo'],
        'Última Aula': ['2024-01-15', '2024-01-14', '2024-01-13', '2024-01-10', '2024-01-12']
    }
    
    df = pd.DataFrame(data)
    
    # Adiciona badges coloridos
    def format_status(status):
        if status == 'Ativo':
            return '<span class="badge badge-success">Ativo</span>'
        else:
            return '<span class="badge badge-danger">Inativo</span>'
    
    df['Status'] = df['Status'].apply(format_status)
    
    # Exibe a tabela
    st.markdown(df.to_html(escape=False, index=False), unsafe_allow_html=True)

def create_sidebar():
    """Sidebar moderna"""
    with st.sidebar:
        st.markdown("""
            <div style="text-align: center; padding: 1rem 0;">
                <div class="avatar">🥋</div>
                <h3>BJJ Digital</h3>
                <p style="color: #666; font-size: 0.9rem;">Sistema de Gestão</p>
            </div>
        """, unsafe_allow_html=True)
        
        st.markdown("---")
        
        # Menu de navegação
        st.markdown("### 📌 Navegação")
        menu_options = ["Dashboard", "Alunos", "Financeiro", "Aulas", "Relatórios", "Configurações"]
        selected = st.selectbox("Selecione uma página", menu_options)
        
        st.markdown("---")
        
        # Filtros
        st.markdown("### 🔍 Filtros")
        periodo = st.selectbox("Período", ["Hoje", "Últimos 7 dias", "Este mês", "Este ano"])
        faixa = st.multiselect("Faixa", ["Todas", "Branca", "Azul", "Roxa", "Marrom", "Preta"])
        
        st.markdown("---")
        
        # Status do sistema
        st.markdown("### 📊 Status do Sistema")
        col1, col2 = st.columns(2)
        with col1:
            st.metric("DB Status", "✅", "Online")
        with col2:
            st.metric("Uptime", "99.8%")
        
        st.markdown("---")
        
        # Botão de ação
        if st.button("🔄 Atualizar Dados", type="primary", use_container_width=True):
            st.rerun()

# ========== APLICAÇÃO PRINCIPAL ==========

def main():
    # Sidebar
    create_sidebar()
    
    # Conteúdo principal
    create_stats_section()
    
    st.markdown('<div class="stSeparator"></div>', unsafe_allow_html=True)
    
    create_charts_section()
    
    st.markdown('<div class="stSeparator"></div>', unsafe_allow_html=True)
    
    create_data_table()
    
    # Footer
    st.markdown("---")
    col1, col2, col3 = st.columns(3)
    with col2:
        st.markdown("""
            <div style="text-align: center; color: #666; font-size: 0.9rem; padding: 1rem;">
                🥋 BJJ Digital Dashboard • v2.0 • {date}
            </div>
        """.format(date=datetime.now().strftime("%d/%m/%Y")), unsafe_allow_html=True)

if __name__ == "__main__":
    main()
