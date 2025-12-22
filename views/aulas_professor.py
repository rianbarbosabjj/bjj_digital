import streamlit as st
import utils as ce
import time

# ======================================================
# 1. FUNÇÕES AUXILIARES DE VISUALIZAÇÃO (PREVIEW)
# ======================================================
def componente_visualizacao_aluno(titulo, blocos):
    """
    Renderiza a aula exatamente como o aluno verá.
    Sem botões de edição, apenas consumo de conteúdo.
    """
    st.markdown(f"## 📘 {titulo}")
    st.markdown("---")

    if not blocos:
        st.info("📭 Esta aula ainda não tem conteúdo.")
        return

    for bloco in blocos:
        tipo = bloco.get("tipo", "texto")
        
        # Tenta obter URL (compatibilidade V2 e Legado)
        # O utils.py padronizou como 'url', mas mantemos fallback
        url = bloco.get("url") or bloco.get("url_link") or bloco.get("conteudo")
        
        # --- RENDERIZAÇÃO LIMPA ---
        if tipo == "texto":
            # Renderiza Markdown (permite negrito, listas, etc)
            st.markdown(bloco.get("conteudo", ""), unsafe_allow_html=True)
            
        elif tipo == "imagem":
            if url:
                st.image(url, use_column_width=True)
                
        elif tipo == "video":
            if url:
                st.video(url)
        
        # Espaçamento leve entre blocos
        st.markdown("<br>", unsafe_allow_html=True)


# ======================================================
# 2. DIÁLOGOS (MODAIS) PARA CRIAÇÃO RÁPIDA
# ======================================================
@st.dialog("Novo Módulo")
def dialog_criar_modulo(curso_id, total_modulos):
    with st.form("form_modulo"):
        titulo = st.text_input("Nome do Módulo")
        if st.form_submit_button("Salvar Módulo"):
            if titulo:
                ce.criar_modulo(curso_id, titulo, "", total_modulos + 1)
                st.success("Módulo criado!")
                st.rerun()

@st.dialog("Nova Aula")
def dialog_criar_aula(curso_id, modulos, usuario):
    mapa_modulos = {m['titulo']: m['id'] for m in modulos}
    
    with st.form("form_aula_basica"):
        st.caption("Crie a estrutura primeiro. O conteúdo você adiciona na próxima tela.")
        titulo = st.text_input("Título da Aula")
        modulo_select = st.selectbox("Selecione o Módulo", list(mapa_modulos.keys()))
        duracao = st.number_input("Duração estimada (min)", value=10, min_value=1)
        
        if st.form_submit_button("Criar Estrutura da Aula"):
            if titulo and modulo_select:
                mod_id = mapa_modulos[modulo_select]
                # Cria a aula vazia na coleção V2
                ce.criar_aula_v2(
                    curso_id=curso_id,
                    modulo_id=mod_id,
                    titulo=titulo,
                    tipo="misto",
                    blocos=[], # Começa vazia
                    duracao_min=duracao,
                    autor_id=usuario.get("id"),
                    autor_nome=usuario.get("nome")
                )
                st.success("Aula criada!")
                st.rerun()

# ======================================================
# 3. O EDITOR COMPLETO (LEGO + PREVIEW + UPLOAD)
# ======================================================
def editor_de_aula(aula, curso_id):
    
    # --- A. GESTÃO DE ESTADO (MEMÓRIA TEMPORÁRIA) ---
    if "blocos_temp" not in st.session_state:
        conteudo = aula.get("conteudo", {})
        # Garante que seja uma lista
        blocos_iniciais = conteudo.get("blocos", []) if isinstance(conteudo, dict) else []
        st.session_state["blocos_temp"] = blocos_iniciais

    if "preview_mode" not in st.session_state:
        st.session_state["preview_mode"] = False

    blocos = st.session_state["blocos_temp"]

    # --- B. CABEÇALHO DO EDITOR ---
    c_titulo, c_botoes = st.columns([3, 2])
    
    with c_titulo:
        if st.session_state["preview_mode"]:
            st.caption("👀 MODO VISUALIZAÇÃO DO ALUNO")
        else:
            st.markdown(f"### ✏️ Editando: {aula['titulo']}")

    with c_botoes:
        # Botão Toggle (Alternar entre Edição e Visão do Aluno)
        lbl_btn = "✏️ Voltar a Editar" if st.session_state["preview_mode"] else "👁️ Ver como Aluno"
        if st.button(lbl_btn, use_container_width=True):
            st.session_state["preview_mode"] = not st.session_state["preview_mode"]
            st.rerun()

    st.divider()

    # --- C. RENDERIZAÇÃO CONDICIONAL (PREVIEW VS EDITOR) ---
    
    # CASO 1: MODO PREVIEW
    if st.session_state["preview_mode"]:
        with st.container(border=True):
            componente_visualizacao_aluno(aula['titulo'], blocos)
        
        # Botão de voltar ao editor também no rodapé do preview para facilitar
        if st.button("⬅️ Voltar para Edição"):
            st.session_state["preview_mode"] = False
            st.rerun()
        return  # Encerra a função aqui para não carregar o editor

    # CASO 2: MODO EDITOR (O "LEGO")
    col_view, col_tools = st.columns([2, 1])

    # --- Coluna Esquerda: Lista de Blocos ---
    with col_view:
        st.info("👇 Estrutura da Aula")
        
        if not blocos:
            st.warning("Aula vazia. Use as ferramentas ao lado para adicionar conteúdo 👉")
        
        for i, bloco in enumerate(blocos):
            tipo = bloco.get("tipo", "texto")
            
            with st.container(border=True):
                c_content, c_actions = st.columns([6, 1])
                
                # Resumo do conteúdo
                with c_content:
                    if tipo == "texto":
                        # Mostra só o começo do texto para não ocupar muito espaço
                        txt_preview = bloco.get("conteudo", "")
                        st.markdown(txt_preview if len(txt_preview) < 100 else txt_preview[:100] + "...")
                    
                    elif tipo in ["imagem", "video"]:
                        nome_arq = bloco.get("nome", "Mídia sem nome")
                        st.caption(f"📁 Arquivo: {nome_arq}")
                        
                        url = bloco.get("url") or bloco.get("url_link")
                        if url:
                            if tipo == "imagem":
                                st.image(url, width=150)
                            else:
                                st.video(url)
                        else:
                            st.error("Erro: URL da mídia não encontrada.")

                # Botões de Controle
                with c_actions:
                    if i > 0:
                        if st.button("⬆️", key=f"up_{i}", help="Subir"):
                            blocos[i], blocos[i-1] = blocos[i-1], blocos[i]
                            st.rerun()
                    
                    if i < len(blocos) - 1:
                        if st.button("⬇️", key=f"dw_{i}", help="Descer"):
                            blocos[i], blocos[i+1] = blocos[i+1], blocos[i]
                            st.rerun()
                            
                    if st.button("❌", key=f"del_{i}", type="primary", help="Remover bloco"):
                        blocos.pop(i)
                        st.rerun()

    # --- Coluna Direita: Ferramentas ---
    with col_tools:
        st.markdown("### 🛠️ Adicionar")
        tab_txt, tab_img, tab_vid = st.tabs(["Texto", "📷 Foto", "🎥 Vídeo"])

        # ABA 1: TEXTO
        with tab_txt:
            txt_input = st.text_area("Escreva aqui", height=150, help="Suporta Markdown")
            if st.button("➕ Add Texto"):
                if txt_input.strip():
                    blocos.append({"tipo": "texto", "conteudo": txt_input})
                    st.toast("Texto adicionado!")
                    st.rerun()

        # ABA 2: IMAGEM
        with tab_img:
            arquivo_img = st.file_uploader("Upload Imagem", type=['png', 'jpg', 'jpeg'])
            if arquivo_img and st.button("Enviar Imagem"):
                with st.spinner("Enviando para nuvem..."):
                    caminho = f"midia_cursos/{curso_id}/{aula['id']}/{int(time.time())}_{arquivo_img.name}"
                    url = ce.upload_arquivo_simples(arquivo_img, caminho)
                    
                    if url:
                        blocos.append({
                            "tipo": "imagem",
                            "url": url,
                            "origem": "upload",
                            "nome": arquivo_img.name
                        })
                        st.success("Imagem adicionada!")
                        st.rerun()
                    else:
                        st.error("Falha no upload.")
            
            st.markdown("---")
            url_ext_img = st.text_input("Ou URL da imagem")
            if st.button("Add URL Imagem") and url_ext_img:
                blocos.append({"tipo": "imagem", "url": url_ext_img, "origem": "link"})
                st.rerun()

        # ABA 3: VÍDEO
        with tab_vid:
            arquivo_vid = st.file_uploader("Upload Vídeo (MP4)", type=['mp4', 'mov'])
            if arquivo_vid:
                st.caption(f"Tamanho: {arquivo_vid.size / 1024 / 1024:.1f} MB")
                if st.button("Enviar Vídeo"):
                    with st.spinner("Enviando vídeo..."):
                        caminho = f"midia_cursos/{curso_id}/{aula['id']}/{int(time.time())}_{arquivo_vid.name}"
                        url = ce.upload_arquivo_simples(arquivo_vid, caminho)
                        
                        if url:
                            blocos.append({
                                "tipo": "video",
                                "url": url,
                                "origem": "upload",
                                "nome": arquivo_vid.name
                            })
                            st.success("Vídeo adicionado!")
                            st.rerun()
                        else:
                            st.error("Falha no upload.")
            
            st.markdown("---")
            url_yt = st.text_input("Ou YouTube/Vimeo")
            if st.button("Add YouTube") and url_yt:
                url_final = ce.normalizar_link_video(url_yt)
                blocos.append({"tipo": "video", "url": url_final, "origem": "link"})
                st.rerun()

    st.divider()
    
    # --- RODAPÉ: SALVAR OU CANCELAR ---
    c_back, c_save = st.columns([1, 4])
    
    if c_back.button("Cancelar"):
        del st.session_state["blocos_temp"]
        st.session_state["aula_editando_id"] = None
        st.session_state["preview_mode"] = False
        st.rerun()
        
    if c_save.button("💾 SALVAR ALTERAÇÕES", type="primary", use_container_width=True):
        sucesso = ce.editar_aula_v2(aula['id'], {"blocos": blocos})
        
        if sucesso:
            st.balloons()
            st.toast("Aula salva com sucesso!")
            del st.session_state["blocos_temp"]
            st.session_state["aula_editando_id"] = None
            st.session_state["preview_mode"] = False
            time.sleep(1)
            st.rerun()
        else:
            st.error("Erro ao salvar no banco de dados.")

# ======================================================
# 4. FUNÇÃO PRINCIPAL (VIEW GERAL)
# ======================================================
def gerenciar_conteudo_curso(curso: dict, usuario: dict):
    
    # 1. Verifica se estamos editando uma aula específica
    if st.session_state.get("aula_editando_id"):
        # Recupera dados da aula (simulação rápida buscando na lista local para evitar query extra)
        aula_alvo = None
        estrutura = ce.listar_modulos_e_aulas(curso.get("id"))
        for m in estrutura:
            for a in m['aulas']:
                if a['id'] == st.session_state["aula_editando_id"]:
                    aula_alvo = a
                    break
        
        if aula_alvo:
            editor_de_aula(aula_alvo, curso.get("id"))
            return
        else:
            st.error("Erro: Aula não encontrada.")
            st.session_state["aula_editando_id"] = None
            st.rerun()

    # 2. Visão Geral (Lista de Módulos)
    c1, c2 = st.columns([3, 1])
    c1.markdown(f"## 🎛️ Gestão: {curso.get('titulo')}")
    if c2.button("← Voltar ao Menu"):
        st.session_state["cursos_view"] = "detalhe"
        st.rerun()
        
    st.divider()

    # Busca dados atualizados
    modulos = ce.listar_modulos_e_aulas(curso.get("id")) or []

    # Toolbar de Ações
    col_actions = st.columns(4)
    with col_actions[0]:
        if st.button("➕ Novo Módulo", use_container_width=True):
            dialog_criar_modulo(curso.get("id"), len(modulos))
    with col_actions[1]:
        if st.button("➕ Nova Aula", use_container_width=True, disabled=(len(modulos)==0)):
            dialog_criar_aula(curso.get("id"), modulos, usuario)

    st.markdown("<br>", unsafe_allow_html=True)

    if not modulos:
        st.info("Nenhum módulo criado. Comece clicando em 'Novo Módulo'.")
        return

    # Renderiza a árvore do curso
    for mod in modulos:
        with st.expander(f"📦 {mod['titulo']}", expanded=True):
            aulas = mod.get("aulas", [])
            
            if not aulas:
                st.caption("Nenhuma aula neste módulo.")
            
            for aula in aulas:
                # Layout de linha: Ícone | Nome | Botão Editar
                c_icon, c_name, c_btn = st.columns([0.5, 4, 1])
                c_icon.markdown("📄")
                c_name.markdown(f"**{aula['titulo']}** <small style='color:gray'>({aula.get('duracao_min', 0)} min)</small>", unsafe_allow_html=True)
                
                if c_btn.button("Editar", key=f"btn_edit_{aula['id']}"):
                    st.session_state["aula_editando_id"] = aula['id']
                    st.rerun()
