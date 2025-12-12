# bjj_digital/views/cursos.py

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime
from typing import Optional, Dict, List, Tuple
from streamlit_tags import st_tags

# Ajuste os imports conforme a estrutura do seu projeto
from courses_engine import (
    criar_curso,
    listar_cursos_do_professor,
    listar_cursos_disponiveis_para_usuario,
    inscrever_usuario_em_curso,
    obter_inscricao,
    atualizar_progresso_curso
)
from database import get_db

# ======================================================
# CONFIGURAÇÃO DE ESTILO GLOBAL
# ======================================================

def aplicar_estilos():
    """Aplica estilos CSS personalizados para toda a aplicação"""
    st.markdown("""
    <style>
    /* Container principal moderno */
    .stApp {
        background: linear-gradient(135deg, #0f172a 0%, #1e293b 100%);
    }
    
    /* Cards modernos com sombras e gradientes */
    .modern-card {
        background: linear-gradient(145deg, rgba(255,255,255,0.05), rgba(255,255,255,0.02));
        backdrop-filter: blur(10px);
        border: 1px solid rgba(255,255,255,0.1);
        border-radius: 20px;
        padding: 1.5rem;
        margin: 1rem 0;
        transition: all 0.3s ease;
    }
    
    .modern-card:hover {
        transform: translateY(-5px);
        box-shadow: 0 20px 40px rgba(0,0,0,0.3);
        border-color: rgba(16, 185, 129, 0.5);
    }
    
    /* Badges modernas */
    .badge {
        display: inline-block;
        padding: 4px 12px;
        border-radius: 20px;
        font-size: 0.85rem;
        font-weight: 600;
        margin: 2px;
    }
    
    .badge-success {
        background: linear-gradient(135deg, #10b981, #059669);
        color: white;
    }
    
    .badge-warning {
        background: linear-gradient(135deg, #f59e0b, #d97706);
        color: white;
    }
    
    .badge-danger {
        background: linear-gradient(135deg, #ef4444, #dc2626);
        color: white;
    }
    
    .badge-info {
        background: linear-gradient(135deg, #3b82f6, #1d4ed8);
        color: white;
    }
    
    /* Botões customizados */
    .stButton > button {
        border-radius: 12px;
        font-weight: 600;
        transition: all 0.3s ease;
    }
    
    /* Progress bars customizadas */
    .stProgress > div > div > div {
        background: linear-gradient(90deg, #10b981, #3b82f6);
    }
    
    /* Tabs modernas */
    .stTabs [data-baseweb="tab-list"] {
        gap: 8px;
        background: rgba(255,255,255,0.05);
        border-radius: 12px;
        padding: 8px;
    }
    
    .stTabs [data-baseweb="tab"] {
        border-radius: 8px;
        padding: 10px 20px;
    }
    
    /* Inputs modernos */
    .stTextInput > div > div > input,
    .stTextArea > div > textarea {
        border-radius: 12px;
        border: 1px solid rgba(255,255,255,0.2);
        background: rgba(255,255,255,0.05);
        color: white;
    }
    
    /* Métricas personalizadas */
    .metric-card {
        background: rgba(255,255,255,0.05);
        border-radius: 16px;
        padding: 1.5rem;
        border: 1px solid rgba(255,255,255,0.1);
    }
    
    /* Animações */
    @keyframes fadeIn {
        from { opacity: 0; transform: translateY(20px); }
        to { opacity: 1; transform: translateY(0); }
    }
    
    .animate-fadeIn {
        animation: fadeIn 0.5s ease-out;
    }
    </style>
    """, unsafe_allow_html=True)

# ======================================================
# COMPONENTES REUTILIZÁVEIS
# ======================================================

def card_curso(curso: dict, usuario: dict, view_type: str = "professor"):
    """Componente de card de curso moderno e reutilizável"""
    
    with st.container():
        col1, col2 = st.columns([3, 1])
        
        with col1:
            # Header com badges
            st.markdown(f"### {curso.get('titulo')}")
            
            # Badges inline
            col_badges = st.columns([1, 1, 2])
            with col_badges[0]:
                status = "Ativo" if curso.get('ativo', True) else "Inativo"
                badge_color = "success" if curso.get('ativo', True) else "danger"
                st.markdown(f"<span class='badge badge-{badge_color}'>{status}</span>", 
                          unsafe_allow_html=True)
            
            with col_badges[1]:
                modalidade = curso.get('modalidade', '-')
                st.markdown(f"<span class='badge badge-info'>{modalidade}</span>", 
                          unsafe_allow_html=True)
            
            with col_badges[2]:
                publico = 'Equipe' if curso.get('publico') == 'equipe' else 'Geral'
                st.markdown(f"<span class='badge badge-warning'>{publico}</span>", 
                          unsafe_allow_html=True)
            
            # Descrição truncada
            desc = curso.get("descricao", "")
            if desc:
                st.markdown(f"<div style='opacity:0.8; margin-top:10px;'>{desc[:150]}...</div>", 
                          unsafe_allow_html=True)
        
        with col2:
            # Preço e ações
            if curso.get("pago"):
                st.markdown(f"**R$ {curso.get('preco', 0):.2f}**")
                st.caption(f"Split: {curso.get('split_custom', 10)}%")
            else:
                st.markdown("**Gratuito**")
            
            st.write("")  # Espaçamento
            
            if view_type == "professor":
                c1, c2 = st.columns(2)
                with c1:
                    if st.button("✏️", key=f"edit_{curso['id']}", 
                               help="Editar curso", use_container_width=True):
                        _dialogo_editar_curso(curso, usuario)
                with c2:
                    status_icon = "⏸️" if curso.get('ativo', True) else "▶️"
                    status_tooltip = "Pausar" if curso.get('ativo', True) else "Ativar"
                    if st.button(status_icon, key=f"toggle_{curso['id']}", 
                               help=status_tooltip, use_container_width=True):
                        _toggle_status_curso(curso["id"], not curso.get('ativo', True))
                        st.rerun()
            
            elif view_type == "aluno":
                inscricao = obter_inscricao(usuario["id"], curso["id"])
                if inscricao:
                    st.success("✅ Inscrito")
                else:
                    if st.button("Inscrever-se", key=f"insc_{curso['id']}", 
                               use_container_width=True, type="primary"):
                        inscrever_usuario_em_curso(usuario["id"], curso["id"])
                        st.success("🎉 Inscrição realizada!")
                        st.rerun()

def metric_card(title: str, value, change: str = None, icon: str = "📊"):
    """Componente de métrica personalizada"""
    col1, col2 = st.columns([1, 3])
    
    with col1:
        st.markdown(f"<div style='font-size:2.5rem;'>{icon}</div>", 
                   unsafe_allow_html=True)
    
    with col2:
        st.markdown(f"<h3 style='margin:0;'>{value}</h3>", unsafe_allow_html=True)
        st.markdown(f"<div style='opacity:0.7;'>{title}</div>", unsafe_allow_html=True)
        if change:
            st.markdown(f"<small>{change}</small>", unsafe_allow_html=True)

# ======================================================
# PÁGINA PRINCIPAL
# ======================================================

def pagina_cursos(usuario: dict):
    """
    Interface de cursos modernizada
    """
    # Aplicar estilos globais
    aplicar_estilos()
    
    tipo = str(usuario.get("tipo", "aluno")).lower()
    
    # Header moderno
    st.markdown("""
    <div class='animate-fadeIn' style='margin-bottom: 2rem;'>
        <h1 style='margin-bottom: 0.5rem;'>📚 Gestão de Cursos</h1>
        <div style='display: flex; align-items: center; gap: 1rem; opacity: 0.7;'>
            <div>Bem-vindo, <strong>{}</strong></div>
            <div>•</div>
            <div class='badge badge-info'>{}</div>
        </div>
    </div>
    """.format(usuario.get("nome", "Usuário"), tipo.capitalize()), 
    unsafe_allow_html=True)
    
    # Separador estilizado
    st.markdown("---")
    
    # Redirecionamento baseado no tipo
    if tipo in ["admin", "professor"]:
        _interface_professor_moderna(usuario)
    else:
        _interface_aluno_moderna(usuario)

# ======================================================
# VISÃO MODERNA DO PROFESSOR / ADMIN
# ======================================================

def _interface_professor_moderna(usuario: dict):
    """Interface moderna para professores/admins"""
    
    # Abas com ícones e descrições
    tab1, tab2, tab3 = st.tabs([
        "📊 Dashboard",
        "📘 Meus Cursos",
        "➕ Criar Curso"
    ])
    
    with tab1:
        _prof_dashboard_moderno(usuario)
    
    with tab2:
        _prof_listar_cursos_moderno(usuario)
    
    with tab3:
        _prof_criar_curso_moderno(usuario)

def _prof_dashboard_moderno(usuario: dict):
    """Dashboard visual moderno"""
    
    db = get_db()
    cursos = listar_cursos_do_professor(usuario["id"])
    
    if not cursos:
        st.info("🎯 Comece criando seu primeiro curso!")
        return
    
    # Coletar estatísticas
    total_inscritos = 0
    total_receita = 0
    progresso_medio = 0
    cursos_ativos = 0
    
    for curso in cursos:
        if curso.get('ativo'):
            cursos_ativos += 1
        
        # Buscar inscrições
        inscricoes = db.collection("enrollments").where("course_id", "==", curso["id"]).stream()
        for ins in inscricoes:
            total_inscritos += 1
            dados = ins.to_dict()
            
            if dados.get("pago") and curso.get("pago"):
                preco = curso.get("preco", 0)
                split = curso.get("split_custom", 10) / 100
                total_receita += preco * (1 - split)
            
            progresso_medio += float(dados.get("progresso", 0))
    
    if total_inscritos > 0:
        progresso_medio = progresso_medio / total_inscritos
    
    # Métricas em grid
    st.markdown("### 📈 Estatísticas Gerais")
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        metric_card("Cursos Ativos", cursos_ativos, f"de {len(cursos)} total", "📚")
    
    with col2:
        metric_card("Alunos", total_inscritos, "matriculados", "👥")
    
    with col3:
        metric_card("Receita", f"R$ {total_receita:.2f}", "líquida estimada", "💰")
    
    with col4:
        metric_card("Progresso", f"{progresso_medio:.0f}%", "médio dos alunos", "📈")
    
    st.markdown("---")
    
    # Gráficos
    if cursos_ativos > 0:
        col_chart1, col_chart2 = st.columns(2)
        
        with col_chart1:
            # Gráfico de distribuição de alunos por curso
            st.markdown("### 👥 Alunos por Curso")
            dados_grafico = []
            for curso in cursos:
                if curso.get('ativo'):
                    count = len(list(db.collection("enrollments")
                                   .where("course_id", "==", curso["id"])
                                   .stream()))
                    dados_grafico.append({
                        'Curso': curso['titulo'][:20] + ("..." if len(curso['titulo']) > 20 else ""),
                        'Alunos': count
                    })
            
            if dados_grafico:
                df = pd.DataFrame(dados_grafico)
                fig = px.bar(df, x='Curso', y='Alunos', 
                           color='Alunos', color_continuous_scale='Viridis')
                st.plotly_chart(fig, use_container_width=True)
        
        with col_chart2:
            # Gráfico de pizza de cursos ativos/inativos
            st.markdown("### 📊 Status dos Cursos")
            status_counts = {
                'Ativos': sum(1 for c in cursos if c.get('ativo')),
                'Inativos': sum(1 for c in cursos if not c.get('ativo'))
            }
            
            fig = go.Figure(data=[go.Pie(
                labels=list(status_counts.keys()),
                values=list(status_counts.values()),
                hole=.3,
                marker_colors=['#10b981', '#ef4444']
            )])
            fig.update_layout(showlegend=True)
            st.plotly_chart(fig, use_container_width=True)

def _prof_listar_cursos_moderno(usuario: dict):
    """Listagem moderna de cursos do professor"""
    
    cursos = listar_cursos_do_professor(usuario["id"])
    
    if not cursos:
        st.info("""
        🎯 **Você ainda não criou cursos!**
        
        Crie seu primeiro curso para compartilhar seu conhecimento com os alunos.
        """)
        return
    
    # Filtros avançados
    with st.expander("🔍 Filtros Avançados", expanded=False):
        col1, col2, col3 = st.columns(3)
        
        with col1:
            status_filter = st.multiselect(
                "Status",
                ["Ativo", "Inativo"],
                default=["Ativo"]
            )
        
        with col2:
            modalidade_filter = st.multiselect(
                "Modalidade",
                ["EAD", "Presencial"],
                default=["EAD", "Presencial"]
            )
        
        with col3:
            publico_filter = st.multiselect(
                "Público",
                ["geral", "equipe"],
                default=["geral", "equipe"]
            )
    
    # Aplicar filtros
    cursos_filtrados = []
    for curso in cursos:
        status = "Ativo" if curso.get('ativo', True) else "Inativo"
        if status_filter and status not in status_filter:
            continue
        if modalidade_filter and curso.get('modalidade') not in modalidade_filter:
            continue
        if publico_filter and curso.get('publico') not in publico_filter:
            continue
        cursos_filtrados.append(curso)
    
    # Exibir cards
    st.markdown(f"### 📘 Meus Cursos ({len(cursos_filtrados)})")
    
    # Opção de visualização
    view_mode = st.radio(
        "Visualização:",
        ["Grid", "Lista"],
        horizontal=True,
        label_visibility="collapsed"
    )
    
    if view_mode == "Grid":
        # Grid responsivo
        cols = st.columns(2)
        for idx, curso in enumerate(cursos_filtrados):
            with cols[idx % 2]:
                card_curso(curso, usuario, "professor")
    else:
        # Lista
        for curso in cursos_filtrados:
            card_curso(curso, usuario, "professor")

def _prof_criar_curso_moderno(usuario: dict):
    """Formulário moderno de criação de curso"""
    
    st.markdown("""
    <div style='background: linear-gradient(135deg, rgba(16,185,129,0.1), rgba(59,130,246,0.1)); 
                padding: 2rem; border-radius: 20px; margin-bottom: 2rem;'>
        <h2 style='margin:0;'>🎯 Criar Novo Curso</h2>
        <p style='opacity:0.8; margin-top:0.5rem;'>Preencha os detalhes abaixo para criar seu curso</p>
    </div>
    """, unsafe_allow_html=True)
    
    # Formulário em etapas
    with st.form("form_criar_curso_moderno", border=False):
        
        # Etapa 1: Informações básicas
        st.markdown("### 📝 Informações Básicas")
        col1, col2 = st.columns([2, 1])
        
        with col1:
            titulo = st.text_input(
                "Título do Curso *",
                placeholder="Ex: Fundamentos do Jiu-Jitsu para Iniciantes",
                help="Seja claro e objetivo no título"
            )
            
            descricao = st.text_area(
                "Descrição Detalhada *",
                height=120,
                placeholder="Descreva o que os alunos aprenderão, pré-requisitos, metodologia...",
                help="Quanto mais detalhada, melhor para os alunos entenderem o conteúdo"
            )
        
        with col2:
            # Upload de thumbnail (simulado - em produção, integrar com storage)
            st.markdown("**Thumbnail do Curso**")
            uploaded_file = st.file_uploader(
                "Escolha uma imagem",
                type=['png', 'jpg', 'jpeg'],
                label_visibility="collapsed"
            )
            if uploaded_file:
                st.image(uploaded_file, use_column_width=True)
            else:
                st.info("📷 Faça upload de uma imagem para seu curso")
        
        st.markdown("---")
        
        # Etapa 2: Configurações
        st.markdown("### ⚙️ Configurações")
        
        col_config1, col_config2 = st.columns(2)
        
        with col_config1:
            modalidade = st.selectbox(
                "Modalidade *",
                ["EAD", "Presencial", "Híbrido"],
                help="Como o curso será ministrado?"
            )
            
            publico = st.radio(
                "Público Alvo *",
                ["geral", "equipe"],
                format_func=lambda v: "🌍 Aberto (Geral)" if v == "geral" else "👥 Restrito (Equipe)",
                help="O curso é aberto para todos ou restrito à uma equipe?"
            )
            
            if publico == "equipe":
                equipe_destino = st.text_input(
                    "Nome da Equipe *",
                    placeholder="Digite o nome da sua equipe"
                )
            else:
                equipe_destino = None
        
        with col_config2:
            # Configurações avançadas
            with st.expander("⚡ Configurações Avançadas", expanded=True):
                certificado_auto = st.checkbox(
                    "Emitir certificado automaticamente",
                    value=True,
                    help="O certificado será gerado automaticamente ao concluir o curso"
                )
                
                max_alunos = st.number_input(
                    "Vagas disponíveis",
                    min_value=0,
                    value=0,
                    help="0 = ilimitado"
                )
                
                duracao_estimada = st.text_input(
                    "Duração estimada",
                    placeholder="Ex: 8 semanas, 40 horas",
                    help="Tempo estimado para conclusão"
                )
        
        st.markdown("---")
        
        # Etapa 3: Valores
        st.markdown("### 💰 Configurações Financeiras")
        
        col_fin1, col_fin2, col_fin3 = st.columns(3)
        
        with col_fin1:
            pago = st.toggle(
                "Curso Pago?",
                value=False,
                help="O curso terá valor ou será gratuito?"
            )
        
        with col_fin2:
            preco = st.number_input(
                "Valor do Curso (R$) *" if pago else "Valor do Curso",
                min_value=0.0,
                value=0.0 if not pago else 197.00,
                step=10.0,
                disabled=not pago,
                help="Valor total do curso"
            )
        
        with col_fin3:
            is_admin = usuario.get("tipo") == "admin"
            if pago and is_admin:
                split_custom = st.slider(
                    "Taxa da Plataforma (%)",
                    0, 100,
                    value=10,
                    help="Percentual retido pela plataforma"
                )
            else:
                split_custom = 10
        
        # Validação e submissão
        st.markdown("---")
        submit_col1, submit_col2, submit_col3 = st.columns([1, 2, 1])
        
        with submit_col2:
            submit_btn = st.form_submit_button(
                "🚀 Criar Curso Agora",
                use_container_width=True,
                type="primary"
            )
        
        if submit_btn:
            # Validações
            erros = []
            
            if not titulo.strip():
                erros.append("⚠️ O título é obrigatório")
            
            if not descricao.strip():
                erros.append("⚠️ A descrição é obrigatória")
            
            if publico == "equipe" and (not equipe_destino or not equipe_destino.strip()):
                erros.append("⚠️ Informe o nome da equipe")
            
            if pago and preco <= 0:
                erros.append("⚠️ Curso pago deve ter valor maior que zero")
            
            if erros:
                for erro in erros:
                    st.error(erro)
            else:
                try:
                    criar_curso(
                        professor_id=usuario["id"],
                        nome_professor=usuario.get("nome", ""),
                        titulo=titulo,
                        descricao=descricao,
                        modalidade=modalidade,
                        publico=publico,
                        equipe_destino=equipe_destino,
                        pago=pago,
                        preco=preco if pago else 0.0,
                        split_custom=split_custom,
                        certificado_automatico=certificado_auto,
                        max_alunos=max_alunos if max_alunos > 0 else None,
                        duracao_estimada=duracao_estimada if duracao_estimada else None
                    )
                    
                    # Mensagem de sucesso animada
                    st.success("""
                    🎉 **Curso criado com sucesso!**
                    
                    Seu curso já está disponível para matrículas. 
                    Acesse a aba "Meus Cursos" para gerenciá-lo.
                    """)
                    
                    # Reset do formulário
                    st.rerun()
                    
                except Exception as e:
                    st.error(f"""
                    ❌ **Erro ao criar curso:**
                    
                    ```{str(e)}```
                    
                    Verifique os dados e tente novamente.
                    """)

# ======================================================
# VISÃO MODERNA DO ALUNO
# ======================================================

def _interface_aluno_moderna(usuario: dict):
    """Interface moderna para alunos"""
    
    # Abas com animação
    tab_disp, tab_meus, tab_recomendados = st.tabs([
        "🛒 Cursos Disponíveis",
        "🎓 Meus Cursos",
        "⭐ Recomendados"
    ])
    
    with tab_disp:
        _aluno_cursos_disponiveis_moderno(usuario)
    
    with tab_meus:
        _aluno_meus_cursos_moderno(usuario)
    
    with tab_recomendados:
        _aluno_cursos_recomendados(usuario)

def _aluno_cursos_disponiveis_moderno(usuario: dict):
    """Exibição moderna de cursos disponíveis"""
    
    cursos = listar_cursos_disponiveis_para_usuario(usuario)
    
    if not cursos:
        st.info("""
        📭 **Nenhum curso disponível no momento**
        
        Novos cursos serão disponibilizados em breve. 
        Verifique também se você atende aos pré-requisitos dos cursos existentes.
        """)
        return
    
    # Barra de busca e filtros
    col_search, col_filter = st.columns([3, 1])
    
    with col_search:
        search_term = st.text_input(
            "🔍 Buscar cursos...",
            placeholder="Digite o nome, professor ou assunto"
        )
    
    with col_filter:
        filter_type = st.selectbox(
            "Filtrar por:",
            ["Todos", "Gratuitos", "Pagos", "EAD", "Presencial"]
        )
    
    # Aplicar filtros
    cursos_filtrados = []
    for curso in cursos:
        # Filtro de busca
        if search_term:
            busca = search_term.lower()
            titulo = curso.get('titulo', '').lower()
            desc = curso.get('descricao', '').lower()
            professor = curso.get('nome_professor', '').lower()
            
            if busca not in titulo and busca not in desc and busca not in professor:
                continue
        
        # Filtro por tipo
        if filter_type == "Gratuitos" and curso.get('pago'):
            continue
        elif filter_type == "Pagos" and not curso.get('pago'):
            continue
        elif filter_type == "EAD" and curso.get('modalidade') != 'EAD':
            continue
        elif filter_type == "Presencial" and curso.get('modalidade') != 'Presencial':
            continue
        
        cursos_filtrados.append(curso)
    
    # Exibição
    st.markdown(f"### 📚 Cursos Disponíveis ({len(cursos_filtrados)})")
    
    if not cursos_filtrados:
        st.warning("Nenhum curso encontrado com os filtros aplicados.")
        return
    
    # Grid de cursos
    cols = st.columns(2)
    for idx, curso in enumerate(cursos_filtrados):
        with cols[idx % 2]:
            with st.container():
                st.markdown("<div class='modern-card'>", unsafe_allow_html=True)
                
                # Header com imagem
                col_img, col_info = st.columns([1, 3])
                
                with col_img:
                    # Thumbnail do curso
                    emoji = "🥋" if "jiu" in curso.get('titulo', '').lower() else "📚"
                    st.markdown(f"<div style='font-size:2.5rem; text-align:center;'>{emoji}</div>", 
                              unsafe_allow_html=True)
                
                with col_info:
                    # Informações principais
                    st.markdown(f"**{curso.get('titulo')}**")
                    
                    # Professor
                    st.caption(f"👨‍🏫 {curso.get('nome_professor', 'Professor')}")
                    
                    # Badges
                    col_badge1, col_badge2 = st.columns(2)
                    with col_badge1:
                        modalidade = curso.get('modalidade', '-')
                        st.markdown(f"<small>📍 {modalidade}</small>", unsafe_allow_html=True)
                    
                    with col_badge2:
                        if curso.get('pago'):
                            st.markdown(f"<small>💰 R$ {curso.get('preco', 0):.2f}</small>", 
                                      unsafe_allow_html=True)
                        else:
                            st.markdown(f"<small>🎁 Gratuito</small>", unsafe_allow_html=True)
                
                # Descrição resumida
                desc = curso.get("descricao", "")
                if desc:
                    st.markdown(f"<div style='font-size:0.9em; opacity:0.8; margin:10px 0;'>"
                              f"{desc[:100]}...</div>", unsafe_allow_html=True)
                
                # Botão de ação
                inscricao = obter_inscricao(usuario["id"], curso["id"])
                
                if inscricao:
                    st.success("✅ Você já está inscrito!")
                    if st.button("Acessar Curso", key=f"acessar_{curso['id']}", 
                               use_container_width=True):
                        st.session_state['curso_atual'] = curso['id']
                        st.rerun()
                else:
                    if st.button("Inscrever-se", key=f"inscrever_{curso['id']}", 
                               use_container_width=True, type="primary"):
                        with st.spinner("Realizando inscrição..."):
                            inscrever_usuario_em_curso(usuario["id"], curso["id"])
                        st.success("🎉 Inscrição realizada com sucesso!")
                        st.rerun()
                
                st.markdown("</div>", unsafe_allow_html=True)

def _aluno_meus_cursos_moderno(usuario: dict):
    """Exibição moderna dos cursos do aluno"""
    
    db = get_db()
    if not db:
        st.error("Erro de conexão com o banco de dados.")
        return
    
    # Buscar inscrições
    q = db.collection("enrollments").where("user_id", "==", usuario["id"]).stream()
    inscricoes = list(q)
    
    if not inscricoes:
        st.info("""
        📭 **Você ainda não está matriculado em nenhum curso**
        
        Explore os cursos disponíveis e comece sua jornada de aprendizado!
        """)
        return
    
    # Organizar por status
    cursos_ativos = []
    cursos_concluidos = []
    
    for ins in inscricoes:
        dados = ins.to_dict()
        curso_id = dados.get("course_id")
        
        # Buscar dados do curso
        curso_ref = db.collection("courses").document(curso_id).get()
        if not curso_ref.exists:
            continue
        
        curso = curso_ref.to_dict()
        curso["inscricao_id"] = ins.id
        curso["progresso"] = float(dados.get("progresso", 0))
        curso["pago_status"] = "✅ Pago" if dados.get("pago") else "⏳ Pendente"
        curso["certificado"] = "✅" if dados.get("certificado_emitido") else "⏳"
        
        if curso["progresso"] >= 100:
            cursos_concluidos.append(curso)
        else:
            cursos_ativos.append(curso)
    
    # Tabs para organização
    if cursos_ativos and cursos_concluidos:
        tab_ativos, tab_concluidos = st.tabs([
            f"📚 Em Andamento ({len(cursos_ativos)})",
            f"🎓 Concluídos ({len(cursos_concluidos)})"
        ])
        
        with tab_ativos:
            _exibir_cursos_aluno(cursos_ativos, usuario)
        
        with tab_concluidos:
            _exibir_cursos_aluno(cursos_concluidos, usuario, concluido=True)
    
    elif cursos_ativos:
        st.markdown(f"### 📚 Cursos em Andamento ({len(cursos_ativos)})")
        _exibir_cursos_aluno(cursos_ativos, usuario)
    
    else:
        st.markdown(f"### 🎓 Cursos Concluídos ({len(cursos_concluidos)})")
        _exibir_cursos_aluno(cursos_concluidos, usuario, concluido=True)

def _exibir_cursos_aluno(cursos: list, usuario: dict, concluido: bool = False):
    """Exibe cards dos cursos do aluno"""
    
    for curso in cursos:
        with st.container():
            st.markdown("<div class='modern-card'>", unsafe_allow_html=True)
            
            col1, col2, col3 = st.columns([1, 3, 1])
            
            with col1:
                # Ícone/thumbnail
                emoji = "🥋" if concluido else "📚"
                st.markdown(f"<div style='font-size:2.5rem; text-align:center;'>{emoji}</div>", 
                          unsafe_allow_html=True)
            
            with col2:
                # Informações do curso
                st.markdown(f"**{curso.get('titulo')}**")
                st.caption(f"👨‍🏫 {curso.get('nome_professor', 'Professor')}")
                
                if not concluido:
                    # Barra de progresso
                    progresso = curso.get("progresso", 0)
                    st.progress(progresso / 100, text=f"Progresso: {int(progresso)}%")
                    
                    # Estatísticas rápidas
                    col_stat1, col_stat2 = st.columns(2)
                    with col_stat1:
                        st.caption(f"💰 {curso.get('pago_status')}")
                    with col_stat2:
                        st.caption(f"📜 {curso.get('certificado')} Certificado")
                else:
                    st.success("✅ Curso concluído!")
                    st.caption(f"🎓 Certificado: {curso.get('certificado')}")
            
            with col3:
                # Ações
                st.write("")  # Espaçamento
                
                if concluido:
                    if st.button("📜 Certificado", key=f"cert_{curso['inscricao_id']}", 
                               use_container_width=True):
                        # Em produção, integrar com geração de certificado
                        st.info("Funcionalidade de certificado em desenvolvimento")
                else:
                    if st.button("▶️ Continuar", key=f"cont_{curso['inscricao_id']}", 
                               use_container_width=True, type="primary"):
                        st.session_state['curso_atual'] = curso.get('id')
                        st.rerun()
            
            st.markdown("</div>", unsafe_allow_html=True)

def _aluno_cursos_recomendados(usuario: dict):
    """Sugere cursos baseados no perfil do aluno"""
    
    # Em produção, implementar lógica de recomendação
    st.info("""
    🚧 **Sistema de recomendações em desenvolvimento**
    
    Em breve, sugeriremos cursos baseados em:
    - Seus interesses
    - Cursos concluídos
    - Perfil de aprendizado
    - Popularidade entre alunos similares
    """)
    
    # Mock de recomendações
    recomendacoes_mock = [
        {"titulo": "Jiu-Jitsu Avançado: Finalizações", "nivel": "Avançado"},
        {"titulo": "Defesa Pessoal para Iniciantes", "nivel": "Iniciante"},
        {"titulo": "Preparação Física para Atletas", "nivel": "Intermediário"},
    ]
    
    for rec in recomendacoes_mock:
        with st.container(border=True):
            col1, col2 = st.columns([3, 1])
            with col1:
                st.markdown(f"**{rec['titulo']}**")
                st.caption(f"⭐ Recomendado para seu nível: {rec['nivel']}")
            with col2:
                st.button("Ver Curso", key=f"ver_{rec['titulo'][:10]}", use_container_width=True)

# ======================================================
# MODAL DE EDIÇÃO MODERNO
# ======================================================

@st.dialog("✏️ Editar Curso", width="large")
def _dialogo_editar_curso(curso: dict, usuario: dict):
    """Modal moderno para edição de curso"""
    
    # Estilização do modal
    st.markdown("""
    <style>
    /* Override do modal */
    div[data-testid="stDialog"] > div:first-child {
        background: linear-gradient(145deg, #1e293b, #0f172a);
        border: 1px solid rgba(16, 185, 129, 0.3);
        border-radius: 20px;
        padding: 1.5rem;
    }
    </style>
    """, unsafe_allow_html=True)
    
    is_admin = usuario.get("tipo") == "admin"
    
    # Formulário de edição
    with st.form("form_editar_curso_modal", border=False):
        
        # Tabs para organização
        tab_basico, tab_avancado, tab_financeiro = st.tabs([
            "📝 Básico", "⚙️ Avançado", "💰 Financeiro"
        ])
        
        with tab_basico:
            titulo = st.text_input("Título do Curso", value=curso.get("titulo", ""))
            descricao = st.text_area("Descrição", value=curso.get("descricao", ""), height=120)
            
            col1, col2 = st.columns(2)
            with col1:
                modalidade = st.selectbox(
                    "Modalidade",
                    ["EAD", "Presencial", "Híbrido"],
                    index=["EAD", "Presencial", "Híbrido"].index(
                        curso.get("modalidade", "EAD")
                    ) if curso.get("modalidade") in ["EAD", "Presencial", "Híbrido"] else 0
                )
            
            with col2:
                publico = st.selectbox(
                    "Público",
                    ["geral", "equipe"],
                    index=0 if curso.get("publico") == "geral" else 1,
                    format_func=lambda v: "🌍 Geral" if v == "geral" else "👥 Equipe"
                )
                
                if publico == "equipe":
                    equipe_destino = st.text_input(
                        "Equipe Destino",
                        value=curso.get("equipe_destino", "")
                    )
                else:
                    equipe_destino = None
        
        with tab_avancado:
            col_av1, col_av2 = st.columns(2)
            
            with col_av1:
                ativo = st.toggle("Curso Ativo", value=curso.get("ativo", True))
                certificado_auto = st.toggle(
                    "Certificado Automático",
                    value=curso.get("certificado_automatico", True)
                )
            
            with col_av2:
                max_alunos = st.number_input(
                    "Vagas Máximas",
                    value=curso.get("max_alunos", 0),
                    min_value=0,
                    help="0 = ilimitado"
                )
                
                duracao = st.text_input(
                    "Duração Estimada",
                    value=curso.get("duracao_estimada", ""),
                    placeholder="Ex: 8 semanas"
                )
        
        with tab_financeiro:
            col_fin1, col_fin2 = st.columns(2)
            
            with col_fin1:
                pago = st.toggle("Curso Pago", value=curso.get("pago", False))
                
                preco = st.number_input(
                    "Valor (R$)",
                    value=float(curso.get("preco", 0.0)),
                    min_value=0.0,
                    step=10.0,
                    disabled=not pago
                )
            
            with col_fin2:
                if pago and is_admin:
                    split_custom = st.slider(
                        "Split da Plataforma (%)",
                        0, 100,
                        value=int(curso.get("split_custom", 10)),
                        help="Percentual retido pela plataforma"
                    )
                else:
                    split_custom = curso.get("split_custom", 10)
                    st.info(f"Split atual: {split_custom}%")
                    st.caption("Apenas administradores podem alterar")
        
        # Botões de ação
        st.markdown("---")
        col_btn1, col_btn2, col_btn3 = st.columns([1, 2, 1])
        
        with col_btn2:
            submitted = st.form_submit_button(
                "💾 Salvar Alterações",
                type="primary",
                use_container_width=True
            )
        
        if submitted:
            try:
                _salvar_edicao_curso_moderno(
                    curso_id=curso["id"],
                    titulo=titulo,
                    descricao=descricao,
                    modalidade=modalidade,
                    publico=publico,
                    equipe_destino=equipe_destino,
                    ativo=ativo,
                    pago=pago,
                    preco=preco,
                    split_custom=split_custom,
                    certificado_automatico=certificado_auto,
                    max_alunos=max_alunos if max_alunos > 0 else None,
                    duracao_estimada=duracao if duracao else None
                )
                st.success("✅ Curso atualizado com sucesso!")
                st.rerun()
            except Exception as e:
                st.error(f"❌ Erro ao salvar: {str(e)}")

def _salvar_edicao_curso_moderno(
    curso_id: str,
    titulo: str,
    descricao: str,
    modalidade: str,
    publico: str,
    equipe_destino: Optional[str],
    ativo: bool,
    pago: bool,
    preco: Optional[float],
    split_custom: Optional[int],
    certificado_automatico: bool,
    max_alunos: Optional[int],
    duracao_estimada: Optional[str]
):
    """Atualiza curso com campos modernos"""
    db = get_db()
    
    safe_preco = float(preco) if (pago and preco is not None) else 0.0
    safe_split = int(split_custom) if split_custom is not None else 10
    
    doc_updates = {
        "titulo": titulo.strip(),
        "descricao": descricao.strip(),
        "modalidade": modalidade,
        "publico": publico,
        "equipe_destino": equipe_destino or None,
        "ativo": bool(ativo),
        "pago": bool(pago),
        "preco": safe_preco,
        "split_custom": safe_split,
        "certificado_automatico": bool(certificado_automatico),
        "max_alunos": max_alunos,
        "duracao_estimada": duracao_estimada,
        "ultima_atualizacao": datetime.now().isoformat()
    }
    
    db.collection("courses").document(curso_id).update(doc_updates)

def _toggle_status_curso(curso_id: str, novo_ativo: bool):
    """Alterna status do curso com feedback"""
    db = get_db()
    db.collection("courses").document(curso_id).update({
        "ativo": bool(novo_ativo),
        "status": "ativo" if novo_ativo else "inativo",
        "ultima_atualizacao": datetime.now().isoformat()
    })