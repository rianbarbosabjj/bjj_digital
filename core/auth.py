import streamlit as st
import bcrypt
from core.db import (
    buscar_usuario_por_email,
    inserir_usuario,
    cpf_existe,
    email_existe,
    atualizar_endereco,
    buscar_usuario_por_id
)
from core.cpf import limpar_cpf, validar_cpf
from core.cep import buscar_cep


# =====================================================
# SESSÃO E VERIFICAÇÃO
# =====================================================

def verificar_sessao():
    """Retorna o usuário logado ou None."""
    if "usuario" not in st.session_state:
        return None
    return st.session_state.usuario


# =====================================================
# AUTENTICAÇÃO
# =====================================================

def autenticar(email, senha):
    """Autentica o usuário usando bcrypt."""
    user = buscar_usuario_por_email(email)
    if not user:
        return None

    senha_db = user["senha"]

    if senha_db is None:
        return None

    if bcrypt.checkpw(senha.encode(), senha_db.encode()):
        return user

    return None


# =====================================================
# CADASTRO
# =====================================================

def tela_cadastro():
    st.subheader("Criar Conta")

    nome = st.text_input("Nome completo")
    email = st.text_input("Email")
    cpf_digitado = st.text_input("CPF")
    senha = st.text_input("Senha", type="password")
    confirmar = st.text_input("Confirmar senha", type="password")

    if st.button("Criar conta", use_container_width=True):

        if not nome or not email or not cpf_digitado or not senha:
            st.warning("Preencha todos os campos.")
            return

        cpf_limpo = limpar_cpf(cpf_digitado)

        if not validar_cpf(cpf_limpo):
            st.error("CPF inválido.")
            return

        if cpf_existe(cpf_limpo):
            st.error("Este CPF já está cadastrado.")
            return

        if email_existe(email):
            st.error("Este e-mail já está cadastrado.")
            return

        if senha != confirmar:
            st.error("As senhas não coincidem.")
            return

        senha_hash = bcrypt.hashpw(senha.encode(), bcrypt.gensalt()).decode()

        inserir_usuario(nome, email, senha_hash, cpf_limpo)
        st.success("Conta criada com sucesso! Faça login.")
        st.session_state["modo_login"] = "login"


# =====================================================
# TELA DE LOGIN
# =====================================================

def tela_login():
    st.title("BJJ Digital")

    if "modo_login" not in st.session_state:
        st.session_state.modo_login = "login"

    modo = st.session_state.modo_login

    if modo == "login":
        st.subheader("Entrar")

        email = st.text_input("Email")
        senha = st.text_input("Senha", type="password")

        if st.button("Login", use_container_width=True):
            user = autenticar(email, senha)
            if user:
                st.session_state.usuario = dict(user)
                st.success("Login realizado!")
                st.rerun()
            else:
                st.error("Email ou senha incorretos.")

        st.markdown("---")
        if st.button("Criar conta", use_container_width=True):
            st.session_state.modo_login = "cadastro"

    elif modo == "cadastro":
        tela_cadastro()

        st.markdown("---")
        if st.button("Voltar ao Login", use_container_width=True):
            st.session_state.modo_login = "login"


# =====================================================
# COMPLETAR CADASTRO (ENDEREÇO)
# =====================================================

def tela_completar_cadastro(usuario):

    st.subheader("Complete seu cadastro")

    cep = st.text_input("CEP", key="cep_input")

    if st.button("Buscar CEP") and cep:
        dados = buscar_cep(cep)
        if dados:
            st.session_state.endereco_auto = dados
        else:
            st.error("CEP não encontrado.")

    endereco = st.text_input("Endereço", value=st.session_state.get("endereco_auto", {}).get("logradouro", ""))
    bairro = st.text_input("Bairro", value=st.session_state.get("endereco_auto", {}).get("bairro", ""))
    cidade = st.text_input("Cidade", value=st.session_state.get("endereco_auto", {}).get("localidade", ""))
    estado = st.text_input("Estado", value=st.session_state.get("endereco_auto", {}).get("uf", ""))
    numero = st.text_input("Número")

    if st.button("Salvar informações", use_container_width=True):
        if not (endereco and bairro and cidade and estado and numero):
            st.warning("Preencha todos os campos.")
            return

        atualizar_endereco(
            usuario["id"],
            {
                "endereco": endereco,
                "bairro": bairro,
                "cidade": cidade,
                "estado": estado,
                "cep": cep,
                "numero": numero
            }
        )

        st.success("Cadastro atualizado com sucesso!")
        st.rerun()

