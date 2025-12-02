import streamlit as st
import pandas as pd
import plotly.express as px
from database import get_db

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
                fig_pizza = px.pie(df_pizza, values='Qtd', names='Status', color='Status',
                                   color_discrete_map={'Aprovado':'#00CC96', 'Reprovado':'#EF553B'})
                st.plotly_chart(fig_pizza, use_container_width=True)

        # Gráfico de Barras: Exames por Faixa
        with c2:
            st.subheader("Exames por Faixa")
            if 'faixa' in df_res.columns:
                df_faixa = df_res['faixa'].value_counts().reset_index()
                df_faixa.columns = ['Faixa', 'Qtd']
                fig_bar = px.bar(df_faixa, x='Faixa', y='Qtd', color='Faixa')
                st.plotly_chart(fig_bar, use_container_width=True)

        # Tabela Recente
        st.subheader("Últimos 5 Exames Realizados")
        cols_view = ['usuario', 'faixa', 'pontuacao', 'aprovado', 'data']
        # Tratamento simples para colunas inexistentes
        for c in cols_view: 
            if c not in df_res.columns: df_res[c] = "-"
            
        st.dataframe(
            df_res[cols_view].sort_values(by='data', ascending=False).head(5), 
            hide_index=True, 
            use_container_width=True
        )

    # =========================================
    # ABA 2: ANÁLISE DE QUESTÕES (INTELIGÊNCIA)
    # =========================================
    with tab2:
        # Verifica se temos dados detalhados (o ajuste do passo 1)
        tem_detalhes = 'detalhes' in df_res.columns and df_res['detalhes'].notna().any()
        
        if not tem_detalhes:
            st.warning("⚠️ Os dados detalhados de acertos por questão começaram a ser coletados agora. Realize alguns exames para alimentar os gráficos abaixo.")
        else:
            # Processamento dos Detalhes (Explodir a lista de detalhes)
            todas_respostas = []
            for idx, row in df_res.iterrows():
                detalhes = row.get('detalhes')
                if isinstance(detalhes, list):
                    for item in detalhes:
                        todas_respostas.append(item)
            
            if todas_respostas:
                df_analise = pd.DataFrame(todas_respostas)
                
                # Agrupar por ID da Questão
                stats_quest = df_analise.groupby('questao_id').agg(
                    vezes_usada=('questao_id', 'count'),
                    acertos=('acertou', 'sum')
                ).reset_index()
                
                stats_quest['taxa_acerto'] = (stats_quest['acertos'] / stats_quest['vezes_usada']) * 100
                stats_quest['erros'] = stats_quest['vezes_usada'] - stats_quest['acertos']

                # Cruzar com o texto da pergunta (df_quest)
                if not df_quest.empty:
                    stats_completo = pd.merge(stats_quest, df_quest[['id', 'pergunta', 'criado_por', 'dificuldade']], left_on='questao_id', right_on='id', how='left')
                else:
                    stats_completo = stats_quest
                    stats_completo['pergunta'] = 'Questão Deletada'
                    stats_completo['criado_por'] = '-'

                # --- 1. Top Questões Mais Erradas ---
                st.subheader("🚨 Top 5 Questões Mais Difíceis (Mais Erradas)")
                df_top_erros = stats_completo.sort_values(by='taxa_acerto', ascending=True).head(5)
                for _, row in df_top_erros.iterrows():
                    with st.container(border=True):
                        st.markdown(f"**{row['pergunta']}**")
                        c_a, c_b, c_c = st.columns(3)
                        c_a.error(f"Taxa de Acerto: {row['taxa_acerto']:.1f}%")
                        c_b.info(f"Vezes aplicada: {row['vezes_usada']}")
                        c_c.caption(f"Autor: {row.get('criado_por', '-')}")

                st.markdown("---")

                # --- 2. Análise do Professor Logado ---
                st.subheader(f"👨‍🏫 Estatísticas das Questões de: {user.get('nome', 'Mim')}")
                
                # Filtrar apenas questões criadas por este usuário
                meus_stats = stats_completo[stats_completo['criado_por'] == user.get('nome')]
                
                if meus_stats.empty:
                    st.info("Você ainda não tem questões cadastradas que foram utilizadas em exames.")
                else:
                    col_m1, col_m2 = st.columns(2)
                    col_m1.metric("Minhas Questões Usadas", len(meus_stats))
                    media_minha = meus_stats['taxa_acerto'].mean()
                    col_m2.metric("Média de Acerto das minhas questões", f"{media_minha:.1f}%")
                    
                    st.dataframe(
                        meus_stats[['pergunta', 'vezes_usada', 'taxa_acerto', 'dificuldade']].sort_values(by='vezes_usada', ascending=False),
                        column_config={
                            "pergunta": "Pergunta",
                            "vezes_usada": "Aparições",
                            "taxa_acerto": st.column_config.ProgressColumn("Taxa de Acerto", format="%.1f%%", min_value=0, max_value=100),
                            "dificuldade": "Nível"
                        },
                        hide_index=True,
                        use_container_width=True
                    )
            else:
                st.info("Aguardando mais dados...")
