import streamlit as st
import time
from typing import Dict
import utils as ce 

# Configuração de Cores (Fallback seguro)
try:
    from config import COR_FUNDO, COR_TEXTO, COR_DESTAQUE, COR_BOTAO, COR_HOVER
except ImportError:
    COR_FUNDO, COR_TEXTO, COR_DESTAQUE, COR_BOTAO, COR_HOVER = "#0e2d26", "#FFFFFF", "#FFD770", "#078B6C", "#FFD770"

def aplicar_estilos_aulas():
    st.markdown(f"""
    <style>
    .streamlit-expanderHeader {{
        background-color: rgba(14, 45, 38, 0.5) !important;
        border: 1px solid rgba(255, 215, 112, 0.1) !important;
        border-radius: 8px !important;
        color: {COR_DESTAQUE} !important;
        font-weight: 600 !important;
    }}
    .aula-card-admin {{
        background: rgba(255, 255, 255, 0.02);
        border-left: 3px solid {COR_BOTAO};
        padding: 1rem;
        margin-bottom: 0.5rem;
        border-radius: 0 8px 8px 0;
        display: flex; align-items: center; justify-content: space-between;
    }}
    .tipo-badge {{
        font-size: 0.7rem; padding: 0.2rem 0.5rem; border-radius: 4px;
        background: rgba(255,255,255,0.1); margin-right: 0.5rem;
        text-transform: uppercase; color: #ddd;
    }}
    /* Ajuste para garantir visibilidade do uploader */
    div[data-testid="stFileUploader"] {{
        padding: 1rem; border: 1px dashed rgba(255, 255, 255, 0.2);
        border-radius: 8px; background: rgba(0,0,0,0.2);
    }}
    </style>
    """, unsafe_allow_html=True)

def gerenciar_conteudo_curso(curso: Dict, usuario: Dict):
    aplicar_estilos_aulas()
    
    # --- Cabeçalho ---
    c_voltar, c_tit = st.columns([1, 5])
    with c_voltar:
        if st.button("← Voltar", use_container_width=True):
            st.session_state['cursos_view'] = 'detalhe'
            st.rerun()
    with c_tit:
        st.subheader(f"Gerenciar Conteúdo: {curso.get('titulo', 'Curso')}")

    # --- Criar Novo Módulo ---
    with st.expander("➕ Criar Novo Módulo", expanded=False):
        with st.form("new_mod_form", clear_on_submit=True):
            t_mod = st.text_input("Título do Módulo", placeholder="Ex: Módulo 1 - Guarda Fechada")
            d_mod = st.text_area("Descrição", placeholder="O que será ensinado?")
            if st.form_submit_button("Criar Módulo", type="primary"):
                # Validação simples
                if t_mod:
                    try:
                        # Passamos 0 se der erro na contagem, para não travar
                        mods = ce.listar_modulos_e_aulas(curso['id'])
                        qtd_mods = len(mods) if mods else 0
                        
                        ce.criar_modulo(curso['id'], t_mod, d_mod, qtd_mods + 1)
                        st.success("Módulo criado!")
                        time.sleep(1)
                        st.rerun()
                    except Exception as e:
                        st.error(f"Erro ao criar: {e}")
                else:
                    st.error("Título obrigatório.")

    st.markdown("---")
    
    # --- Listagem de Módulos e Aulas ---
    # Proteção: Se a função retornar None, usamos lista vazia
    modulos = ce.listar_modulos_e_aulas(curso['id']) or []
    
    if not modulos:
        st.info("Nenhum módulo criado ainda. Use o formulário acima para começar.")
        return

    st.markdown("### 📚 Estrutura do Curso")

    for i, mod in enumerate(modulos):
        # PROTEÇÃO CONTRA DADOS SUJOS:
        # Usamos .get() para garantir que nunca pegamos um valor nulo
        mod_id = mod.get('id')
        mod_titulo = mod.get('titulo', f'Módulo {i+1}')
        lista_aulas = mod.get('aulas', []) # Se não tiver aulas, retorna lista vazia
        qtd_aulas = len(lista_aulas)
        
        # AQUI OCORRIA O ERRO ANTES (Agora está protegido)
        label_expander = f"{i+1}. {mod_titulo} ({qtd_aulas} aulas)"
        
        with st.expander(label_expander, expanded=False, key=f"exp_mod_{mod_id}"):
            st.caption(mod.get('descricao', ''))
            
            # --- Lista Aulas Existentes ---
            if lista_aulas:
                for aula in lista_aulas:
                    tp = aula.get('tipo', 'geral')
                    ic = "🎥" if tp=='video' else "🖼️" if tp=='imagem' else "📝"
                    
                    # Verifica se existe material de apoio de forma segura
                    conteudo = aula.get('conteudo', {})
                    tem_pdf = "📎 PDF" if isinstance(conteudo, dict) and conteudo.get('material_apoio_nome') else ""
                    
                    html_aula = f"""
                    <div class="aula-card-admin">
                        <div><span class="tipo-badge">{tp}</span><strong>{ic} {aula.get('titulo', 'Sem título')}</strong></div>
                        <div style="font-size:0.8rem; text-align:right;">
                            {aula.get('duracao_min',0)} min<br>
                            <span style="color:{COR_DESTAQUE};">{tem_pdf}</span>
                        </div>
                    </div>"""
                    st.markdown(html_aula, unsafe_allow_html=True)
            else:
                st.caption("Sem aulas neste módulo.")

            st.markdown("<br>", unsafe_allow_html=True)
            
            # --- Formulário de Nova Aula ---
            if st.checkbox(f"➕ Adicionar Aula em '{mod_titulo}'", key=f"chk_add_{mod_id}"):
                with st.container(border=True):
                    st.markdown("#### Nova Aula")
                    
                    tit_aula = st.text_input("Título", key=f"ta_{mod_id}")
                    tipo_aula = st.selectbox("Tipo", ["video", "imagem", "texto"], key=f"sa_{mod_id}")
                    dur_aula = st.number_input("Duração (min)", 1, 120, 10, key=f"na_{mod_id}")
                    
                    conteudo = {}
                    
                    if tipo_aula == "video":
                        src = st.radio("Origem:", ["Link (YouTube/Vimeo)", "Upload (MP4)"], horizontal=True, key=f"src_v_{mod_id}")
                        if "Link" in src:
                            conteudo["url"] = st.text_input("Cole o Link:", placeholder="https://...", key=f"lnk_v_{mod_id}")
                            conteudo["tipo_video"] = "link"
                        else:
                            f = st.file_uploader("Arquivo MP4:", type=["mp4","mov"], key=f"up_v_{mod_id}")
                            if f:
                                conteudo["arquivo_video"] = f
                                conteudo["tipo_video"] = "upload"
                                conteudo["nome_arquivo_video"] = f.name

                    elif tipo_aula == "imagem":
                        src = st.radio("Origem:", ["Link URL", "Upload (JPG/PNG)"], horizontal=True, key=f"src_i_{mod_id}")
                        if "Link" in src:
                            conteudo["url"] = st.text_input("URL da Imagem:", key=f"lnk_i_{mod_id}")
                            conteudo["tipo_imagem"] = "link"
                        else:
                            f = st.file_uploader("Arquivo Imagem:", type=["jpg","png","jpeg"], key=f"up_i_{mod_id}")
                            if f:
                                conteudo["arquivo_imagem"] = f
                                conteudo["tipo_imagem"] = "upload"
                                conteudo["nome_arquivo_imagem"] = f.name

                    elif tipo_aula == "texto":
                        conteudo["texto"] = st.text_area("Conteúdo (Markdown):", height=150, key=f"txt_{mod_id}")

                    st.markdown("---")
                    st.markdown("**📎 Material de Apoio**")
                    pdf = st.file_uploader("Upload PDF (Opcional):", type=["pdf"], key=f"pdf_{mod_id}")
                    if pdf:
                        conteudo["material_apoio"] = pdf
                        conteudo["nome_arquivo_pdf"] = pdf.name

                    st.markdown("<br>", unsafe_allow_html=True)
                    
                    if st.button(f"💾 Salvar Aula", key=f"sv_{mod_id}", type="primary"):
                        try:
                            # Chama a função de criação
                            ce.criar_aula(mod_id, tit_aula, tipo_aula, conteudo, dur_aula)
                            st.success("Aula adicionada!")
                            time.sleep(1)
                            st.rerun()
                        except Exception as e:
                            st.error(f"Erro ao salvar: {e}")
def pagina_aulas(usuario: dict):
    st.warning("Acesse via Gerenciador de Cursos.")
