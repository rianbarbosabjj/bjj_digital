"""
BJJ Digital - Sistema de Gerenciamento de Aulas
Permite aos professores criar módulos, adicionar conteúdo (Vídeo/Texto) e Material de Apoio.
Integração com utils.py (Motor Unificado).
"""

import streamlit as st
import time
from typing import Dict

# Importa o motor unificado (utils)
import utils as ce 

# --- 1. CONFIGURAÇÃO DE CORES (Igual ao app.py e cursos.py) ---
try:
    from config import COR_FUNDO, COR_TEXTO, COR_DESTAQUE, COR_BOTAO, COR_HOVER
except ImportError:
    COR_FUNDO = "#0e2d26"
    COR_TEXTO = "#FFFFFF"
    COR_DESTAQUE = "#FFD770"
    COR_BOTAO = "#078B6C" # Verde BJJ Digital
    COR_HOVER = "#FFD770"

def aplicar_estilos_aulas():
    """CSS específico para o gerenciador de aulas (Atualizado com cores do tema)"""
    st.markdown(f"""
    <style>
    /* Estilo para os Módulos (Expanders) */
    .streamlit-expanderHeader {{
        background-color: rgba(14, 45, 38, 0.5) !important;
        border: 1px solid rgba(255, 215, 112, 0.1) !important;
        border-radius: 8px !important;
        color: {COR_DESTAQUE} !important;
        font-weight: 600 !important;
    }}
    
    /* Card de Aula dentro do Módulo */
    .aula-card-admin {{
        background: rgba(255, 255, 255, 0.02);
        border-left: 3px solid {COR_BOTAO};
        padding: 1rem;
        margin-bottom: 0.5rem;
        border-radius: 0 8px 8px 0;
        display: flex;
        align-items: center;
        justify-content: space-between;
    }}
    
    .tipo-badge {{
        font-size: 0.7rem;
        padding: 0.2rem 0.5rem;
        border-radius: 4px;
        background: rgba(255,255,255,0.1);
        margin-right: 0.5rem;
        text-transform: uppercase;
        color: #ddd;
    }}
    
    /* Botões Primários (Salvar/Criar) - VERDES */
    .stButton>button[kind="primary"] {{
        background: linear-gradient(135deg, {COR_BOTAO} 0%, #056853 100%) !important;
        color: white !important;
        border: none !important;
    }}
    .stButton>button[kind="primary"]:hover {{
        background: {COR_HOVER} !important;
        color: #0e2d26 !important;
        transform: translateY(-2px);
    }}

    /* Botões Secundários (Voltar) */
    .stButton>button[kind="secondary"] {{
        border: 1px solid {COR_DESTAQUE} !important;
        color: {COR_DESTAQUE} !important;
        background: transparent !important;
    }}
    .stButton>button[kind="secondary"]:hover {{
        background: {COR_DESTAQUE} !important;
        color: #0e2d26 !important;
    }}

    /* Upload Box customizada */
    div[data-testid="stFileUploader"] {{
        padding: 1rem;
        border: 1px dashed rgba(255, 255, 255, 0.2);
        border-radius: 8px;
        background: rgba(0,0,0,0.2);
    }}
    </style>
    """, unsafe_allow_html=True)

def gerenciar_conteudo_curso(curso: Dict, usuario: Dict):
    """
    Interface principal para o Professor gerenciar módulos e aulas de um curso.
    """
    aplicar_estilos_aulas()
    
    # Header
    col_voltar, col_titulo = st.columns([1, 5])
    with col_voltar:
        if st.button("← Voltar", use_container_width=True, type="secondary"):
            # Retorna para a tela de detalhes no cursos.py
            st.session_state['cursos_view'] = 'detalhe'
            st.rerun()
            
    with col_titulo:
        st.subheader(f"Gerenciar Conteúdo: {curso['titulo']}")

    # ======================================================
    # 1. CRIAÇÃO DE NOVOS MÓDULOS
    # ======================================================
    with st.expander("➕ Criar Novo Módulo", expanded=False):
        with st.form("form_novo_modulo", clear_on_submit=True):
            st.markdown("Defina um novo capítulo ou seção para o seu curso.")
            titulo_mod = st.text_input("Título do Módulo", placeholder="Ex: Módulo 1 - Fundamentos da Guarda")
            desc_mod = st.text_area("Descrição (Opcional)", placeholder="O que será abordado neste módulo?")
            
            submitted = st.form_submit_button("Criar Módulo", type="primary")
            if submitted:
                if not titulo_mod:
                    st.error("O título do módulo é obrigatório.")
                else:
                    try:
                        # Pega a quantidade atual de módulos para definir a ordem
                        modulos_existentes = ce.listar_modulos_do_curso(curso['id'])
                        nova_ordem = len(modulos_existentes) + 1
                        
                        ce.criar_modulo(curso['id'], titulo_mod, desc_mod, nova_ordem)
                        st.success("Módulo criado com sucesso!")
                        time.sleep(1)
                        st.rerun()
                    except Exception as e:
                        st.error(f"Erro ao criar módulo: {e}")

    st.markdown("---")

    # ======================================================
    # 2. LISTAGEM E GERENCIAMENTO DE MÓDULOS/AULAS
    # ======================================================
    
    # Carrega estrutura atualizada usando o UTILS.PY
    modulos_completos = ce.listar_modulos_e_aulas(curso['id'])
    
    if not modulos_completos:
        st.info("Este curso ainda não possui módulos. Comece criando um acima! 👆")
        return

    st.markdown("### 📚 Estrutura do Curso")

    for index, modulo in enumerate(modulos_completos):
        # Container do Módulo
        with st.expander(f"{index + 1}. {modulo['titulo']} ({len(modulo['aulas'])} aulas)", expanded=False):
            
            st.caption(modulo.get('descricao', 'Sem descrição.'))
            
            # --- LISTA DE AULAS EXISTENTES ---
            if modulo['aulas']:
                for aula in modulo['aulas']:
                    tipo = aula.get('tipo', 'geral')
                    icone = "🎥" if tipo == 'video' else "📝" if tipo == 'texto' else "❓"
                    
                    # Verifica se tem material de apoio
                    tem_pdf = "📎 PDF" if aula.get('conteudo', {}).get('material_apoio_nome') else ""
                    
                    st.markdown(f"""
                    <div class="aula-card-admin">
                        <div>
                            <span class="tipo-badge">{tipo}</span>
                            <strong>{icone} {aula['titulo']}</strong>
                        </div>
                        <div style="font-size: 0.8rem; opacity: 0.7; text-align: right;">
                            {aula.get('duracao_min', 0)} min <br>
                            <span style="color: {COR_DESTAQUE}; font-size: 0.7rem;">{tem_pdf}</span>
                        </div>
                    </div>
                    """, unsafe_allow_html=True)
            else:
                st.info("Nenhuma aula neste módulo ainda.")

            # --- ADICIONAR NOVA AULA NESTE MÓDULO ---
            st.markdown("<br>", unsafe_allow_html=True)
            if st.checkbox(f"➕ Adicionar Aula em '{modulo['titulo']}'", key=f"check_add_{modulo['id']}"):
                
                with st.container(border=True):
                    st.markdown("#### Nova Aula")
                    
                    # Inputs controlados por keys únicas baseadas no ID do módulo
                    titulo_aula = st.text_input("Título da Aula", key=f"t_aula_{modulo['id']}")
                    tipo_aula = st.selectbox("Tipo de Conteúdo", ["video", "texto", "quiz"], key=f"s_aula_{modulo['id']}")
                    duracao = st.number_input("Duração estimada (minutos)", min_value=1, value=10, key=f"n_aula_{modulo['id']}")
                    
                    conteudo = {}
                    
                    # === LÓGICA DE VÍDEO (LINK OU UPLOAD) ===
                    if tipo_aula == "video":
                        fonte_video = st.radio("Fonte do Vídeo", ["Link Externo (YouTube/Vimeo)", "Upload de Arquivo"], horizontal=True, key=f"font_v_{modulo['id']}")
                        
                        if fonte_video == "Link Externo (YouTube/Vimeo)":
                            url_video = st.text_input("Cole o Link aqui", placeholder="https://...", key=f"v_aula_{modulo['id']}")
                            conteudo["url"] = url_video
                            conteudo["tipo_video"] = "link"
                        else:
                            arquivo_video = st.file_uploader("Carregar Vídeo (MP4, MOV)", type=["mp4", "mov", "avi"], key=f"up_v_{modulo['id']}")
                            if arquivo_video:
                                # Nota: O engine precisará tratar o upload para storage
                                conteudo["arquivo_video"] = arquivo_video 
                                conteudo["tipo_video"] = "upload"
                                conteudo["nome_arquivo_video"] = arquivo_video.name
                                st.success(f"Vídeo '{arquivo_video.name}' selecionado.")
                        
                    elif tipo_aula == "texto":
                        texto_conteudo = st.text_area("Conteúdo da Aula (Markdown suportado)", height=200, key=f"txt_aula_{modulo['id']}")
                        conteudo["texto"] = texto_conteudo
                        
                    elif tipo_aula == "quiz":
                        pergunta = st.text_input("Pergunta", key=f"q_perg_{modulo['id']}")
                        opcoes_txt = st.text_area("Opções (uma por linha)", placeholder="Opção A\nOpção B\nOpção C", key=f"q_ops_{modulo['id']}")
                        correta = st.selectbox("Opção Correta (Índice 1-N)", range(1, 6), key=f"q_corr_{modulo['id']}")
                        
                        lista_opcoes = opcoes_txt.split('\n') if opcoes_txt else []
                        conteudo = {
                            "pergunta": pergunta,
                            "opcoes": lista_opcoes,
                            "correta": correta
                        }

                    # === MATERIAL DE APOIO (PDF) ===
                    st.markdown("---")
                    st.markdown("**📎 Material de Apoio (Opcional)**")
                    pdf_apoio = st.file_uploader("Adicionar PDF", type=["pdf"], key=f"pdf_{modulo['id']}")
                    if pdf_apoio:
                         # Nota: O engine precisará tratar o upload
                         conteudo["material_apoio"] = pdf_apoio
                         conteudo["nome_arquivo_pdf"] = pdf_apoio.name
                         st.info(f"PDF '{pdf_apoio.name}' anexado.")

                    st.markdown("<br>", unsafe_allow_html=True)

                    # Botão Salvar Aula
                    if st.button(f"💾 Salvar Aula em '{modulo['titulo']}'", key=f"btn_save_aula_{modulo['id']}", type="primary"):
                        
                        # Validações Básicas
                        erro = None
                        if not titulo_aula:
                            erro = "O título da aula é obrigatório."
                        elif tipo_aula == "video":
                             if conteudo.get("tipo_video") == "link" and not conteudo.get("url"):
                                 erro = "O link do vídeo é obrigatório."
                             elif conteudo.get("tipo_video") == "upload" and not conteudo.get("arquivo_video"):
                                 erro = "Você selecionou upload mas não carregou nenhum vídeo."
                        elif tipo_aula == "texto" and not conteudo.get("texto"):
                            erro = "O conteúdo de texto é obrigatório."

                        if erro:
                            st.error(erro)
                        else:
                            try:
                                ce.criar_aula(
                                    module_id=modulo['id'],
                                    titulo=titulo_aula,
                                    tipo=tipo_aula,
                                    conteudo=conteudo,
                                    duracao_min=duracao
                                )
                                st.success("Aula adicionada com sucesso!")
                                time.sleep(1)
                                st.rerun()
                            except Exception as e:
                                st.error(f"Erro ao salvar aula: {e}")

# Função de entrada padrão
def pagina_aulas(usuario: dict):
    st.warning("Este módulo deve ser acessado através do Gerenciador de Cursos.")
