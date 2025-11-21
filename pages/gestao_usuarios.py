import streamlit as st
import pandas as pd
from core.db import consultar_todos, executar, buscar_usuario_por_id
from core.cpf import limpar_cpf, validar_cpf
import bcrypt


def gestao_usuarios():
    st.title("🔑 Gestão de Usuários")

    # ============================
    # LISTA DE USUÁRIOS
    # ============================
    usuarios = consultar_todos("""
        SELECT id, nome, email, cpf, tipo
        FROM usuarios
        ORDER BY nome
    """)

    if not usuarios:
        st.info("Nenhum usuário cadastrado ainda.")
        return

    df = pd.DataFrame(usuarios)
    df.columns = ["ID", "Nome", "Email", "CPF", "Tipo"]

    st.subheader("Usuários cadastrados")
    st.dataframe(df, use_container_width=True)

    st.markdown("---")

    # ============================
    # SELECIONAR USUÁRIO PARA EDIÇÃO
    # ============================
    lista_nomes = [f"{u['id']} - {u['nome']}" for u in usuarios]
    selecao = st.selectbox("Selecione um usuário", lista_nomes)

    user_id = int(selecao.split(" - ")[0])
    user = buscar_usuario_por_id(user_id)

    st.markdown(f"### Editando: **{user['nome']}**")

    # ============================
    # FORMULÁRIO DE EDIÇÃO
    # ============================
    novo_nome = st.text_input("Nome", value=user["nome"])
    novo_email = st.text_input("Email", value=user["email"])
    novo_cpf = st.text_input("CPF (somente números)", value=user["cpf"] or "")

    tipo = st.selectbox(
        "Tipo de usuário",
        ["aluno", "professor", "admin"],
        index=["aluno", "professor", "admin"].index(user["tipo"])
    )

    if st.button("Salvar alterações", use_container_width=True):

        # Validação do CPF
        cpf_limpo = limpar_cpf(novo_cpf)
        if novo_cpf and not validar_cpf(cpf_limpo):
            st.error("CPF inválido.")
            return

        try:
            executar("""
                UPDATE usuarios
                SET nome=?, email=?, cpf=?, tipo=?
                WHERE id=?
            """, (
                novo_nome.upper(),
                novo_email.lower(),
                cpf_limpo,
                tipo,
                user_id
            ))

            st.success("Dados atualizados com sucesso!")
            st.rerun()

        except Exception as e:
            st.error(f"Erro ao atualizar: {e}")

    st.markdown("---")

    # ============================
    # ALTERAR SENHA
    # ============================
    st.subheader("Redefinir senha")

    nova_senha = st.text_input("Nova senha", type="password")
    confirmar = st.text_input("Confirmar senha", type="password")

    if st.button("Atualizar senha"):

        if nova_senha != confirmar:
            st.error("As senhas não coincidem.")
            return

        hash_pw = bcrypt.hashpw(nova_senha.encode(), bcrypt.gensalt()).decode()

        executar("UPDATE usuarios SET senha=? WHERE id=?", (hash_pw, user_id))
        st.success("Senha redefinida!")

    st.markdown("---")

    # ============================
    # EXCLUIR USUÁRIO
    # ============================
    if st.button("🗑️ Excluir usuário", type="primary"):
        executar("DELETE FROM usuarios WHERE id=?", (user_id,))
        st.success("Usuário excluído com sucesso.")
        st.rerun()

