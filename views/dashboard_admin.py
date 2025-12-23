#views/dashboard_admin.py

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from database import get_db

# =========================================
# FUNÇÕES AUXILIARES DE ESTILO
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

# =========================================
# DASHBOARD ANALÍTICO
# =========================================
def render_dashboard_geral():
    st.markdown("### 📊 Inteligência do Projeto")
    db = get_db()
    
    # 1. Coleta de Dados
    with st.spinner("Compilando estatísticas globais..."):
        users_docs = list(db.collection('usuarios').stream())
        df_users = pd.DataFrame([d.to_dict() for d in users_docs])
        
        res_docs = list(db.collection('resultados').stream())
        df_res = pd.DataFrame([d.to_dict() for d in res_docs])
        
        q_docs = list(db.collection('questoes').stream())
        df_q = pd.DataFrame([d.to_dict() | {'id': d.id} for d in q_docs])

        eq_docs = list(db.collection('equipes').stream())
        df_equipes = pd.DataFrame([d.to_dict() | {'id': d.id} for d in eq_docs])
        
        alunos_vinc = list(db.collection('alunos').stream())
        df_alunos_vinc = pd.DataFrame([d.to_dict() for d in alunos_vinc])
        
        profs_vinc = list(db.collection('professores').stream())
        df_profs_vinc = pd.DataFrame([d.to_dict() for d in profs_vinc])

    # 2. KPIs
    total_users = len(df_users)
    total_alunos = len(df_users[df_users['tipo_usuario'] == 'aluno']) if not df_users.empty else 0
    total_profs = len(df_users[df_users['tipo_usuario'] == 'professor']) if not df_users.empty else 0
    total_questoes = len(df_q)
    total_equipes = len(df_equipes)
    
    col1, col2, col3, col4, col5 = st.columns(5)
    col1.metric("👥 Usuários", total_users)
    col2.metric("🥋 Professores(as)", total_profs)
    col3.metric("🧠 Questões", total_questoes)
    col4.metric("🏛️ Equipes", total_equipes)
    
    total_exames = len(df_res)
    aprovados = len(df_res[df_res['aprovado'] == True]) if not df_res.empty else 0
    taxa_aprovacao = (aprovados / total_exames * 100) if total_exames > 0 else 0
    col5.metric("🏆 Aprovação", f"{taxa_aprovacao:.1f}%")
    
    st.markdown("---")

    # 3. Evolução Temporal de CADASTROS
    st.markdown("##### 📅 Evolução de Cadastros (Mensal)")
    if not df_users.empty and 'data_criacao' in df_users.columns:
        try:
            df_ev = df_users.copy()
            df_ev['data_criacao'] = pd.to_datetime(df_ev['data_criacao'], errors='coerce', utc=True)
            df_ev = df_ev.dropna(subset=['data_criacao'])
            df_ev = df_ev[df_ev['tipo_usuario'].isin(['aluno', 'professor'])]
            df_ev['Tipo'] = df_ev['tipo_usuario'].str.capitalize()
            df_ev['mes_dt'] = df_ev['data_criacao'].dt.to_period('M').dt.to_timestamp()
            
            df_counts = df_ev.groupby(['mes_dt', 'Tipo']).size().reset_index(name='Qtd')
            df_counts = df_counts.sort_values('mes_dt')
            
            fig_line = px.line(df_counts, x='mes_dt', y='Qtd', color='Tipo', markers=True,
                               color_discrete_map={'Aluno': '#078B6C', 'Professor(a)': '#FFD770'},
                               labels={'mes_dt': 'Mês', 'Qtd': 'Novos Usuários'})
            
            st.plotly_chart(estilizar_grafico(fig_line), use_container_width=True)
        except Exception as e:
            st.error(f"Erro ao gerar gráfico de evolução: {e}")
    else:
        st.info("Sem dados temporais suficientes para gerar o gráfico de evolução.")

    # 4. Resultados Consolidados (ALTERADO PARA PIE CHART)
    st.markdown("##### 🎯 Resultados Consolidados (Total)")
    if not df_res.empty:
        try:
            df_status = df_res['aprovado'].value_counts().reset_index()
            df_status.columns = ['Status', 'Qtd']
            df_status['Status'] = df_status['Status'].map({True: 'Aprovado', False: 'Reprovado'})
            
            # Gráfico de Pizza (Donut)
            fig_res = px.pie(df_status, values='Qtd', names='Status', color='Status',
                             color_discrete_map={'Aprovado': '#078B6C', 'Reprovado': '#EF553B'},
                             hole=0.5)
            
            fig_res.update_traces(textinfo='percent+value', textfont_size=14)
            st.plotly_chart(estilizar_grafico(fig_res), use_container_width=True)
            
        except Exception as e:
            st.error(f"Erro ao gerar gráfico de resultados: {e}")
    else:
        st.info("Sem dados de exames realizados para gerar o gráfico.")

    st.markdown("---")

    # 5. Demografia e Equipes
    c1, c2 = st.columns(2)
    
    with c1:
        st.markdown("##### 👫 Distribuição por Sexo")
        if not df_users.empty and 'sexo' in df_users.columns:
            df_sexo = df_users.groupby(['tipo_usuario', 'sexo']).size().reset_index(name='Qtd')
            df_sexo['tipo_usuario'] = df_sexo['tipo_usuario'].str.capitalize()
            fig_sexo = px.bar(df_sexo, x='tipo_usuario', y='Qtd', color='sexo', barmode='group',
                              text='Qtd', color_discrete_map={'Masculino': '#078B6C', 'Feminino': '#FFD770'},
                              labels={'tipo_usuario': 'Perfil', 'Qtd': 'Quantidade', 'sexo': 'Sexo'})
            st.plotly_chart(estilizar_grafico(fig_sexo), use_container_width=True)
        else:
            st.info("Sem dados demográficos.")

    with c2:
        st.markdown("##### 🏛️ Tamanho das Equipes")
        if not df_equipes.empty:
            if not df_alunos_vinc.empty:
                count_alunos = df_alunos_vinc['equipe_id'].value_counts().reset_index()
                count_alunos.columns = ['id', 'Alunos']
            else: count_alunos = pd.DataFrame(columns=['id', 'Alunos'])
            
            if not df_profs_vinc.empty:
                count_profs = df_profs_vinc['equipe_id'].value_counts().reset_index()
                count_profs.columns = ['id', 'Professores']
            else: count_profs = pd.DataFrame(columns=['id', 'Professores'])
            
            df_merged = pd.merge(df_equipes[['id', 'nome']], count_alunos, on='id', how='left').fillna(0)
            df_merged = pd.merge(df_merged, count_profs, on='id', how='left').fillna(0)
            df_merged['Total'] = df_merged['Alunos'] + df_merged['Professores']
            df_top_eq = df_merged.sort_values(by='Total', ascending=False).head(5)
            
            fig_eq = go.Figure(data=[
                go.Bar(name='Alunos(as)', x=df_top_eq['nome'], y=df_top_eq['Alunos'], marker_color='#078B6C'),
                go.Bar(name='Professores(as)', x=df_top_eq['nome'], y=df_top_eq['Professores'], marker_color='#FFD770')
            ])
            fig_eq.update_layout(barmode='stack', title="Top 5 Equipes (Membros)")
            st.plotly_chart(estilizar_grafico(fig_eq), use_container_width=True)
        else:
            st.info("Sem equipes cadastradas.")

    # 6. Contribuidores e Faixas
    c3, c4 = st.columns(2)
    
    with c3:
        st.markdown("##### ✍️ Top Contribuidores (Questões)")
        if not df_q.empty and 'criado_por' in df_q.columns:
            df_q['autor_limpo'] = df_q['criado_por'].apply(lambda x: x.split('(')[0].strip() if x else "Desconhecido")
            df_contrib = df_q['autor_limpo'].value_counts().reset_index().head(7)
            df_contrib.columns = ['Autor', 'Qtd']
            fig_contrib = px.bar(df_contrib, x='Qtd', y='Autor', orientation='h', text='Qtd',
                                 color='Qtd', color_continuous_scale='Greens')
            st.plotly_chart(estilizar_grafico(fig_contrib), use_container_width=True)
        else:
            st.info("Banco de questões vazio.")

    with c4:
        st.markdown("##### 🥋 Distribuição de Alunos(as) por Faixa")
        if not df_users.empty and 'faixa_atual' in df_users.columns:
            df_faixas = df_users[df_users['tipo_usuario'] == 'aluno']['faixa_atual'].value_counts().reset_index()
            df_faixas.columns = ['Faixa', 'Qtd']
            fig_f = px.pie(df_faixas, values='Qtd', names='Faixa', hole=0.4, 
                           color_discrete_sequence=px.colors.sequential.RdBu)
            st.plotly_chart(estilizar_grafico(fig_f), use_container_width=True)
        else:
            st.info("Sem dados de faixas.")
