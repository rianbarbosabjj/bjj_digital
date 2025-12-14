"""
BJJ Digital - Sistema de Gerenciamento de Aulas
Permite aos professores criar módulos e adicionar conteúdo aos cursos.
"""

import streamlit as st
import time
from typing import Dict

# Importa a engine para operações de banco de dados
import courses_engine as ce

def aplicar_estilos_aulas():
    """CSS específico para o gerenciador de aulas"""
    st.markdown("""
    <style>
    /* Estilo para os Módulos (Expanders) */
    .streamlit-expanderHeader {
        background-color: rgba(14, 45, 38, 0.5);
        border: 1px solid rgba(255, 215, 112, 0.1);
        border-radius: 8px;
        color: #FFD770;
        font-weight: 600;
    }
    
    /* Card de Aula dentro do Módulo */
    .aula-card-admin {
        background: rgba(255, 255, 255, 0.02);
        border-left: 3px solid #078B6C;
        padding: 1rem;
        margin-bottom: 0.5rem;
        border-radius: 0 8px 8px 0;
        display: flex;
        align-items: center;
        justify_content: space-between;
    }
    
    .tipo-badge {
        font-size: 0.7rem;
        padding: 0.2rem 0.5rem;
        border-radius: 4px;
        background: rgba(255,255,255,0.1);
        margin-right: 0.5rem;
        text-transform: uppercase;
    }
    
    /* Formulário de Adição */
    .add-box {
        background: rgba(7, 139, 108, 0.05);
        border: 1px dashed rgba(7, 139, 108, 0.3);
        border-radius: 12px;
        padding: 1.5rem;
        margin-top: 1rem;
    }
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
        if st.button("← Voltar", use_container_width=True):
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
    
    # Carrega estrutura atualizada
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
                    icone = "🎥" if aula['tipo'] == 'video' else "📝" if aula['tipo'] == 'texto' else "❓"
                    
                    st.markdown(f"""
                    <div class="aula-card-admin">
                        <div>
                            <span class="tipo-badge">{aula['tipo']}</span>
                            <strong>{icone} {aula['titulo']}</strong>
                        </div>
                        <div style="font-size: 0.8rem; opacity: 0.7;">
                            {aula.get('duracao_min', 0)} min
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
                    
                    if tipo_aula == "video":
                        url_video = st.text_input("Link do Vídeo (YouTube/Vimeo)", placeholder="https://...", key=f"v_aula_{modulo['id']}")
                        conteudo["url"] = url_video
                        st.caption("ℹ️ O sistema irá incorporar o vídeo automaticamente.")
                        
                    elif tipo_aula == "texto":
                        texto_conteudo = st.text_area("Conteúdo da Aula (Markdown suportado)", height=200, key=f"txt_aula_{modulo['id']}")
                        conteudo["texto"] = texto_conteudo
                        
                    elif tipo_aula == "quiz":
                        pergunta = st.text_input("Pergunta", key=f"q_perg_{modulo['id']}")
                        opcoes = st.text_area("Opções (uma por linha)", placeholder="Opção A\nOpção B\nOpção C", key=f"q_ops_{modulo['id']}")
                        correta = st.selectbox("Opção Correta (Índice 1-N)", range(1, 6), key=f"q_corr_{modulo['id']}")
                        conteudo = {
                            "pergunta": pergunta,
                            "opcoes": options.split('\n') if 'options' in locals() else [], # Placeholder logic
                            "correta": correta
                        }
                        if opcoes:
                            conteudo["opcoes"] = opcoes.split('\n')

                    # Botão Salvar Aula
                    if st.button(f"💾 Salvar Aula em '{modulo['titulo']}'", key=f"btn_save_aula_{modulo['id']}", type="primary"):
                        if not titulo_aula:
                            st.error("O título da aula é obrigatório.")
                        elif tipo_aula == "video" and not conteudo.get("url"):
                            st.error("O link do vídeo é obrigatório.")
                        elif tipo_aula == "texto" and not conteudo.get("texto"):
                            st.error("O conteúdo de texto é obrigatório.")
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

# Função de entrada padrão (caso seja chamado diretamente, embora cursos.py controle)
def pagina_aulas(usuario: dict):
    st.warning("Este módulo deve ser acessado através do Gerenciador de Cursos.")
