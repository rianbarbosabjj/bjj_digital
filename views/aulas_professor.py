import streamlit as st
import utils as ce
import time

# --- FUNÇÕES AUXILIARES (MODAIS) ---

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
    # Prepara dicionário para dropdown
    mapa_modulos = {m['titulo']: m['id'] for m in modulos}
    
    with st.form("form_aula_basica"):
        st.caption("Crie a estrutura primeiro, adicione conteúdo depois.")
        titulo = st.text_input("Título da Aula")
        modulo_select = st.selectbox("Selecione o Módulo", list(mapa_modulos.keys()))
        duracao = st.number_input("Duração (min)", value=10)
        
        if st.form_submit_button("Criar Aula"):
            if titulo and modulo_select:
                mod_id = mapa_modulos[modulo_select]
                # Cria aula vazia (sem blocos por enquanto)
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
                st.success("Aula criada! Agora você pode editá-la.")
                st.rerun()

# --- EDITOR DE BLOCOS (SEPARADO) ---
def editor_de_aula(aula, curso_id):
    st.markdown(f"## ✏️ Editando: {aula['titulo']}")
    
    # --- 1. INICIALIZAÇÃO DO ESTADO ---
    # Carrega os blocos existentes apenas na primeira vez que abre o editor
    if "blocos_temporarios" not in st.session_state:
        # Tenta pegar do banco, se não existir, inicia lista vazia
        st.session_state["blocos_temporarios"] = aula.get("blocos", [])

    # Atalho para a lista de blocos
    blocos = st.session_state["blocos_temporarios"]

    col_esq, col_dir = st.columns([2, 1])

    # --- 2. ÁREA DE VISUALIZAÇÃO E EDIÇÃO (LADO ESQUERDO) ---
    with col_esq:
        st.info("👇 Esta é a estrutura atual da sua aula:")
        
        if not blocos:
            st.warning("A aula está vazia. Adicione blocos ao lado 👉")

        # Loop para renderizar cada bloco com controles
        for i, bloco in enumerate(blocos):
            tipo = bloco.get("tipo")
            conteudo = bloco.get("conteudo")

            # Cria um container visual (caixa) para cada bloco
            with st.container(border=True):
                c_conteudo, c_acoes = st.columns([5, 1])

                with c_conteudo:
                    # Renderiza o conteúdo real (Preview)
                    if tipo == "texto":
                        st.markdown(conteudo)
                    elif tipo == "imagem":
                        try:
                            st.image(conteudo, use_column_width=True)
                        except:
                            st.error(f"Erro ao carregar imagem: {conteudo}")
                    elif tipo == "video":
                        try:
                            st.video(conteudo)
                        except:
                            st.error(f"Erro ao carregar vídeo: {conteudo}")

                # Botões de controle (Mover e Excluir)
                with c_acoes:
                    # Botão SUBIR
                    if i > 0:
                        if st.button("⬆️", key=f"up_{i}", help="Mover para cima"):
                            blocos[i], blocos[i-1] = blocos[i-1], blocos[i]
                            st.rerun()
                    
                    # Botão DESCER
                    if i < len(blocos) - 1:
                        if st.button("⬇️", key=f"down_{i}", help="Mover para baixo"):
                            blocos[i], blocos[i+1] = blocos[i+1], blocos[i]
                            st.rerun()
                    
                    # Botão EXCLUIR
                    if st.button("🗑️", key=f"del_{i}", type="primary"):
                        blocos.pop(i)
                        st.rerun()

    # --- 3. FERRAMENTAS DE ADIÇÃO (LADO DIREITO) ---
    with col_dir:
        st.markdown("### ➕ Adicionar Conteúdo")
        
        tab_txt, tab_img, tab_vid = st.tabs(["Texto", "Imagem", "Vídeo"])

        # --- Adicionar Texto ---
        with tab_txt:
            novo_texto = st.text_area("Escreva aqui (Markdown suportado)", height=150)
            if st.button("Adicionar Texto"):
                if novo_texto.strip():
                    blocos.append({"tipo": "texto", "conteudo": novo_texto})
                    st.toast("Texto adicionado no final!")
                    st.rerun()

        # --- Adicionar Imagem ---
        with tab_img:
            # Opção A: URL da Imagem
            url_img = st.text_input("Link da Imagem (URL)")
            if st.button("Adicionar Imagem por Link"):
                if url_img:
                    blocos.append({"tipo": "imagem", "conteudo": url_img})
                    st.rerun()
            
            st.divider()
            
            # Opção B: Upload (Simulado)
            uploaded_img = st.file_uploader("Ou faça upload", type=['png', 'jpg'])
            if uploaded_img:
                # AQUI VOCÊ FARIA O UPLOAD PARA O STORAGE (S3/FIREBASE) E PEGARIA A URL
                # Exemplo simulado:
                st.warning("Upload requer integração com Storage. Usando placeholder.")
                # blocos.append({"tipo": "imagem", "conteudo": url_retornada_do_storage})

        # --- Adicionar Vídeo ---
        with tab_vid:
            url_video = st.text_input("Link do Vídeo (YouTube/Vimeo/MP4)")
            if st.button("Adicionar Vídeo"):
                if url_video:
                    blocos.append({"tipo": "video", "conteudo": url_video})
                    st.rerun()

    st.divider()

    # --- 4. BARRA DE SALVAMENTO ---
    col_save_1, col_save_2 = st.columns([1, 4])
    
    with col_save_1:
        if st.button("← Cancelar"):
            del st.session_state["blocos_temporarios"]
            st.session_state["aula_editando_id"] = None
            st.rerun()

    with col_save_2:
        if st.button("💾 SALVAR ALTERAÇÕES NA AULA", type="primary", use_container_width=True):
            # Chamada ao Backend
            ce.atualizar_aula_blocos(
                curso_id=curso_id,
                aula_id=aula['id'],
                novos_blocos=blocos
            )
            
            # Limpeza
            del st.session_state["blocos_temporarios"]
            st.session_state["aula_editando_id"] = None
            
            st.success("Aula atualizada com sucesso!")
            time.sleep(1) # Pausa dramática para o usuário ler
            st.rerun()

# --- FUNÇÃO PRINCIPAL ---

def gerenciar_conteudo_curso(curso: dict, usuario: dict):
    # Cabeçalho limpo com colunas
    c1, c2 = st.columns([3, 1])
    c1.markdown(f"## 🎛️ Gestão: {curso.get('titulo')}")
    if c2.button("← Voltar à Lista"):
        st.session_state["cursos_view"] = "detalhe"
        st.rerun()
    
    st.divider()

    # Verifica se estamos em modo de edição de uma aula específica
    if st.session_state.get("aula_editando_id"):
        # Busca os dados da aula que está sendo editada
        # (Aqui estou simulando, você buscaria no banco pelo ID)
        aula_atual = {"id": st.session_state["aula_editando_id"], "titulo": "Aula Selecionada"} 
        editor_de_aula(aula_atual, curso.get("id"))
        return

    # --- VISÃO GERAL (ESTRUTURA) ---
    modulos = ce.listar_modulos_e_aulas(curso.get("id")) or []

    # Botões de Ação no Topo (Toolbar)
    col_actions = st.columns(4)
    with col_actions[0]:
        if st.button("➕ Novo Módulo", use_container_width=True):
            dialog_criar_modulo(curso.get("id"), len(modulos))
    with col_actions[1]:
        if st.button("➕ Nova Aula", use_container_width=True, disabled=len(modulos)==0):
            dialog_criar_aula(curso.get("id"), modulos, usuario)

    st.markdown("---")

    # Listagem Limpa e Hierárquica
    if not modulos:
        st.warning("O curso está vazio. Comece criando um módulo acima.")
        return

    for mod in modulos:
        with st.expander(f"📦 {mod['titulo']}", expanded=True):
            aulas = mod.get("aulas", [])
            
            if not aulas:
                st.caption("Módulo vazio.")
            
            for aula in aulas:
                # Layout de linha para cada aula: Ícone + Título + Botão Editar
                c_txt, c_btn = st.columns([4, 1])
                c_txt.markdown(f"📄 **{aula['titulo']}** <span style='color:gray; font-size:0.8em'>({aula.get('duracao_min')} min)</span>", unsafe_allow_html=True)
                
                if c_btn.button("Editar", key=f"btn_edit_{aula['id']}"):
                    st.session_state["aula_editando_id"] = aula['id']
                    st.rerun()
