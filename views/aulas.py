[file name]: aulas.py
[file content begin]
"""
BJJ Digital - Sistema de Aulas e Módulos
Tela moderna para navegação em cursos
"""

import streamlit as st
import time
from datetime import datetime
from typing import Dict, List, Optional

# Importações internas
from database import get_db
from views.components import (
    aplicar_estilos_modernos,
    badge,
    progress_bar,
    stats_card,
    course_card,
    lesson_card,
    empty_state
)
from courses_engine import (
    listar_modulos_do_curso,
    listar_aulas_do_modulo,
    marcar_aula_concluida,
    verificar_aula_concluida,
    obter_inscricao,
    listar_cursos_disponiveis_para_usuario
)

# =========================================
# PÁGINA PRINCIPAL DE AULAS
# =========================================

def pagina_aulas(usuario: Dict):
    """
    Página principal do sistema de aulas.
    Gerencia navegação entre cursos, módulos e aulas.
    """
    aplicar_estilos_modernos()
    
    # Estado da navegação
    if "curso_selecionado" not in st.session_state:
        st.session_state.curso_selecionado = None
    if "modulo_selecionado" not in st.session_state:
        st.session_state.modulo_selecionado = None
    if "aula_selecionada" not in st.session_state:
        st.session_state.aula_selecionada = None
    
    # Header
    st.markdown(f"""
    <div style="display: flex; align-items: center; justify-content: space-between; margin-bottom: 2rem;">
        <div>
            <h1 style="margin-bottom: 0.2rem;">🎓 Portal de Aulas</h1>
            <p style="opacity: 0.8; margin: 0;">Bem-vindo(a), <strong>{usuario.get('nome', 'Aluno').split()[0]}</strong></p>
        </div>
        <div style="display: flex; gap: 1rem;">
            <button class="btn-outline-gold" onclick="window.history.back()" style="cursor: pointer;">← Voltar</button>
            <button class="btn-modern" onclick="alert('Ajuda')">❔ Ajuda</button>
        </div>
    </div>
    """, unsafe_allow_html=True)
    
    # Lógica de navegação
    curso_atual = st.session_state.curso_selecionado
    modulo_atual = st.session_state.modulo_selecionado
    aula_atual = st.session_state.aula_selecionada
    
    if not curso_atual:
        _tela_selecao_cursos(usuario)
    elif curso_atual and not modulo_atual:
        _tela_modulos_do_curso(usuario, curso_atual)
    elif modulo_atual and not aula_atual:
        _tela_aulas_do_modulo(usuario, curso_atual, modulo_atual)
    else:
        _tela_aula_detalhe(usuario, curso_atual, modulo_atual, aula_atual)

# =========================================
# TELA 1: SELEÇÃO DE CURSOS
# =========================================

def _tela_selecao_cursos(usuario: Dict):
    """Lista todos os cursos disponíveis para o usuário"""
    
    st.markdown("### 📚 Meus Cursos")
    st.markdown("Selecione um curso para começar suas aulas.")
    
    try:
        cursos = listar_cursos_disponiveis_para_usuario(usuario)
        meus_cursos = []
        
        for curso in cursos:
            # Verifica inscrição
            inscricao = obter_inscricao(usuario["id"], curso["id"])
            if inscricao:
                curso["progresso"] = inscricao.get("progresso", 0)
                curso["inscrito"] = True
            else:
                curso["progresso"] = 0
                curso["inscrito"] = False
            meus_cursos.append(curso)
        
        if not meus_cursos:
            empty_state(
                icon="📭",
                titulo="Nenhum curso disponível",
                descricao="Você ainda não está inscrito em nenhum curso. Entre em contato com seu professor."
            )
            return
        
        # Métricas
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            total = len(meus_cursos)
            stats_card(total, "Cursos", "📚")
        
        with col2:
            ativos = sum(1 for c in meus_cursos if c.get("ativo", True))
            stats_card(ativos, "Ativos", "🟢")
        
        with col3:
            em_andamento = sum(1 for c in meus_cursos if 0 < c.get("progresso", 0) < 100)
            stats_card(em_andamento, "Em Andamento", "🔄")
        
        with col4:
            concluidos = sum(1 for c in meus_cursos if c.get("progresso", 0) >= 100)
            stats_card(concluidos, "Concluídos", "🏆")
        
        st.markdown("---")
        
        # Grid de cursos
        cols = st.columns(3)
        for idx, curso in enumerate(meus_cursos):
            with cols[idx % 3]:
                _render_card_curso(curso, usuario)
    
    except Exception as e:
        st.error(f"Erro ao carregar cursos: {e}")

def _render_card_curso(curso: Dict, usuario: Dict):
    """Renderiza card de curso moderno"""
    
    progresso = curso.get("progresso", 0)
    inscrito = curso.get("inscrito", False)
    
    # Badges
    badges = []
    if curso.get("modalidade") == "EAD":
        badges.append("🌐 EAD")
    else:
        badges.append("🏢 Presencial")
    
    if curso.get("pago"):
        badges.append("💲 Pago")
    else:
        badges.append("🎯 Gratuito")
    
    # Descrição curta
    desc = curso.get("descricao", "")[:100] + "..." if len(curso.get("descricao", "")) > 100 else curso.get("descricao", "")
    
    # Ação
    acao = None
    acao_texto = "Continuar" if progresso > 0 else "Começar"
    
    if inscrito:
        acao = f"""
        Streamlit.setComponentValue({{
            'type': 'select_course',
            'course_id': '{curso["id"]}'
        }});
        """
    else:
        acao_texto = "Inscrever-se"
        acao = f"""
        Streamlit.setComponentValue({{
            'type': 'enroll_course',
            'course_id': '{curso["id"]}'
        }});
        """
    
    # HTML do card
    st.markdown(f"""
    <div class="course-card">
        <div class="course-card-icon">{"🎓" if progresso >= 100 else "📚"}</div>
        <h4 style="margin: 0 0 0.5rem 0;">{curso.get('titulo', 'Sem Título')}</h4>
        <div style="margin-bottom: 1rem; opacity: 0.8; flex-grow: 1;">{desc}</div>
        
        <div style="margin-bottom: 1rem;">
            {"".join([f'<span class="badge badge-primary" style="margin-right: 0.5rem; margin-bottom: 0.5rem;">{b}</span>' for b in badges])}
        </div>
        
        <div style="margin-bottom: 1rem;">
            <small>Progresso: {progresso:.0f}%</small>
            <div class="progress-container">
                <div class="progress-fill" style="width: {progresso}%"></div>
            </div>
        </div>
        
        <div style="margin-top: auto;">
            <button class="btn-modern" onclick="{acao}" style="width: 100%;">
                {acao_texto}
            </button>
        </div>
    </div>
    """, unsafe_allow_html=True)
    
    # Handler do botão
    if st.button(acao_texto, key=f"btn_curso_{curso['id']}", use_container_width=True):
        if inscrito:
            st.session_state.curso_selecionado = curso["id"]
            st.rerun()
        else:
            # Lógica de inscrição
            from courses_engine import inscrever_usuario_em_curso
            try:
                inscrever_usuario_em_curso(usuario["id"], curso["id"])
                st.success("✅ Inscrito com sucesso!")
                time.sleep(1)
                st.rerun()
            except Exception as e:
                st.error(f"Erro na inscrição: {e}")

# =========================================
# TELA 2: MÓDULOS DO CURSO
# =========================================

def _tela_modulos_do_curso(usuario: Dict, curso_id: str):
    """Lista módulos de um curso específico"""
    
    db = get_db()
    curso_ref = db.collection("courses").document(curso_id).get()
    
    if not curso_ref.exists:
        st.error("Curso não encontrado.")
        st.session_state.curso_selecionado = None
        st.rerun()
        return
    
    curso = curso_ref.to_dict()
    curso["id"] = curso_id
    
    # Header com breadcrumb
    st.markdown(f"""
    <div style="display: flex; align-items: center; gap: 1rem; margin-bottom: 1.5rem;">
        <button class="btn-outline-gold" onclick="window.history.back()" style="cursor: pointer;">← Voltar</button>
        <div style="flex-grow: 1;">
            <h2 style="margin: 0;">{curso.get('titulo', 'Curso')}</h2>
            <p style="opacity: 0.7; margin: 0.25rem 0 0 0;">{curso.get('descricao', '')}</p>
        </div>
    </div>
    """, unsafe_allow_html=True)
    
    # Progresso do curso
    inscricao = obter_inscricao(usuario["id"], curso_id)
    progresso = inscricao.get("progresso", 0) if inscricao else 0
    
    col1, col2, col3 = st.columns([2, 1, 1])
    with col1:
        st.markdown(f"### 📊 Seu Progresso: {progresso:.0f}%")
        progress_bar(progresso)
    
    with col2:
        stats_card(
            curso.get("modalidade", "EAD"),
            "Modalidade",
            "🌐" if curso.get("modalidade") == "EAD" else "🏢"
        )
    
    with col3:
        stats_card(
            "Gratuito" if not curso.get("pago") else f"R$ {curso.get('preco', 0):.2f}",
            "Valor",
            "🎯" if not curso.get("pago") else "💲"
        )
    
    st.markdown("---")
    st.markdown("### 🗂️ Módulos do Curso")
    
    try:
        modulos = listar_modulos_do_curso(curso_id)
        
        if not modulos:
            empty_state(
                icon="📂",
                titulo="Nenhum módulo disponível",
                descricao="Este curso ainda não possui módulos cadastrados. Em breve!"
            )
            return
        
        for modulo in modulos:
            with st.container():
                st.markdown(f"""
                <div class="modern-card">
                    <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 1rem;">
                        <h3 style="margin: 0;">{modulo.get('titulo', 'Módulo')}</h3>
                        <span class="badge badge-gold">Módulo {modulo.get('ordem', 1)}</span>
                    </div>
                    <p style="opacity: 0.8; margin-bottom: 1.5rem;">{modulo.get('descricao', '')}</p>
                    <button class="btn-modern" id="btn_modulo_{modulo['id']}" style="width: 100%;">
                        👁️ Ver Aulas
                    </button>
                </div>
                """, unsafe_allow_html=True)
                
                if st.button("👁️ Ver Aulas", key=f"btn_mod_{modulo['id']}", use_container_width=True):
                    st.session_state.modulo_selecionado = modulo["id"]
                    st.rerun()
    
    except Exception as e:
        st.error(f"Erro ao carregar módulos: {e}")

# =========================================
# TELA 3: AULAS DO MÓDULO
# =========================================

def _tela_aulas_do_modulo(usuario: Dict, curso_id: str, modulo_id: str):
    """Lista aulas de um módulo específico"""
    
    db = get_db()
    
    # Carrega dados
    curso_ref = db.collection("courses").document(curso_id).get()
    modulo_ref = db.collection("course_modules").document(modulo_id).get()
    
    if not curso_ref.exists or not modulo_ref.exists:
        st.error("Dados não encontrados.")
        st.session_state.modulo_selecionado = None
        st.rerun()
        return
    
    curso = curso_ref.to_dict()
    modulo = modulo_ref.to_dict()
    
    # Header com breadcrumb
    st.markdown(f"""
    <div style="display: flex; align-items: center; gap: 1rem; margin-bottom: 1.5rem;">
        <button class="btn-outline-gold" onclick="window.history.back()" style="cursor: pointer;">← Voltar</button>
        <div style="flex-grow: 1;">
            <h2 style="margin: 0;">{modulo.get('titulo', 'Módulo')}</h2>
            <p style="opacity: 0.7; margin: 0.25rem 0 0 0;">
                {curso.get('titulo', 'Curso')} • Módulo {modulo.get('ordem', 1)}
            </p>
        </div>
    </div>
    """, unsafe_allow_html=True)
    
    st.markdown(f"<p style='opacity: 0.8; margin-bottom: 2rem;'>{modulo.get('descricao', '')}</p>", unsafe_allow_html=True)
    
    st.markdown("### 🎬 Aulas")
    
    try:
        aulas = listar_aulas_do_modulo(modulo_id)
        
        if not aulas:
            empty_state(
                icon="🎥",
                titulo="Nenhuma aula disponível",
                descricao="Este módulo ainda não possui aulas cadastradas."
            )
            return
        
        # Estatísticas do módulo
        total_aulas = len(aulas)
        concluidas = 0
        
        for aula in aulas:
            if verificar_aula_concluida(usuario["id"], aula["id"]):
                concluidas += 1
        
        progresso_modulo = (concluidas / total_aulas * 100) if total_aulas > 0 else 0
        
        col1, col2 = st.columns(2)
        with col1:
            stats_card(total_aulas, "Aulas", "📝")
        with col2:
            stats_card(f"{progresso_modulo:.0f}%", "Concluído", "✅")
        
        st.markdown("---")
        
        # Lista de aulas
        for idx, aula in enumerate(aulas):
            concluida = verificar_aula_concluida(usuario["id"], aula["id"])
            
            # Determina se é a aula atual (primeira não concluída)
            atual = False
            if idx == 0 and not concluida:
                atual = True
            elif idx > 0:
                aula_anterior = aulas[idx - 1]
                if verificar_aula_concluida(usuario["id"], aula_anterior["id"]) and not concluida:
                    atual = True
            
            duracao = f"{aula.get('duracao_min', 0)} min" if aula.get('duracao_min', 0) > 0 else "Duração variável"
            
            lesson_card(
                numero=idx + 1,
                titulo=aula.get('titulo', 'Aula sem título'),
                duracao=duracao,
                concluido=concluida,
                atual=atual,
                acao=f"abrir_aula('{aula['id']}')"
            )
            
            # Botão de ação
            if st.button(
                "▶️ Assistir" if not concluida else "✅ Revisar",
                key=f"btn_aula_{aula['id']}",
                use_container_width=True,
                type="primary" if atual else "secondary"
            ):
                st.session_state.aula_selecionada = aula["id"]
                st.rerun()
    
    except Exception as e:
        st.error(f"Erro ao carregar aulas: {e}")

# =========================================
# TELA 4: DETALHE DA AULA
# =========================================

def _tela_aula_detalhe(usuario: Dict, curso_id: str, modulo_id: str, aula_id: str):
    """Exibe o conteúdo detalhado de uma aula"""
    
    db = get_db()
    
    # Carrega dados
    aula_ref = db.collection("course_lessons").document(aula_id).get()
    modulo_ref = db.collection("course_modules").document(modulo_id).get()
    curso_ref = db.collection("courses").document(curso_id).get()
    
    if not all([aula_ref.exists, modulo_ref.exists, curso_ref.exists]):
        st.error("Aula não encontrada.")
        st.session_state.aula_selecionada = None
        st.rerun()
        return
    
    aula = aula_ref.to_dict()
    modulo = modulo_ref.to_dict()
    curso = curso_ref.to_dict()
    
    # Breadcrumb complexo
    st.markdown(f"""
    <div style="display: flex; align-items: center; gap: 1rem; margin-bottom: 1.5rem;">
        <button class="btn-outline-gold" onclick="window.history.back()" style="cursor: pointer;">← Voltar</button>
        <div style="flex-grow: 1;">
            <div style="font-size: 0.9rem; opacity: 0.7; margin-bottom: 0.25rem;">
                {curso.get('titulo', 'Curso')} • {modulo.get('titulo', 'Módulo')}
            </div>
            <h2 style="margin: 0;">{aula.get('titulo', 'Aula')}</h2>
        </div>
    </div>
    """, unsafe_allow_html=True)
    
    # Metadados da aula
    col1, col2, col3 = st.columns(3)
    
    with col1:
        tipo = aula.get('tipo', 'texto')
        icon_tipo = {
            'video': '🎥',
            'texto': '📄',
            'quiz': '❓',
            'arquivo': '📎'
        }.get(tipo, '📝')
        stats_card(tipo.capitalize(), "Tipo", icon_tipo)
    
    with col2:
        duracao = aula.get('duracao_min', 0)
        stats_card(f"{duracao} min" if duracao > 0 else "Flexível", "Duração", "⏱️")
    
    with col3:
        concluida = verificar_aula_concluida(usuario["id"], aula_id)
        stats_card("Concluída" if concluida else "Pendente", "Status", "✅" if concluida else "⏳")
    
    st.markdown("---")
    
    # Conteúdo da aula baseado no tipo
    tipo = aula.get('tipo', 'texto')
    conteudo = aula.get('conteudo', {})
    
    st.markdown("### 📖 Conteúdo da Aula")
    
    if tipo == 'video':
        _render_video_aula(conteudo)
    elif tipo == 'texto':
        _render_texto_aula(conteudo)
    elif tipo == 'quiz':
        _render_quiz_aula(conteudo)
    elif tipo == 'arquivo':
        _render_arquivo_aula(conteudo)
    else:
        st.info("Tipo de aula não reconhecido.")
    
    # Ações
    st.markdown("---")
    col_btn1, col_btn2, col_btn3 = st.columns([1, 1, 2])
    
    with col_btn1:
        if st.button("← Aula Anterior", use_container_width=True):
            # Lógica para aula anterior
            _navegar_aula_anterior(usuario, curso_id, modulo_id, aula_id)
    
    with col_btn2:
        if st.button("Próxima Aula →", use_container_width=True, type="primary"):
            # Lógica para próxima aula
            _navegar_proxima_aula(usuario, curso_id, modulo_id, aula_id)
    
    with col_btn3:
        concluida = verificar_aula_concluida(usuario["id"], aula_id)
        if not concluida:
            if st.button("✅ Marcar como Concluída", use_container_width=True, type="secondary"):
                try:
                    marcar_aula_concluida(usuario["id"], aula_id)
                    st.success("🎉 Aula concluída com sucesso!")
                    time.sleep(1)
                    
                    # Tenta ir para próxima aula
                    _navegar_proxima_aula(usuario, curso_id, modulo_id, aula_id)
                except Exception as e:
                    st.error(f"Erro ao marcar como concluída: {e}")
        else:
            st.success("✅ Você já concluiu esta aula!")

# =========================================
# RENDERIZADORES DE CONTEÚDO
# =========================================

def _render_video_aula(conteudo: Dict):
    """Renderiza aula do tipo vídeo"""
    url = conteudo.get('url', '')
    titulo = conteudo.get('titulo', 'Vídeo da Aula')
    
    if not url:
        st.warning("Vídeo não disponível.")
        return
    
    st.markdown(f"#### {titulo}")
    
    # YouTube
    if 'youtube.com' in url or 'youtu.be' in url:
        try:
            # Extrai ID do vídeo
            import re
            video_id = None
            
            patterns = [
                r'youtube\.com/watch\?v=([^&]+)',
                r'youtu\.be/([^?]+)',
                r'youtube\.com/embed/([^?]+)'
            ]
            
            for pattern in patterns:
                match = re.search(pattern, url)
                if match:
                    video_id = match.group(1)
                    break
            
            if video_id:
                st.video(f"https://www.youtube.com/watch?v={video_id}")
            else:
                st.markdown(f"[Assistir no YouTube]({url})")
        except:
            st.markdown(f"[Assistir no YouTube]({url})")
    
    # Vimeo
    elif 'vimeo.com' in url:
        st.markdown(f"[Assistir no Vimeo]({url})")
    
    # Arquivo MP4 direto
    elif url.endswith('.mp4'):
        st.video(url)
    
    else:
        st.markdown(f"[Abrir mídia]({url})")
    
    # Descrição
    descricao = conteudo.get('descricao', '')
    if descricao:
        st.markdown("---")
        st.markdown(f"**Descrição:** {descricao}")

def _render_texto_aula(conteudo: Dict):
    """Renderiza aula do tipo texto"""
    titulo = conteudo.get('titulo', 'Conteúdo Textual')
    texto = conteudo.get('texto', '')
    
    st.markdown(f"#### {titulo}")
    
    if not texto:
        st.info("Conteúdo textual não disponível.")
        return
    
    # Renderiza markdown
    st.markdown(texto)
    
    # Anexos
    anexos = conteudo.get('anexos', [])
    if anexos:
        st.markdown("---")
        st.markdown("#### 📎 Anexos")
        for anexo in anexos:
            nome = anexo.get('nome', 'Arquivo')
            url = anexo.get('url', '#')
            st.markdown(f"- [{nome}]({url})")

def _render_quiz_aula(conteudo: Dict):
    """Renderiza aula do tipo quiz"""
    st.warning("Quiz interativo em desenvolvimento.")
    st.markdown("Em breve: questões interativas para testar seu conhecimento.")
    
    # Fallback para texto
    if 'texto' in conteudo:
        st.markdown(conteudo['texto'])

def _render_arquivo_aula(conteudo: Dict):
    """Renderiza aula do tipo arquivo"""
    arquivos = conteudo.get('arquivos', [])
    
    if not arquivos:
        st.info("Nenhum arquivo disponível.")
        return
    
    st.markdown("#### 📂 Materiais para Download")
    
    for arquivo in arquivos:
        nome = arquivo.get('nome', 'Arquivo')
        url = arquivo.get('url', '#')
        tipo = arquivo.get('tipo', '')
        tamanho = arquivo.get('tamanho', '')
        
        icon = {
            'pdf': '📕',
            'doc': '📘',
            'zip': '🗜️',
            'image': '🖼️'
        }.get(tipo, '📎')
        
        info_tamanho = f" • {tamanho}" if tamanho else ""
        
        st.markdown(f"""
        <div class="lesson-card">
            <div style="font-size: 1.5rem;">{icon}</div>
            <div style="flex-grow: 1;">
                <div style="font-weight: 600;">{nome}</div>
                <div style="font-size: 0.85rem; opacity: 0.7;">{tipo.upper()}{info_tamanho}</div>
            </div>
            <div>
                <a href="{url}" target="_blank" class="btn-modern" style="text-decoration: none; display: inline-block; padding: 0.5rem 1rem !important;">
                    📥 Baixar
                </a>
            </div>
        </div>
        """, unsafe_allow_html=True)

# =========================================
# NAVEGAÇÃO ENTRE AULAS
# =========================================

def _navegar_aula_anterior(usuario: Dict, curso_id: str, modulo_id: str, aula_atual_id: str):
    """Navega para a aula anterior"""
    db = get_db()
    
    # Lista todas as aulas do módulo
    aulas = listar_aulas_do_modulo(modulo_id)
    
    # Encontra posição atual
    pos_atual = -1
    for idx, aula in enumerate(aulas):
        if aula["id"] == aula_atual_id:
            pos_atual = idx
            break
    
    # Se não for a primeira, vai para anterior
    if pos_atual > 0:
        st.session_state.aula_selecionada = aulas[pos_atual - 1]["id"]
    else:
        # Se for a primeira, volta para lista de módulos
        st.session_state.aula_selecionada = None
    
    st.rerun()

def _navegar_proxima_aula(usuario: Dict, curso_id: str, modulo_id: str, aula_atual_id: str):
    """Navega para a próxima aula"""
    db = get_db()
    
    # Lista todas as aulas do módulo
    aulas = listar_aulas_do_modulo(modulo_id)
    
    # Encontra posição atual
    pos_atual = -1
    for idx, aula in enumerate(aulas):
        if aula["id"] == aula_atual_id:
            pos_atual = idx
            break
    
    # Se não for a última, vai para próxima
    if pos_atual < len(aulas) - 1:
        st.session_state.aula_selecionada = aulas[pos_atual + 1]["id"]
    else:
        # Se for a última, volta para lista de módulos
        st.session_state.aula_selecionada = None
    
    st.rerun()

# =========================================
# FUNÇÃO DE INICIALIZAÇÃO
# =========================================

def init_aulas():
    """Inicializa o sistema de aulas"""
    # Apenas aplica estilos
    aplicar_estilos_modernos()
[file content end]
