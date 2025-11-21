import streamlit as st
from datetime import datetime
from core.db import consultar_todos, consultar_um, executar


# ====================================================================================
# 📌 Tela de Aprovação de Solicitações de Faixa
# Somente para PROFESSOR e ADMIN
# ====================================================================================

def tela_solicitacoes_faixa(usuario):

    if usuario["tipo"] not in ["professor", "admin"]:
        st.error("Você não tem permissão para acessar esta página.")
        return

    st.title("🎖 Aprovar Mudanças de Faixa")

    st.info("Aqui você pode aprovar ou recusar solicitações enviadas pelos alunos.")

    # Buscar solicitações pendentes
    pendentes = consultar_todos("""
        SELECT s.id, s.usuario_id, s.faixa_atual, s.faixa_solicitada, s.data_solicitacao,
               u.nome, u.data_nascimento
        FROM solicitacoes_faixa s
        JOIN usuarios u ON u.id = s.usuario_id
        WHERE s.status='pendente'
        ORDER BY s.id ASC
    """)

    if not pendentes:
        st.success("Nenhuma solicitação pendente no momento.")
        return

    for s in pendentes:

        st.markdown("---")
        st.subheader(f"👤 {s['nome']}")

        st.write(f"**Faixa atual:** {s['faixa_atual']}")
        st.write(f"**Faixa solicitada:** {s['faixa_solicitada']}")
        st.write(f"**Data da solicitação:** {s['data_solicitacao']}")
        st.write(f"**Data de nascimento:** {s['data_nascimento']}")

        col1, col2 = st.columns(2)

        # ===========================
        # APROVAR
        # ===========================
        if col1.button(f"✔ Aprovar solicitação #{s['id']}", use_container_width=True):

            # Atualizar faixa do aluno
            executar("""
                UPDATE usuarios
                SET faixa=?
                WHERE id=?
            """, (s["faixa_solicitada"], s["usuario_id"]))

            # Atualizar status da solicitação
            executar("""
                UPDATE solicitacoes_faixa
                SET status='aprovado',
                    data_resposta=?,
                    resposta_por=?
                WHERE id=?
            """, (
                datetime.now().strftime("%d/%m/%Y %H:%M"),
                usuario["id"],
                s["id"]
            ))

            st.success(
                f"Solicitação #{s['id']} aprovada! "
                f"{s['nome']} agora é faixa **{s['faixa_solicitada']}**."
            )
            st.rerun()

        # ===========================
        # RECUSAR
        # ===========================
        if col2.button(f"❌ Recusar solicitação #{s['id']}", use_container_width=True):

            executar("""
                UPDATE solicitacoes_faixa
                SET status='recusado',
                    data_resposta=?,
                    resposta_por=?
                WHERE id=?
            """, (
                datetime.now().strftime("%d/%m/%Y %H:%M"),
                usuario["id"],
                s["id"]
            ))

            st.warning(f"Solicitação #{s['id']} recusada.")
            st.rerun()

    st.markdown("---")
