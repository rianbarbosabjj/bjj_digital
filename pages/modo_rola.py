import streamlit as st
from core.ui import aplicar_css
from core.db import consultar_todos, executar

def tela_modo_rola(usuario):

    aplicar_css()

    st.markdown(
        "<h1 style='text-align:center; color:#FFD770;'>🥋 Modo Rola</h1>",
        unsafe_allow_html=True
    )
    st.write("")

    st.markdown(
        "<p style='text-align:center;'>Selecione dois praticantes para registrar uma rola:</p>",
        unsafe_allow_html=True
    )

    # ============================================================
    # 🔹 Carregar usuários (alunos e professores)
    # ============================================================
    usuarios = consultar_todos("""
        SELECT id, nome FROM usuarios 
        WHERE tipo='aluno' OR tipo='professor'
        ORDER BY nome
    """)

    lista_nomes = {u["nome"]: u["id"] for u in usuarios}
    nomes = list(lista_nomes.keys())

    col1, col2 = st.columns(2)

    with col1:
        atleta1 = st.selectbox("Atleta 1", nomes)

    with col2:
        atleta2 = st.selectbox("Atleta 2", nomes)

    if atleta1 == atleta2:
        st.error("Os dois atletas devem ser diferentes.")
        return

    st.markdown("---")

    # ============================================================
    # 🔹 BOTÕES DE RESULTADO
    # ============================================================
    st.markdown("<h3 style='text-align:center;'>Registrar Resultado</h3>", unsafe_allow_html=True)
    colA, colB, colC = st.columns(3)

    id1 = lista_nomes[atleta1]
    id2 = lista_nomes[atleta2]

    # Vitória do atleta 1
    with colA:
        if st.button(f"🏆 {atleta1} venceu"):
            executar("""
                INSERT INTO modo_rola (vencedor_id, perdedor_id, resultado)
                VALUES (?, ?, ?)
            """, (id1, id2, "vitoria"))
            st.success(f"Registrado: {atleta1} venceu!")
            st.rerun()

    # Empate
    with colB:
        if st.button("🤝 Empate"):
            executar("""
                INSERT INTO modo_rola (vencedor_id, perdedor_id, resultado)
                VALUES (?, ?, ?)
            """, (id1, id2, "empate"))
            st.success("Registrado: Empate!")
            st.rerun()

    # Vitória do atleta 2
    with colC:
        if st.button(f"🏆 {atleta2} venceu"):
            executar("""
                INSERT INTO modo_rola (vencedor_id, perdedor_id, resultado)
                VALUES (?, ?, ?)
            """, (id2, id1, "vitoria"))
            st.success(f"Registrado: {atleta2} venceu!")
            st.rerun()

    st.markdown("---")

    # ============================================================
    # 🔹 RANKING ATUAL
    # ============================================================
    st.markdown("<h3 style='text-align:center;'>🏆 Ranking Geral</h3>", unsafe_allow_html=True)

    ranking = consultar_todos("""
        SELECT 
            u.nome,
            SUM(CASE WHEN m.resultado='vitoria' THEN 1 ELSE 0 END) AS vitorias,
            SUM(CASE WHEN m.resultado='empate' THEN 1 ELSE 0 END) AS empates
        FROM modo_rola m
        JOIN usuarios u ON u.id = m.vencedor_id
        GROUP BY u.nome
        ORDER BY vitorias DESC, empates DESC
    """)

    if ranking:
        st.table(ranking)
    else:
        st.info("Nenhuma rola registrada ainda.")

    st.markdown("---")

    # ============================================================
    # 🔹 RESETAR TUDO
    # ============================================================
    if st.button("🗑️ Limpar Histórico de Rolas"):
        executar("DELETE FROM modo_rola")
        st.success("Histórico limpo!")
        st.rerun()
