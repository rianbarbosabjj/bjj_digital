import streamlit as st
import pandas as pd
import time
import utils as ce
# Importa o editor "Lego"
import views.aulas_professor as editor_view 

def pagina_cursos_professor(usuario):
    # ======================================================
    # 1. ROTEAMENTO INTERNO (Lista <-> Editor)
    # ======================================================
    if st.session_state.get("curso_professor_selecionado"):
        curso_atual = st.session_state["curso_professor_selecionado"]
        editor_view.gerenciar_conteudo_curso(curso_atual, usuario)
        
        # Lógica de retorno
        if st.session_state.get("cursos_view") == "lista":
            st.session_state["curso_professor_selecionado"] = None
            st.rerun()
        return 

    # ======================================================
    # 2. TELA PRINCIPAL (COM ABAS)
    # ======================================================
    st.markdown(f"## 👨‍🏫 Painel do Professor: {usuario.get('nome').split()[0]}")
    
    # Criação das Abas
    tab_cursos, tab_financeiro = st.tabs(["📚 Meus Cursos", "💰 Meu Financeiro"])

    # ------------------------------------------------------
    # ABA 1: GERENCIAR CURSOS
    # ------------------------------------------------------
    with tab_cursos:
        col_topo_1, col_topo_2 = st.columns([4, 1])
        with col_topo_2:
            if st.button("➕ Novo Curso", type="primary", use_container_width=True):
                dialog_criar_curso_novo(usuario)

        cursos = ce.listar_cursos_do_professor(usuario["id"])

        if not cursos:
            st.info("Você ainda não criou nenhum curso.")
        else:
            for curso in cursos:
                with st.container(border=True):
                    c1, c2 = st.columns([4, 1])
                    with c1:
                        st.markdown(f"### {curso.get('titulo')}")
                        st.caption(f"Preço: R$ {curso.get('preco', 0):.2f} | Status: {'Ativo' if curso.get('ativo') else 'Inativo'}")
                    with c2:
                        st.write("")
                        if st.button("✏️ Editar", key=f"edt_{curso['id']}", use_container_width=True):
                            st.session_state["curso_professor_selecionado"] = curso
                            st.session_state["cursos_view"] = "detalhe"
                            st.rerun()
                        if st.button("⚙️ Config", key=f"cfg_{curso['id']}", use_container_width=True):
                            dialog_editar_info_curso(curso)

    # ------------------------------------------------------
    # ABA 2: FINANCEIRO (A Lógica de Pagamento Visual)
    # ------------------------------------------------------
    with tab_financeiro:
        st.write("Acompanhe seus ganhos (90% do valor das vendas).")
        st.write("")
        
        # 1. Busca os dados no backend
        saldo, historico = ce.obter_resumo_financeiro(usuario["id"])
        
        # 2. Mostra Big Numbers (Métricas)
        col_metric1, col_metric2, col_metric3 = st.columns(3)
        with col_metric1:
            st.metric("Saldo Total Acumulado", f"R$ {saldo:.2f}")
        with col_metric2:
            st.metric("Vendas Realizadas", len(historico))
        with col_metric3:
            # Botão de Saque Simulado
            if saldo > 0:
                if st.button("💸 Solicitar Saque", use_container_width=True):
                    ce.solicitar_saque(usuario["id"], saldo)
                    st.toast("Solicitação enviada ao admin!")
                    time.sleep(2)
            else:
                st.button("💸 Solicitar Saque", disabled=True, use_container_width=True)

        st.divider()
        
        # 3. Tabela de Extrato
        st.subheader("📜 Extrato de Vendas")
        if historico:
            df = pd.DataFrame(historico)
            st.dataframe(
                df, 
                use_container_width=True, 
                hide_index=True,
                column_config={
                    "Sua Parte (90%)": st.column_config.TextColumn(
                        "Sua Parte (90%)",
                        help="Valor líquido já descontada a taxa da plataforma (10%)"
                    )
                }
            )
        else:
            st.info("Nenhuma venda registrada ainda.")

# ======================================================
# 3. DIÁLOGOS (Helpers)
# ======================================================
@st.dialog("Criar Novo Curso")
def dialog_criar_curso_novo(usuario):
    with st.form("form_create_curso"):
        titulo = st.text_input("Título do Curso")
        desc = st.text_area("Descrição")
        c1, c2 = st.columns(2)
        preco = c1.number_input("Preço (0 para Gratuito)", min_value=0.0, step=10.0)
        duracao = c2.text_input("Duração (ex: 2h)")
        
        if st.form_submit_button("Criar Curso"):
            if titulo:
                ce.criar_curso(
                    professor_id=usuario['id'],
                    nome_professor=usuario['nome'],
                    professor_equipe=usuario.get('equipe', ''),
                    titulo=titulo,
                    descricao=desc,
                    modalidade="Online",
                    publico="todos",
                    equipe_destino="",
                    pago=(preco > 0),
                    preco=preco,
                    split_custom=False,
                    certificado_automatico=True,
                    duracao_estimada=duracao,
                    nivel="Geral"
                )
                st.success("Curso criado!")
                st.rerun()

@st.dialog("Configurações do Curso")
def dialog_editar_info_curso(curso):
    st.markdown(f"**{curso['titulo']}**")
    with st.form("form_edit_meta"):
        novo_titulo = st.text_input("Título", value=curso.get('titulo',''))
        novo_preco = st.number_input("Preço", value=float(curso.get('preco', 0)))
        if st.form_submit_button("Salvar"):
            ce.editar_curso(curso['id'], {"titulo": novo_titulo, "preco": novo_preco, "pago": novo_preco > 0})
            st.rerun()
