import streamlit as st
import json
from core.db import consultar_todos, executar, executar_retorna_id, consultar_um


# ============================================================
# LISTA DE FAIXAS (ORDEM OFICIAL IBJJF)
# ============================================================

FAIXAS = [
    "Cinza Branca", "Cinza", "Cinza Preta",
    "Amarela Branca", "Amarela", "Amarela Preta",
    "Laranja Branca", "Laranja", "Laranja Preta",
    "Verde Branca", "Verde", "Verde Preta",
    "Azul", "Roxa", "Marrom", "Preta"
]


# ============================================================
# PÁGINA DE GESTÃO DE EXAMES (PROFESSOR)
# ============================================================

def gestao_exames():

    st.title("📝 Gestão de Exames")
    st.markdown("Crie, edite, ative e visualize exames configurados para cada faixa.")

    # ============================================================
    # LISTAR EXAMES EXISTENTES
    # ============================================================

    st.subheader("📚 Exames já criados")

    exames = consultar_todos("""
        SELECT * FROM exames_config ORDER BY id DESC
    """)

    if exames:
        for exame in exames:
            col1, col2, col3, col4 = st.columns([3, 2, 1, 1])
            with col1:
                st.markdown(f"**{exame['nome']}** — *{exame['faixa']}*")
            with col2:
                st.markdown("Ativo: **Sim**" if exame["ativo"] else "Ativo: **Não**")
            with col3:
                if st.button("Ativar", key=f"ativar_{exame['id']}"):
                    executar("UPDATE exames_config SET ativo=0 WHERE faixa=?", (exame["faixa"],))
                    executar("UPDATE exames_config SET ativo=1 WHERE id=?", (exame["id"],))
                    st.success("Exame ativado!")
                    st.rerun()
            with col4:
                if st.button("Excluir", key=f"del_{exame['id']}"):
                    executar("DELETE FROM exames_config WHERE id=?", (exame["id"],))
                    st.warning("Exame excluído.")
                    st.rerun()
    else:
        st.info("Nenhum exame criado ainda.")

    st.markdown("---")

    # ============================================================
    # CRIAR NOVO EXAME
    # ============================================================

    st.subheader("➕ Criar novo exame")

    nome_exame = st.text_input("Nome do exame")

    faixa = st.selectbox("Selecione a faixa", FAIXAS)

    embaralhar = st.checkbox("Embaralhar questões no exame", value=True)

    # ============================================================
    # FILTRAR QUESTÕES POR TEMA
    # ============================================================

    st.markdown("### Filtrar questões")

    temas = consultar_todos("""
        SELECT DISTINCT tema FROM questoes ORDER BY tema
    """)

    lista_temas = [t["tema"] for t in temas]

    tema_selecionado = st.selectbox("Selecione um tema", ["Todos"] + lista_temas)

    # ============================================================
    # LISTAR QUESTÕES DISPONÍVEIS
    # ============================================================

    st.markdown("### Questões disponíveis")

    if tema_selecionado == "Todos":
        questoes = consultar_todos("""
            SELECT * FROM questoes
            WHERE faixa=?
        """, (faixa,))
    else:
        questoes = consultar_todos("""
            SELECT * FROM questoes
            WHERE faixa=? AND tema=?
        """, (faixa, tema_selecionado))

    if not questoes:
        st.info("Nenhuma questão encontrada para esta combinação.")
        return

    # Caixa de seleção múltipla — professor escolhe questões da prova
    opcoes_label = [
        f"ID {q['id']} — {q['pergunta'][:60]}..."
        for q in questoes
    ]

    selecionadas = st.multiselect(
        "Escolha as questões que farão parte do exame",
        options=opcoes_label
    )

    # Converte lista de labels para IDs
    ids_escolhidos = []
    for sel in selecionadas:
        id_q = int(sel.split(" ")[1])
        ids_escolhidos.append(id_q)

    # ============================================================
    # SALVAR EXAME
    # ============================================================

    if st.button("Salvar exame", type="primary"):

        if not nome_exame.strip():
            st.error("O exame precisa de um nome.")
            return

        if not ids_escolhidos:
            st.error("Selecione pelo menos uma questão.")
            return

        executar_retorna_id("""
            INSERT INTO exames_config (nome, faixa, questoes_ids, embaralhar, ativo, professor_id, criado_em)
            VALUES (?, ?, ?, ?, 0, ?, ?)
        """, (
            nome_exame.strip(),
            faixa,
            json.dumps(ids_escolhidos),
            1 if embaralhar else 0,
            st.session_state["usuario"]["id"],
            st.session_state.get("agora", "")
        ))

        st.success("Exame criado com sucesso!")
        st.rerun()
