import streamlit as st
import pandas as pd
import plotly.express as px
from database import get_db

# =========================================
# FUNÇÃO AUXILIAR DE ESTILO
# =========================================
def estilizar_grafico(fig):
    """Aplica o tema Dark/Gold do BJJ Digital aos gráficos Plotly."""
    fig.update_layout(
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font={"color": "#FFFFFF", "family": "Poppins, sans-serif"},
        margin=dict(l=20, r=20, t=40, b=20),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
    )
    fig.update_xaxes(showgrid=False, zeroline=False, color="#FFD770")
    fig.update_yaxes(showgrid=True, gridcolor="rgba(255,255,255,0.1)", zeroline=False, color="#FFFFFF")
    return fig

def dashboard_professor():
    st.markdown("<h1 style='color:#FFD770;'>📊 Dashboard do Mestre</h1>", unsafe_allow_html=True)
    
    if st.session_state.menu_selection == "📊 Dashboard":
        if st.button("🏠 Voltar ao Início", key="btn_voltar_dash"):
            st.session_state.menu_selection = "Início"; st.rerun()

    db = get_db()
    user = st.session_state.usuario

    # 1. Carregar Dados
    with st.spinner("Analisando dados do dojo..."):
        # Resultados
        docs_res = list(db.collection('resultados').stream())
        dados_res = [d.to_dict() for d in docs_res]
        df_res = pd.DataFrame(dados_res)

        # Questões
        docs_quest = list(db.collection('questoes').stream())
        dados_quest = []
        for d in docs_quest:
            dic = d.to_dict(); dic['id'] = d.id; dados_quest.append(dic)
        df_quest = pd.DataFrame(dados_quest)

    if df_res.empty:
        st.info("Nenhum exame realizado ainda para gerar estatísticas.")
        return

    # --- FILTRO: REMOVE DADOS DO "MODO ROLA" ---
    if 'faixa' in df_res.columns:
        df_res = df_res[df_res['faixa'] != 'Modo Rola']

    if df_res.empty:
        st.warning("Existem dados de 'Modo Rola', mas nenhum 'Exame de Faixa' oficial foi realizado ainda.")
        return

    # =========================================
    # KPI's
    # =========================================
    total_exames = len(df_res)
    total_aprovados = len(df_res[df_res['aprovado'] == True])
    taxa_aprovacao = (total_aprovados / total_exames * 100) if total_exames > 0 else 0
    
    st.markdown("""
    <style>
    div[data-testid="stMetric"] { background-color: rgba(0,0,0,0.2); border: 1px solid rgba(255, 215, 112, 0.1); padding: 15px; border-radius: 10px; text-align: center; }
    div[data-testid="stMetric"] label { color: #FFD770 !important; }
    div[data-testid="stMetric"] div[data-testid="stMetricValue"] { color: #FFFFFF !important; }
    </style>
    """, unsafe_allow_html=True)

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Total de Exames", total_exames)
    c2.metric("Aprovados", total_aprovados)
    c3.metric("Reprovados", total_exames - total_aprovados)
    c4.metric("Taxa de Aprovação", f"{taxa_aprovacao:.1f}%")

    st.markdown("---")

    tab1, tab2 = st.tabs(["📈 Desempenho Geral", "🧠 Análise de Questões"])

    # =========================================
    # ABA 1: VISÃO GERAL
    # =========================================
    with tab1:
        c1, c2 = st.columns(2)
        with c1:
            st.subheader("Aprovação Global")
            if 'aprovado' in df_res.columns:
                df_pizza = df_res['aprovado'].value_counts().reset_index()
                df_pizza.columns = ['Status', 'Qtd']
                df_pizza['Status'] = df_pizza['Status'].map({True: 'Aprovado', False: 'Reprovado'})
                fig_pizza = px.pie(df_pizza, values='Qtd', names='Status', color='Status', 
                                   color_discrete_map={'Aprovado': '#078B6C', 'Reprovado': '#EF553B'}, hole=0.4)
                st.plotly_chart(estilizar_grafico(fig_pizza), use_container_width=True)

        with c2:
            st.subheader("Exames por Faixa")
            if 'faixa' in df_res.columns:
                df_faixa = df_res['faixa'].value_counts().reset_index()
                df_faixa.columns = ['Faixa', 'Qtd']
                fig_bar = px.bar(df_faixa, x='Faixa', y='Qtd', text='Qtd', color_discrete_sequence=['#FFD770'])
                fig_bar.update_traces(textposition='outside')
                st.plotly_chart(estilizar_grafico(fig_bar), use_container_width=True)

        # --- TABELA MODERNIZADA ---
        st.subheader("Últimos Exames Realizados")
        
        # Preparação dos dados para ficar bonito
        df_display = df_res.copy()
        
        # 1. Ícone no nome
        df_display['usuario_visual'] = "🥋 " + df_display['usuario']
        
        # 2. Status com Emoji (Substitui checkbox)
        df_display['status_visual'] = df_display['aprovado'].apply(lambda x: "🏆 Aprovado" if x else "🔴 Reprovado")
        
        # 3. Formatar Data
        if 'data' in df_display.columns:
            df_display['data_formatada'] = pd.to_datetime(df_display['data']).dt.strftime('%d/%m %H:%M')
        else:
            df_display['data_formatada'] = "-"
            
        # 4. Garantir numérico para barra
        df_display['pontuacao'] = pd.to_numeric(df_display['pontuacao'], errors='coerce').fillna(0)

        # Seleção e Ordem das Colunas
        cols_final = ['usuario_visual', 'faixa', 'pontuacao', 'status_visual', 'data_formatada']
        
        st.dataframe(
            df_display[cols_final].sort_values(by='data_formatada', ascending=False).head(10).style
            .bar(subset=['pontuacao'], color='#078B6C', vmin=0, vmax=100) # Barra Verde
            .format({'pontuacao': '{:.1f}%'}),
            hide_index=True, 
            use_container_width=True,
            column_config={
                "usuario_visual": st.column_config.TextColumn("Atleta", width="medium"),
                "faixa": st.column_config.TextColumn("Faixa", width="small"),
                "pontuacao": st.column_config.Column("Performance", width="small"), # Barra verde (estilo pandas)
                "status_visual": st.column_config.TextColumn("Status", width="small"),
                "data_formatada": st.column_config.TextColumn("Data", width="small")
            }
        )

    # =========================================
    # ABA 2: INTELIGÊNCIA
    # =========================================
    with tab2:
        tem_detalhes = 'detalhes' in df_res.columns and df_res['detalhes'].notna().any()
        
        if not tem_detalhes:
            st.warning("⚠️ Realize novos exames oficiais para alimentar os gráficos de inteligência.")
        else:
            todas_respostas = []
            for idx, row in df_res.iterrows():
                detalhes = row.get('detalhes')
                if isinstance(detalhes, list):
                    for item in detalhes: todas_respostas.append(item)
            
            if todas_respostas:
                df_analise = pd.DataFrame(todas_respostas)
                stats_quest = df_analise.groupby('questao_id').agg(
                    vezes_usada=('questao_id', 'count'), acertos=('acertou', 'sum')
                ).reset_index()
                stats_quest['taxa_acerto'] = (stats_quest['acertos'] / stats_quest['vezes_usada']) * 100

                if not df_quest.empty:
                    stats_completo = pd.merge(stats_quest, df_quest[['id', 'pergunta', 'criado_por', 'dificuldade']], left_on='questao_id', right_on='id', how='left')
                else:
                    stats_completo = stats_quest; stats_completo['pergunta'] = 'Questão Deletada'; stats_completo['criado_por'] = '-'

                st.subheader("🚨 Onde os alunos mais erram? (Apenas Exames)")
                df_top_erros = stats_completo.sort_values(by='taxa_acerto', ascending=True).head(7)
                df_top_erros['pergunta_curta'] = df_top_erros['pergunta'].apply(lambda x: x[:40] + "..." if len(str(x)) > 40 else x)

                fig_err = px.bar(
                    df_top_erros, x='taxa_acerto', y='pergunta_curta', orientation='h', text='taxa_acerto',
                    title="Questões com Menor Taxa de Acerto", color='taxa_acerto',
                    color_continuous_scale=['#EF553B', '#FFD770', '#078B6C'] 
                )
                fig_err.update_traces(texttemplate='%{text:.1f}%', textposition='outside')
                st.plotly_chart(estilizar_grafico(fig_err), use_container_width=True)

                st.markdown("---")

                st.subheader(f"👨‍🏫 Estatísticas das Questões de: {user.get('nome', 'Mim')}")
                meus_stats = stats_completo[stats_completo['criado_por'] == user.get('nome')]
                
                if meus_stats.empty:
                    st.info("Você ainda não tem questões cadastradas que foram utilizadas em exames oficiais.")
                else:
                    c_m1, c_m2, c_m3 = st.columns(3)
                    c_m1.metric("Minhas Questões Usadas", len(meus_stats))
                    c_m2.metric("Total de Aplicações", meus_stats['vezes_usada'].sum())
                    c_m3.metric("Média de Acerto Global", f"{meus_stats['taxa_acerto'].mean():.1f}%")
                    
                    st.dataframe(
                        meus_stats[['pergunta', 'vezes_usada', 'taxa_acerto', 'dificuldade']]
                        .sort_values(by='vezes_usada', ascending=False)
                        .style.bar(subset=['taxa_acerto'], color='#078B6C', vmin=0, vmax=100)
                        .format({'taxa_acerto': '{:.1f}%'}),
                        column_config={
                            "pergunta": "Pergunta",
                            "vezes_usada": st.column_config.NumberColumn("Aplicações", format="%d"),
                            "taxa_acerto": "Taxa de Acerto",
                            "dificuldade": "Nível"
                        },
                        hide_index=True,
                        use_container_width=True
                    )
            else:
                st.info("Aguardando dados...")
