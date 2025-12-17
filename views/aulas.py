import streamlit as st
import time
from typing import Dict
import utils as ce 

# Configuração de Cores (Paleta BJJ Digital)
try:
    from config import COR_FUNDO, COR_TEXTO, COR_DESTAQUE, COR_BOTAO, COR_HOVER
except ImportError:
    COR_FUNDO, COR_TEXTO, COR_DESTAQUE, COR_BOTAO, COR_HOVER = "#0e2d26", "#FFFFFF", "#FFD770", "#078B6C", "#FFD770"

def aplicar_estilos_aulas():
    st.markdown(f"""
    <style>
    /* Estilo Geral do Expander */
    .streamlit-expanderHeader {{
        background-color: #163E33 !important;
        border: 1px solid rgba(255, 215, 112, 0.2) !important;
        border-radius: 8px !important;
        color: {COR_DESTAQUE} !important;
        font-size: 1.1rem !important;
        font-weight: 600 !important;
    }}
    
    /* Card da Aula (Faixa Visual) */
    .aula-strip {{
        background: rgba(255, 255, 255, 0.03);
        border-left: 4px solid {COR_BOTAO};
        padding: 12px 15px;
        margin-bottom: 8px;
        border-radius: 0 6px 6px 0;
        display: flex; 
        align-items: center; 
        justify-content: space-between;
        transition: all 0.2s ease;
    }}
    .aula-strip:hover {{
        background: rgba(255, 255, 255, 0.06);
        border-left-color: {COR_DESTAQUE};
    }}

    /* Badges (Etiquetas) */
    .badge-tipo {{
        font-size: 0.75rem;
        padding: 4px 8px;
        border-radius: 12px;
        font-weight: bold;
        text-transform: uppercase;
        margin-right: 10px;
        min-width: 60px;
        text-align: center;
        display: inline-block;
    }}
    .badge-video {{ background-color: rgba(52, 152, 219, 0.2); color: #3498db; border: 1px solid #3498db; }}
    .badge-imagem {{ background-color: rgba(155, 89, 182, 0.2); color: #9b59b6; border: 1px solid #9b59b6; }}
    .badge-texto {{ background-color: rgba(46, 204, 113, 0.2); color: #2ecc71; border: 1px solid #2ecc71; }}

    /* Área de Perigo */
    .danger-zone {{
        border: 1px solid #e74c3c;
        background-color: rgba(231, 76, 60, 0.05);
        border-radius: 8px;
        padding: 15px;
        margin-top: 15px;
    }}
    
    /* Ajuste de inputs */
    div[data-testid="stFileUploader"] {{
        background: rgba(0,0,0,0.15);
        border: 1px dashed rgba(255,255,255,0.2);
        border-radius: 8px;
        padding: 10px;
    }}
    </style>
    """, unsafe_allow_html=True)

def gerenciar_conteudo_curso(curso: Dict, usuario: Dict):
    aplicar_estilos_aulas()
    
    # --- Carregar Dados com Segurança ---
    try:
        modulos = ce.listar_modulos_e_aulas(curso['id']) or []
    except Exception:
        modulos = []

    # Calcular Métricas Rápidas
    total_aulas = sum([len(m.get('aulas', [])) for m in modulos]) if modulos else 0

    # --- Header do Painel ---
    c1, c2, c3 = st.columns([1, 4, 2])
    with c1:
        if st.button("⬅ Voltar", use_container_width=True):
            st.session_state['cursos_view'] = 'detalhe'
            st.rerun()
    with c2:
        st.subheader(f"📂 {curso.get('titulo', 'Curso')}")
    with c3:
        # Mini Dashboard
        st.markdown(f"""
        <div style="text-align:right; font-size:0.9rem; color:#aaa;">
            📦 Módulos: <b style="color:{COR_DESTAQUE}">{len(modulos)}</b> &nbsp;|&nbsp; 
            🎬 Aulas: <b style="color:{COR_DESTAQUE}">{total_aulas}</b>
        </div>
        """, unsafe_allow_html=True)

    st.markdown("---")

    # --- Área de CRIAÇÃO DE MÓDULO (Destacada) ---
    with st.container():
        col_new, _ = st.columns([2, 1]) # Limita a largura para ficar mais elegante
        with col_new:
            with st.expander("✨ Criar Novo Módulo", expanded=False):
                with st.form("new_mod_form", clear_on_submit=True):
                    st.markdown("##### Detalhes do Novo Módulo")
                    t_mod = st.text_input("Nome do Módulo", placeholder="Ex: Módulo 01 - Fundamentos")
                    d_mod = st.text_area("Descrição Rápida", placeholder="O que o aluno vai aprender aqui?", height=68)
                    
                    if st.form_submit_button("🚀 Criar Módulo", type="primary", use_container_width=True):
                        if t_mod:
                            try:
                                ce.criar_modulo(curso['id'], t_mod, d_mod, len(modulos) + 1)
                                st.toast("Módulo criado com sucesso!", icon="✅")
                                time.sleep(1)
                                st.rerun()
                            except Exception as e:
                                st.error(f"Erro: {e}")
                        else:
                            st.warning("O módulo precisa de um nome.")

    st.markdown("<br>", unsafe_allow_html=True)

    # --- LISTAGEM DE MÓDULOS ---
    if not modulos:
        st.info("👋 Comece criando seu primeiro módulo acima!")
        return

    st.markdown("### 📚 Grade Curricular")

    for i, mod in enumerate(modulos):
        try:
            # Tratamento Seguro de Dados
            mod_id = str(mod.get('id', f'temp_{i}'))
            mod_titulo = str(mod.get('titulo', 'Sem Título'))
            mod_desc = str(mod.get('descricao', ''))
            lista_aulas = mod.get('aulas') or []
            
            label = f"{i+1}. {mod_titulo} ({len(lista_aulas)} aulas)"
            
            # --- CARD DO MÓDULO ---
            with st.expander(label, expanded=False):
                if mod_desc:
                    st.caption(f"📝 {mod_desc}")
                
                # Listagem Visual das Aulas
                if lista_aulas:
                    st.markdown("<div style='margin-bottom:15px'></div>", unsafe_allow_html=True)
                    for aula in lista_aulas:
                        tp = str(aula.get('tipo', 'geral')).lower()
                        titulo_aula = aula.get('titulo', 'Sem Título')
                        duracao = aula.get('duracao_min', 0)
                        
                        # Ícones e Classes CSS baseadas no tipo
                        if tp == 'video':
                            icon, css_class, badge_text = "🎥", "badge-video", "VÍDEO"
                        elif tp == 'imagem':
                            icon, css_class, badge_text = "🖼️", "badge-imagem", "IMG"
                        else:
                            icon, css_class, badge_text = "📝", "badge-texto", "TEXTO"
                            
                        # Material de Apoio
                        conteudo = aula.get('conteudo', {}) or {}
                        tem_pdf = "📎 Material" if isinstance(conteudo, dict) and conteudo.get('material_apoio_nome') else ""

                        # HTML Customizado para a Linha da Aula
                        html_row = f"""
                        <div class="aula-strip">
                            <div style="display:flex; align-items:center;">
                                <span class="badge-tipo {css_class}">{badge_text}</span>
                                <span style="font-weight:500; font-size:1rem;">{titulo_aula}</span>
                            </div>
                            <div style="text-align:right; font-size:0.8rem; color:#aaa;">
                                ⏱ {duracao} min &nbsp; <span style="color:{COR_DESTAQUE}">{tem_pdf}</span>
                            </div>
                        </div>
                        """
                        st.markdown(html_row, unsafe_allow_html=True)
                else:
                    st.markdown("""
                    <div style="padding:20px; text-align:center; color:#666; border:1px dashed #444; border-radius:8px;">
                        <i>Nenhuma aula adicionada neste módulo.</i>
                    </div>
                    """, unsafe_allow_html=True)

                st.markdown("<br>", unsafe_allow_html=True)

                # --- ÁREA DE ADICIONAR AULA (Separada Visualmente) ---
                if st.checkbox(f"➕ Adicionar Conteúdo em '{mod_titulo}'", key=f"chk_{mod_id}"):
                    with st.container(border=True):
                        c_form1, c_form2 = st.columns([1, 1])
                        
                        with c_form1:
                            tit_aula = st.text_input("Título da Aula", key=f"ta_{mod_id}")
                            tipo_aula = st.selectbox("Formato", ["video", "imagem", "texto"], key=f"sa_{mod_id}")
                            dur_aula = st.number_input("Duração (min)", 1, 120, 10, key=f"na_{mod_id}")
                        
                        with c_form2:
                            conteudo = {}
                            st.markdown("###### Conteúdo Principal")
                            
                            if tipo_aula == "video":
                                aba_v = st.radio("Fonte do Vídeo", ["Link Externo", "Upload Arquivo"], horizontal=True, label_visibility="collapsed", key=f"src_v_{mod_id}")
                                if "Link" in aba_v:
                                    conteudo["url"] = st.text_input("Link (YouTube/Vimeo)", placeholder="https://...", key=f"lnk_v_{mod_id}")
                                    conteudo["tipo_video"] = "link"
                                else:
                                    f = st.file_uploader("Vídeo MP4", type=["mp4","mov"], key=f"up_v_{mod_id}")
                                    if f:
                                        conteudo["arquivo_video"] = f
                                        conteudo["tipo_video"] = "upload"
                                        conteudo["nome_arquivo_video"] = f.name
                            
                            elif tipo_aula == "imagem":
                                aba_i = st.radio("Fonte", ["Link", "Upload"], horizontal=True, label_visibility="collapsed", key=f"src_i_{mod_id}")
                                if "Link" in aba_i:
                                    conteudo["url"] = st.text_input("Link da Imagem", key=f"lnk_i_{mod_id}")
                                    conteudo["tipo_imagem"] = "link"
                                else:
                                    f = st.file_uploader("Imagem (JPG/PNG)", type=["jpg","png"], key=f"up_i_{mod_id}")
                                    if f:
                                        conteudo["arquivo_imagem"] = f
                                        conteudo["tipo_imagem"] = "upload"
                                        conteudo["nome_arquivo_imagem"] = f.name
                            
                            elif tipo_aula == "texto":
                                conteudo["texto"] = st.text_area("Texto / Markdown", height=100, key=f"txt_{mod_id}")

                        # Material de Apoio (Full Width)
                        st.markdown("---")
                        pdf = st.file_uploader("📎 Material Complementar (PDF - Opcional)", type=["pdf"], key=f"pdf_{mod_id}")
                        if pdf:
                            conteudo["material_apoio"] = pdf
                            conteudo["nome_arquivo_pdf"] = pdf.name

                        if st.button(f"💾 Salvar Aula em '{mod_titulo}'", type="primary", use_container_width=True, key=f"btn_sv_{mod_id}"):
                             ce.criar_aula(mod_id, tit_aula, tipo_aula, conteudo, dur_aula)
                             st.toast("Aula salva com sucesso!", icon="💾")
                             time.sleep(1)
                             st.rerun()

                # --- OPÇÕES AVANÇADAS (Exclusão) ---
                with st.expander("⚙️ Opções do Módulo (Excluir)", expanded=False):
                    st.markdown("<div class='danger-zone'>", unsafe_allow_html=True)
                    c_del1, c_del2 = st.columns([3, 1])
                    with c_del1:
                        st.caption("Atenção: Excluir o módulo apagará permanentemente todas as suas aulas.")
                        check_del = st.checkbox("Estou ciente e quero excluir", key=f"chk_del_{mod_id}")
                    with c_del2:
                        if check_del:
                            if st.button("🗑️ Excluir", key=f"btn_del_{mod_id}", type="primary"):
                                ce.excluir_modulo(mod_id)
                                st.rerun()
                    st.markdown("</div>", unsafe_allow_html=True)

        except Exception as e:
            st.error(f"Erro visual no módulo {i+1}: {e}")

def pagina_aulas(usuario: dict):
    st.warning("Acesse via Gerenciador de Cursos.")
