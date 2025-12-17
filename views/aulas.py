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
        # Proteção contra título nulo
        titulo_curso = curso.get('titulo', 'Curso Sem Título')
        st.subheader(f"Gerenciar Conteúdo: {titulo_curso}")

    # --- Criar Novo Módulo ---
    with st.expander("➕ Criar Novo Módulo", expanded=False):
        with st.form("new_mod_form", clear_on_submit=True):
            t_mod = st.text_input("Título do Módulo", placeholder="Ex: Módulo 1 - Guarda Fechada")
            d_mod = st.text_area("Descrição", placeholder="O que será ensinado?")
            
            if st.form_submit_button("Criar Módulo", type="primary"):
                if t_mod:
                    try:
                        # Busca módulos existentes para calcular a ordem
                        mods = ce.listar_modulos_e_aulas(curso['id'])
                        qtd_mods = len(mods) if mods else 0
                        
                        ce.criar_modulo(curso['id'], t_mod, d_mod, qtd_mods + 1)
                        st.success("Módulo criado!")
                        time.sleep(1)
                        st.rerun()
                    except Exception as e:
                        st.error(f"Erro ao criar módulo: {e}")
                else:
                    st.error("Título obrigatório.")

    st.markdown("---")
    
    # --- Listagem de Módulos e Aulas (Blindada) ---
    try:
        modulos = ce.listar_modulos_e_aulas(curso['id']) or []
    except Exception as e:
        st.error(f"Erro de conexão ao buscar módulos: {e}")
        modulos = []

    if not modulos:
        st.info("Nenhum módulo criado ainda. Use o formulário acima para começar.")
        return

    st.markdown("### 📚 Estrutura do Curso")

    for i, mod in enumerate(modulos):
        try:
            # --- 1. Tratamento de Dados (Anti-Erro) ---
            # Garante que temos strings válidas e IDs, mesmo que o banco falhe
            mod_id = str(mod.get('id', f'temp_{i}'))
            mod_titulo = str(mod.get('titulo', 'Sem Título'))
            
            lista_aulas = mod.get('aulas')
            if lista_aulas is None:
                lista_aulas = []
                
            qtd_aulas = len(lista_aulas)
            label_expander = f"{i+1}. {mod_titulo} ({qtd_aulas} aulas)"
            
            # --- 2. Interface do Módulo ---
            with st.expander(label_expander, expanded=False, key=f"exp_mod_{mod_id}"):
                st.caption(str(mod.get('descricao', '')))
                
                # Listar Aulas
                if lista_aulas:
                    for aula in lista_aulas:
                        tp = str(aula.get('tipo', 'geral'))
                        t_aula = str(aula.get('titulo', 'Sem Título'))
                        d_min = aula.get('duracao_min', 0)
                        ic = "🎥" if tp=='video' else "🖼️" if tp=='imagem' else "📝"
                        
                        conteudo = aula.get('conteudo', {}) or {}
                        tem_pdf = "📎 PDF" if isinstance(conteudo, dict) and conteudo.get('material_apoio_nome') else ""
                        
                        html_aula = f"""
                        <div class="aula-card-admin">
                            <div><span class="tipo-badge">{tp}</span><strong>{ic} {t_aula}</strong></div>
                            <div style="font-size:0.8rem; text-align:right;">
                                {d_min} min<br>
                                <span style="color:{COR_DESTAQUE};">{tem_pdf}</span>
                            </div>
                        </div>"""
                        st.markdown(html_aula, unsafe_allow_html=True)
                else:
                    st.caption("Sem aulas neste módulo.")

                st.markdown("<br>", unsafe_allow_html=True)
                
                # --- Formulário Adicionar Aula ---
                if st.checkbox(f"➕ Adicionar Aula", key=f"chk_add_{mod_id}"):
                    with st.container(border=True):
                        st.markdown("#### Nova Aula")
                        tit_aula = st.text_input("Título", key=f"ta_{mod_id}")
                        tipo_aula = st.selectbox("Tipo", ["video", "imagem", "texto"], key=f"sa_{mod_id}")
                        dur_aula = st.number_input("Duração (min)", 1, 120, 10, key=f"na_{mod_id}")
                        
                        conteudo = {}
                        
                        if tipo_aula == "video":
                            src = st.radio("Origem:", ["Link", "Upload"], horizontal=True, key=f"src_v_{mod_id}")
                            if "Link" in src:
                                conteudo["url"] = st.text_input("Link:", key=f"lnk_v_{mod_id}")
                                conteudo["tipo_video"] = "link"
                            else:
                                f = st.file_uploader("Arquivo MP4:", type=["mp4","mov"], key=f"up_v_{mod_id}")
                                if f:
                                    conteudo["arquivo_video"] = f
                                    conteudo["tipo_video"] = "upload"
                                    conteudo["nome_arquivo_video"] = f.name
                        
                        elif tipo_aula == "imagem":
                            src = st.radio("Origem:", ["Link", "Upload"], horizontal=True, key=f"src_i_{mod_id}")
                            if "Link" in src:
                                conteudo["url"] = st.text_input("URL:", key=f"lnk_i_{mod_id}")
                                conteudo["tipo_imagem"] = "link"
                            else:
                                f = st.file_uploader("Arquivo JPG/PNG:", type=["jpg","png"], key=f"up_i_{mod_id}")
                                if f:
                                    conteudo["arquivo_imagem"] = f
                                    conteudo["tipo_imagem"] = "upload"
                                    conteudo["nome_arquivo_imagem"] = f.name

                        elif tipo_aula == "texto":
                            conteudo["texto"] = st.text_area("Texto:", key=f"txt_{mod_id}")

                        st.markdown("---")
                        # Botão Salvar
                        if st.button(f"💾 Salvar", key=f"sv_{mod_id}", type="primary"):
                             ce.criar_aula(mod_id, tit_aula, tipo_aula, conteudo, dur_aula)
                             st.success("Salvo!")
                             time.sleep(1)
                             st.rerun()

        except Exception as e:
            st.error(f"⚠️ Erro ao renderizar módulo {i+1}: {e}")
            st.write(mod) # Mostra o dado problemático para debug

def pagina_aulas(usuario: dict):
    st.warning("Acesse via Gerenciador de Cursos.")
