"""
BJJ Digital - Sistema de Cursos (Versão Modernizada)
Integração com aulas e design atualizado (Com Funcionalidades Completas)
"""

import streamlit as st
import pandas as pd
import time
from datetime import datetime, MINYEAR
from typing import Optional, Dict, List
import plotly.express as px

# Importações internas
from database import get_db

# Importa o módulo completo com alias para chamadas genéricas
import courses_engine as ce 

# Importa a nova view de gerenciamento de aulas
import views.aulas as aulas_view 

# Importa funções específicas
from courses_engine import (
    criar_curso,
    listar_cursos_do_professor,
    listar_cursos_disponiveis_para_usuario,
    inscrever_usuario_em_curso,
    obter_inscricao,
    listar_modulos_e_aulas,
    verificar_aula_concluida,    # Adicionado para evitar erro na função wrapper
    marcar_aula_concluida,       # Adicionado para evitar erro na função wrapper
    editar_curso                 # Adicionado para garantir funcionamento da edição
)

# --- 1. CONFIGURAÇÃO DE CORES IGUAL AO APP.PY ---
try:
    from config import COR_FUNDO, COR_TEXTO, COR_DESTAQUE, COR_BOTAO, COR_HOVER
except ImportError:
    COR_FUNDO = "#0e2d26"
    COR_TEXTO = "#FFFFFF"
    COR_DESTAQUE = "#FFD770"
    COR_BOTAO = "#078B6C" # Verde BJJ Digital
    COR_HOVER = "#FFD770" # Dourado

# ======================================================
# LÓGICAS DE CONSULTA DE PROGRESSO (Wrapper para UI)
# ======================================================

def obter_progresso_aula(user_id: str, curso_id: str, aula_id: str) -> bool:
    """Função wrapper para verificar se a aula está concluída, usando o Engine."""
    return ce.verificar_aula_concluida(user_id, aula_id)

def registrar_progresso_aula(user_id: str, curso_id: str, aula_id: str) -> int:
    """Marca a aula como concluída e retorna o novo progresso total."""
    ce.marcar_aula_concluida(user_id, aula_id) 
    inscricao_atualizada = obter_inscricao(user_id, curso_id)
    
    if inscricao_atualizada:
        return inscricao_atualizada.get("progresso", 0)
    else:
        return 0

# ======================================================
# ESTILOS MODERNOS PARA CURSOS (ATUALIZADO)
# ======================================================

def aplicar_estilos_cursos():
    """Aplica estilos modernos específicos para cursos, ALINHADO COM APP.PY"""
    
    # Usamos f-string para injetar as variáveis de cor corretamente
    st.markdown(f"""
    <style>
    /* CARDS DE CURSO MODERNOS */
    .curso-card-moderno {{
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
    }}
    
    .curso-card-moderno::before {{
        content: '';
        position: absolute;
        top: 0;
        left: 0;
        right: 0;
        height: 4px;
        background: linear-gradient(90deg, {COR_BOTAO} 0%, {COR_DESTAQUE} 100%);
        border-radius: 20px 20px 0 0;
    }}
    
    .curso-card-moderno:hover {{
        border-color: {COR_DESTAQUE};
        transform: translateY(-8px);
        box-shadow: 0 20px 60px rgba(0, 0, 0, 0.4);
    }}
    
    .curso-card-moderno.completed::before {{
        background: linear-gradient(90deg, #10B981 0%, #34D399 100%);
    }}
    
    .curso-card-moderno.in-progress::before {{
        background: linear-gradient(90deg, #3B82F6 0%, #60A5FA 100%);
    }}
    
    .curso-icon {{
        font-size: 2.5rem;
        margin-bottom: 1rem;
        text-align: center;
        background: linear-gradient(135deg, {COR_BOTAO} 0%, {COR_DESTAQUE} 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
    }}
    
    .curso-badges {{
        display: flex;
        flex-wrap: wrap;
        gap: 0.5rem;
        margin: 1rem 0;
    }}
    
    .curso-badge {{
        padding: 0.25rem 0.75rem;
        border-radius: 20px;
        font-size: 0.75rem;
        font-weight: 600;
        background: rgba(255, 255, 255, 0.1);
        border: 1px solid rgba(255, 255, 255, 0.2);
    }}
    
    .curso-badge.gold {{
        background: rgba(255, 215, 112, 0.15);
        border-color: rgba(255, 215, 112, 0.3);
        color: {COR_DESTAQUE};
    }}
    
    .curso-badge.green {{
        background: rgba(7, 139, 108, 0.15);
        border-color: rgba(7, 139, 108, 0.3);
        color: {COR_BOTAO};
    }}
    
    .curso-badge.blue {{
        background: rgba(59, 130, 246, 0.15);
        border-color: rgba(59, 130, 246, 0.3);
        color: #60A5FA;
    }}
    
    /* PROGRESS BAR MODERNA */
    .curso-progress {{
        background: rgba(255, 255, 255, 0.05);
        border-radius: 10px;
        height: 10px;
        overflow: hidden;
        margin: 0.75rem 0;
    }}
    
    .curso-progress-fill {{
        height: 100%;
        background: linear-gradient(90deg, {COR_BOTAO} 0%, {COR_DESTAQUE} 100%);
        border-radius: 10px;
        transition: width 0.5s ease;
    }}
    
    /* DETALHES */
    .detalhes-grid {{
        display: grid;
        grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
        gap: 1rem;
        margin: 1rem 0 2rem 0;
    }}
    .detalhe-card {{
        background: linear-gradient(145deg, rgba(255, 255, 255, 0.03) 0%, rgba(255, 255, 255, 0.01) 100%);
        border: 1px solid rgba(255, 215, 112, 0.15);
        border-radius: 16px;
        padding: 1.2rem;
        display: flex;
        align-items: center;
        backdrop-filter: blur(10px);
        transition: transform 0.3s ease, border-color 0.3s ease;
    }}
    .detalhe-card:hover {{
        border-color: rgba(255, 215, 112, 0.4);
        transform: translateY(-3px);
    }}
    .detalhe-icon {{
        font-size: 2.2rem;
        margin-right: 1rem;
        background: linear-gradient(135deg, {COR_DESTAQUE} 0%, #E6B91E 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        filter: drop-shadow(0 2px 4px rgba(0,0,0,0.3));
    }}
    .detalhe-info {{
        display: flex;
        flex-direction: column;
    }}
    .detalhe-label {{
        font-size: 0.75rem;
        text-transform: uppercase;
        letter-spacing: 1px;
        opacity: 0.7;
        margin-bottom: 0.2rem;
    }}
    .detalhe-value {{
        font-size: 1.1rem;
        font-weight: 700;
        color: white;
    }}

    /* AULA COMPLETA */
    .aula-completa {{
        background-color: rgba(7, 139, 108, 0.1);
        border-left: 5px solid {COR_BOTAO};
        padding: 0.5rem;
        border-radius: 8px;
        color: #34D399;
        margin-bottom: 0.5rem;
        display: flex;
        align-items: center;
    }}
    
    /* AREA MATERIAL DE APOIO */
    .material-apoio-box {{
        margin-top: 1.5rem;
        padding: 1rem;
        background: rgba(255, 255, 255, 0.05);
        border-radius: 12px;
        border: 1px solid rgba(255, 215, 112, 0.1);
    }}

    div.stButton > button, div.stFormSubmitButton > button {{ 
        background: linear-gradient(135deg, {COR_BOTAO} 0%, #056853 100%) !important; 
        color: white !important; 
        border: 1px solid rgba(255,255,255,0.1) !important; 
        padding: 0.6em 1.5em !important; 
        font-weight: 600 !important;
        border-radius: 8px !important; 
        transition: all 0.3s ease !important;
    }}
    
    /* Hover dos Botões Primários - Fica DOURADO */
    .stButton>button[data-testid="stFormSubmitButton"]:hover, 
    .stButton>button[kind="primary"]:hover,
    .stButton>button[key^="enroll_"]:hover,
    .stButton>button[key^="cont_"]:hover,
    .stButton>button[key^="btn_det_add_aulas"]:hover,
    .stButton>button[key^="btn_dl_pdf"]:hover {{
        background: {COR_HOVER} !important;
        color: #0e2d26 !important;
        transform: translateY(-2px);
        box-shadow: 0 4px 12px rgba(255, 215, 112, 0.3);
    }}

    div.stButton > button, div.stFormSubmitButton > button {{ 
        background: linear-gradient(135deg, {COR_BOTAO} 0%, #056853 100%) !important; 
        color: white !important; 
        border: 1px solid rgba(255,255,255,0.1) !important; 
        padding: 0.6em 1.5em !important; 
        font-weight: 600 !important;
        border-radius: 8px !important; 
        transition: all 0.3s ease !important;
    }}
    div.stButton > button:hover {{ 
        background: {COR_HOVER} !important; 
        color: #0e2d26 !important; 
        transform: translateY(-2px);
        box-shadow: 0 4px 12px rgba(255, 215, 112, 0.3);
    }}
    
    .stButton>button[kind="secondary"]:hover,
    .stButton>button[key^="edit_"]:hover,
    .stButton>button[key^="view_"]:hover,
    .stButton>button[key^="access_"]:hover,
    .stButton>button[key^="cert_"]:hover,
    .stButton>button[key^="rev_"]:hover,
    .stButton>button[key^="btn_voltar_"]:hover,
    .stButton>button[key^="btn_det_editar"]:hover {{
        background: {COR_DESTAQUE} !important;
        color: #0e2d26 !important;
        transform: translateY(-2px);
    }}
    
    /* HEADER MODERNO */
    .curso-header {{
        background: linear-gradient(135deg, rgba(14, 45, 38, 0.8) 0%, rgba(9, 31, 26, 0.9) 100%);
        border-bottom: 1px solid rgba(255, 215, 112, 0.2);
        padding: 1.5rem;
        border-radius: 0 0 20px 20px;
        margin-bottom: 2rem;
    }}
    
    /* STATS CARDS */
    .stats-card-moderno {{
        background: rgba(255, 255, 255, 0.03);
        border: 1px solid rgba(255, 255, 255, 0.05);
        border-radius: 16px;
        padding: 1.5rem;
        text-align: center;
        transition: all 0.3s ease;
    }}
    
    .stats-card-moderno:hover {{
        background: rgba(255, 255, 255, 0.05);
        border-color: {COR_DESTAQUE};
        transform: translateY(-4px);
    }}
    
    .stats-value-moderno {{
        font-size: 2.5rem;
        font-weight: 700;
        background: linear-gradient(135deg, {COR_DESTAQUE} 0%, #FFFFFF 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        margin: 0.5rem 0;
    }}
    
    .stats-label-moderno {{
        color: rgba(255, 255, 255, 0.7);
        font-size: 0.9rem;
        text-transform: uppercase;
        letter-spacing: 1px;
    }}
    
    /* EMPTY STATE */
    .empty-state {{
        text-align: center;
        padding: 4rem 2rem;
        border-radius: 20px;
        background: rgba(255,255,255,0.02);
        border: 2px dashed rgba(255,215,112,0.2);
    }}
    
    .empty-state-icon {{
        font-size: 4rem;
        margin-bottom: 1rem;
        opacity: 0.5;
    }}
    
    </style>
    """, unsafe_allow_html=True)

# ======================================================
# LÓGICAS DE ROTEAMENTO E NAVEGAÇÃO
# ======================================================

def navegar_para(view: str, curso: Optional[Dict] = None):
    """Atualiza o estado de navegação para a tela desejada."""
    st.session_state['cursos_view'] = view
    st.session_state['curso_selecionado'] = curso
    st.rerun()

def pagina_cursos(usuario: dict):
    """Página principal do sistema de cursos, gerencia navegação."""
    
    aplicar_estilos_cursos()
    
    # 1. Obter estado atual (ou definir padrão)
    if 'cursos_view' not in st.session_state:
        st.session_state['cursos_view'] = 'lista'
    if 'curso_selecionado' not in st.session_state:
        st.session_state['curso_selecionado'] = None
  
    # Botão de voltar
    if st.session_state.get('cursos_view') != 'lista':
        # Botão para voltar da sub-tela para a lista principal
        if st.button("← Voltar à Lista de Cursos", key="btn_voltar_lista_cursos", type="secondary"):
            navegar_para('lista')
    else:
        # Botão para voltar para o menu principal do aplicativo
        if st.button("← Voltar ao Início", key="btn_voltar_menu_principal"):
            st.session_state.menu_selection = "Início"
            st.rerun()
    
    st.markdown("<br>", unsafe_allow_html=True)
    
    # 2. Roteamento baseado no estado
    view = st.session_state.get('cursos_view')
    curso_selecionado = st.session_state.get('curso_selecionado')
    tipo = str(usuario.get("tipo", "aluno")).lower()
    
    if view == 'lista':
        if tipo in ["admin", "professor"]:
            _interface_professor_moderna(usuario)
        else:
            _interface_aluno_moderna(usuario)
            
    elif view == 'detalhe' and curso_selecionado:
        _exibir_detalhes_curso(curso_selecionado, usuario)

    elif view == 'aulas' and curso_selecionado:
        _pagina_aulas(curso_selecionado, usuario)

    elif view == 'edicao' and curso_selecionado and tipo in ["admin", "professor"]:
        _pagina_edicao_curso(curso_selecionado, usuario)

    # --- NOVA ROTA: GERENCIADOR DE CONTEÚDO ---
    elif view == 'gerenciar_conteudo' and curso_selecionado and tipo in ["admin", "professor"]:
        aulas_view.gerenciar_conteudo_curso(curso_selecionado, usuario)

    else:
        # Fallback para a lista se o estado for inválido
        st.session_state['cursos_view'] = 'lista'
        st.rerun()

# ======================================================
# PÁGINAS ESPECÍFICAS (Detalhe, Aulas, Edição)
# ======================================================

def _exibir_detalhes_curso(curso: dict, usuario: dict):
    """Exibe a página de detalhes de um curso, incluindo módulos."""
    
    st.markdown(f"## 📚 {curso.get('titulo', 'Detalhe do Curso')}")
    st.markdown("---")
    
    col_info, col_acao = st.columns([3, 1])

    with col_info:
        st.markdown(f"#### 📖 Descrição Completa")
        st.write(curso.get('descricao', 'Descrição detalhada não disponível.'))
        
        st.markdown(f"#### ⚙️ Detalhes")
        
        # Extraindo dados para facilitar
        prof = curso.get("professor_nome", "N/A").title()
        mod = curso.get("modalidade", "N/A")
        nivel = curso.get("nivel", "Todos os Níveis")
        duracao = curso.get("duracao_estimada", "Aberto")

        # HTML corrigido
        html_detalhes = f"""<div class="detalhes-grid"><div class="detalhe-card"><div class="detalhe-icon">🥋</div><div class="detalhe-info"><span class="detalhe-label">Professor</span><span class="detalhe-value">{prof}</span></div></div><div class="detalhe-card"><div class="detalhe-icon">📡</div><div class="detalhe-info"><span class="detalhe-label">Modalidade</span><span class="detalhe-value">{mod}</span></div></div><div class="detalhe-card"><div class="detalhe-icon">📈</div><div class="detalhe-info"><span class="detalhe-label">Nível</span><span class="detalhe-value">{nivel}</span></div></div><div class="detalhe-card"><div class="detalhe-icon">⏳</div><div class="detalhe-info"><span class="detalhe-label">Duração Estimada</span><span class="detalhe-value">{duracao}</span></div></div></div>"""
        st.markdown(html_detalhes, unsafe_allow_html=True)

        st.markdown(f"#### 📝 Conteúdo Programático (Módulos)")
        modulos = listar_modulos_e_aulas(curso['id']) 
        if modulos:
            for modulo in modulos:
                with st.expander(f"Módulo {modulos.index(modulo) + 1}: {modulo['titulo']} ({len(modulo['aulas'])} aulas)", expanded=True):
                    if modulo['aulas']:
                        st.markdown("- " + "\n- ".join([a['titulo'] for a in modulo['aulas']]))
                    else:
                        st.caption("Nenhuma aula adicionada a este módulo.")
        else:
            st.info("Este curso ainda não possui módulos cadastrados.")

    with col_acao:
        is_professor = usuario.get("tipo", "aluno") in ["admin", "professor"]
        inscricao = obter_inscricao(usuario["id"], curso["id"])
        ja_inscrito = inscricao is not None

        if is_professor:
             if st.button("✏️ Editar Curso", key="btn_det_editar", use_container_width=True, type="secondary"):
                 navegar_para('edicao', curso)
             
             # --- BOTÃO CONECTADO AO GERENCIADOR DE AULAS ---
             if st.button("➕ Adicionar Aulas", key="btn_det_add_aulas", use_container_width=True, type="primary"):
                 navegar_para('gerenciar_conteudo', curso)
        
        elif ja_inscrito:
            # Se for aluno e já inscrito
            progresso = inscricao.get("progresso", 0)
            st.metric("Seu Progresso", f"{progresso:.0f}%", delta=None)

            if progresso >= 100:
                if st.button("📜 Emitir Certificado", key="btn_det_certificado", use_container_width=True, type="secondary"):
                    st.success("✅ Certificado de Conclusão emitido com sucesso! ")
                if st.button("🔁 Acessar Aulas Novamente", key="btn_det_revisar", use_container_width=True, type="secondary"):
                    navegar_para('aulas', curso)
            else:
                 if st.button("🎬 Continuar Assistindo", key="btn_det_continuar", use_container_width=True, type="primary"):
                    navegar_para('aulas', curso)
        else:
            # Se for aluno e não inscrito
            if curso.get('pago', False):
                 st.markdown(f"**Valor: R$ {curso.get('preco', 0):.2f}**")
            
            if st.button("🔓 Inscrever-se Agora", key="btn_det_inscrever", use_container_width=True, type="primary"):
                try:
                    inscrever_usuario_em_curso(usuario["id"], curso["id"])
                    st.success("🎉 Inscrição realizada com sucesso! Você será redirecionado para as aulas.")
                    time.sleep(1)
                    navegar_para('aulas', curso)
                except Exception as e:
                    st.error(f"Erro na inscrição: {e}")

def _pagina_aulas(curso: dict, usuario: dict):
    """Página de consumo do curso, exibe aulas e permite marcar progresso (ATUALIZADA)."""
    
    st.markdown(f"## 🎬 Aulas: {curso.get('titulo', 'Curso')}")
    st.markdown("---")
    
    inscricao = obter_inscricao(usuario["id"], curso["id"])
    if not inscricao:
        st.error("Erro: Inscrição não encontrada. Por favor, volte e inscreva-se novamente.")
        return
        
    progresso_total = inscricao.get("progresso", 0)
    st.progress(progresso_total / 100, text=f"Progresso Geral: {progresso_total:.0f}%")

    col_video, col_modulos = st.columns([3, 1])

    modulos = listar_modulos_e_aulas(curso['id'])
    
    # 1. Gerenciar Aula Atual
    if 'aula_atual' not in st.session_state:
        try:
            # Encontra a primeira aula não concluída
            primeira_aula = None
            for mod in modulos:
                for aula in mod['aulas']:
                    if not obter_progresso_aula(usuario["id"], curso["id"], aula['id']):
                        primeira_aula = aula
                        break
                if primeira_aula:
                    break
            
            st.session_state['aula_atual'] = primeira_aula if primeira_aula else modulos[0]['aulas'][0]

        except IndexError:
             with col_video:
                st.warning("Nenhuma aula encontrada para este curso.")
             return
    
    aula_atual = st.session_state['aula_atual']
    aula_completa = obter_progresso_aula(usuario["id"], curso["id"], aula_atual['id'])

    with col_video:
        st.markdown(f"### ▶️ {aula_atual['titulo']}")
        
        conteudo = aula_atual.get('conteudo', {})
        tipo = aula_atual.get('tipo')

        # --- LÓGICA DE EXIBIÇÃO DE VÍDEO (LINK OU UPLOAD) ---
        if tipo == 'video':
            tipo_video = conteudo.get('tipo_video', 'link') # default para 'link' se não existir
            
            if tipo_video == 'link':
                url = conteudo.get('url')
                if url:
                    st.video(url)
                else:
                    st.info("Link de vídeo indisponível.")
            elif tipo_video == 'upload':
                arquivo = conteudo.get('arquivo_video')
                if arquivo:
                    st.video(arquivo)
                else:
                    st.info("Arquivo de vídeo não encontrado.")
            
            # Descrição do vídeo (opcional)
            if isinstance(conteudo, dict) and conteudo.get('descricao'):
                st.markdown("---")
                st.write(conteudo.get('descricao'))

        elif tipo == 'texto':
            texto = conteudo.get('texto') if isinstance(conteudo, dict) else ""
            st.markdown(texto)
            
        elif tipo == 'quiz':
            st.warning("⚠️ Esta é uma avaliação. Para progredir, marque como concluída.")
            st.markdown("---")
            if isinstance(conteudo, dict):
                st.write(conteudo.get('pergunta', 'Pergunta não definida'))
                # Lógica básica de quiz (apenas visual por enquanto)
                if 'opcoes' in conteudo:
                    st.radio("Escolha uma opção:", conteudo['opcoes'], key=f"quiz_{aula_atual['id']}")
        else:
             st.info("Conteúdo em formato desconhecido.")

        # --- ÁREA DE MATERIAL DE APOIO (PDF) ---
        material_pdf = conteudo.get('material_apoio')
        if material_pdf:
            st.markdown("<div class='material-apoio-box'>", unsafe_allow_html=True)
            st.markdown("#### 📎 Material de Apoio")
            nome_pdf = conteudo.get('nome_arquivo_pdf', 'Material de Apoio.pdf')
            st.download_button(
                label=f"📥 Baixar {nome_pdf}",
                data=material_pdf,
                file_name=nome_pdf,
                mime="application/pdf",
                key=f"btn_dl_pdf_{aula_atual['id']}",
                type="primary"
            )
            st.markdown("</div>", unsafe_allow_html=True)

        st.markdown("<br>", unsafe_allow_html=True)

        # Botão de conclusão
        if not aula_completa:
             if st.button(f"✅ Marcar '{aula_atual['titulo']}' como Concluída", key=f"btn_concluir_aula_{aula_atual['id']}", type="primary"):
                 novo_progresso = registrar_progresso_aula(usuario["id"], curso["id"], aula_atual['id'])
                 st.success(f"Aula concluída! Progresso atualizado para {novo_progresso:.0f}%")
                 time.sleep(1)
                 st.rerun()
        else:
            st.markdown('<div class="aula-completa">🎉 Concluído</div>', unsafe_allow_html=True)
            if progresso_total < 100:
                if st.button("Próxima Aula →", key=f"btn_proxima_{aula_atual['id']}", type="secondary"):
                     st.info("Selecione a próxima aula no menu ao lado.")
            
    # 2. Navegação Lateral de Módulos
    with col_modulos:
        st.markdown("### 📋 Módulos")
        
        for modulo in modulos:
            st.subheader(f"{modulo['titulo']}", divider='orange')
            for aula in modulo['aulas']:
                is_completa = obter_progresso_aula(usuario["id"], curso["id"], aula['id'])
                is_atual = aula['id'] == aula_atual['id']
                
                label = f"{'✅' if is_completa else '⚪'} {aula['titulo']}"
                
                if is_atual:
                    st.markdown(f"**▶️ {label}**")
                else:
                    if st.button(label, key=f"btn_aula_{aula['id']}", use_container_width=True, type="secondary"):
                        st.session_state['aula_atual'] = aula
                        st.rerun()

def _pagina_edicao_curso(curso_original: dict, usuario: dict):
    """Formulário moderno para editar cursos"""
    
    st.markdown(f"## ✏️ Editando Curso: {curso_original.get('titulo', 'Novo Curso')}")
    st.markdown("---")
    
    pago_toggle_key = f"edit_pago_toggle_{curso_original['id']}"
    if pago_toggle_key not in st.session_state:
        st.session_state[pago_toggle_key] = curso_original.get("pago", False)

    with st.form(f"form_editar_curso_moderno_{curso_original['id']}", border=True):
        
        st.markdown("### 📝 Informações Básicas")
        
        col1, col2 = st.columns([2, 1])
        
        with col1:
            titulo = st.text_input(
                "Título do Curso *",
                value=curso_original.get("titulo", ""),
                key=f"edit_titulo_{curso_original['id']}"
            )
            
            descricao = st.text_area(
                "Descrição Detalhada *",
                value=curso_original.get("descricao", ""),
                height=120,
                key=f"edit_descricao_{curso_original['id']}"
            )
        
        with col2:
            modalidade = st.selectbox(
                "Modalidade *",
                ["EAD", "Presencial", "Híbrido"],
                index=["EAD", "Presencial", "Híbrido"].index(curso_original.get("modalidade", "EAD")),
                key=f"edit_modalidade_{curso_original['id']}"
            )
            
            publico = st.selectbox(
                "Público Alvo *",
                ["geral", "equipe"],
                format_func=lambda v: "🌍 Geral (Público Aberto)" if v == "geral" else "👥 Apenas Minha Equipe",
                index=["geral", "equipe"].index(curso_original.get("publico", "geral")),
                key=f"edit_publico_{curso_original['id']}"
            )
            
            equipe_destino = curso_original.get("equipe_destino")
            if publico == "equipe":
                equipe_destino = st.text_input(
                    "Nome da Equipe *",
                    value=equipe_destino or "",
                    key=f"edit_equipe_{curso_original['id']}"
                )
        
        st.markdown("---")
        st.markdown("### ⚙️ Configurações")
        
        col3, col4 = st.columns(2)
        
        with col3:
            certificado_auto = st.checkbox(
                "Emitir certificado automaticamente",
                value=curso_original.get("certificado_automatico", True),
                key=f"edit_certificado_{curso_original['id']}"
            )
            st.checkbox(
                "Curso Ativo (Disponível para Inscrição)",
                value=curso_original.get("ativo", True),
                key=f"edit_ativo_{curso_original['id']}"
            )
        
        with col4:
            duracao_estimada = st.text_input(
                "Duração Estimada",
                value=curso_original.get("duracao_estimada", ""),
                key=f"edit_duracao_{curso_original['id']}"
            )
            
            nivel = st.selectbox(
                "Nível do Curso",
                ["Iniciante", "Intermediário", "Avançado", "Todos os Níveis"],
                index=["Iniciante", "Intermediário", "Avançado", "Todos os Níveis"].index(curso_original.get("nivel", "Todos os Níveis")),
                key=f"edit_nivel_{curso_original['id']}"
            )
        
        st.markdown("---")
        st.markdown("### 💰 Configurações Financeiras")
        
        col5, col6, col7 = st.columns([1, 1, 1])
        
        with col5:
            st.toggle(
                "Curso Pago?",
                value=st.session_state[pago_toggle_key],
                key=pago_toggle_key,
            )
        
        with col6:
            preco = st.number_input(
                "Valor (R$)",
                min_value=0.0,
                value=curso_original.get("preco", 0.0),
                step=10.0,
                disabled=not st.session_state[pago_toggle_key],
                key=f"edit_preco_{curso_original['id']}"
            )
        
        with col7:
            is_admin = usuario.get("tipo") == "admin"
            split_custom = curso_original.get("split_custom", 10)
            
            if st.session_state[pago_toggle_key]:
                if is_admin:
                    split_custom = st.slider(
                        "Taxa da Plataforma (%)",
                        0, 100,
                        value=split_custom,
                        key=f"edit_split_{curso_original['id']}"
                    )
                else:
                    st.caption(f"Taxa da plataforma: {split_custom}%")
                    st.info("Apenas administradores podem alterar a taxa.")
            else:
                split_custom = None 

        st.markdown("---")
        
        # Botão de submit
        col_submit1, col_submit2 = st.columns([1, 3])
        
        with col_submit1:
            if st.form_submit_button("❌ Cancelar", use_container_width=True, type="secondary"):
                navegar_para('lista')
        
        with col_submit2:
            submit = st.form_submit_button(
                "💾 Salvar Alterações",
                type="primary",
                use_container_width=True
            )
            
            if submit:
                # 1. Monta o payload de dados
                dados_atualizados = {
                    "titulo": titulo,
                    "descricao": descricao,
                    "modalidade": modalidade,
                    "publico": publico,
                    "equipe_destino": equipe_destino if publico == "equipe" else None,
                    "certificado_automatico": st.session_state[f"edit_certificado_{curso_original['id']}"],
                    "ativo": st.session_state[f"edit_ativo_{curso_original['id']}"],
                    "duracao_estimada": duracao_estimada,
                    "nivel": nivel,
                    "pago": st.session_state[pago_toggle_key],
                    "preco": preco if st.session_state[pago_toggle_key] else 0.0,
                    "split_custom": split_custom,
                    "atualizado_em": datetime.now() # Adiciona timestamp
                }
                
                # 2. Validações simples
                if not titulo.strip() or not descricao.strip():
                      st.error("⚠️ Título e descrição são obrigatórios.")
                      return
                
                # 3. Chama a função de edição (usando a função real do courses_engine)
                try:
                    if ce.editar_curso(curso_original["id"], dados_atualizados):
                        st.success("🎉 Curso atualizado com sucesso!")
                        time.sleep(1)
                        # Redireciona de volta para os detalhes (ou lista)
                        navegar_para('detalhe', dados_atualizados) 
                    else:
                        st.error("❌ Erro desconhecido ao salvar. Tente novamente.")
                except Exception as e:
                    st.error(f"❌ Erro ao salvar curso: {e}")


# ======================================================
# INTERFACE DO PROFESSOR / ADMIN
# ======================================================

def _interface_professor_moderna(usuario: dict):
    tab1, tab2, tab3 = st.tabs([
        "📘 Meus Cursos",
        "➕ Criar Novo",
        "📊 Dashboard"
    ])
    
    with tab1:
        _professor_listar_cursos(usuario)
    
    with tab2:
        _pagina_edicao_curso_new(usuario) 
    
    with tab3:
        _professor_dashboard(usuario)


def _pagina_edicao_curso_new(usuario: dict):
    """Função para Criar Novo Curso"""
    
    st.markdown("""
    <div style="background: rgba(255,255,255,0.05); padding: 1.5rem; border-radius: 20px; margin-bottom: 2rem;">
        <h3 style="margin: 0 0 0.5rem 0;">🚀 Criar Novo Curso</h3>
        <p style="opacity: 0.8; margin: 0;">Preencha os detalhes abaixo para criar um curso incrível!</p>
    </div>
    """, unsafe_allow_html=True)
    
    # Inicializa o estado do toggle
    if "criar_curso_pago_toggle_new" not in st.session_state:
        st.session_state["criar_curso_pago_toggle_new"] = False
        
    with st.form("form_criar_curso_moderno_new", clear_on_submit=False, border=True):
        
        st.markdown("### 📝 Informações Básicas")
        
        col1, col2 = st.columns([2, 1])
        
        with col1:
            titulo = st.text_input(
                "Título do Curso *", placeholder="Ex: Fundamentos do Jiu-Jitsu para Iniciantes", key="c_titulo_input"
            )
            descricao = st.text_area(
                "Descrição Detalhada *", height=120, placeholder="Descreva o que os alunos aprenderão...", key="c_descricao_input"
            )
        
        with col2:
            modalidade = st.selectbox("Modalidade *", ["EAD", "Presencial", "Híbrido"], key="c_modalidade_select")
            publico = st.selectbox("Público Alvo *", ["geral", "equipe"], format_func=lambda v: "🌍 Geral (Público Aberto)" if v == "geral" else "👥 Apenas Minha Equipe", key="c_publico_select")
            equipe_destino = None
            if publico == "equipe":
                equipe_destino = st.text_input("Nome da Equipe *", placeholder="Ex: Equipe BJJ Champions", key="c_equipe_input")
        
        st.markdown("---")
        st.markdown("### 💰 Configurações Financeiras")
        
        col5, col6, col7 = st.columns([1, 1, 1])
        
        with col5:
            pago = st.toggle("Curso Pago?", value=st.session_state["criar_curso_pago_toggle_new"], key="criar_curso_pago_toggle_new")
        
        with col6:
            preco = st.number_input("Valor (R$)", min_value=0.0, value=0.0, step=10.0, disabled=not st.session_state["criar_curso_pago_toggle_new"], key="c_preco_input")
        
        with col7:
            is_admin = usuario.get("tipo") == "admin"
            split_custom = 10
            if st.session_state["criar_curso_pago_toggle_new"] and is_admin:
                split_custom = st.slider("Taxa da Plataforma (%)", 0, 100, value=10, key="c_split_slider")
            elif st.session_state["criar_curso_pago_toggle_new"]:
                st.caption(f"Taxa da plataforma: {split_custom}%")
        
        st.markdown("---")
        
        col_submit1, col_submit2 = st.columns([1, 3])
        
        with col_submit1:
            if st.form_submit_button("❌ Limpar", use_container_width=True, type="secondary"):
                 # Resetando inputs por chave
                 st.session_state["c_titulo_input"] = ""
                 st.session_state["c_descricao_input"] = ""
                 st.session_state["c_equipe_input"] = "" if "c_equipe_input" in st.session_state else ""
                 st.session_state["c_preco_input"] = 0.0
                 st.session_state["criar_curso_pago_toggle_new"] = False
                 st.rerun() # Limpa o formulário
        
        with col_submit2:
            submit = st.form_submit_button("🚀 Criar Curso Agora", type="primary", use_container_width=True)
            
            if submit:
                # Lógica de criação
                erros = []
                if not titulo.strip(): erros.append("⚠️ O título é obrigatório.")
                if not descricao.strip(): erros.append("⚠️ A descrição é obrigatória.")
                if publico == "equipe" and (not equipe_destino or not equipe_destino.strip()): erros.append("⚠️ Informe o nome da equipe.")
                if pago and preco <= 0: erros.append("⚠️ Cursos pagos devem ter valor maior que zero.")
                
                if erros:
                    for erro in erros: st.error(erro)
                    return
                
                try:
                    # USANDO A FUNÇÃO REAL: criar_curso do courses_engine.py
                    curso_id = criar_curso(
                        professor_id=usuario["id"], nome_professor=usuario.get("nome", ""),
                        titulo=titulo, descricao=descricao, modalidade=modalidade, publico=publico,
                        equipe_destino=equipe_destino, pago=pago, preco=preco if pago else 0.0,
                        split_custom=split_custom, certificado_automatico=True, # Valores simplificados
                    )
                    st.success("🎉 Curso criado com sucesso!")
                    st.balloons()
                    time.sleep(1)
                    navegar_para('lista') # Volta para a lista de cursos
                except Exception as e:
                    st.error(f"❌ Erro ao criar curso: {e}")

def _professor_listar_cursos(usuario: dict):
    """Lista cursos do professor com design moderno (Ajustado para navegação)"""
    
    try:
        cursos = listar_cursos_do_professor(usuario["id"])
    except Exception as e:
        st.error(f"❌ Erro ao carregar cursos: {e}")
        cursos = []
    
    # Grid de cursos
    st.markdown("### 🎯 Meus Cursos")
    
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
    
    # Implemente a lógica de filtragem original aqui antes de prosseguir com o loop
    cursos_filtrados = cursos
    
    cols = st.columns(3)
    for idx, curso in enumerate(cursos_filtrados):
        with cols[idx % 3]:
            _render_card_curso_professor(curso, usuario)

def _render_card_curso_professor(curso: dict, usuario: dict):
    """Renderiza card de curso para professor (Ajustado para navegação e correção de botões)"""
    
    ativo = curso.get('ativo', True)
    pago = curso.get('pago', False)
    modalidade = curso.get('modalidade', 'EAD')
    publico = curso.get('publico', 'geral')
    
    card_class = "curso-card-moderno"
    if not ativo: card_class += " in-progress"
    
    icon = "🎓" if ativo else "⏸️"
    if pago: icon = "💎" if ativo else "💸"
    
    # HTML SEM RECUO para evitar blocos de código
    badges_html = f"""<div class="curso-badges"><span class="curso-badge {'gold' if ativo else ''}">{"🟢 Ativo" if ativo else "🔴 Inativo"}</span><span class="curso-badge green">{modalidade}</span><span class="curso-badge blue">{"👥 Equipe" if publico == 'equipe' else "🌍 Geral"}</span></div>"""
    
    preco_html = ""
    if pago:
        preco = curso.get('preco', 0)
        split = curso.get('split_custom', 10)
        preco_html = f"""<div style="margin: 1rem 0; padding: 0.75rem; background: rgba(255,215,112,0.1); border-radius: 10px;"><div style="font-size: 1.5rem; font-weight: bold; color: {COR_DESTAQUE};">R$ {preco:.2f}</div><div style="font-size: 0.85rem; opacity: 0.8;">Taxa: {split}% • Liq: R$ {preco * (1 - split/100):.2f}</div></div>"""
    else:
        preco_html = """<div style="margin: 1rem 0; padding: 0.75rem; background: rgba(7,139,108,0.1); border-radius: 10px;"><div style="font-size: 1.25rem; font-weight: bold; color: #078B6C;">🎯 Curso Gratuito</div><div style="font-size: 0.85rem; opacity: 0.8;">Sem custos para os alunos</div></div>"""
    
    desc = curso.get('descricao', 'Sem descrição')
    if len(desc) > 120: desc = desc[:120] + "..."
    
    st.markdown(f"""
    <div class="{card_class}">
        <div class="curso-icon">{icon}</div>
        <h4 style="margin: 0 0 0.5rem 0;">{curso.get('titulo', 'Sem Título')}</h4>
        <p style="opacity: 0.8; margin-bottom: 1rem; flex-grow: 1;">{desc}</p>
        {badges_html}
        {preco_html}
    </div>
    """, unsafe_allow_html=True)
    
    st.markdown(f'<div style="margin-top: -1rem; margin-bottom: 1rem;">', unsafe_allow_html=True)
    col1, col2 = st.columns(2)
    with col1:
        if st.button("✏️ Editar", key=f"edit_prof_{curso['id']}", use_container_width=True, type="secondary"):
            navegar_para('edicao', curso)
    
    with col2:
        if st.button("👁️ Ver", key=f"view_prof_{curso['id']}", use_container_width=True, type="secondary"):
             navegar_para('detalhe', curso)
    
    st.markdown('</div>', unsafe_allow_html=True)

def _professor_dashboard(usuario: dict):
    """Dashboard do professor (CORRIGIDO: Importação do Plotly)"""
    
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
        
        # Gráfico de barras (O `px` agora está importado no topo do arquivo)
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
    
    min_date = datetime(MINYEAR, 1, 1) 
    cursos_recentes = sorted(cursos, 
                             key=lambda x: x.get('criado_em', min_date) if isinstance(x.get('criado_em'), datetime) else min_date, 
                             reverse=True)[:5]
    
    for curso in cursos_recentes:
        with st.container(border=True):
            col1, col2, col3 = st.columns([3, 1, 1])
            
            with col1:
                st.markdown(f"**{curso.get('titulo', 'Sem Título')}**")
                
                data_criacao = curso.get('criado_em', 'Data não disponível')
                data_str = data_criacao.strftime("%d/%m/%Y") if isinstance(data_criacao, datetime) else str(data_criacao)
                
                st.caption(f"Criado em: {data_str}")
            
            with col2:
                status = "🟢 Ativo" if curso.get('ativo', True) else "🔴 Inativo"
                st.markdown(f"`{status}`")
            
            with col3:
                if st.button("Ver", key=f"dash_view_prof_{curso.get('id', '')}", type="secondary"):
                    navegar_para('detalhe', curso)

# ======================================================
# INTERFACE DO ALUNO (Ajustada)
# ======================================================

def _interface_aluno_moderna(usuario: dict):
    tab1, tab2 = st.tabs([
        "🛒 Cursos Disponíveis",
        "🎓 Meus Cursos"
    ])
    
    with tab1:
        _aluno_cursos_disponiveis(usuario)
    
    with tab2:
        _aluno_meus_cursos(usuario)

def _aluno_cursos_disponiveis(usuario: dict):
    """Cursos disponíveis para o aluno (Ajustado para navegação)"""
    
    st.markdown("### 🎯 Cursos Disponíveis")
    st.markdown("Escolha um curso para começar sua jornada no Jiu-Jitsu!")
    
    try:
        cursos = listar_cursos_disponiveis_para_usuario(usuario)
    except Exception as e:
        st.error(f"Erro ao carregar cursos: {e}")
        cursos = []
    
    # Lógica de filtragem omitida para brevidade
    cursos_filtrados = cursos 
    
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
    """Renderiza card de curso para aluno (Ajustado para navegação e correção de botões)"""
    
    try:
        inscricao = obter_inscricao(usuario["id"], curso["id"])
        ja_inscrito = inscricao is not None
        progresso = inscricao.get("progresso", 0) if inscricao else 0
    except:
        ja_inscrito = False
        progresso = 0
    
    pago = curso.get("pago", False)
    modalidade = curso.get("modalidade", "EAD")
    professor = curso.get("professor_nome", "Professor")
    
    card_class = "curso-card-moderno"
    if progresso >= 100: card_class += " completed"
    elif ja_inscrito: card_class += " in-progress"
    
    icon = "🎓" if progresso >= 100 else ("📚" if not pago else "🔒")
    
    # HTML SEM RECUO para evitar blocos de código
    badges_html = f"""<div class="curso-badges"><span class="curso-badge {'gold' if ja_inscrito else 'green'}">{"✅ Inscrito" if ja_inscrito else "🎯 Disponível"}</span><span class="curso-badge green">{modalidade}</span></div>"""
    
    preco_html = ""
    if pago:
        preco = curso.get('preco', 0)
        preco_html = f"""<div style="margin: 1rem 0; padding: 0.75rem; background: rgba(255,215,112,0.1); border-radius: 10px;"><div style="font-size: 1.5rem; font-weight: bold; color: {COR_DESTAQUE};">R$ {preco:.2f}</div><div style="font-size: 0.85rem; opacity: 0.8;">Acesso vitalício • Certificado inclusivo</div></div>"""
    else:
        preco_html = """<div style="margin: 1rem 0; padding: 0.75rem; background: rgba(7,139,108,0.1); border-radius: 10px;"><div style="font-size: 1.25rem; font-weight: bold; color: #078B6C;">🎯 Gratuito</div><div style="font-size: 0.85rem; opacity: 0.8;">Sem custos • Acesso imediato</div></div>"""
    
    desc = curso.get('descricao', 'Sem descrição disponível.')
    if len(desc) > 100: desc = desc[:100] + "..."
    
    professor_html = f"""<div style="margin: 0.5rem 0; padding: 0.5rem; background: rgba(255,255,255,0.05); border-radius: 8px;"><div style="font-size: 0.9rem; opacity: 0.8;">👨‍🏫 Instrutor</div><div style="font-weight: 600;">{professor}</div></div>"""
    
    st.markdown(f"""
    <div class="{card_class}">
        <div class="curso-icon">{icon}</div>
        <h4 style="margin: 0 0 0.5rem 0;">{curso.get('titulo', 'Sem Título')}</h4>
        <p style="opacity: 0.8; margin-bottom: 1rem; flex-grow: 1;">{desc}</p>
        
        {professor_html}
        {badges_html}
        {preco_html}
    </div>
    """, unsafe_allow_html=True)
    
    st.markdown(f'<div style="margin-top: -1rem; margin-bottom: 1rem;">', unsafe_allow_html=True)

    # Botões funcionais Streamlit (CORRIGIDO: Navegação)
    if ja_inscrito:
        # Opção 1: Acessar Aulas
        if st.button("🎬 Acessar Curso", key=f"access_aluno_{curso['id']}", use_container_width=True, type="primary"):
            navegar_para('aulas', curso)
    else:
        # Opção 2: Inscrever-se / Ver Detalhes (se pago)
        if pago:
             # Se for pago, vai para os detalhes para ver a descrição completa antes de inscrever
             if st.button("👁️ Ver Detalhes", key=f"detalhes_aluno_{curso['id']}", use_container_width=True, type="secondary"):
                 navegar_para('detalhe', curso)
        else:
            # Se for gratuito, pode se inscrever direto
            if st.button("🔓 Inscrever-se", key=f"enroll_aluno_{curso['id']}", use_container_width=True, type="primary"):
                try:
                    inscrever_usuario_em_curso(usuario["id"], curso["id"])
                    st.success("🎉 Inscrição realizada com sucesso! Redirecionando...")
                    time.sleep(1)
                    navegar_para('aulas', curso)
                except Exception as e:
                    st.error(f"Erro na inscrição: {e}")
                
    st.markdown('</div>', unsafe_allow_html=True)

def _aluno_meus_cursos(usuario: dict):
    """Cursos em que o aluno está inscrito (Ajustado para progresso e certificados)"""
    
    try:
        todos_cursos = listar_cursos_disponiveis_para_usuario(usuario)
        
        meus_cursos = []
        for curso in todos_cursos:
            inscricao = obter_inscricao(usuario["id"], curso["id"])
            if inscricao:
                # O progresso é lido do Engine
                progresso_real = inscricao.get("progresso", 0) 

                curso["progresso"] = progresso_real
                curso["inscricao_data"] = inscricao.get("criado_em", "")
                meus_cursos.append(curso)
    
    except Exception as e:
        st.error(f"Erro ao carregar cursos: {e}")
        meus_cursos = []
        
    # Separa por status
    cursos_andamento = [c for c in meus_cursos if c['progresso'] < 100]
    cursos_concluidos = [c for c in meus_cursos if c['progresso'] >= 100]
    
    # Cursos em andamento
    if cursos_andamento:
        st.markdown("---")
        st.markdown(f"#### 🔄 Cursos em Andamento ({len(cursos_andamento)})")
        
        for curso in cursos_andamento:
            with st.container(border=True):
                col1, col2, col3 = st.columns([3, 2, 1])
                
                with col1:
                    st.markdown(f"**{curso.get('titulo', 'Curso')}**")
                    progresso = curso.get('progresso', 0)
                    st.caption(f"Progresso: {progresso:.0f}%")
                    st.progress(progresso / 100) # Barra de progresso nativa
                
                with col2:
                    modalidade = curso.get('modalidade', 'EAD')
                    st.markdown(f"**Modalidade:** {modalidade}")
                    
                    if curso.get('pago'):
                        st.markdown(f"**Valor:** R$ {curso.get('preco', 0):.2f}")
                
                with col3:
                    if st.button("Continuar", key=f"cont_aluno_{curso['id']}", use_container_width=True, type="primary"):
                        navegar_para('aulas', curso)
    
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
                    if st.button("📜 Certificado", key=f"cert_aluno_{curso['id']}", use_container_width=True, type="secondary"):
                         st.success("✅ Certificado de Conclusão emitido com sucesso! ")
                
                with col3:
                    if st.button("🔁 Revisar", key=f"rev_aluno_{curso['id']}", use_container_width=True, type="secondary"):
                        navegar_para('aulas', curso)
