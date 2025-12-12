# bjj_digital/views/cursos.py

import streamlit as st
import pandas as pd
from typing import Optional, Dict, List
from datetime import datetime
import plotly.express as px

# Ajuste os imports conforme a estrutura do seu projeto
from courses_engine import (
    criar_curso,
    listar_cursos_do_professor,
    listar_cursos_disponiveis_para_usuario,
    inscrever_usuario_em_curso,
    obter_inscricao,
)
from database import get_db

# ======================================================
# ESTILOS GLOBAIS
# ======================================================

def aplicar_estilos_cursos():
    """Aplica estilos CSS para a página de cursos"""
    st.markdown("""
    <style>
    /* Cards modernos */
    .curso-card {
        background: rgba(255, 255, 255, 0.05);
        border: 1px solid rgba(255, 255, 255, 0.1);
        border-radius: 16px;
        padding: 1.5rem;
        margin: 1rem 0;
        transition: all 0.3s ease;
    }
    
    .curso-card:hover {
        border-color: rgba(16, 185, 129, 0.3);
        transform: translateY(-2px);
        box-shadow: 0 10px 25px rgba(0, 0, 0, 0.2);
    }
    
    /* Badges */
    .badge {
        display: inline-block;
        padding: 4px 12px;
        border-radius: 20px;
        font-size: 0.85rem;
        font-weight: 600;
        margin: 2px;
    }
    
    .badge-verde {
        background: rgba(16, 185, 129, 0.2);
        color: #10b981;
        border: 1px solid rgba(16, 185, 129, 0.3);
    }
    
    .badge-amarelo {
        background: rgba(245, 158, 11, 0.2);
        color: #f59e0b;
        border: 1px solid rgba(245, 158, 11, 0.3);
    }
    
    .badge-vermelho {
        background: rgba(239, 68, 68, 0.2);
        color: #ef4444;
        border: 1px solid rgba(239, 68, 68, 0.3);
    }
    
    .badge-azul {
        background: rgba(59, 130, 246, 0.2);
        color: #3b82f6;
        border: 1px solid rgba(59, 130, 246, 0.3);
    }
    
    /* Modal customizado */
    .modal-overlay {
        position: fixed;
        top: 0;
        left: 0;
        right: 0;
        bottom: 0;
        background: rgba(0, 0, 0, 0.7);
        display: flex;
        align-items: center;
        justify-content: center;
        z-index: 9999;
    }
    
    .modal-content {
        background: linear-gradient(145deg, #1e293b, #0f172a);
        border: 1px solid rgba(255, 255, 255, 0.1);
        border-radius: 16px;
        padding: 2rem;
        width: 90%;
        max-width: 800px;
        max-height: 90vh;
        overflow-y: auto;
        box-shadow: 0 20px 60px rgba(0, 0, 0, 0.5);
    }
    
    /* Progress bars */
    .stProgress > div > div > div {
        background: linear-gradient(90deg, #10b981, #3b82f6);
        border-radius: 10px;
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
# PÁGINA PRINCIPAL
# ======================================================

def pagina_cursos(usuario: dict):
    """
    Interface de cursos, adaptada ao tipo de usuário.
    """
    # Aplicar estilos
    aplicar_estilos_cursos()
    
    tipo = str(usuario.get("tipo", "aluno")).lower()

    # Cabeçalho moderno
    st.markdown(f"""
    <div class="animate-fadeIn">
        <h1 style="margin-bottom: 0.5rem;">📚 Gestão de Cursos</h1>
        <div style="display: flex; align-items: center; gap: 1rem; opacity: 0.8;">
            <div>Bem-vindo, <strong>{usuario.get('nome', 'Usuário').split()[0]}</strong></div>
            <div>•</div>
            <div class="badge badge-azul">{tipo.capitalize()}</div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("---")

    # Verificar se há modal para mostrar
    if 'show_edit_modal' in st.session_state and st.session_state.show_edit_modal:
        _render_modal_editar_curso()
    
    if tipo in ["admin", "professor"]:
        _interface_professor_moderna(usuario)
    else:
        _interface_aluno_moderna(usuario)

# ======================================================
# VISÃO DO PROFESSOR / ADMIN MODERNA
# ======================================================

def _interface_professor_moderna(usuario: dict):
    """Interface moderna para professores/admins"""
    
    # Abas com ícones
    tab1, tab2, tab3 = st.tabs([
        "📘 Meus Cursos",
        "➕ Criar Curso", 
        "📊 Dashboard"
    ])

    with tab1:
        _prof_listar_cursos_moderno(usuario)

    with tab2:
        _prof_criar_curso_moderno(usuario)

    with tab3:
        _prof_dashboard_moderno(usuario)

def _prof_listar_cursos_moderno(usuario: dict):
    """Listagem moderna de cursos"""
    
    try:
        cursos = listar_cursos_do_professor(usuario["id"])
    except Exception as e:
        st.error(f"❌ Erro ao carregar cursos: {e}")
        cursos = []
    
    if not cursos:
        st.info("""
        🎯 **Você ainda não criou cursos!**
        
        Crie seu primeiro curso para compartilhar seu conhecimento com os alunos.
        Acesse a aba **"Criar Curso"** para começar.
        """)
        return
    
    # Filtros
    with st.expander("🔍 Filtros", expanded=True):
        col1, col2 = st.columns(2)
        
        with col1:
            status_filter = st.multiselect(
                "Status",
                ["Ativo", "Inativo"],
                default=["Ativo"]
            )
        
        with col2:
            modalidades = list(set([c.get('modalidade', 'EAD') for c in cursos]))
            modalidade_filter = st.multiselect(
                "Modalidade",
                modalidades,
                default=modalidades
            )
    
    # Aplicar filtros
    cursos_filtrados = []
    for curso in cursos:
        status = "Ativo" if curso.get('ativo', True) else "Inativo"
        modalidade = curso.get('modalidade', 'EAD')
        
        if status_filter and status not in status_filter:
            continue
        if modalidade_filter and modalidade not in modalidade_filter:
            continue
            
        cursos_filtrados.append(curso)
    
    # Métricas rápidas
    col_m1, col_m2, col_m3 = st.columns(3)
    with col_m1:
        total_cursos = len(cursos_filtrados)
        st.metric("Cursos", total_cursos)
    
    with col_m2:
        cursos_ativos = sum(1 for c in cursos_filtrados if c.get('ativo', True))
        st.metric("Ativos", cursos_ativos)
    
    with col_m3:
        cursos_gratuitos = sum(1 for c in cursos_filtrados if not c.get('pago', False))
        st.metric("Gratuitos", cursos_gratuitos)
    
    st.markdown("---")
    
    # Exibição em cards
    for curso in cursos_filtrados:
        _card_curso_professor(curso, usuario)

def _card_curso_professor(curso: dict, usuario: dict):
    """Card moderno para curso do professor"""
    
    with st.container():
        st.markdown("<div class='curso-card'>", unsafe_allow_html=True)
        
        col1, col2, col3 = st.columns([3, 1.5, 1])
        
        with col1:
            # Status
            ativo = curso.get('ativo', True)
            status_badge = "🟢 Ativo" if ativo else "🔴 Inativo"
            status_class = "badge-verde" if ativo else "badge-vermelho"
            
            # Título
            st.markdown(f"### {curso.get('titulo', 'Sem Título')}")
            
            # Badges
            col_badges = st.columns([1, 1, 2])
            with col_badges[0]:
                st.markdown(f"<span class='badge {status_class}'>{status_badge}</span>", unsafe_allow_html=True)
            
            with col_badges[1]:
                modalidade = curso.get('modalidade', '-')
                st.markdown(f"<span class='badge badge-azul'>{modalidade}</span>", unsafe_allow_html=True)
            
            with col_badges[2]:
                publico = 'Equipe' if curso.get('publico') == 'equipe' else 'Geral'
                st.markdown(f"<span class='badge badge-amarelo'>{publico}</span>", unsafe_allow_html=True)
            
            # Descrição
            desc = curso.get("descricao", "")
            if desc:
                st.markdown(f"<div style='opacity: 0.8; margin-top: 0.5rem;'>{desc[:150]}...</div>", unsafe_allow_html=True)
        
        with col2:
            # Informações financeiras
            if curso.get("pago"):
                preco = curso.get('preco', 0.0)
                split = int(curso.get('split_custom', 10))
                
                st.metric("Preço", f"R$ {preco:.2f}")
                st.caption(f"Taxa: {split}%")
            else:
                st.metric("Preço", "Gratuito")
                st.caption("Sem taxa")
        
        with col3:
            st.write("")  # Espaçamento
            
            # Botões de ação
            col_btn1, col_btn2 = st.columns(2)
            
            with col_btn1:
                if st.button("✏️", key=f"edit_{curso['id']}", help="Editar curso", use_container_width=True):
                    st.session_state['edit_curso'] = curso
                    st.session_state['show_edit_modal'] = True
                    st.rerun()
            
            with col_btn2:
                if ativo:
                    if st.button("⏸️", key=f"pause_{curso['id']}", help="Pausar curso", use_container_width=True):
                        _toggle_status_curso(curso["id"], False)
                        st.rerun()
                else:
                    if st.button("▶️", key=f"play_{curso['id']}", help="Ativar curso", use_container_width=True):
                        _toggle_status_curso(curso["id"], True)
                        st.rerun()
        
        st.markdown("</div>", unsafe_allow_html=True)

def _prof_criar_curso_moderno(usuario: dict):
    """Formulário moderno para criação de curso"""
    
    st.markdown("""
    <div style="background: linear-gradient(135deg, rgba(16,185,129,0.1), rgba(59,130,246,0.1)); 
                padding: 1.5rem; border-radius: 16px; margin-bottom: 2rem;">
        <h3 style="margin: 0;">🎯 Criar Novo Curso</h3>
        <p style="opacity: 0.8; margin-top: 0.5rem;">Preencha os detalhes abaixo para criar seu curso</p>
    </div>
    """, unsafe_allow_html=True)
    
    with st.form("form_criar_curso_moderno", border=True):
        # Informações básicas
        st.markdown("#### 📝 Informações do Curso")
        
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
                placeholder="Descreva o que os alunos aprenderão, metodologia, pré-requisitos...",
                help="Quanto mais detalhada, melhor para atrair alunos"
            )
        
        with col2:
            modalidade = st.selectbox(
                "Modalidade *",
                ["EAD", "Presencial", "Híbrido"],
                help="Como o curso será ministrado?"
            )
            
            publico = st.selectbox(
                "Público Alvo *",
                ["geral", "equipe"],
                format_func=lambda v: "🌍 Aberto (Geral)" if v == "geral" else "👥 Restrito (Equipe)"
            )
            
            equipe_destino = None
            if publico == "equipe":
                equipe_destino = st.text_input(
                    "Nome da Equipe *",
                    placeholder="Digite o nome da equipe",
                    help="Apenas membros desta equipe poderão acessar"
                )
        
        # Configurações
        st.markdown("#### ⚙️ Configurações")
        
        col_config1, col_config2 = st.columns(2)
        
        with col_config1:
            certificado_auto = st.checkbox(
                "Emitir certificado automaticamente",
                value=True,
                help="O certificado será gerado automatically ao concluir o curso"
            )
        
        with col_config2:
            # Configurações avançadas
            with st.expander("Configurações Avançadas"):
                max_alunos = st.number_input(
                    "Vagas disponíveis",
                    min_value=0,
                    value=0,
                    help="0 = ilimitado"
                )
                
                duracao_estimada = st.text_input(
                    "Duração estimada",
                    placeholder="Ex: 8 semanas, 40 horas"
                )
        
        # Valores
        st.markdown("#### 💰 Valores")
        
        col_val1, col_val2, col_val3 = st.columns(3)
        
        with col_val1:
            pago = st.toggle(
                "Curso Pago?",
                value=False,
                help="O curso terá valor ou será gratuito?"
            )
        
        with col_val2:
            preco = st.number_input(
                "Valor (R$) *" if pago else "Valor (R$)",
                min_value=0.0,
                value=0.0 if not pago else 197.00,
                step=10.0,
                disabled=not pago,
                help="Valor total do curso"
            )
        
        with col_val3:
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
                if pago and not is_admin:
                    st.info(f"Taxa da plataforma: {split_custom}%")
        
        # Botão de envio
        st.markdown("---")
        submit_btn = st.form_submit_button(
            "🚀 Criar Curso",
            type="primary",
            use_container_width=True
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
                        certificado_automatico=certificado_auto
                    )
                    
                    st.success("""
                    🎉 **Curso criado com sucesso!**
                    
                    Seu curso já está disponível para matrículas. 
                    Acesse a aba "Meus Cursos" para gerenciá-lo.
                    """)
                    
                    time.sleep(2)
                    st.rerun()
                    
                except Exception as e:
                    st.error(f"""
                    ❌ **Erro ao criar curso:**
                    
                    ```{str(e)}```
                    
                    Verifique os dados e tente novamente.
                    """)

def _prof_dashboard_moderno(usuario: dict):
    """Dashboard moderno para professores"""
    
    db = get_db()
    if not db:
        st.error("❌ Erro de conexão com o banco de dados.")
        return
    
    try:
        cursos = listar_cursos_do_professor(usuario["id"])
    except Exception as e:
        st.error(f"❌ Erro ao carregar cursos: {e}")
        cursos = []
    
    if not cursos:
        st.info("📭 Você ainda não criou cursos. Crie um curso para visualizar o dashboard.")
        return
    
    # Coletar estatísticas
    total_inscritos = 0
    total_receita = 0
    progresso_medio = 0
    cursos_ativos = 0
    
    for curso in cursos:
        if curso.get('ativo', True):
            cursos_ativos += 1
        
        try:
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
        except:
            continue
    
    if total_inscritos > 0:
        progresso_medio = progresso_medio / total_inscritos
    
    # Métricas
    st.markdown("### 📈 Estatísticas Gerais")
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("Cursos Ativos", cursos_ativos, f"de {len(cursos)} total")
    
    with col2:
        st.metric("Alunos", total_inscritos, "matriculados")
    
    with col3:
        st.metric("Receita", f"R$ {total_receita:.2f}", "líquida estimada")
    
    with col4:
        st.metric("Progresso", f"{progresso_medio:.0f}%", "médio dos alunos")
    
    st.markdown("---")
    
    # Seleção de curso para detalhes
    if cursos:
        st.markdown("### 📊 Detalhes por Curso")
        
        # Lista de cursos para seleção
        curso_opcoes = {c["titulo"]: c["id"] for c in cursos}
        curso_selecionado = st.selectbox(
            "Selecione um curso para ver detalhes:",
            list(curso_opcoes.keys())
        )
        
        curso_id = curso_opcoes[curso_selecionado]
        
        try:
            # Buscar inscrições do curso selecionado
            inscricoes_ref = db.collection("enrollments").where("course_id", "==", curso_id).stream()
            inscricoes = []
            
            for ins in inscricoes_ref:
                dados = ins.to_dict()
                dados["inscricao_id"] = ins.id
                inscricoes.append(dados)
            
            if inscricoes:
                # Preparar dados para tabela
                dados_tabela = []
                
                for ins in inscricoes:
                    # Buscar nome do aluno
                    aluno_ref = db.collection("usuarios").document(ins.get("user_id")).get()
                    nome_aluno = aluno_ref.to_dict().get("nome", "Sem nome") if aluno_ref.exists else "Sem nome"
                    
                    dados_tabela.append({
                        "Aluno": nome_aluno,
                        "Progresso": f"{ins.get('progresso', 0):.0f}%",
                        "Pagamento": "✅ Pago" if ins.get("pago") else "⏳ Pendente",
                        "Certificado": "✅ Emitido" if ins.get("certificado_emitido") else "⏳ Aguardando"
                    })
                
                # Exibir tabela
                df = pd.DataFrame(dados_tabela)
                st.dataframe(df, use_container_width=True, hide_index=True)
                
                # Gráfico de progresso
                if len(dados_tabela) > 0:
                    st.markdown("#### 📈 Distribuição de Progresso")
                    
                    progressos = [float(d["Progresso"].replace("%", "")) for d in dados_tabela]
                    
                    if progressos:
                        # Criar histograma
                        fig = px.histogram(
                            x=progressos,
                            nbins=10,
                            title="Distribuição de Progresso dos Alunos",
                            labels={"x": "Progresso (%)", "y": "Quantidade de Alunos"},
                            color_discrete_sequence=["#10b981"]
                        )
                        st.plotly_chart(fig, use_container_width=True)
            else:
                st.info(f"📭 Ainda não há alunos matriculados no curso **{curso_selecionado}**.")
                
        except Exception as e:
            st.error(f"❌ Erro ao carregar dados do curso: {e}")

# ======================================================
# MODAL DE EDIÇÃO ALTERNATIVO (COMPATÍVEL)
# ======================================================

def _render_modal_editar_curso():
    """Renderiza o modal de edição usando HTML/JavaScript"""
    
    if 'edit_curso' not in st.session_state:
        st.session_state.show_edit_modal = False
        return
    
    curso = st.session_state['edit_curso']
    usuario = st.session_state.get('usuario', {})
    
    # HTML/JS para o modal
    modal_html = f"""
    <div id="modal-overlay" class="modal-overlay">
        <div id="modal-content" class="modal-content animate-fadeIn">
            <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 1.5rem;">
                <h3 style="margin: 0;">✏️ Editar Curso</h3>
                <button onclick="closeModal()" style="
                    background: none;
                    border: none;
                    color: white;
                    font-size: 1.5rem;
                    cursor: pointer;
                    opacity: 0.7;
                ">×</button>
            </div>
    """
    
    # Formulário dentro do modal (usaremos um formulário do Streamlit separado)
    st.markdown(modal_html, unsafe_allow_html=True)
    
    # Aqui começa o formulário do Streamlit
    is_admin = usuario.get("tipo") == "admin"
    
    with st.form(f"form_editar_{curso['id']}", border=False):
        # Informações básicas
        titulo = st.text_input("Título *", value=curso.get("titulo", ""), key=f"titulo_{curso['id']}")
        descricao = st.text_area("Descrição *", value=curso.get("descricao", ""), height=100, key=f"desc_{curso['id']}")
        
        col1, col2 = st.columns(2)
        
        with col1:
            modalidade = st.selectbox(
                "Modalidade",
                ["EAD", "Presencial", "Híbrido"],
                index=["EAD", "Presencial", "Híbrido"].index(
                    curso.get("modalidade", "EAD")
                ) if curso.get("modalidade") in ["EAD", "Presencial", "Híbrido"] else 0,
                key=f"modalidade_{curso['id']}"
            )
        
        with col2:
            publico = st.selectbox(
                "Público",
                ["geral", "equipe"],
                index=0 if curso.get("publico") == "geral" else 1,
                format_func=lambda v: "🌍 Geral" if v == "geral" else "👥 Equipe",
                key=f"publico_{curso['id']}"
            )
            
            equipe_destino = None
            if publico == "equipe":
                equipe_destino = st.text_input(
                    "Equipe Destino",
                    value=curso.get("equipe_destino", ""),
                    key=f"equipe_{curso['id']}"
                )
        
        # Status e certificado
        col3, col4 = st.columns(2)
        
        with col3:
            ativo = st.checkbox("Curso Ativo", value=curso.get("ativo", True), key=f"ativo_{curso['id']}")
        
        with col4:
            certificado_auto = st.checkbox(
                "Certificado Automático",
                value=curso.get("certificado_automatico", True),
                key=f"cert_{curso['id']}"
            )
        
        # Valores
        st.markdown("#### 💰 Valores")
        
        col5, col6 = st.columns(2)
        
        with col5:
            pago = st.checkbox("Curso Pago", value=curso.get("pago", False), key=f"pago_{curso['id']}")
            
            preco = st.number_input(
                "Valor (R$)",
                value=float(curso.get("preco", 0.0)),
                min_value=0.0,
                step=10.0,
                disabled=not pago,
                key=f"preco_{curso['id']}"
            )
        
        with col6:
            if pago and is_admin:
                split_custom = st.slider(
                    "Taxa da Plataforma (%)",
                    0, 100,
                    value=int(curso.get("split_custom", 10)),
                    key=f"split_{curso['id']}"
                )
            else:
                split_custom = curso.get("split_custom", 10)
                if pago:
                    st.info(f"Taxa atual: {split_custom}%")
                    st.caption("Apenas administradores podem alterar")
        
        # Botões
        st.markdown("---")
        col_btn1, col_btn2, col_btn3 = st.columns([1, 1, 1])
        
        with col_btn2:
            submitted = st.form_submit_button(
                "💾 Salvar Alterações",
                type="primary",
                use_container_width=True
            )
        
        with col_btn3:
            cancelar = st.form_submit_button(
                "❌ Cancelar",
                type="secondary",
                use_container_width=True
            )
        
        if submitted:
            # Validações
            if not titulo.strip():
                st.error("⚠️ O título é obrigatório")
            elif not descricao.strip():
                st.error("⚠️ A descrição é obrigatória")
            else:
                try:
                    _salvar_edicao_curso(
                        curso_id=curso["id"],
                        titulo=titulo,
                        descricao=descricao,
                        modalidade=modalidade,
                        publico=publico,
                        equipe_destino=equipe_destino,
                        pago=pago,
                        preco=preco,
                        split_custom=split_custom,
                        certificado_automatico=certificado_auto
                    )
                    
                    # Atualizar status
                    db = get_db()
                    if db:
                        db.collection("courses").document(curso["id"]).update({
                            "ativo": ativo
                        })
                    
                    st.success("✅ Curso atualizado com sucesso!")
                    
                    # Limpar estado do modal
                    st.session_state.pop('edit_curso', None)
                    st.session_state.pop('show_edit_modal', None)
                    
                    # JavaScript para recarregar a página
                    st.markdown("""
                    <script>
                        setTimeout(function() {
                            window.location.reload();
                        }, 1500);
                    </script>
                    """, unsafe_allow_html=True)
                    
                except Exception as e:
                    st.error(f"❌ Erro ao salvar: {str(e)}")
        
        if cancelar:
            st.session_state.pop('edit_curso', None)
            st.session_state.pop('show_edit_modal', None)
            st.rerun()
    
    # Fechar o modal HTML
    st.markdown("</div></div>", unsafe_allow_html=True)
    
    # JavaScript para fechar o modal
    st.markdown("""
    <script>
    function closeModal() {{
        // Remove o modal do DOM
        var modal = document.getElementById('modal-overlay');
        if (modal) {{
            modal.style.display = 'none';
        }}
        
        // Envia uma requisição para fechar o modal no servidor
        fetch(window.location.href + '?close_modal=true', {{method: 'GET'}})
            .then(() => {{
                // Recarrega a página para atualizar o estado
                setTimeout(() => {{ window.location.reload(); }}, 100);
            }});
    }}
    
    // Fecha o modal ao pressionar ESC
    document.addEventListener('keydown', function(event) {{
        if (event.key === 'Escape') {{
            closeModal();
        }}
    }});
    
    // Fecha o modal ao clicar fora
    document.getElementById('modal-overlay').addEventListener('click', function(event) {{
        if (event.target.id === 'modal-overlay') {{
            closeModal();
        }}
    }});
    </script>
    """, unsafe_allow_html=True)

# ======================================================
# VISÃO DO ALUNO MODERNA
# ======================================================

def _interface_aluno_moderna(usuario: dict):
    """Interface moderna para alunos"""
    
    tab1, tab2 = st.tabs([
        "🛒 Cursos Disponíveis",
        "🎓 Meus Cursos"
    ])

    with tab1:
        _aluno_cursos_disponiveis_moderno(usuario)

    with tab2:
        _aluno_meus_cursos_moderno(usuario)

def _aluno_cursos_disponiveis_moderno(usuario: dict):
    """Exibição moderna de cursos disponíveis"""
    
    try:
        cursos = listar_cursos_disponiveis_para_usuario(usuario)
    except Exception as e:
        st.error(f"❌ Erro ao carregar cursos: {e}")
        cursos = []
    
    if not cursos:
        st.info("""
        📭 **Nenhum curso disponível no momento**
        
        Novos cursos serão disponibilizados em breve. 
        Verifique também se você atende aos pré-requisitos dos cursos existentes.
        """)
        return
    
    # Filtros
    with st.expander("🔍 Filtros", expanded=True):
        col1, col2 = st.columns(2)
        
        with col1:
            termo_busca = st.text_input("Buscar cursos...", placeholder="Digite o nome ou assunto")
        
        with col2:
            tipo_filtro = st.selectbox(
                "Tipo",
                ["Todos", "Gratuitos", "Pagos", "EAD", "Presencial"]
            )
    
    # Aplicar filtros
    cursos_filtrados = []
    for curso in cursos:
        # Busca
        if termo_busca:
            busca = termo_busca.lower()
            titulo = curso.get('titulo', '').lower()
            desc = curso.get('descricao', '').lower()
            
            if busca not in titulo and busca not in desc:
                continue
        
        # Tipo
        if tipo_filtro == "Gratuitos" and curso.get('pago'):
            continue
        elif tipo_filtro == "Pagos" and not curso.get('pago'):
            continue
        elif tipo_filtro == "EAD" and curso.get('modalidade') != 'EAD':
            continue
        elif tipo_filtro == "Presencial" and curso.get('modalidade') != 'Presencial':
            continue
        
        cursos_filtrados.append(curso)
    
    # Exibição
    st.markdown(f"### 📚 Cursos Disponíveis ({len(cursos_filtrados)})")
    
    if not cursos_filtrados:
        st.warning("Nenhum curso encontrado com os filtros aplicados.")
        return
    
    # Grid de cards
    cols = st.columns(2)
    for idx, curso in enumerate(cursos_filtrados):
        with cols[idx % 2]:
            _card_curso_aluno(curso, usuario)

def _card_curso_aluno(curso: dict, usuario: dict):
    """Card moderno para curso disponível para aluno"""
    
    with st.container():
        st.markdown("<div class='curso-card'>", unsafe_allow_html=True)
        
        # Verificar se já está inscrito
        try:
            inscricao = obter_inscricao(usuario["id"], curso["id"])
        except:
            inscricao = None
        
        # Header
        st.markdown(f"#### {curso.get('titulo', 'Sem Título')}")
        
        # Badges
        col_badges = st.columns(3)
        with col_badges[0]:
            modalidade = curso.get('modalidade', '-')
            st.markdown(f"<span class='badge badge-azul'>{modalidade}</span>", unsafe_allow_html=True)
        
        with col_badges[1]:
            if curso.get('pago'):
                preco = curso.get('preco', 0.0)
                st.markdown(f"<span class='badge badge-amarelo'>R$ {preco:.2f}</span>", unsafe_allow_html=True)
            else:
                st.markdown(f"<span class='badge badge-verde'>Gratuito</span>", unsafe_allow_html=True)
        
        with col_badges[2]:
            professor = curso.get('nome_professor', 'Professor')
            st.caption(f"👨‍🏫 {professor}")
        
        # Descrição
        desc = curso.get("descricao", "")
        if desc:
            st.markdown(f"<div style='opacity: 0.8; margin: 1rem 0;'>{desc[:120]}...</div>", unsafe_allow_html=True)
        
        # Botão de ação
        if inscricao:
            st.success("✅ Você já está inscrito!")
            if st.button("Acessar Curso", key=f"acessar_{curso['id']}", use_container_width=True):
                # Aqui você pode redirecionar para o curso
                st.session_state['curso_atual'] = curso['id']
                st.rerun()
        else:
            if st.button("Inscrever-se", key=f"inscrever_{curso['id']}", use_container_width=True, type="primary"):
                try:
                    inscrever_usuario_em_curso(usuario["id"], curso["id"])
                    st.success("🎉 Inscrição realizada com sucesso!")
                    time.sleep(1.5)
                    st.rerun()
                except Exception as e:
                    st.error(f"❌ Erro na inscrição: {e}")
        
        st.markdown("</div>", unsafe_allow_html=True)

def _aluno_meus_cursos_moderno(usuario: dict):
    """Exibição moderna dos cursos do aluno"""
    
    db = get_db()
    if not db:
        st.error("❌ Erro de conexão com o banco de dados.")
        return
    
    try:
        # Buscar inscrições
        inscricoes_ref = db.collection("enrollments").where("user_id", "==", usuario["id"]).stream()
        inscricoes = []
        
        for ins in inscricoes_ref:
            dados = ins.to_dict()
            dados["inscricao_id"] = ins.id
            inscricoes.append(dados)
    except Exception as e:
        st.error(f"❌ Erro ao carregar inscrições: {e}")
        inscricoes = []
    
    if not inscricoes:
        st.info("""
        📭 **Você ainda não está matriculado em nenhum curso**
        
        Explore os cursos disponíveis e comece sua jornada de aprendizado!
        """)
        return
    
    # Organizar por progresso
    cursos_em_andamento = []
    cursos_concluidos = []
    
    for ins in inscricoes:
        try:
            curso_ref = db.collection("courses").document(ins.get("course_id")).get()
            if curso_ref.exists:
                curso = curso_ref.to_dict()
                curso["id"] = curso_ref.id
                curso["progresso"] = float(ins.get("progresso", 0))
                curso["pago_status"] = "✅ Pago" if ins.get("pago") else "⏳ Pendente"
                curso["inscricao_id"] = ins["inscricao_id"]
                
                if curso["progresso"] >= 100:
                    cursos_concluidos.append(curso)
                else:
                    cursos_em_andamento.append(curso)
        except:
            continue
    
    # Exibição
    if cursos_em_andamento:
        st.markdown(f"### 📚 Cursos em Andamento ({len(cursos_em_andamento)})")
        
        for curso in cursos_em_andamento:
            _card_meu_curso(curso, usuario)
    
    if cursos_concluidos:
        st.markdown(f"### 🎓 Cursos Concluídos ({len(cursos_concluidos)})")
        
        for curso in cursos_concluidos:
            _card_meu_curso(curso, usuario, concluido=True)

def _card_meu_curso(curso: dict, usuario: dict, concluido: bool = False):
    """Card para curso do aluno (inscrito)"""
    
    with st.container():
        st.markdown("<div class='curso-card'>", unsafe_allow_html=True)
        
        col1, col2, col3 = st.columns([1, 3, 1])
        
        with col1:
            # Ícone
            emoji = "🥋" if concluido else "📚"
            st.markdown(f"<div style='font-size: 2.5rem; text-align: center;'>{emoji}</div>", unsafe_allow_html=True)
        
        with col2:
            # Informações
            st.markdown(f"#### {curso.get('titulo', 'Sem Título')}")
            
            if not concluido:
                # Barra de progresso
                progresso = curso.get("progresso", 0)
                st.progress(progresso / 100, text=f"Progresso: {int(progresso)}%")
                
                # Status de pagamento
                if curso.get("pago") and curso.get("pago_status") == "⏳ Pendente":
                    st.warning("⚠️ Pagamento pendente")
            else:
                st.success("✅ Curso concluído!")
        
        with col3:
            st.write("")  # Espaçamento
            
            if concluido:
                if st.button("📜 Certificado", key=f"cert_{curso['id']}", use_container_width=True):
                    # Em produção, integrar com geração de certificado
                    st.info("Funcionalidade de certificado em desenvolvimento")
            else:
                if st.button("▶️ Continuar", key=f"continuar_{curso['id']}", use_container_width=True, type="primary"):
                    st.session_state['curso_atual'] = curso['id']
                    st.rerun()
        
        st.markdown("</div>", unsafe_allow_html=True)

# ======================================================
# FUNÇÕES AUXILIARES (MANTIDAS DO ORIGINAL)
# ======================================================

def _salvar_edicao_curso(
    curso_id: str,
    titulo: str,
    descricao: str,
    modalidade: str,
    publico: str,
    equipe_destino: Optional[str],
    pago: bool,
    preco: Optional[float],
    split_custom: Optional[int],
    certificado_automatico: bool
):
    """Atualiza o documento do curso no Firestore."""
    db = get_db()
    
    safe_preco = float(preco) if (pago and preco is not None) else 0.0
    safe_split = int(split_custom) if split_custom is not None else 10

    doc_updates = {
        "titulo": titulo.strip(),
        "descricao": descricao.strip(),
        "modalidade": modalidade,
        "publico": publico,
        "equipe_destino": equipe_destino or None,
        "pago": bool(pago),
        "preco": safe_preco,
        "split_custom": safe_split,
        "certificado_automatico": bool(certificado_automatico),
    }

    db.collection("courses").document(curso_id).update(doc_updates)

def _toggle_status_curso(curso_id: str, novo_ativo: bool):
    """Ativa ou desativa o curso."""
    db = get_db()
    db.collection("courses").document(curso_id).update({
        "ativo": bool(novo_ativo),
        "status": "ativo" if novo_ativo else "inativo"
    })

# ======================================================
# IMPORTAÇÃO NECESSÁRIA
# ======================================================

import time  # Adicionado para usar time.sleep()