import streamlit as st
import utils as ce
import time

# ======================================================
# 1. DIÁLOGOS (MODAIS) PARA CRIAÇÃO RÁPIDA
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
# 2. O EDITOR "LEGO" (INTEGRADO AO SEU UTILS)
# ======================================================
def editor_de_aula(aula, curso_id):
    st.markdown(f"### ✏️ Editando: {aula['titulo']}")
    
    # --- A. GERENCIAMENTO DE ESTADO ---
    # Se é a primeira vez abrindo essa aula, carrega os blocos do banco
    if "blocos_temp" not in st.session_state:
        # Pega os blocos que vieram do banco (campo 'conteudo' -> 'blocos' conforme seu utils)
        # O utils retorna: {"conteudo": {"blocos": [...]}} para compatibilidade
        conteudo = aula.get("conteudo", {})
        blocos_iniciais = conteudo.get("blocos", []) if isinstance(conteudo, dict) else []
        st.session_state["blocos_temp"] = blocos_iniciais

    blocos = st.session_state["blocos_temp"]

    # Layout: Esquerda (Visualização) | Direita (Ferramentas)
    col_view, col_tools = st.columns([2, 1])

    # --- B. COLUNA DA ESQUERDA (VISUALIZAÇÃO/ORDENAÇÃO) ---
    with col_view:
        st.info("👇 **Conteúdo da Aula** (O que o aluno vai ver)")
        
        if not blocos:
            st.warning("Aula vazia. Use as ferramentas ao lado para adicionar conteúdo 👉")
        
        # Itera sobre os blocos para mostrar e permitir reordenar
        for i, bloco in enumerate(blocos):
            tipo = bloco.get("tipo", "texto")
            
            # Caixa visual do bloco
            with st.container(border=True):
                c_content, c_actions = st.columns([6, 1])
                
                # Renderiza o conteúdo (Preview)
                with c_content:
                    if tipo == "texto":
                        st.markdown(bloco.get("conteudo", ""))
                    
                    elif tipo in ["imagem", "video"]:
                        # Tenta pegar 'url' (padrão V2) ou 'url_link' (legado)
                        url = bloco.get("url") or bloco.get("url_link") or bloco.get("conteudo")
                        
                        if url:
                            if tipo == "imagem":
                                st.image(url, use_column_width=True)
                            else:
                                st.video(url)
                        else:
                            st.error("Mídia sem URL")

                # Botões de Ação (Subir, Descer, Excluir)
                with c_actions:
                    if i > 0:
                        if st.button("⬆️", key=f"up_{i}"):
                            blocos[i], blocos[i-1] = blocos[i-1], blocos[i]
                            st.rerun()
                    
                    if i < len(blocos) - 1:
                        if st.button("⬇️", key=f"dw_{i}"):
                            blocos[i], blocos[i+1] = blocos[i+1], blocos[i]
                            st.rerun()
                            
                    if st.button("❌", key=f"del_{i}", type="primary"):
                        blocos.pop(i)
                        st.rerun()

    # --- C. COLUNA DA DIREITA (FERRAMENTAS DE ADIÇÃO) ---
    with col_tools:
        st.markdown("### 🛠️ Adicionar")
        tab_txt, tab_img, tab_vid = st.tabs(["Texto", "📷 Foto", "🎥 Vídeo"])

        # 1. TEXTO
        with tab_txt:
            txt_input = st.text_area("Digite o conteúdo", height=150, help="Aceita Markdown (*itálico*, **negrito**)")
            if st.button("➕ Add Texto"):
                if txt_input.strip():
                    blocos.append({"tipo": "texto", "conteudo": txt_input})
                    st.toast("Texto adicionado!")
                    st.rerun()

        # 2. IMAGEM (INTEGRAÇÃO COM UTILS)
        with tab_img:
            arquivo_img = st.file_uploader("Upload Imagem", type=['png', 'jpg', 'jpeg'])
            if arquivo_img and st.button("Enviar Imagem"):
                with st.spinner("Enviando para o Cloud..."):
                    # Define caminho organizado: curso/aula/timestamp_nome
                    caminho = f"midia_cursos/{curso_id}/{aula['id']}/{int(time.time())}_{arquivo_img.name}"
                    
                    # CHAMA SEU UTILS.PY
                    url_publica = ce.upload_arquivo_simples(arquivo_img, caminho)
                    
                    if url_publica:
                        # Adiciona no padrão V2
                        blocos.append({
                            "tipo": "imagem",
                            "url": url_publica,
                            "origem": "upload",
                            "nome": arquivo_img.name
                        })
                        st.success("Imagem adicionada!")
                        st.rerun()
                    else:
                        st.error("Falha no upload.")

            st.divider()
            url_ext_img = st.text_input("Ou URL da imagem")
            if st.button("Add URL Imagem"):
                if url_ext_img:
                    blocos.append({"tipo": "imagem", "url": url_ext_img, "origem": "link"})
                    st.rerun()

        # 3. VÍDEO (INTEGRAÇÃO COM UTILS)
        with tab_vid:
            arquivo_vid = st.file_uploader("Upload Vídeo (MP4)", type=['mp4', 'mov'])
            if arquivo_vid:
                st.caption(f"Tamanho: {arquivo_vid.size / 1024 / 1024:.1f} MB")
                if st.button("Enviar Vídeo"):
                    with st.spinner("Enviando vídeo (pode demorar)..."):
                        caminho = f"midia_cursos/{curso_id}/{aula['id']}/{int(time.time())}_{arquivo_vid.name}"
                        
                        # CHAMA SEU UTILS.PY
                        url_publica = ce.upload_arquivo_simples(arquivo_vid, caminho)
                        
                        if url_publica:
                            blocos.append({
                                "tipo": "video",
                                "url": url_publica,
                                "origem": "upload",
                                "nome": arquivo_vid.name
                            })
                            st.success("Vídeo adicionado!")
                            st.rerun()
                        else:
                            st.error("Falha no upload.")
            
            st.divider()
            url_youtube = st.text_input("Ou YouTube/Vimeo")
            if st.button("Add YouTube"):
                if url_youtube:
                    # Normaliza link usando função do seu utils
                    url_final = ce.normalizar_link_video(url_youtube)
                    blocos.append({"tipo": "video", "url": url_final, "origem": "link"})
                    st.rerun()

    st.divider()
    
    # --- D. SALVAR E SAIR ---
    c_back, c_save = st.columns([1, 4])
    if c_back.button("Cancelar"):
        del st.session_state["blocos_temp"]
        st.session_state["aula_editando_id"] = None
        st.rerun()
        
    if c_save.button("💾 SALVAR AULA", type="primary", use_container_width=True):
        # Chama a função de edição do seu utils
        sucesso = ce.editar_aula_v2(aula['id'], {"blocos": blocos})
        
        if sucesso:
            st.toast("Aula salva com sucesso!")
            del st.session_state["blocos_temp"]
            st.session_state["aula_editando_id"] = None
            time.sleep(1)
            st.rerun()
        else:
            st.error("Erro ao salvar no banco de dados.")

# ======================================================
# 3. FUNÇÃO PRINCIPAL (VIEW GERAL)
# ======================================================
def gerenciar_conteudo_curso(curso: dict, usuario: dict):
    
    # Se estiver editando uma aula específica, mostra o editor e para por aqui
    if st.session_state.get("aula_editando_id"):
        # Recupera dados básicos da aula para passar ao editor
        # (Idealmente buscaria do banco, mas podemos passar um dict básico se tivermos o ID e Título)
        # Para garantir, vou varrer a estrutura local, ou você pode fazer um 'ce.get_aula(id)'
        
        aula_alvo = None
        # Procura a aula na lista de módulos carregada (solução rápida)
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
            st.error("Aula não encontrada.")
            st.session_state["aula_editando_id"] = None
            st.rerun()

    # --- VISÃO GERAL (LISTA DE MÓDULOS) ---
    c1, c2 = st.columns([3, 1])
    c1.markdown(f"## 🎛️ Gestão: {curso.get('titulo')}")
    if c2.button("← Voltar ao Menu"):
        st.session_state["cursos_view"] = "detalhe"
        st.rerun()
        
    st.divider()

    # Busca estrutura atualizada
    modulos = ce.listar_modulos_e_aulas(curso.get("id")) or []

    # Barra de Ferramentas
    col_actions = st.columns(4)
    with col_actions[0]:
        if st.button("➕ Novo Módulo", use_container_width=True):
            dialog_criar_modulo(curso.get("id"), len(modulos))
    with col_actions[1]:
        # Só permite criar aula se existir módulo
        if st.button("➕ Nova Aula", use_container_width=True, disabled=(len(modulos)==0)):
            dialog_criar_aula(curso.get("id"), modulos, usuario)

    st.markdown("<br>", unsafe_allow_html=True)

    if not modulos:
        st.info("Nenhum módulo criado. Comece clicando em 'Novo Módulo'.")
        return

    # Renderiza a Árvore do Curso
    for mod in modulos:
        with st.expander(f"📦 {mod['titulo']}", expanded=True):
            aulas = mod.get("aulas", [])
            
            if not aulas:
                st.caption("Nenhuma aula neste módulo.")
            
            for aula in aulas:
                # Linha da aula
                c_icon, c_name, c_btn = st.columns([0.5, 4, 1])
                c_icon.markdown("📄")
                c_name.markdown(f"**{aula['titulo']}** <small>({aula.get('duracao_min', 0)} min)</small>", unsafe_allow_html=True)
                
                if c_btn.button("Editar", key=f"btn_edit_{aula['id']}"):
                    st.session_state["aula_editando_id"] = aula['id']
                    st.rerun()
