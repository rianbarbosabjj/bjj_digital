import streamlit as st
import pandas as pd
import plotly.express as px
from database import get_db

# =========================================
# FUNÇÃO AUXILIAR DE ESTILO (DRY)
# =========================================
def estilizar_grafico(fig):
    """Aplica o tema Dark/Gold do BJJ Digital aos gráficos Plotly."""
    fig.update_layout(
        paper_bgcolor="rgba(0,0,0,0)",  # Fundo transparente
        plot_bgcolor="rgba(0,0,0,0)",   # Área do gráfico transparente
        font={"color": "#FFFFFF", "family": "Poppins, sans-serif"}, # Texto branco
        margin=dict(l=20, r=20, t=40, b=20),
        legend=dict(
            orientation="h", 
            yanchor="bottom", y=1.02, 
            xanchor="right", x=1
        )
    )
    # Remove linhas de grade feias, deixa sutil
    fig.update_xaxes(showgrid=False, zeroline=False, color="#FFD770")
    fig.update_yaxes(showgrid=True, gridcolor="rgba(255,255,255,0.1)", zeroline=False, color="#FFFFFF")
    return fig

def dashboard_professor():
    st.markdown("<h1 style='color:#FFD700;'>📊 Dashboard do Mestre</h1>", unsafe_allow_html=True)
    if st.button("🏠 Voltar ao Início", key="btn_voltar_dash"):
        st.session_state.menu_selection = "Início"; st.rerun()

    db = get_db()
    user = st.session_state.usuario

    # 1. Carregar Dados
    with st.spinner("Analisando dados do dojo..."):
        # Resultados dos Exames
        docs_res = list(db.collection('resultados').stream())
        dados_res = [d.to_dict() for d in docs_res]
        df_res = pd.DataFrame(dados_res)

        # Questões (Para saber quais são do professor)
        docs_quest = list(db.collection('questoes').stream())
        dados_quest = []
        for d in docs_quest:
            dic = d.to_dict()
            dic['id'] = d.id
            dados_quest.append(dic)
        df_quest = pd.DataFrame(dados_quest)

    if df_res.empty:
        st.info("Nenhum exame realizado ainda para gerar estatísticas.")
        return

    # =========================================
    # KPI's TOPO (Indicadores Gerais)
    # =========================================
    total_exames = len(df_res)
    total_aprovados = len(df_res[df_res['aprovado'] == True])
    taxa_aprovacao = (total_aprovados / total_exames * 100) if total_exames > 0 else 0
    
    # CSS Customizado para os Cards de KPI ficarem bonitos
    st.markdown("""
    <style>
    div[data-testid="stMetric"] {
        background-color: rgba(0,0,0,0.2);
        border: 1px solid rgba(255, 215, 112, 0.1);
        padding: 15px;
        border-radius: 10px;
        text-align: center;
    }
    div[data-testid="stMetric"] label { color: #FFD770 !important; }
    div[data-testid="stMetric"] div[data-testid="stMetricValue"] { color: #FFFFFF !important; }
    </style>
    """, unsafe_allow_html=True)

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Total de Exames", total_exames)
    col2.metric("Aprovados", total_aprovados)
    col3.metric("Reprovados", total_exames - total_aprovados)
    col4.metric("Taxa de Aprovação", f"{taxa_aprovacao:.1f}%")

    st.markdown("---")

    tab1, tab2 = st.tabs(["📈 Desempenho Geral", "🧠 Análise de Questões"])

    # =========================================
    # ABA 1: VISÃO GERAL
    # =========================================
    with tab1:
        c1, c2 = st.columns(2)
        
        # Gráfico de Pizza: Aprovados vs Reprovados
        with c1:
            st.subheader("Aprovação Global")
            if 'aprovado' in df_res.columns:
                df_pizza = df_res['aprovado'].value_counts().reset_index()
                df_pizza.columns = ['Status', 'Qtd']
                df_pizza['Status'] = df_pizza['Status'].map({True: 'Aprovado', False: 'Reprovado'})
                
                # Cores Personalizadas: Verde Esmeralda vs Vermelho Suave
                cores_pizza = {'Aprovado': '#078B6C', 'Reprovado': '#EF553B'}
                
                fig_pizza = px.pie(
                    df_pizza, values='Qtd', names='Status', 
                    color='Status', color_discrete_map=cores_pizza,
                    hole=0.4 # Donut Chart é mais moderno
                )
                fig_pizza = estilizar_grafico(fig_pizza)
                st.plotly_chart(fig_pizza, use_container_width=True)

        # Gráfico de Barras: Exames por Faixa
        with c2:
            st.subheader("Exames por Faixa")
            if 'faixa' in df_res.columns:
                df_faixa = df_res['faixa'].value_counts().reset_index()
                df_faixa.columns = ['Faixa', 'Qtd']
                
                fig_bar = px.bar(
                    df_faixa, x='Faixa', y='Qtd',
                    text='Qtd', # Mostra o número em cima da barra
                    color_discrete_sequence=['#FFD770'] # Usa a cor Dourada do sistema
                )
                fig_bar = estilizar_grafico(fig_bar)
                fig_bar.update_traces(textposition='outside') # Número fora da barra
                st.plotly_chart(fig_bar, use_container_width=True)

        # Tabela Recente
        st.subheader("Últimos 5 Exames Realizados")
        cols_view = ['usuario', 'faixa', 'pontuacao', 'aprovado', 'data']
        for c in cols_view: 
            if c not in df_res.columns: df_res[c] = "-"
            
        # Formatar Data para ficar bonita
        df_display = df_res.copy()
        if 'data' in df_display.columns:
            df_display['data'] = pd.to_datetime(df_display['data']).dt.strftime('%d/%m/%Y %H:%M')

        st.dataframe(
            df_display[cols_view].sort_values(by='data', ascending=False).head(5), 
            hide_index=True, 
            use_container_width=True,
            column_config={
                "usuario": "Aluno",
                "pontuacao": st.column_config.ProgressColumn("Nota", format="%.1f%%", min_value=0, max_value=100),
                "aprovado": st.column_config.CheckboxColumn("Aprovado"),
                "data": "Data"
            }
        )

    # =========================================
    # ABA 2: ANÁLISE DE QUESTÕES (INTELIGÊNCIA)
    # =========================================
    with tab2:
        tem_detalhes = 'detalhes' in df_res.columns and df_res['detalhes'].notna().any()
        
        if not tem_detalhes:
            st.warning("⚠️ Realize novos exames para alimentar os gráficos de inteligência.")
        else:
            todas_respostas = []
            for idx, row in df_res.iterrows():
                detalhes = row.get('detalhes')
                if isinstance(detalhes, list):
                    for item in detalhes:
                        todas_respostas.append(item)
            
            if todas_respostas:
                df_analise = pd.DataFrame(todas_respostas)
                
                stats_quest = df_analise.groupby('questao_id').agg(
                    vezes_usada=('questao_id', 'count'),
                    acertos=('acertou', 'sum')
                ).reset_index()
                
                stats_quest['taxa_acerto'] = (stats_quest['acertos'] / stats_quest['vezes_usada']) * 100

                if not df_quest.empty:
                    stats_completo = pd.merge(stats_quest, df_quest[['id', 'pergunta', 'criado_por', 'dificuldade']], left_on='questao_id', right_on='id', how='left')
                else:
                    stats_completo = stats_quest
                    stats_completo['pergunta'] = 'Questão Deletada'
                    stats_completo['criado_por'] = '-'

                # --- 1. Gráfico de Barras: Top Erros ---
                st.subheader("🚨 Onde os alunos mais erram?")
                df_top_erros = stats_completo.sort_values(by='taxa_acerto', ascending=True).head(7)
                
                # Encurtar perguntas muito longas para o gráfico
                df_top_erros['pergunta_curta'] = df_top_erros['pergunta'].apply(lambda x: x[:40] + "..." if len(str(x)) > 40 else x)

                fig_err = px.bar(
                    df_top_erros, 
                    x='taxa_acerto', 
                    y='pergunta_curta', 
                    orientation='h', # Barras horizontais
                    text='taxa_acerto',
                    title="Questões com Menor Taxa de Acerto",
                    color='taxa_acerto',
                    color_continuous_scale=['#EF553B', '#FFD770', '#078B6C'] # Vermelho -> Amarelo -> Verde
                )
                fig_err = estilizar_grafico(fig_err)
                fig_err.update_traces(texttemplate='%{text:.1f}%', textposition='outside')
                st.plotly_chart(fig_err, use_container_width=True)

                st.markdown("---")

                # --- 2. Análise do Professor Logado ---
                st.subheader(f"👨‍🏫 Estatísticas das Questões de: {user.get('nome', 'Mim')}")
                meus_stats = stats_completo[stats_completo['criado_por'] == user.get('nome')]
                
                if meus_stats.empty:
                    st.info("Você ainda não tem questões cadastradas que foram utilizadas em exames.")
                else:
                    c_m1, c_m2, c_m3 = st.columns(3)
                    c_m1.metric("Minhas Questões Usadas", len(meus_stats))
                    c_m2.metric("Total de Aplicações", meus_stats['vezes_usada'].sum())
                    media_minha = meus_stats['taxa_acerto'].mean()
                    c_m3.metric("Média de Acerto Global", f"{media_minha:.1f}%")
                    
                    st.dataframe(
                        meus_stats[['pergunta', 'vezes_usada', 'taxa_acerto', 'dificuldade']].sort_values(by='vezes_usada', ascending=False),
                        column_config={
                            "pergunta": "Pergunta",
                            "vezes_usada": st.column_config.NumberColumn("Aplicações", format="%d"),
                            "taxa_acerto": st.column_config.ProgressColumn("Taxa de Acerto", format="%.1f%%", min_value=0, max_value=100),
                            "dificuldade": "Nível"
                        },
                        hide_index=True,
                        use_container_width=True
                    )
            else:
                st.info("Aguardando dados...")
