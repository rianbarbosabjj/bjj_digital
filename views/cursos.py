# ============================================
# BJJ DIGITAL – SISTEMA DE CURSOS
# views/cursos.py
# ============================================

import streamlit as st
import pandas as pd
import time
from datetime import datetime
from typing import Optional, Dict, List

# Importações internas do projeto
from courses_engine import (
    criar_curso,
    listar_cursos_do_professor,
    listar_cursos_disponiveis_para_usuario,
    inscrever_usuario_em_curso,
    obter_inscricao,
)
from database import get_db


# ======================================================
# ESTILOS DO BJJ DIGITAL (HERDADOS DE main/app.py)
# ======================================================

def aplicar_estilos_modal_bjj():
    """Estilo visual do modal 100% Streamlit com tema do BJJ Digital."""
    try:
        from config import COR_TEXTO, COR_DESTAQUE, COR_FUNDO, COR_BOTAO, COR_HOVER
    except:
        COR_TEXTO = "#FFFFFF"
        COR_DESTAQUE = "#FFD770"
        COR_FUNDO = "#0e2d26"
        COR_BOTAO = "#078B6C"
        COR_HOVER = "#FFD770"

    st.markdown(f"""
    <style>
    .bjj-modal-overlay {{
        position: fixed;
        top: 0;
        left: 0;
        width: 100vw;
        height: 100vh;
        background: rgba(0, 0, 0, 0.65);
        z-index: 999998;
        display: flex;
        justify-content: center;
        align-items: center;
        backdrop-filter: blur(3px);
    }}

    .bjj-modal-card {{
        background: rgba(0, 0, 0, 0.35);
        border: 1px solid rgba(255, 215, 112, 0.25);
        border-radius: 14px;
        padding: 2rem;
        width: 60%;
        max-width: 900px;
        max-height: 85vh;
        overflow-y: auto;
        box-shadow: 0 0 25px rgba(0,0,0,0.45);
        animation: fadein 0.25s ease-out;
    }}

    @keyframes fadein {{
        from {{ opacity: 0; transform: translateY(-10px); }}
        to {{ opacity: 1; transform: translateY(0); }}
    }}

    .bjj-close-btn {{
        background: none !important;
        border: none !important;
        font-size: 1.7rem;
        color: {COR_DESTAQUE} !important;
        cursor: pointer;
        float: right;
        margin-top: -10px;
    }}

    .bjj-close-btn:hover {{
        opacity: 0.9;
        transform: scale(1.1);
    }}
    </style>
    """, unsafe_allow_html=True)


# ======================================================
# PÁGINA PRINCIPAL
# ======================================================

def pagina_cursos(usuario: dict):
    """ Página inicial da gestão de cursos """
    
    aplicar_estilos_modal_bjj()

    tipo = str(usuario.get("tipo", "aluno")).lower()

    st.markdown(f"""
    <h1 style='margin-bottom: 0.2em;'>📚 Gestão de Cursos</h1>
    <p style='text-align:center; opacity:0.8;'>Bem-vindo(a), <strong>{usuario.get('nome','Usuário').split()[0]}</strong></p>
    """, unsafe_allow_html=True)

    st.markdown("---")

    # Renderiza modal se for necessário
    if st.session_state.get("show_edit_modal"):
        _render_modal_editar_curso()

    if tipo in ["admin", "professor"]:
        _interface_professor_moderna(usuario)
    else:
        _interface_aluno_moderna(usuario)


# ======================================================
# INTERFACE DO PROFESSOR / ADMIN
# ======================================================

def _interface_professor_moderna(usuario: dict):
    """ Interface moderna para professores/admin """
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
# ======================================================
# LISTAGEM DOS CURSOS DO PROFESSOR (MODERNO)
# ======================================================

def _prof_listar_cursos_moderno(usuario: dict):
    try:
        cursos = listar_cursos_do_professor(usuario["id"])
    except Exception as e:
        st.error(f"❌ Erro ao carregar cursos: {e}")
        cursos = []

    if not cursos:
        st.info("""
        🎯 **Você ainda não criou nenhum curso.**
        Use a aba **Criar Curso** para começar.
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

    cursos_filtrados = []
    for curso in cursos:
        status = "Ativo" if curso.get('ativo', True) else "Inativo"
        modalidade = curso.get('modalidade', 'EAD')

        if status_filter and status not in status_filter:
            continue
        if modalidade_filter and modalidade not in modalidade_filter:
            continue

        cursos_filtrados.append(curso)

    # Métricas
    col_m1, col_m2, col_m3 = st.columns(3)
    with col_m1:
        st.metric("Cursos", len(cursos_filtrados))
    with col_m2:
        st.metric("Ativos", sum(1 for c in cursos_filtrados if c.get('ativo', True)))
    with col_m3:
        st.metric("Gratuitos", sum(1 for c in cursos_filtrados if not c.get('pago', False)))

    st.markdown("---")

    for curso in cursos_filtrados:
        _card_curso_professor(curso, usuario)


# ======================================================
# CARD DO CURSO PARA O PROFESSOR
# ======================================================

def _card_curso_professor(curso: dict, usuario: dict):

    with st.container():
        st.markdown("<div class='curso-card'>", unsafe_allow_html=True)

        col1, col2, col3 = st.columns([3, 1.5, 1])

        with col1:
            ativo = curso.get('ativo', True)
            status_badge = "🟢 Ativo" if ativo else "🔴 Inativo"
            status_class = "badge-verde" if ativo else "badge-vermelho"

            st.markdown(f"### {curso.get('titulo', 'Sem Título')}")

            col_badges = st.columns([1, 1, 2])
            with col_badges[0]:
                st.markdown(f"<span class='badge {status_class}'>{status_badge}</span>", unsafe_allow_html=True)
            with col_badges[1]:
                modalidade = curso.get('modalidade', '-')
                st.markdown(f"<span class='badge badge-azul'>{modalidade}</span>", unsafe_allow_html=True)
            with col_badges[2]:
                publico = 'Equipe' if curso.get('publico') == 'equipe' else 'Geral'
                st.markdown(f"<span class='badge badge-amarelo'>{publico}</span>", unsafe_allow_html=True)

            desc = curso.get("descricao", "")
            if desc:
                st.markdown(f"<div style='opacity: 0.8; margin-top: 0.5rem;'>{desc[:150]}...</div>", unsafe_allow_html=True)

        with col2:
            if curso.get("pago"):
                preco = curso.get('preco', 0.0)
                split = int(curso.get('split_custom', 10))
                st.metric("Preço", f"R$ {preco:.2f}")
                st.caption(f"Taxa: {split}%")
            else:
                st.metric("Preço", "Gratuito")
                st.caption("Sem taxa")

        with col3:
            col_btn1, col_btn2 = st.columns(2)

            with col_btn1:
                if st.button("✏️", key=f"edit_{curso['id']}", help="Editar curso", use_container_width=True):
                    st.session_state['edit_curso'] = curso
                    st.session_state['show_edit_modal'] = True
                    st.rerun()

            with col_btn2:
                if curso.get("ativo", True):
                    if st.button("⏸️", key=f"pause_{curso['id']}", help="Desativar", use_container_width=True):
                        _toggle_status_curso(curso["id"], False)
                        st.rerun()
                else:
                    if st.button("▶️", key=f"play_{curso['id']}", help="Ativar", use_container_width=True):
                        _toggle_status_curso(curso["id"], True)
                        st.rerun()

        st.markdown("</div>", unsafe_allow_html=True)


# ======================================================
# FORMULÁRIO DE CRIAÇÃO DE CURSO
# ======================================================

def _prof_criar_curso_moderno(usuario: dict):

    st.markdown("""
    <div style="background: rgba(255,255,255,0.05); padding: 1.5rem; border-radius: 14px;">
        <h3 style="margin:0;">🎯 Criar Novo Curso</h3>
        <p style="opacity:0.8;">Preencha os detalhes abaixo para criar um curso.</p>
    </div>
    """, unsafe_allow_html=True)

    with st.form("form_criar_curso_moderno", border=True):

        st.markdown("### 📝 Informações do Curso")

        col1, col2 = st.columns([2, 1])
        with col1:
            titulo = st.text_input("Título do Curso *", placeholder="Ex: Fundamentos do Jiu-Jitsu para Iniciantes")
            descricao = st.text_area("Descrição Detalhada *", height=120)
        with col2:
            modalidade = st.selectbox("Modalidade *", ["EAD", "Presencial", "Híbrido"])
            publico = st.selectbox(
                "Público Alvo *",
                ["geral", "equipe"],
                format_func=lambda v: "🌍 Geral" if v == "geral" else "👥 Equipe",
            )
            equipe_destino = None
            if publico == "equipe":
                equipe_destino = st.text_input("Nome da Equipe *")

        st.markdown("### ⚙️ Configurações")
        col3, col4 = st.columns(2)
        with col3:
            certificado_auto = st.checkbox("Emitir certificado automaticamente", value=True)
        with col4:
            with st.expander("Configurações Avançadas"):
                max_alunos = st.number_input("Vagas", min_value=0, value=0)
                duracao_estimada = st.text_input("Duração estimada")

        st.markdown("### 💰 Valores")
        col5, col6, col7 = st.columns(3)
        with col5:
            pago = st.toggle("Curso Pago?", value=False)
        with col6:
            preco = st.number_input("Valor (R$)", min_value=0.0, step=10.0, disabled=not pago)
        with col7:
            is_admin = usuario.get("tipo") == "admin"
            split_custom = 10
            if pago and is_admin:
                split_custom = st.slider("Taxa da Plataforma (%)", 0, 100, value=10)
            elif pago:
                st.caption("Taxa da plataforma: 10%")

        st.markdown("---")

        submit_btn = st.form_submit_button("🚀 Criar Curso", type="primary", use_container_width=True)

        if submit_btn:

            erros = []
            if not titulo.strip():
                erros.append("⚠️ O título é obrigatório.")
            if not descricao.strip():
                erros.append("⚠️ A descrição é obrigatória.")
            if publico == "equipe" and (not equipe_destino or not equipe_destino.strip()):
                erros.append("⚠️ Informe o nome da equipe.")
            if pago and preco <= 0:
                erros.append("⚠️ Curso pago deve ter valor maior que zero.")

            if erros:
                for e in erros:
                    st.error(e)
                return

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
                )

                st.success("🎉 Curso criado com sucesso!")
                time.sleep(1.5)
                st.rerun()

            except Exception as e:
                st.error(f"❌ Erro ao criar curso: {e}")


# ======================================================
# DASHBOARD DO PROFESSOR
# ======================================================

def _prof_dashboard_moderno(usuario: dict):

    db = get_db()
    if not db:
        st.error("❌ Erro ao conectar ao banco.")
        return

    try:
        cursos = listar_cursos_do_professor(usuario["id"])
    except:
        st.error("Erro ao carregar cursos.")
        return

    if not cursos:
        st.info("📭 Você ainda não criou cursos.")
        return

    total_inscritos = 0
    total_receita = 0
    progresso_medio = 0
    cursos_ativos = 0

    for curso in cursos:
        if curso.get("ativo", True):
            cursos_ativos += 1

        inscricoes = db.collection("enrollments").where("course_id", "==", curso["id"]).stream()
        for ins in inscricoes:
            dados = ins.to_dict()
            total_inscritos += 1
            progresso_medio += float(dados.get("progresso", 0))

            if curso.get("pago") and dados.get("pago"):
                preco = curso.get("preco", 0)
                split = curso.get("split_custom", 10) / 100
                total_receita += preco * (1 - split)

    progresso_medio = (progresso_medio / total_inscritos) if total_inscritos else 0

    col1, col2, col3, col4 = st.columns(4)
    with col1: st.metric("Cursos Ativos", cursos_ativos)
    with col2: st.metric("Alunos", total_inscritos)
    with col3: st.metric("Receita", f"R$ {total_receita:.2f}")
    with col4: st.metric("Progresso Médio", f"{progresso_medio:.0f}%")

    st.markdown("---")

    st.markdown("### 📊 Detalhes por Curso")

    curso_opcoes = {c["titulo"]: c["id"] for c in cursos}
    curso_selecionado = st.selectbox("Selecione um curso:", list(curso_opcoes.keys()))
    curso_id = curso_opcoes[curso_selecionado]

    inscricoes_ref = db.collection("enrollments").where("course_id", "==", curso_id).stream()
    inscricoes = []

    for ins in inscricoes_ref:
        dados = ins.to_dict()
        dados["inscricao_id"] = ins.id
        inscricoes.append(dados)

    if not inscricoes:
        st.info(f"📭 Nenhum aluno matriculado em **{curso_selecionado}**.")
        return

    # Tabela
    dados_tabela = []
    for ins in inscricoes:
        aluno_ref = db.collection("usuarios").document(ins.get("user_id")).get()
        nome = aluno_ref.to_dict().get("nome", "Aluno") if aluno_ref.exists else "Aluno"

        dados_tabela.append({
            "Aluno": nome,
            "Progresso": f"{ins.get('progresso', 0):.0f}%",
            "Pagamento": "✅ Pago" if ins.get("pago") else "⏳ Pendente",
            "Certificado": "🎉 Emitido" if ins.get("certificado_emitido") else "⏳ Aguardando",
        })

    df = pd.DataFrame(dados_tabela)
    st.dataframe(df, use_container_width=True, hide_index=True)
# ======================================================
# INTERFACE DO ALUNO — CURSOS DISPONÍVEIS & MEUS CURSOS
# ======================================================

def _interface_aluno_moderna(usuario: dict):
    tab1, tab2 = st.tabs([
        "🛒 Cursos Disponíveis",
        "🎓 Meus Cursos"
    ])

    with tab1:
        _aluno_cursos_disponiveis_moderno(usuario)

    with tab2:
        _aluno_meus_cursos_moderno(usuario)


# ======================================================
# CURSOS DISPONÍVEIS PARA ALUNOS
# ======================================================

def _aluno_cursos_disponiveis_moderno(usuario: dict):

    try:
        cursos = listar_cursos_disponiveis_para_usuario(usuario)
    except Exception as e:
        st.error(f"Erro ao carregar cursos: {e}")
        cursos = []

    if not cursos:
        st.info("""
        📭 **Nenhum curso disponível no momento**
        Novos cursos serão adicionados em breve.
        """)
        return

    with st.expander("🔍 Filtros", expanded=True):
        col1, col2 = st.columns(2)

        with col1:
            termo_busca = st.text_input("Buscar cursos...", placeholder="Digite parte do título ou assunto")

        with col2:
            tipo_filtro = st.selectbox("Tipo", ["Todos", "Gratuitos", "Pagos", "EAD", "Presencial"])

    cursos_filtrados = []

    for curso in cursos:
        # filtragem por texto
        if termo_busca:
            txt = termo_busca.lower()
            if txt not in curso.get('titulo', '').lower() and txt not in curso.get('descricao', '').lower():
                continue

        # filtros específicos
        if tipo_filtro == "Gratuitos" and curso.get("pago"):
            continue
        if tipo_filtro == "Pagos" and not curso.get("pago"):
            continue
        if tipo_filtro == "EAD" and curso.get("modalidade") != "EAD":
            continue
        if tipo_filtro == "Presencial" and curso.get("modalidade") != "Presencial":
            continue

        cursos_filtrados.append(curso)

    st.markdown(f"### 📚 Cursos Disponíveis ({len(cursos_filtrados)})")

    if not cursos_filtrados:
        st.warning("Nenhum curso encontrado com os filtros aplicados.")
        return

    colunas = st.columns(2)

    for idx, curso in enumerate(cursos_filtrados):
        with colunas[idx % 2]:
            _card_curso_aluno(curso, usuario)


# ======================================================
# CARD DO CURSO PARA O ALUNO
# ======================================================

def _card_curso_aluno(curso: dict, usuario: dict):

    with st.container():
        st.markdown("<div class='curso-card'>", unsafe_allow_html=True)

        try:
            inscricao = obter_inscricao(usuario["id"], curso["id"])
        except:
            inscricao = None

        st.markdown(f"#### {curso.get('titulo', 'Sem Título')}")

        col_badges = st.columns(3)

        with col_badges[0]:
            modalidade = curso.get('modalidade', '-')
            st.markdown(f"<span class='badge badge-azul'>{modalidade}</span>", unsafe_allow_html=True)

        with col_badges[1]:
            if curso.get("pago"):
                st.markdown(f"<span class='badge badge-amarelo'>R$ {curso.get('preco', 0):.2f}</span>", unsafe_allow_html=True)
            else:
                st.markdown(f"<span class='badge badge-verde'>Gratuito</span>", unsafe_allow_html=True)

        with col_badges[2]:
            professor = curso.get("nome_professor", "Professor")
            st.caption(f"👨‍🏫 {professor}")

        desc = curso.get("descricao", "")
        if desc:
            st.markdown(f"<div style='opacity:0.7; margin: 1em 0;'>{desc[:120]}...</div>", unsafe_allow_html=True)

        if inscricao:
            st.success("✅ Você já está inscrito!")

            if st.button("Acessar Curso", key=f"acc_{curso['id']}", use_container_width=True):
                st.session_state['curso_atual'] = curso["id"]
                st.rerun()

        else:
            if st.button("Inscrever-se", key=f"ins_{curso['id']}", use_container_width=True, type="primary"):
                try:
                    inscrever_usuario_em_curso(usuario["id"], curso["id"])
                    st.success("🎉 Inscrição realizada!")
                    time.sleep(1)
                    st.rerun()
                except Exception as e:
                    st.error(f"Erro na inscrição: {e}")

        st.markdown("</div>", unsafe_allow_html=True)


# ======================================================
# MEUS CURSOS (ALUNO)
# ======================================================

def _aluno_meus_cursos_moderno(usuario: dict):

    db = get_db()
    if not db:
        st.error("Erro de conexão com o banco.")
        return

    try:
        inscricoes_ref = db.collection("enrollments").where("user_id", "==", usuario["id"]).stream()
    except:
        st.error("Erro ao carregar inscrições.")
        return

    inscricoes = []
    for ins in inscricoes_ref:
        d = ins.to_dict()
        d["inscricao_id"] = ins.id
        inscricoes.append(d)

    if not inscricoes:
        st.info("📭 Você ainda não está inscrito em nenhum curso.")
        return

    cursos_em_andamento = []
    cursos_concluidos = []

    for reg in inscricoes:
        curso_ref = db.collection("courses").document(reg.get("course_id")).get()
        if not curso_ref.exists:
            continue

        curso = curso_ref.to_dict()
        curso["id"] = curso_ref.id
        curso["progresso"] = float(reg.get("progresso", 0))
        curso["pago_status"] = "Pago" if reg.get("pago") else "Pendente"
        curso["inscricao_id"] = reg["inscricao_id"]

        if curso["progresso"] >= 100:
            cursos_concluidos.append(curso)
        else:
            cursos_em_andamento.append(curso)

    if cursos_em_andamento:
        st.markdown(f"### 📚 Cursos em Andamento ({len(cursos_em_andamento)})")
        for c in cursos_em_andamento:
            _card_meu_curso(c, usuario)

    if cursos_concluidos:
        st.markdown(f"### 🎓 Cursos Concluídos ({len(cursos_concluidos)})")
        for c in cursos_concluidos:
            _card_meu_curso(c, usuario, concluido=True)


# ======================================================
# CARD DO CURSO DO ALUNO
# ======================================================

def _card_meu_curso(curso: dict, usuario: dict, concluido=False):

    with st.container():
        st.markdown("<div class='curso-card'>", unsafe_allow_html=True)

        col1, col2, col3 = st.columns([1, 4, 1])

        with col1:
            st.markdown(f"<div style='font-size:2.5rem; text-align:center;'>{'🎓' if concluido else '📚'}</div>",
                        unsafe_allow_html=True)

        with col2:
            st.markdown(f"#### {curso.get('titulo','Sem Título')}")
            progresso = curso.get("progresso", 0)

            if not concluido:
                st.progress(progresso / 100, text=f"Progresso: {int(progresso)}%")

                if curso.get("pago") and curso.get("pago_status") == "Pendente":
                    st.warning("⚠️ Pagamento pendente")
            else:
                st.success("Curso concluído!")

        with col3:
            if concluido:
                if st.button("📜 Certificado", key=f"cert_{curso['id']}", use_container_width=True):
                    st.info("Em breve: Certificado disponível via sistema 🤝")
            else:
                if st.button("▶️ Continuar", key=f"go_{curso['id']}", use_container_width=True, type="primary"):
                    st.session_state['curso_atual'] = curso["id"]
                    st.rerun()

        st.markdown("</div>", unsafe_allow_html=True)


# ======================================================
# MODAL DE EDIÇÃO — 100% STREAMLIT — VISUAL BJJ DIGITAL
# ======================================================

def _render_modal_editar_curso():
    """Modal moderno sem HTML/JS conflitante, 100% Streamlit."""
    aplicar_estilos_modal_bjj()

    if "edit_curso" not in st.session_state:
        st.session_state.show_edit_modal = False
        return

    curso = st.session_state["edit_curso"]
    usuario = st.session_state.get("usuario", {})
    is_admin = usuario.get("tipo") == "admin"

    # Overlay
    st.markdown('<div class="bjj-modal-overlay">', unsafe_allow_html=True)
    st.markdown('<div class="bjj-modal-card">', unsafe_allow_html=True)

    # Botão fechar
    colx = st.columns([10, 1])
    with colx[1]:
        if st.button("✖", key="btn_close_modal", help="Fechar janela"):
            st.session_state.pop("edit_curso", None)
            st.session_state.pop("show_edit_modal", None)
            st.rerun()

    st.markdown("<h3>Editar Curso</h3>", unsafe_allow_html=True)

    with st.form(f"form_edit_{curso['id']}"):

        titulo = st.text_input("Título *", curso.get("titulo", ""))
        descricao = st.text_area("Descrição *", curso.get("descricao", ""), height=120)

        col1, col2 = st.columns(2)

        with col1:
            modalidade = st.selectbox(
                "Modalidade",
                ["EAD", "Presencial", "Híbrido"],
                index=["EAD", "Presencial", "Híbrido"].index(curso.get("modalidade", "EAD"))
            )

        with col2:
            publico = st.selectbox(
                "Público",
                ["geral", "equipe"],
                index=0 if curso.get("publico") == "geral" else 1,
                format_func=lambda v: "🌍 Geral" if v == "geral" else "👥 Equipe"
            )

            equipe_destino = None
            if publico == "equipe":
                equipe_destino = st.text_input("Equipe Destino", curso.get("equipe_destino", ""))

        col3, col4 = st.columns(2)
        with col3:
            ativo = st.checkbox("Curso Ativo", curso.get("ativo", True))
        with col4:
            certificado_auto = st.checkbox(
                "Certificado Automático",
                curso.get("certificado_automatico", True)
            )

        st.markdown("### Valores")

        col5, col6 = st.columns(2)
        with col5:
            pago = st.checkbox("Curso Pago", curso.get("pago", False))
            preco = st.number_input(
                "Preço (R$)",
                min_value=0.0,
                value=float(curso.get("preco", 0.0)),
                step=10.0,
                disabled=not pago
            )

        with col6:
            if pago and is_admin:
                split_custom = st.slider(
                    "Taxa da Plataforma (%)",
                    0, 100,
                    curso.get("split_custom", 10)
                )
            else:
                split_custom = curso.get("split_custom", 10)
                if pago:
                    st.caption(f"Taxa atual: {split_custom}% (somente admins podem alterar)")

        st.markdown("---")

        colA, colB = st.columns(2)
        cancelar = colA.form_submit_button("❌ Cancelar")
        salvar = colB.form_submit_button("💾 Salvar Alterações")

        if cancelar:
            st.session_state.pop("edit_curso", None)
            st.session_state.pop("show_edit_modal", None)
            st.rerun()

        if salvar:
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
                    certificado_automatico=certificado_auto,
                )

                get_db().collection("courses").document(curso["id"]).update({"ativo": ativo})

                st.success("Curso atualizado com sucesso!")
                time.sleep(1)
                st.session_state.pop("edit_curso", None)
                st.session_state.pop("show_edit_modal", None)
                st.rerun()

            except Exception as e:
                st.error(f"Erro ao salvar: {e}")

    st.markdown("</div></div>", unsafe_allow_html=True)


# ======================================================
# FUNÇÕES AUXILIARES
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
    certificado_automatico: bool,
):
    db = get_db()

    doc_updates = {
        "titulo": titulo.strip(),
        "descricao": descricao.strip(),
        "modalidade": modalidade,
        "publico": publico,
        "equipe_destino": equipe_destino or None,
        "pago": bool(pago),
        "preco": float(preco) if pago else 0.0,
        "split_custom": int(split_custom) if split_custom else 10,
        "certificado_automatico": bool(certificado_automatico),
    }

    db.collection("courses").document(curso_id).update(doc_updates)


def _toggle_status_curso(curso_id: str, novo_ativo: bool):
    db = get_db()
    db.collection("courses").document(curso_id).update({
        "ativo": bool(novo_ativo),
        "status": "ativo" if novo_ativo else "inativo"
    })
