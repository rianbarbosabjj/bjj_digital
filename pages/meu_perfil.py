import streamlit as st
from datetime import datetime
from core.db import consultar_um, consultar_todos, executar, executar_retorna_id

# =================================================================================
# 📌 Função auxiliar: calcular idade no ano corrente (IBJJF)
# =================================================================================

def idade_no_ano(data_nascimento):
    try:
        nasc = datetime.strptime(data_nascimento, "%Y-%m-%d")
        ano_atual = datetime.now().year
        return ano_atual - nasc.year
    except:
        return None


# =================================================================================
# 📌 Lista de faixas (Kids + Adulto)
# =================================================================================

FAIXAS_KIDS = [
    "Cinza-Branca", "Cinza", "Cinza-Preta",
    "Amarela-Branca", "Amarela", "Amarela-Preta",
    "Laranja-Branca", "Laranja", "Laranja-Preta",
    "Verde-Branca", "Verde", "Verde-Preta"
]

FAIXAS_ADULTO = ["Azul", "Roxa", "Marrom", "Preta"]


# =================================================================================
# 📌 Página de Perfil do Usuário
# =================================================================================

def tela_perfil(usuario):

    st.title("👤 Meu Perfil")

    st.info("Atualize seus dados pessoais. Alterações de faixa precisam ser aprovadas pelo professor/admin.")

    usuario_id = usuario["id"]

    # Carregar dados atualizados do banco
    user = consultar_um("SELECT * FROM usuarios WHERE id=?", (usuario_id,))

    nome = st.text_input("Nome completo", value=user["nome"])
    cpf = st.text_input("CPF", value=user["cpf"], disabled=True)
    email = st.text_input("Email", value=user["email"], disabled=True)
    endereco = st.text_input("Endereço", value=user["endereco"] or "")

    # ==========================================
    # 📅 Data de nascimento
    # ==========================================

    if user["data_nascimento"]:
        data_nasc = datetime.strptime(user["data_nascimento"], "%Y-%m-%d").date()
    else:
        data_nasc = None

    nova_data_nasc = st.date_input("Data de nascimento", value=data_nasc)

    # ==========================================
    # 🎖 Faixa atual
    # ==========================================

    st.markdown(f"### Faixa atual: **{user['faixa'] or 'Não definida'}**")

    idade = idade_no_ano(str(nova_data_nasc))

    if idade is None:
        st.warning("Selecione a data de nascimento para liberar seleção de faixa.")
        allowed_faixas = []
    else:
        if idade < 16:
            allowed_faixas = FAIXAS_KIDS
        else:
            allowed_faixas = FAIXAS_ADULTO

    st.markdown("#### Solicitar mudança de faixa")

    faixa_solicitada = st.selectbox(
        "Escolha a nova faixa:",
        allowed_faixas,
        index=allowed_faixas.index(user["faixa"]) if user["faixa"] in allowed_faixas else 0
    )

    # ==========================================
    # 🔁 Histórico de solicitações
    # ==========================================

    st.markdown("---")
    st.subheader("📄 Histórico de solicitações de faixa")

    historico = consultar_todos("""
        SELECT * FROM solicitacoes_faixa 
        WHERE usuario_id=? ORDER BY id DESC
    """, (usuario_id,))

    if historico:
        for h in historico:
            st.write(f"**Solicitada:** {h['faixa_solicitada']} — **Status:** {h['status']}")
            st.write(f"Data: {h['data_solicitacao']}")
            st.write("---")
    else:
        st.info("Nenhuma solicitação registrada ainda.")

    st.markdown("---")

    # ==========================================
    # 💾 SALVAR ALTERAÇÕES
    # ==========================================

    if st.button("Salvar alterações", use_container_width=True):

        # Atualizar dados básicos
        executar("""
            UPDATE usuarios
            SET nome=?, endereco=?, data_nascimento=?
            WHERE id=?
        """, (
            nome,
            endereco,
            nova_data_nasc,
            usuario_id
        ))

        # Criar solicitação de faixa SE for diferente da atual
        if faixa_solicitada != user["faixa"]:
            executar("""
                INSERT INTO solicitacoes_faixa (
                    usuario_id, faixa_atual, faixa_solicitada, status, data_solicitacao
                )
                VALUES (?, ?, ?, 'pendente', ?)
            """, (
                usuario_id,
                user["faixa"],
                faixa_solicitada,
                datetime.now().strftime("%d/%m/%Y %H:%M")
            ))

            st.success("Solicitação de mudança de faixa enviada! Aguarde aprovação.")
        else:
            st.success("Perfil atualizado com sucesso!")

        st.rerun()

