import streamlit as st
import time
import pandas as pd # Importante para a tabela de alunos
from typing import Dict
import utils as ce 

# Configuração de Cores
try:
    from config import COR_FUNDO, COR_TEXTO, COR_DESTAQUE, COR_BOTAO, COR_HOVER
except ImportError:
    COR_FUNDO, COR_TEXTO, COR_DESTAQUE, COR_BOTAO, COR_HOVER = "#0e2d26", "#FFFFFF", "#FFD770", "#078B6C", "#FFD770"

def aplicar_estilos_aulas():
    st.markdown(f"""
    <style>
    .streamlit-expanderHeader {{
        background-color: #163E33 !important;
        border: 1px solid rgba(255, 215, 112, 0.2) !important;
        border-radius: 8px !important;
        color: {COR_DESTAQUE} !important;
        font-size: 1.1rem !important;
        font-weight: 600 !important;
    }}
    .aula-strip {{
        background: rgba(255, 255, 255, 0.03);
        border-left: 4px solid {COR_BOTAO};
        padding: 12px 15px;
        margin-bottom: 8px;
        border-radius: 0 6px 6px 0;
        display: flex; align-items: center; justify-content: space-between;
        transition: all 0.2s ease;
    }}
    .aula-strip:hover {{
        background: rgba(255, 255, 255, 0.06);
        border-left-color: {COR_DESTAQUE};
    }}
    .badge-tipo {{
        font-size: 0.75rem; padding: 4px 8px; border-radius: 12px;
        font-weight: bold; text-transform: uppercase; margin-right: 10px;
        min-width: 60px; text-align: center; display: inline-block;
    }}
    .badge-video {{ background-color: rgba(52, 152, 219, 0.2); color: #3498db; border: 1px solid #3498db; }}
    .badge-imagem {{ background-color: rgba(155, 89, 182, 0.2); color: #9b59b6; border: 1px solid #9b59b6; }}
    .badge-texto {{ background-color: rgba(46, 204, 113, 0.2); color: #2ecc71; border: 1px solid #2ecc71; }}
    
    .danger-zone {{
        border: 1px solid #e74c3c; background-color: rgba(231, 76, 60, 0.05);
        border-radius: 8px; padding: 15px; margin-top: 15px;
    }}
    div[data-testid="stFileUploader"] {{
        background: rgba(0,0,0,0.15); border: 1px dashed rgba(255,255,255,0.2);
        border-radius: 8px; padding: 10px;
    }}
    
    /* Estilo das Métricas */
    div[data-testid="stMetricValue"] {{
        color: {COR_DESTAQUE} !important;
    }}
    </style>
    """, unsafe_allow_html=True)

def gerenciar_conteudo_curso(curso: Dict, usuario: Dict):
    aplicar_estilos_aulas()
    
    # --- Dados e Header ---
    try:
        modulos = ce.listar_modulos_e_aulas(curso['id']) or []
    except Exception:
        modulos = []

    c1, c2 = st.columns([1, 5])
    with c1:
        if st.button("⬅ Voltar", use_container_width=True):
            st.session_state['cursos_view'] = 'detalhe'
            st.rerun()
    with c2:
        st.subheader(f"Gerenciar: {curso.get('titulo', 'Curso')}")

    # --- CRIAÇÃO DAS ABAS ---
    tab_conteudo, tab_alunos = st.tabs(["📚 Conteúdo & Aulas", "👥 Alunos & Rendimento"])

    # =================================================================
    # ABA 1: CONTEÚDO (Tudo que já fizemos antes fica aqui)
    # =================================================================
    with tab_conteudo:
        # --- Criar Módulo ---
        with st.container():
            with st.expander("✨ Criar Novo Módulo", expanded=False):
                with st.form("new_mod_form", clear_on_submit=True):
                    st.markdown("##### Detalhes do Novo Módulo")
                    t_mod = st.text_input("Nome do Módulo", placeholder="Ex: Módulo 01 - Fundamentos")
                    d_mod = st.text_area("Descrição", placeholder="O que será ensinado?")
                    
                    if st.form_submit_button("🚀 Criar Módulo", type="primary", use_container_width=True):
                        if t_mod:
                            try:
                                ce.criar_modulo(curso['id'], t_mod, d_mod, len(modulos) + 1)
                                st.toast("Módulo criado!", icon="✅")
                                time.sleep(1)
                                st.rerun()
                            except Exception as e:
                                st.error(f"Erro: {e}")
                        else:
                            st.warning("Título obrigatório.")

        st.markdown("<br>", unsafe_allow_html=True)

        if not modulos:
            st.info("Nenhum módulo criado ainda.")
        else:
            for i, mod in enumerate(modulos):
                try:
                    mod_id = str(mod.get('id', f'temp_{i}'))
                    mod_titulo = str(mod.get('titulo', 'Sem Título'))
                    mod_desc = str(mod.get('descricao', ''))
                    lista_aulas = mod.get('aulas') or []
                    
                    label = f"{i+1}. {mod_titulo} ({len(lista_aulas)} aulas)"
                    
                    with st.expander(label, expanded=False):
                        if mod_desc: st.caption(f"📝 {mod_desc}")
                        
                        if lista_aulas:
                            st.markdown("<div style='margin-bottom:15px'></div>", unsafe_allow_html=True)
                            for aula in lista_aulas:
                                tp = str(aula.get('tipo', 'geral')).lower()
                                titulo_aula = aula.get('titulo', 'Sem Título')
                                duracao = aula.get('duracao_min', 0)
                                
                                if tp == 'video': icon, css, txt = "🎥", "badge-video", "VÍDEO"
                                elif tp == 'imagem': icon, css, txt = "🖼️", "badge-imagem", "IMG"
                                else: icon, css, txt = "📝", "badge-texto", "TEXTO"
                                    
                                conteudo = aula.get('conteudo', {}) or {}
                                tem_pdf = "📎 Material" if isinstance(conteudo, dict) and conteudo.get('material_apoio_nome') else ""

                                st.markdown(f"""
                                <div class="aula-strip">
                                    <div style="display:flex; align-items:center;">
                                        <span class="badge-tipo {css}">{txt}</span>
                                        <span style="font-weight:500; font-size:1rem;">{titulo_aula}</span>
                                    </div>
                                    <div style="text-align:right; font-size:0.8rem; color:#aaa;">
                                        ⏱ {duracao} min &nbsp; <span style="color:{COR_DESTAQUE}">{tem_pdf}</span>
                                    </div>
                                </div>
                                """, unsafe_allow_html=True)
                        else:
                            st.caption("Nenhuma aula neste módulo.")

                        st.markdown("<br>", unsafe_allow_html=True)

                        # Área Adicionar Aula
                        if st.checkbox(f"➕ Adicionar Conteúdo em '{mod_titulo}'", key=f"chk_{mod_id}"):
                            with st.container(border=True):
                                c_f1, c_f2 = st.columns([1, 1])
                                with c_f1:
                                    tit_aula = st.text_input("Título", key=f"ta_{mod_id}")
                                    tipo_aula = st.selectbox("Tipo", ["video", "imagem", "texto"], key=f"sa_{mod_id}")
                                    dur_aula = st.number_input("Minutos", 1, 120, 10, key=f"na_{mod_id}")
                                with c_f2:
                                    conteudo = {}
                                    if tipo_aula == "video":
                                        src = st.radio("Origem", ["Link", "Upload"], horizontal=True, key=f"src_v_{mod_id}")
                                        if "Link" in src:
                                            conteudo["url"] = st.text_input("Link", key=f"lnk_v_{mod_id}")
                                            conteudo["tipo_video"] = "link"
                                        else:
                                            f = st.file_uploader("MP4", type=["mp4","mov"], key=f"up_v_{mod_id}")
                                            if f:
                                                conteudo["arquivo_video"] = f
                                                conteudo["tipo_video"] = "upload"
                                                conteudo["nome_arquivo_video"] = f.name
                                    elif tipo_aula == "imagem":
                                        src = st.radio("Origem", ["Link", "Upload"], horizontal=True, key=f"src_i_{mod_id}")
                                        if "Link" in src:
                                            conteudo["url"] = st.text_input("Link", key=f"lnk_i_{mod_id}")
                                            conteudo["tipo_imagem"] = "link"
                                        else:
                                            f = st.file_uploader("JPG/PNG", type=["jpg","png"], key=f"up_i_{mod_id}")
                                            if f:
                                                conteudo["arquivo_imagem"] = f
                                                conteudo["tipo_imagem"] = "upload"
                                                conteudo["nome_arquivo_imagem"] = f.name
                                    elif tipo_aula == "texto":
                                        conteudo["texto"] = st.text_area("Markdown", height=100, key=f"txt_{mod_id}")

                                pdf = st.file_uploader("Material PDF (Opcional)", type=["pdf"], key=f"pdf_{mod_id}")
                                if pdf:
                                    conteudo["material_apoio"] = pdf
                                    conteudo["nome_arquivo_pdf"] = pdf.name

                                if st.button(f"💾 Salvar Aula", type="primary", use_container_width=True, key=f"bt_sv_{mod_id}"):
                                     ce.criar_aula(mod_id, tit_aula, tipo_aula, conteudo, dur_aula)
                                     st.toast("Salvo!", icon="💾")
                                     time.sleep(1)
                                     st.rerun()

                        # Exclusão
                        with st.expander("⚙️ Excluir Módulo", expanded=False):
                            st.markdown("<div class='danger-zone'>", unsafe_allow_html=True)
                            if st.checkbox("Confirmar exclusão (Apaga todas as aulas)", key=f"del_{mod_id}"):
                                if st.button("🗑️ Excluir Definitivamente", key=f"btn_del_{mod_id}", type="primary"):
                                    ce.excluir_modulo(mod_id)
                                    st.rerun()
                            st.markdown("</div>", unsafe_allow_html=True)
                except Exception as e:
                    st.error(f"Erro ao exibir módulo: {e}")

    # =================================================================
    # ABA 2: ALUNOS & RENDIMENTO (NOVA FUNCIONALIDADE)
    # =================================================================
    with tab_alunos:
        st.markdown("### 📊 Indicadores do Curso")
        
        # 1. Busca os dados
        with st.spinner("Buscando dados financeiros e de alunos..."):
            alunos = ce.listar_alunos_inscritos(curso['id'])
        
        total_alunos = len(alunos)
        is_pago = curso.get('pago', False)
        preco_curso = float(curso.get('preco', 0)) if is_pago else 0.0
        
        # 2. Exibe Métricas
        col_metrics = st.columns(3)
        col_metrics[0].metric("Total de Alunos", total_alunos, border=True)
        
        if is_pago:
            rendimento_estimado = total_alunos * preco_curso
            col_metrics[1].metric("Preço do Curso", f"R$ {preco_curso:.2f}", border=True)
            col_metrics[2].metric("Rendimento Estimado", f"R$ {rendimento_estimado:,.2f}", border=True)
        else:
            col_metrics[1].metric("Tipo", "Gratuito", border=True)
            col_metrics[2].metric("Rendimento", "R$ 0,00", border=True)

        st.markdown("---")
        st.markdown("### 📋 Lista de Inscritos")
        
        if alunos:
            # Transforma em DataFrame para visualização bonita e ordenável
            df_alunos = pd.DataFrame(alunos)
            st.dataframe(
                df_alunos, 
                use_container_width=True,
                hide_index=True,
                column_config={
                    "Nome": st.column_config.TextColumn("Aluno", width="medium"),
                    "Email": st.column_config.TextColumn("Contato", width="medium"),
                    "Progresso": st.column_config.ProgressColumn("Progresso", format="%s", min_value=0, max_value=100),
                    "Status": st.column_config.TextColumn("Status", width="small")
                }
            )
        else:
            st.info("Este curso ainda não possui alunos inscritos.")

def pagina_aulas(usuario: dict):
    st.warning("Acesse via Gerenciador de Cursos.")
