import streamlit as st
import time
import utils as ce
# Importa o editor "Lego" que criamos no início
import views.aulas_professor as editor_view 

def pagina_cursos_professor(usuario):
    st.markdown(f"## 👨‍🏫 Painel do Professor: {usuario.get('nome')}")
    st.markdown("---")

    # ======================================================
    # 1. ROTEAMENTO INTERNO (Lista <-> Editor)
    # ======================================================
    # Verifica se há um curso selecionado para edição
    if st.session_state.get("curso_professor_selecionado"):
        curso_atual = st.session_state["curso_professor_selecionado"]
        
        # Chama o EDITOR DE AULAS (Aquele arquivo 'aulas_professor.py')
        editor_view.gerenciar_conteudo_curso(curso_atual, usuario)
        
        # Se o editor definir que deve voltar, limpamos a seleção
        if st.session_state.get("cursos_view") == "lista":
            st.session_state["curso_professor_selecionado"] = None
            st.rerun()
        return # Para a execução aqui para focar no editor

    # ======================================================
    # 2. LISTAGEM DE CURSOS (Visão Geral)
    # ======================================================
    
    # Botão para criar novo curso
    col_topo_1, col_topo_2 = st.columns([4, 1])
    with col_topo_2:
        if st.button("➕ Novo Curso", type="primary", use_container_width=True):
            dialog_criar_curso_novo(usuario)

    # Busca cursos onde o usuário é dono ou editor
    cursos = ce.listar_cursos_do_professor(usuario["id"])

    if not cursos:
        st.info("Você ainda não possui cursos. Crie o primeiro acima!")
        return

    # Renderiza os cards dos cursos
    for curso in cursos:
        with st.container(border=True):
            c1, c2 = st.columns([4, 1])
            
            with c1:
                st.markdown(f"### {curso.get('titulo')}")
                st.caption(curso.get('descricao', 'Sem descrição'))
                
                # Badges
                infos = []
                if curso.get('publico') == 'equipe': infos.append(f"🔒 Equipe: {curso.get('equipe_destino')}")
                if curso.get('pago'): infos.append(f"💲 R$ {curso.get('preco')}")
                else: infos.append("🆓 Gratuito")
                st.caption(" | ".join(infos))

            with c2:
                st.write("")
                st.write("")
                # BOTÃO QUE LEVA AO EDITOR
                if st.button("✏️ Editar Aulas", key=f"edit_cont_{curso['id']}", use_container_width=True):
                    st.session_state["curso_professor_selecionado"] = curso
                    st.session_state["aula_editando_id"] = None # Reseta edição de aula específica
                    st.session_state["cursos_view"] = "detalhe"
                    st.rerun()
                
                # Botão para editar metadados (Título, Preço, etc) - Opcional
                if st.button("⚙️ Configurações", key=f"edit_meta_{curso['id']}", use_container_width=True):
                    dialog_editar_info_curso(curso)

# ======================================================
# 3. DIÁLOGOS (Criação e Edição de Info)
# ======================================================
@st.dialog("Criar Novo Curso")
def dialog_criar_curso_novo(usuario):
    with st.form("form_create_curso"):
        titulo = st.text_input("Título do Curso")
        desc = st.text_area("Descrição")
        
        c1, c2 = st.columns(2)
        preco = c1.number_input("Preço (0 para Gratuito)", min_value=0.0, step=10.0)
        duracao = c2.text_input("Duração Estimada (ex: 2h 30m)")
        
        pago = preco > 0
        
        if st.form_submit_button("Criar Curso"):
            if titulo:
                # Chama função do utils (adaptada para os parâmetros que você tem)
                ce.criar_curso(
                    professor_id=usuario['id'],
                    nome_professor=usuario['nome'],
                    professor_equipe=usuario.get('equipe', ''),
                    titulo=titulo,
                    descricao=desc,
                    modalidade="Online",
                    publico="todos", # Padrão, depois pode mudar
                    equipe_destino="",
                    pago=pago,
                    preco=preco,
                    split_custom=False,
                    certificado_automatico=True,
                    duracao_estimada=duracao,
                    nivel="Geral"
                )
                st.success("Curso criado!")
                st.rerun()
            else:
                st.warning("O título é obrigatório.")

@st.dialog("Configurações do Curso")
def dialog_editar_info_curso(curso):
    st.write(f"Editando: **{curso['titulo']}**")
    with st.form("form_edit_curso"):
        novo_titulo = st.text_input("Título", value=curso.get('titulo',''))
        novo_preco = st.number_input("Preço", value=float(curso.get('preco', 0)))
        novo_ativo = st.checkbox("Curso Ativo (Visível para alunos)", value=curso.get('ativo', True))
        
        if st.form_submit_button("Salvar Alterações"):
            ce.editar_curso(curso['id'], {
                "titulo": novo_titulo,
                "preco": novo_preco,
                "pago": novo_preco > 0,
                "ativo": novo_ativo
            })
            st.success("Atualizado!")
            st.rerun()
    
    st.divider()
    if st.button("🗑️ Excluir Curso", type="primary"):
        ce.excluir_curso(curso['id'])
        st.rerun()
