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
    st.markdown(f"#### ✏️ Editando: {aula['titulo']}")
    
    # Aqui você carrega os blocos existentes da aula se houver
    # (Assumindo que você tenha uma função para buscar blocos ou eles venham no objeto aula)
    
    st.info("Aqui entraria a interface de 'Drag & Drop' ou adição de blocos isolada.")
    # Exemplo simplificado de adição rápida:
    novo_texto = st.text_area("Adicionar bloco de texto rápido")
    if st.button("Salvar Bloco de Texto"):
        # Lógica para dar append no array de blocos dessa aula específica no banco
        st.toast("Bloco adicionado!")

    if st.button("🔙 Voltar para Estrutura"):
        st.session_state["aula_editando_id"] = None
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
