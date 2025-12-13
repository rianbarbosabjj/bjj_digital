"""
BJJ Digital - Sistema de Cursos (Versão Modernizada)
Integração com aulas e design atualizado
"""

import streamlit as st
import pandas as pd
import time
from datetime import datetime
from typing import Optional, Dict, List

# Importações internas
from database import get_db
from courses_engine import (
    criar_curso,
    listar_cursos_do_professor,
    listar_cursos_disponiveis_para_usuario,
    inscrever_usuario_em_curso,
    obter_inscricao,
)

# ======================================================
# ESTILOS MODERNOS PARA CURSOS
# ======================================================

def aplicar_estilos_cursos():
    """Aplica estilos modernos específicos para cursos"""
    st.markdown("""
    <style>
    /* CARDS DE CURSO MODERNOS */
    .curso-card-moderno {
        background: linear-gradient(145deg, rgba(14, 45, 38, 0.9) 0%, rgba(9, 31, 26, 0.95) 100%);
        border: 1px solid rgba(255, 215, 112, 0.15);
        border-radius: 20px;
        padding: 1.5rem;
        transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
        height: 100%;
        display: flex;
        flex-direction: column;
        position: relative;
        overflow: hidden;
    }
    
    .curso-card-moderno::before {
        content: '';
        position: absolute;
        top: 0;
        left: 0;
        right: 0;
        height: 4px;
        background: linear-gradient(90deg, #078B6C 0%, #FFD770 100%);
        border-radius: 20px 20px 0 0;
    }
    
    .curso-card-moderno:hover {
        border-color: #FFD770;
        transform: translateY(-8px);
        box-shadow: 0 20px 60px rgba(0, 0, 0, 0.4);
    }
    
    .curso-card-moderno.completed::before {
        background: linear-gradient(90deg, #10B981 0%, #34D399 100%);
    }
    
    .curso-card-moderno.in-progress::before {
        background: linear-gradient(90deg, #3B82F6 0%, #60A5FA 100%);
    }
    
    .curso-icon {
        font-size: 2.5rem;
        margin-bottom: 1rem;
        text-align: center;
        background: linear-gradient(135deg, #078B6C 0%, #FFD770 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
    }
    
    .curso-badges {
        display: flex;
        flex-wrap: wrap;
        gap: 0.5rem;
        margin: 1rem 0;
    }
    
    .curso-badge {
        padding: 0.25rem 0.75rem;
        border-radius: 20px;
        font-size: 0.75rem;
        font-weight: 600;
        background: rgba(255, 255, 255, 0.1);
        border: 1px solid rgba(255, 255, 255, 0.2);
    }
    
    .curso-badge.gold {
        background: rgba(255, 215, 112, 0.15);
        border-color: rgba(255, 215, 112, 0.3);
        color: #FFD770;
    }
    
    .curso-badge.green {
        background: rgba(7, 139, 108, 0.15);
        border-color: rgba(7, 139, 108, 0.3);
        color: #078B6C;
    }
    
    .curso-badge.blue {
        background: rgba(59, 130, 246, 0.15);
        border-color: rgba(59, 130, 246, 0.3);
        color: #60A5FA;
    }
    
    /* PROGRESS BAR MODERNA */
    .curso-progress {
        background: rgba(255, 255, 255, 0.05);
        border-radius: 10px;
        height: 10px;
        overflow: hidden;
        margin: 0.75rem 0;
    }
    
    .curso-progress-fill {
        height: 100%;
        background: linear-gradient(90deg, #078B6C 0%, #FFD770 100%);
        border-radius: 10px;
        transition: width 0.5s ease;
    }
    
    /* BOTÕES MODERNOS */
    .curso-btn {
        background: linear-gradient(135deg, #078B6C 0%, #056853 100%) !important;
        color: white !important;
        border: none !important;
        border-radius: 12px !important;
        padding: 0.75rem 1.5rem !important;
        font-weight: 600 !important;
        transition: all 0.3s ease !important;
        box-shadow: 0 4px 15px rgba(7, 139, 108, 0.3) !important;
        width: 100%;
        margin-top: auto;
    }
    
    .curso-btn:hover {
        background: linear-gradient(135deg, #FFD770 0%, #E6B91E 100%) !important;
        transform: translateY(-2px) !important;
        box-shadow: 0 8px 25px rgba(255, 215, 112, 0.4) !important;
        color: #0e2d26 !important;
    }
    
    .curso-btn-outline {
        background: transparent !important;
        color: #FFD770 !important;
        border: 2px solid #FFD770 !important;
        border-radius: 12px !important;
        padding: 0.75rem 1.5rem !important;
        font-weight: 600 !important;
        transition: all 0.3s ease !important;
        width: 100%;
        margin-top: auto;
    }
    
    .curso-btn-outline:hover {
        background: #FFD770 !important;
        color: #0e2d26 !important;
        transform: translateY(-2px);
    }
    
    /* HEADER MODERNO */
    .curso-header {
        background: linear-gradient(135deg, rgba(14, 45, 38, 0.8) 0%, rgba(9, 31, 26, 0.9) 100%);
        border-bottom: 1px solid rgba(255, 215, 112, 0.2);
        padding: 1.5rem;
        border-radius: 0 0 20px 20px;
        margin-bottom: 2rem;
    }
    
    /* STATS CARDS */
    .stats-card-moderno {
        background: rgba(255, 255, 255, 0.03);
        border: 1px solid rgba(255, 255, 255, 0.05);
        border-radius: 16px;
        padding: 1.5rem;
        text-align: center;
        transition: all 0.3s ease;
    }
    
    .stats-card-moderno:hover {
        background: rgba(255, 255, 255, 0.05);
        border-color: #FFD770;
        transform: translateY(-4px);
    }
    
    .stats-value-moderno {
        font-size: 2.5rem;
        font-weight: 700;
        background: linear-gradient(135deg, #FFD770 0%, #FFFFFF 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        margin: 0.5rem 0;
    }
    
    .stats-label-moderno {
        color: rgba(255, 255, 255, 0.7);
        font-size: 0.9rem;
        text-transform: uppercase;
        letter-spacing: 1px;
    }
    
    /* EMPTY STATE */
    .empty-state {
        text-align: center;
        padding: 4rem 2rem;
        border-radius: 20px;
        background: rgba(255,255,255,0.02);
        border: 2px dashed rgba(255,215,112,0.2);
    }
    
    .empty-state-icon {
        font-size: 4rem;
        margin-bottom: 1rem;
        opacity: 0.5;
    }
    
    </style>
    """, unsafe_allow_html=True)

# ======================================================
# PÁGINA PRINCIPAL DE CURSOS
# ======================================================

def pagina_cursos(usuario: dict):
    """Página principal do sistema de cursos"""
    
    aplicar_estilos_cursos()
    
    # Header moderno
    st.markdown(f"""
    <div class="curso-header">
        <h1 style="margin-bottom: 0.5rem; text-align: center;">🎓 Portal de Cursos BJJ</h1>
        <p style="text-align: center; opacity: 0.8; margin: 0;">
            Bem-vindo(a), <strong style="color: #FFD770;">{usuario.get('nome','Usuário').split()[0]}</strong> • 
            {usuario.get('tipo', 'aluno').capitalize()}
        </p>
    </div>
    """, unsafe_allow_html=True)
    
    tipo = str(usuario.get("tipo", "aluno")).lower()
    
    # Botão de voltar
    if st.button("← Voltar ao Início", key="btn_voltar_cursos", use_container_width=False):
        st.session_state.menu_selection = "Início"
        st.rerun()
    
    st.markdown("<br>", unsafe_allow_html=True)
    
    if tipo in ["admin", "professor"]:
        _interface_professor_moderna(usuario)
    else:
        _interface_aluno_moderna(usuario)

# ======================================================
# INTERFACE DO PROFESSOR / ADMIN
# ======================================================

def _interface_professor_moderna(usuario: dict):
    """Interface moderna para professores/admin"""
    
    tab1, tab2, tab3 = st.tabs([
        "📘 Meus Cursos",
        "➕ Criar Novo",
        "📊 Dashboard"
    ])
    
    with tab1:
        _professor_listar_cursos(usuario)
    
    with tab2:
        _professor_criar_curso(usuario)
    
    with tab3:
        _professor_dashboard(usuario)

def _professor_listar_cursos(usuario: dict):
    """Lista cursos do professor com design moderno"""
    
    try:
        cursos = listar_cursos_do_professor(usuario["id"])
    except Exception as e:
        st.error(f"❌ Erro ao carregar cursos: {e}")
        cursos = []
    
    if not cursos:
        st.markdown("""
        <div class="empty-state">
            <div class="empty-state-icon">📭</div>
            <h3 style="color: #FFD770;">Nenhum Curso Criado</h3>
            <p style="opacity: 0.7; max-width: 400px; margin: 0 auto;">
                Você ainda não criou nenhum curso. Use a aba <strong>Criar Novo</strong> 
                para começar a compartilhar seu conhecimento!
            </p>
        </div>
        """, unsafe_allow_html=True)
        return
    
    # Filtros
    with st.expander("🔍 Filtros Avançados", expanded=False):
        col1, col2, col3 = st.columns(3)
        
        with col1:
            status_filter = st.multiselect(
                "Status",
                ["Ativo", "Inativo", "Rascunho"],
                default=["Ativo"]
            )
        
        with col2:
            modalidades = list(set([c.get('modalidade', 'EAD') for c in cursos]))
            modalidade_filter = st.multiselect(
                "Modalidade",
                modalidades,
                default=modalidades
            )
        
        with col3:
            tipo_filter = st.multiselect(
                "Tipo",
                ["Gratuito", "Pago"],
                default=["Gratuito", "Pago"]
            )
    
    # Filtra cursos
    cursos_filtrados = []
    for curso in cursos:
        status = "Ativo" if curso.get('ativo', True) else "Inativo"
        status = "Rascunho" if curso.get('status') == 'rascunho' else status
        modalidade = curso.get('modalidade', 'EAD')
        pago = "Pago" if curso.get("pago") else "Gratuito"
        
        if status_filter and status not in status_filter:
            continue
        if modalidade_filter and modalidade not in modalidade_filter:
            continue
        if tipo_filter and pago not in tipo_filter:
            continue
        
        cursos_filtrados.append(curso)
    
    # Métricas
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.markdown(f"""
        <div class="stats-card-moderno">
            <div class="stats-value-moderno">{len(cursos_filtrados)}</div>
            <div class="stats-label-moderno">Cursos</div>
        </div>
        """, unsafe_allow_html=True)
    
    with col2:
        ativos = sum(1 for c in cursos_filtrados if c.get('ativo', True))
        st.markdown(f"""
        <div class="stats-card-moderno">
            <div class="stats-value-moderno">{ativos}</div>
            <div class="stats-label-moderno">Ativos</div>
        </div>
        """, unsafe_allow_html=True)
    
    with col3:
        gratuitos = sum(1 for c in cursos_filtrados if not c.get('pago', False))
        st.markdown(f"""
        <div class="stats-card-moderno">
            <div class="stats-value-moderno">{gratuitos}</div>
            <div class="stats-label-moderno">Gratuitos</div>
        </div>
        """, unsafe_allow_html=True)
    
    with col4:
        pagos = sum(1 for c in cursos_filtrados if c.get('pago', False))
        st.markdown(f"""
        <div class="stats-card-moderno">
            <div class="stats-value-moderno">{pagos}</div>
            <div class="stats-label-moderno">Pagos</div>
        </div>
        """, unsafe_allow_html=True)
    
    st.markdown("---")
    
    # Grid de cursos
    st.markdown("### 🎯 Meus Cursos")
    
    if not cursos_filtrados:
        st.info("Nenhum curso encontrado com os filtros aplicados.")
        return
    
    cols = st.columns(3)
    for idx, curso in enumerate(cursos_filtrados):
        with cols[idx % 3]:
            _render_card_curso_professor(curso, usuario)

def _render_card_curso_professor(curso: dict, usuario: dict):
    """Renderiza card de curso para professor"""
    
    ativo = curso.get('ativo', True)
    pago = curso.get('pago', False)
    modalidade = curso.get('modalidade', 'EAD')
    publico = curso.get('publico', 'geral')
    
    # Determina classe do card
    card_class = "curso-card-moderno"
    if not ativo:
        card_class += " in-progress"
    
    # Ícone baseado no tipo
    icon = "🎓" if ativo else "⏸️"
    if pago:
        icon = "💎" if ativo else "💸"
    
    # Badges
    badges_html = f"""
    <div class="curso-badges">
        <span class="curso-badge {'gold' if ativo else ''}">{"🟢 Ativo" if ativo else "🔴 Inativo"}</span>
        <span class="curso-badge green">{modalidade}</span>
        <span class="curso-badge blue">{"👥 Equipe" if publico == 'equipe' else "🌍 Geral"}</span>
    </div>
    """
    
    # Informações de preço
    preco_html = ""
    if pago:
        preco = curso.get('preco', 0)
        split = curso.get('split_custom', 10)
        preco_html = f"""
        <div style="margin: 1rem 0; padding: 0.75rem; background: rgba(255,215,112,0.1); border-radius: 10px;">
            <div style="font-size: 1.5rem; font-weight: bold; color: #FFD770;">R$ {preco:.2f}</div>
            <div style="font-size: 0.85rem; opacity: 0.8;">Taxa: {split}% • Receita líquida: R$ {preco * (1 - split/100):.2f}</div>
        </div>
        """
    else:
        preco_html = """
        <div style="margin: 1rem 0; padding: 0.75rem; background: rgba(7,139,108,0.1); border-radius: 10px;">
            <div style="font-size: 1.25rem; font-weight: bold; color: #078B6C;">🎯 Curso Gratuito</div>
            <div style="font-size: 0.85rem; opacity: 0.8;">Sem custos para os alunos</div>
        </div>
        """
    
    # Descrição
    desc = curso.get('descricao', 'Sem descrição')
    if len(desc) > 120:
        desc = desc[:120] + "..."
    
    # HTML do card
    st.markdown(f"""
    <div class="{card_class}">
        <div class="curso-icon">{icon}</div>
        <h4 style="margin: 0 0 0.5rem 0;">{curso.get('titulo', 'Sem Título')}</h4>
        <p style="opacity: 0.8; margin-bottom: 1rem; flex-grow: 1;">{desc}</p>
        
        {badges_html}
        {preco_html}
        
        <div style="margin-top: auto; display: flex; gap: 0.5rem;">
            <button class="curso-btn" id="btn_editar_{curso['id']}">✏️ Editar</button>
            <button class="curso-btn-outline" id="btn_ver_{curso['id']}">👁️ Ver</button>
        </div>
    </div>
    """, unsafe_allow_html=True)
    
    # Botões funcionais
    col1, col2 = st.columns(2)
    with col1:
        if st.button("✏️ Editar", key=f"edit_{curso['id']}", use_container_width=True):
            st.session_state['edit_curso'] = curso
            st.info("🎯 Funcionalidade de edição em desenvolvimento!")
    
    with col2:
        if st.button("👁️ Ver", key=f"view_{curso['id']}", use_container_width=True):
            st.info("🎯 Visualização detalhada em desenvolvimento!")

def _professor_criar_curso(usuario: dict):
    """Formulário moderno para criar cursos"""
    
    st.markdown("""
    <div style="background: rgba(255,255,255,0.05); padding: 1.5rem; border-radius: 20px; margin-bottom: 2rem;">
        <h3 style="margin: 0 0 0.5rem 0;">🚀 Criar Novo Curso</h3>
        <p style="opacity: 0.8; margin: 0;">Preencha os detalhes abaixo para criar um curso incrível!</p>
    </div>
    """, unsafe_allow_html=True)
    
    with st.form("form_criar_curso_moderno", border=True):
        
        st.markdown("### 📝 Informações Básicas")
        
        col1, col2 = st.columns([2, 1])
        
        with col1:
            titulo = st.text_input(
                "Título do Curso *",
                placeholder="Ex: Fundamentos do Jiu-Jitsu para Iniciantes",
                help="Um título claro e atrativo para seu curso"
            )
            
            descricao = st.text_area(
                "Descrição Detalhada *",
                height=120,
                placeholder="Descreva o que os alunos aprenderão, pré-requisitos, metodologia...",
                help="Seja detalhado para atrair os alunos certos"
            )
        
        with col2:
            modalidade = st.selectbox(
                "Modalidade *",
                ["EAD", "Presencial", "Híbrido"],
                help="Como o curso será ministrado"
            )
            
            publico = st.selectbox(
                "Público Alvo *",
                ["geral", "equipe"],
                format_func=lambda v: "🌍 Geral (Público Aberto)" if v == "geral" else "👥 Apenas Minha Equipe",
                help="Quem poderá acessar este curso"
            )
            
            equipe_destino = None
            if publico == "equipe":
                equipe_destino = st.text_input(
                    "Nome da Equipe *",
                    placeholder="Ex: Equipe BJJ Champions",
                    help="Apenas membros desta equipe poderão se inscrever"
                )
        
        st.markdown("---")
        st.markdown("### ⚙️ Configurações")
        
        col3, col4 = st.columns(2)
        
        with col3:
            certificado_auto = st.checkbox(
                "Emitir certificado automaticamente",
                value=True,
                help="Alunos receberão certificado ao concluir 100% do curso"
            )
            
            max_alunos = st.number_input(
                "Número Máximo de Alunos",
                min_value=0,
                value=0,
                help="0 = sem limite"
            )
        
        with col4:
            duracao_estimada = st.text_input(
                "Duração Estimada",
                placeholder="Ex: 8 semanas, 40 horas",
                help="Tempo estimado para conclusão"
            )
            
            nivel = st.selectbox(
                "Nível do Curso",
                ["Iniciante", "Intermediário", "Avançado", "Todos os Níveis"],
                index=2
            )
        
        st.markdown("---")
        st.markdown("### 💰 Configurações Financeiras")
        
        col5, col6, col7 = st.columns([1, 1, 1])
        
        with col5:
            pago = st.toggle(
                "Curso Pago?",
                value=False,
                help="Se ativado, os alunos pagarão para acessar"
            )
        
        with col6:
            preco = st.number_input(
                "Valor (R$)",
                min_value=0.0,
                value=0.0,
                step=10.0,
                disabled=not pago,
                help="Valor total do curso"
            )
        
        with col7:
            is_admin = usuario.get("tipo") == "admin"
            
            if pago and is_admin:
                split_custom = st.slider(
                    "Taxa da Plataforma (%)",
                    0, 100,
                    value=10,
                    help="Percentual que a plataforma fica"
                )
            elif pago:
                split_custom = 10
                st.caption(f"Taxa da plataforma: {split_custom}%")
                st.info("Apenas administradores podem alterar a taxa.")
            else:
                split_custom = None
        
        st.markdown("---")
        
        # Botão de submit
        col_submit1, col_submit2 = st.columns([1, 3])
        
        with col_submit1:
            if st.form_submit_button("❌ Cancelar", use_container_width=True):
                st.info("Operação cancelada.")
        
        with col_submit2:
            submit = st.form_submit_button(
                "🚀 Criar Curso Agora",
                type="primary",
                use_container_width=True
            )
            
            if submit:
                # Validações
                erros = []
                
                if not titulo.strip():
                    erros.append("⚠️ O título é obrigatório.")
                
                if not descricao.strip():
                    erros.append("⚠️ A descrição é obrigatória.")
                
                if publico == "equipe" and (not equipe_destino or not equipe_destino.strip()):
                    erros.append("⚠️ Informe o nome da equipe para cursos restritos.")
                
                if pago and preco <= 0:
                    erros.append("⚠️ Cursos pagos devem ter valor maior que zero.")
                
                if erros:
                    for erro in erros:
                        st.error(erro)
                    return
                
                # Criação do curso
                try:
                    curso_id = criar_curso(
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
                    )
                    
                    st.success("🎉 Curso criado com sucesso!")
                    st.balloons()
                    
                    st.markdown(f"""
                    <div style="background: rgba(7, 139, 108, 0.1); padding: 1.5rem; border-radius: 12px; margin-top: 1rem;">
                        <h4 style="color: #078B6C; margin-top: 0;">✅ Curso Criado!</h4>
                        <p><strong>ID:</strong> <code>{curso_id}</code></p>
                        <p><strong>Próximos passos:</strong></p>
                        <ol style="margin-left: 1.5rem;">
                            <li>Adicione módulos e aulas ao curso</li>
                            <li>Configure datas e prazos (se necessário)</li>
                            <li>Divulgue para seus alunos!</li>
                        </ol>
                    </div>
                    """, unsafe_allow_html=True)
                    
                    time.sleep(2)
                    st.rerun()
                    
                except Exception as e:
                    st.error(f"❌ Erro ao criar curso: {e}")

def _professor_dashboard(usuario: dict):
    """Dashboard do professor"""
    
    st.markdown("### 📊 Dashboard do Instrutor")
    
    try:
        cursos = listar_cursos_do_professor(usuario["id"])
    except:
        st.error("Erro ao carregar dados.")
        return
    
    if not cursos:
        st.info("Nenhum curso encontrado para exibir estatísticas.")
        return
    
    # Estatísticas básicas
    total_cursos = len(cursos)
    cursos_ativos = sum(1 for c in cursos if c.get('ativo', True))
    cursos_pagos = sum(1 for c in cursos if c.get('pago', False))
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.markdown(f"""
        <div class="stats-card-moderno">
            <div class="stats-value-moderno">{total_cursos}</div>
            <div class="stats-label-moderno">Total de Cursos</div>
        </div>
        """, unsafe_allow_html=True)
    
    with col2:
        st.markdown(f"""
        <div class="stats-card-moderno">
            <div class="stats-value-moderno">{cursos_ativos}</div>
            <div class="stats-label-moderno">Cursos Ativos</div>
        </div>
        """, unsafe_allow_html=True)
    
    with col3:
        st.markdown(f"""
        <div class="stats-card-moderno">
            <div class="stats-value-moderno">{cursos_pagos}</div>
            <div class="stats-label-moderno">Cursos Pagos</div>
        </div>
        """, unsafe_allow_html=True)
    
    st.markdown("---")
    
    # Gráfico de distribuição (simplificado)
    st.markdown("#### 📈 Distribuição por Modalidade")
    
    modalidades = {}
    for curso in cursos:
        mod = curso.get('modalidade', 'EAD')
        modalidades[mod] = modalidades.get(mod, 0) + 1
    
    if modalidades:
        df_mod = pd.DataFrame({
            'Modalidade': list(modalidades.keys()),
            'Quantidade': list(modalidades.values())
        })
        
        # Gráfico de barras
        import plotly.express as px
        fig = px.bar(
            df_mod,
            x='Modalidade',
            y='Quantidade',
            color='Modalidade',
            color_discrete_sequence=['#078B6C', '#FFD770', '#3B82F6'],
            text='Quantidade'
        )
        
        fig.update_layout(
            paper_bgcolor='rgba(0,0,0,0)',
            plot_bgcolor='rgba(0,0,0,0)',
            font=dict(color='#FFFFFF'),
            showlegend=False
        )
        
        st.plotly_chart(fig, use_container_width=True)
    
    # Lista de cursos recentes
    st.markdown("#### 📋 Cursos Recentes")
    
    cursos_recentes = sorted(cursos, 
                           key=lambda x: x.get('criado_em', datetime.min), 
                           reverse=True)[:5]
    
    for curso in cursos_recentes:
        with st.container(border=True):
            col1, col2, col3 = st.columns([3, 1, 1])
            
            with col1:
                st.markdown(f"**{curso.get('titulo', 'Sem Título')}**")
                st.caption(f"Criado em: {curso.get('criado_em', 'Data não disponível')}")
            
            with col2:
                status = "🟢 Ativo" if curso.get('ativo', True) else "🔴 Inativo"
                st.markdown(f"`{status}`")
            
            with col3:
                if st.button("Ver", key=f"dash_view_{curso.get('id', '')}"):
                    st.info("Visualização em desenvolvimento")

# ======================================================
# INTERFACE DO ALUNO
# ======================================================

def _interface_aluno_moderna(usuario: dict):
    """Interface moderna para alunos"""
    
    tab1, tab2 = st.tabs([
        "🛒 Cursos Disponíveis",
        "🎓 Meus Cursos"
    ])
    
    with tab1:
        _aluno_cursos_disponiveis(usuario)
    
    with tab2:
        _aluno_meus_cursos(usuario)

def _aluno_cursos_disponiveis(usuario: dict):
    """Cursos disponíveis para o aluno"""
    
    st.markdown("### 🎯 Cursos Disponíveis")
    st.markdown("Escolha um curso para começar sua jornada no Jiu-Jitsu!")
    
    try:
        cursos = listar_cursos_disponiveis_para_usuario(usuario)
    except Exception as e:
        st.error(f"Erro ao carregar cursos: {e}")
        cursos = []
    
    if not cursos:
        st.markdown("""
        <div class="empty-state">
            <div class="empty-state-icon">📭</div>
            <h3 style="color: #FFD770;">Nenhum Curso Disponível</h3>
            <p style="opacity: 0.7; max-width: 400px; margin: 0 auto;">
                No momento não há cursos disponíveis para sua conta.
                Entre em contato com seu professor ou volte mais tarde!
            </p>
        </div>
        """, unsafe_allow_html=True)
        return
    
    # Filtros
    with st.expander("🔍 Filtrar Cursos", expanded=False):
        col1, col2 = st.columns(2)
        
        with col1:
            termo_busca = st.text_input(
                "Buscar por título ou descrição...",
                placeholder="Digite palavras-chave"
            )
        
        with col2:
            tipo_filtro = st.selectbox(
                "Tipo",
                ["Todos", "Gratuitos", "Pagos", "EAD", "Presencial"]
            )
    
    # Filtra cursos
    cursos_filtrados = []
    for curso in cursos:
        # Filtro de texto
        if termo_busca:
            termo = termo_busca.lower()
            titulo = curso.get('titulo', '').lower()
            desc = curso.get('descricao', '').lower()
            
            if termo not in titulo and termo not in desc:
                continue
        
        # Filtro de tipo
        if tipo_filtro == "Gratuitos" and curso.get("pago"):
            continue
        if tipo_filtro == "Pagos" and not curso.get("pago"):
            continue
        if tipo_filtro == "EAD" and curso.get("modalidade") != "EAD":
            continue
        if tipo_filtro == "Presencial" and curso.get("modalidade") != "Presencial":
            continue
        
        cursos_filtrados.append(curso)
    
    st.markdown(f"#### 📚 Resultados ({len(cursos_filtrados)} cursos)")
    
    if not cursos_filtrados:
        st.warning("Nenhum curso encontrado com os filtros aplicados.")
        return
    
    # Grid de cursos
    cols = st.columns(3)
    for idx, curso in enumerate(cursos_filtrados):
        with cols[idx % 3]:
            _render_card_curso_aluno(curso, usuario)

def _render_card_curso_aluno(curso: dict, usuario: dict):
    """Renderiza card de curso para aluno"""
    
    # Verifica se já está inscrito
    try:
        inscricao = obter_inscricao(usuario["id"], curso["id"])
        ja_inscrito = inscricao is not None
    except:
        ja_inscrito = False
    
    pago = curso.get("pago", False)
    modalidade = curso.get("modalidade", "EAD")
    professor = curso.get("professor_nome", "Professor")
    
    # Determina classe do card
    card_class = "curso-card-moderno"
    if ja_inscrito:
        card_class += " completed"
    
    # Ícone
    icon = "🎓" if ja_inscrito else "📚"
    if pago:
        icon = "💎" if ja_inscrito else "🔒"
    
    # Badges
    badges_html = f"""
    <div class="curso-badges">
        <span class="curso-badge {'gold' if ja_inscrito else 'green'}">
            {"✅ Inscrito" if ja_inscrito else "🎯 Disponível"}
        </span>
        <span class="curso-badge green">{modalidade}</span>
    </div>
    """
    
    # Informações de preço
    preco_html = ""
    if pago:
        preco = curso.get('preco', 0)
        preco_html = f"""
        <div style="margin: 1rem 0; padding: 0.75rem; background: rgba(255,215,112,0.1); border-radius: 10px;">
            <div style="font-size: 1.5rem; font-weight: bold; color: #FFD770;">R$ {preco:.2f}</div>
            <div style="font-size: 0.85rem; opacity: 0.8;">Acesso vitalício • Certificado inclusivo</div>
        </div>
        """
    else:
        preco_html = """
        <div style="margin: 1rem 0; padding: 0.75rem; background: rgba(7,139,108,0.1); border-radius: 10px;">
            <div style="font-size: 1.25rem; font-weight: bold; color: #078B6C;">🎯 Gratuito</div>
            <div style="font-size: 0.85rem; opacity: 0.8;">Sem custos • Acesso imediato</div>
        </div>
        """
    
    # Descrição
    desc = curso.get('descricao', 'Sem descrição disponível.')
    if len(desc) > 100:
        desc = desc[:100] + "..."
    
    # Professor
    professor_html = f"""
    <div style="margin: 0.5rem 0; padding: 0.5rem; background: rgba(255,255,255,0.05); border-radius: 8px;">
        <div style="font-size: 0.9rem; opacity: 0.8;">👨‍🏫 Instrutor</div>
        <div style="font-weight: 600;">{professor}</div>
    </div>
    """
    
    # HTML do card
    st.markdown(f"""
    <div class="{card_class}">
        <div class="curso-icon">{icon}</div>
        <h4 style="margin: 0 0 0.5rem 0;">{curso.get('titulo', 'Sem Título')}</h4>
        <p style="opacity: 0.8; margin-bottom: 1rem; flex-grow: 1;">{desc}</p>
        
        {professor_html}
        {badges_html}
        {preco_html}
        
        <button class="{'curso-btn' if not ja_inscrito else 'curso-btn-outline'}" id="btn_curso_{curso['id']}">
            {"🔓 Inscrever-se" if not ja_inscrito else "🎬 Acessar Curso"}
        </button>
    </div>
    """, unsafe_allow_html=True)
    
    # Botão funcional
    if ja_inscrito:
        if st.button("🎬 Acessar Curso", key=f"access_{curso['id']}", use_container_width=True):
            st.info("🎯 Sistema de aulas em desenvolvimento!")
            st.write("Em breve você poderá acessar todas as aulas deste curso.")
    else:
        if st.button("🔓 Inscrever-se", key=f"enroll_{curso['id']}", use_container_width=True, type="primary"):
            try:
                inscrever_usuario_em_curso(usuario["id"], curso["id"])
                st.success("🎉 Inscrição realizada com sucesso!")
                time.sleep(1)
                st.rerun()
            except Exception as e:
                st.error(f"Erro na inscrição: {e}")

def _aluno_meus_cursos(usuario: dict):
    """Cursos em que o aluno está inscrito"""
    
    st.markdown("### 🎓 Meus Cursos")
    
    try:
        # Busca todos os cursos disponíveis primeiro
        todos_cursos = listar_cursos_disponiveis_para_usuario(usuario)
        
        # Filtra apenas os que tem inscrição
        meus_cursos = []
        for curso in todos_cursos:
            inscricao = obter_inscricao(usuario["id"], curso["id"])
            if inscricao:
                curso["progresso"] = inscricao.get("progresso", 0)
                curso["inscricao_data"] = inscricao.get("criado_em", "")
                meus_cursos.append(curso)
    
    except Exception as e:
        st.error(f"Erro ao carregar cursos: {e}")
        meus_cursos = []
    
    if not meus_cursos:
        st.markdown("""
        <div class="empty-state">
            <div class="empty-state-icon">📚</div>
            <h3 style="color: #FFD770;">Nenhum Curso Inscrito</h3>
            <p style="opacity: 0.7; max-width: 400px; margin: 0 auto;">
                Você ainda não está inscrito em nenhum curso.
                Explore a aba <strong>Cursos Disponíveis</strong> para começar sua jornada!
            </p>
        </div>
        """, unsafe_allow_html=True)
        return
    
    # Separa por status
    cursos_andamento = []
    cursos_concluidos = []
    
    for curso in meus_cursos:
        progresso = curso.get("progresso", 0)
        if progresso >= 100:
            cursos_concluidos.append(curso)
        else:
            cursos_andamento.append(curso)
    
    # Métricas
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.markdown(f"""
        <div class="stats-card-moderno">
            <div class="stats-value-moderno">{len(meus_cursos)}</div>
            <div class="stats-label-moderno">Total de Cursos</div>
        </div>
        """, unsafe_allow_html=True)
    
    with col2:
        st.markdown(f"""
        <div class="stats-card-moderno">
            <div class="stats-value-moderno">{len(cursos_andamento)}</div>
            <div class="stats-label-moderno">Em Andamento</div>
        </div>
        """, unsafe_allow_html=True)
    
    with col3:
        st.markdown(f"""
        <div class="stats-card-moderno">
            <div class="stats-value-moderno">{len(cursos_concluidos)}</div>
            <div class="stats-label-moderno">Concluídos</div>
        </div>
        """, unsafe_allow_html=True)
    
    # Cursos em andamento
    if cursos_andamento:
        st.markdown("---")
        st.markdown(f"#### 🔄 Cursos em Andamento ({len(cursos_andamento)})")
        
        for curso in cursos_andamento:
            with st.container(border=True):
                col1, col2, col3 = st.columns([3, 2, 1])
                
                with col1:
                    st.markdown(f"**{curso.get('titulo', 'Curso')}**")
                    st.caption(f"Progresso: {curso.get('progresso', 0):.0f}%")
                    
                    # Barra de progresso
                    progresso = curso.get('progresso', 0)
                    st.markdown(f"""
                    <div class="curso-progress">
                        <div class="curso-progress-fill" style="width: {progresso}%"></div>
                    </div>
                    """, unsafe_allow_html=True)
                
                with col2:
                    modalidade = curso.get('modalidade', 'EAD')
                    st.markdown(f"**Modalidade:** {modalidade}")
                    
                    if curso.get('pago'):
                        st.markdown(f"**Valor:** R$ {curso.get('preco', 0):.2f}")
                
                with col3:
                    if st.button("Continuar", key=f"cont_{curso['id']}", use_container_width=True):
                        st.info("🎯 Sistema de aulas em desenvolvimento!")
    
    # Cursos concluídos
    if cursos_concluidos:
        st.markdown("---")
        st.markdown(f"#### 🏆 Cursos Concluídos ({len(cursos_concluidos)})")
        
        for curso in cursos_concluidos:
            with st.container(border=True):
                col1, col2, col3 = st.columns([3, 1, 1])
                
                with col1:
                    st.markdown(f"**{curso.get('titulo', 'Curso')}**")
                    st.success("✅ Curso concluído com sucesso!")
                
                with col2:
                    if st.button("📜 Certificado", key=f"cert_{curso['id']}", use_container_width=True):
                        st.info("🎯 Sistema de certificados em desenvolvimento!")
                
                with col3:
                    if st.button("🔁 Revisar", key=f"rev_{curso['id']}", use_container_width=True):
                        st.info("🎯 Sistema de revisão em desenvolvimento!")

# ======================================================
# FUNÇÃO AUXILIAR PARA NAVEGAÇÃO
# ======================================================

def navegar_para_aulas(curso_id: str):
    """Redireciona para a tela de aulas do curso"""
    st.session_state.curso_atual = curso_id
    st.rerun()
