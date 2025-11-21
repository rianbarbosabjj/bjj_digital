import os
import streamlit as st

# vamos reaproveitar as cores do tema lá do core/ui.py
try:
    from core.ui import COR_DESTAQUE, COR_TEXTO
except Exception:
    # fallback só pra não quebrar caso ainda não tenha importado as cores
    COR_DESTAQUE = "#FFD770"
    COR_TEXTO = "#FFFFFF"


def tela_inicio(usuario: dict) -> None:
    """
    Tela inicial do BJJ Digital (painel principal).
    Recebe o dicionário `usuario` vindo do core.auth.verificar_sessao().
    """

    # ---------------------------------------------------
    # Função para navegar alterando o menu lateral
    # ---------------------------------------------------
    def navigate_to(page_name: str):
        st.session_state["menu_selection"] = page_name

    # Dados básicos do usuário
    nome = (usuario.get("nome") or "").title()
    faixa = usuario.get("faixa") or "Não definida"
    tipo = (usuario.get("tipo") or "aluno").lower()

    # ---------------------------------------------------
    # HERO / CABEÇALHO
    # ---------------------------------------------------
    col_logo, col_texto = st.columns([1, 3])

    with col_logo:
        logo_path = "assets/logo.png"
        if os.path.exists(logo_path):
            st.image(logo_path, use_container_width=True)
        else:
            st.markdown(
                "<h3 style='color:#FFD770;'>BJJ Digital</h3>",
                unsafe_allow_html=True,
            )

    with col_texto:
        st.markdown(
            f"""
            <div style="
                padding: 18px 22px;
                border-radius: 18px;
                background: linear-gradient(135deg, #0e2d26, #145244);
                border: 1px solid {COR_DESTAQUE};
            ">
                <h2 style="color:{COR_DESTAQUE};margin:0 0 6px 0;">
                    Bem-vinda ao BJJ Digital
                </h2>
                <p style="color:{COR_TEXTO};margin:0;font-size:14px;">
                    {nome}, este é o seu painel para acompanhar treinos, exames e
                    a sua evolução no jiu-jitsu.
                </p>
                <p style="color:{COR_TEXTO};margin-top:10px;font-size:13px;">
                    <strong>Faixa atual:</strong> {faixa}
                    &nbsp;•&nbsp;
                    <strong>Perfil:</strong> {tipo.title()}
                </p>
            </div>
            """,
            unsafe_allow_html=True,
        )

    st.markdown("")

    # ---------------------------------------------------
    # BLOCO: AÇÕES PRINCIPAIS DO ALUNO
    # ---------------------------------------------------
    st.markdown("### 🎯 O que você quer fazer agora?")

    c1, c2, c3 = st.columns(3)

    # ----- Card: Modo Rola -----
    with c1:
        st.markdown(
            f"""
            <div style="
                border-radius:14px;
                border:1px solid {COR_DESTAQUE};
                padding:14px 16px;
                background-color: rgba(17, 56, 48, 0.85);
                min-height: 120px;
            ">
                <h4 style="color:{COR_DESTAQUE};margin-bottom:4px;">
                    Treinar Modo Rola
                </h4>
                <p style="color:{COR_TEXTO};font-size:13px;margin-bottom:8px;">
                    Responda questões aleatórias para aquecer antes do exame
                    e manter o jogo em dia.
                </p>
            </div>
            """,
            unsafe_allow_html=True,
        )
        if st.button("Ir para Modo Rola", key="btn_modo_rola"):
            navigate_to("Modo Rola")

    # ----- Card: Exame de Faixa -----
    with c2:
        st.markdown(
            f"""
            <div style="
                border-radius:14px;
                border:1px solid {COR_DESTAQUE};
                padding:14px 16px;
                background-color: rgba(17, 56, 48, 0.85);
                min-height: 120px;
            ">
                <h4 style="color:{COR_DESTAQUE};margin-bottom:4px;">
                    Exame de Faixa
                </h4>
                <p style="color:{COR_TEXTO};font-size:13px;margin-bottom:8px;">
                    Quando o professor liberar, você faz aqui a prova teórica
                    oficial da sua faixa.
                </p>
            </div>
            """,
            unsafe_allow_html=True,
        )
        if st.button("Ir para Exame", key="btn_exame"):
            navigate_to("Exame de Faixa")

    # ----- Card: Ranking / Histórico -----
    with c3:
        st.markdown(
            f"""
            <div style="
                border-radius:14px;
                border:1px solid {COR_DESTAQUE};
                padding:14px 16px;
                background-color: rgba(17, 56, 48, 0.85);
                min-height: 120px;
            ">
                <h4 style="color:{COR_DESTAQUE};margin-bottom:4px;">
                    Ranking & Histórico
                </h4>
                <p style="color:{COR_TEXTO};font-size:13px;margin-bottom:8px;">
                    Veja seu desempenho, acompanhe sua evolução e compare com
                    as outras pessoas da equipe.
                </p>
            </div>
            """,
            unsafe_allow_html=True,
        )
        if st.button("Ver Ranking", key="btn_ranking"):
            navigate_to("Ranking")

    # ---------------------------------------------------
    # BLOCO: PAINEL DE GESTÃO (PROFESSOR / ADMIN)
    # ---------------------------------------------------
    if tipo in ("professor", "admin"):
        st.markdown("---")
        st.markdown("### 🧩 Painel de gestão")

        g1, g2, g3 = st.columns(3)

        # ----- Gestão de Questões -----
        with g1:
            st.markdown(
                f"""
                <div style="
                    border-radius:14px;
                    border:1px solid {COR_DESTAQUE};
                    padding:14px 16px;
                    background-color: rgba(17, 56, 48, 0.85);
                    min-height: 120px;
                ">
                    <h4 style="color:{COR_DESTAQUE};margin-bottom:4px;">
                        Banco de Questões
                    </h4>
                    <p style="color:{COR_TEXTO};font-size:13px;margin-bottom:8px;">
                        Cadastre, edite e organize as questões por faixa e tema
                        para os exames e treinos.
                    </p>
                </div>
                """,
                unsafe_allow_html=True,
            )
            if st.button("Gestão de Questões", key="btn_g_questoes"):
                navigate_to("Gestão de Questões")

        # ----- Gestão de Equipes -----
        with g2:
            st.markdown(
                f"""
                <div style="
                    border-radius:14px;
                    border:1px solid {COR_DESTAQUE};
                    padding:14px 16px;
                    background-color: rgba(17, 56, 48, 0.85);
                    min-height: 120px;
                ">
                    <h4 style="color:{COR_DESTAQUE};margin-bottom:4px;">
                        Equipes & Turmas
                    </h4>
                    <p style="color:{COR_TEXTO};font-size:13px;margin-bottom:8px;">
                        Organize turmas, vincule alunos aos professores e
                        acompanhe a evolução de cada grupo.
                    </p>
                </div>
                """,
                unsafe_allow_html=True,
            )
            if st.button("Gestão de Equipes", key="btn_g_equipes"):
                navigate_to("Gestão de Equipes")

        # ----- Exames / Painel do Professor -----
        with g3:
            label = "Gestão de Exames" if tipo == "admin" else "Painel do Professor"
            destino = "Gestão de Exames" if tipo == "admin" else "Painel do Professor"

            st.markdown(
                f"""
                <div style="
                    border-radius:14px;
                    border:1px solid {COR_DESTAQUE};
                    padding:14px 16px;
                    background-color: rgba(17, 56, 48, 0.85);
                    min-height: 120px;
                ">
                    <h4 style="color:{COR_DESTAQUE};margin-bottom:4px;">
                        Exames & Resultados
                    </h4>
                    <p style="color:{COR_TEXTO};font-size:13px;margin-bottom:8px;">
                        Acompanhe exames aplicados, notas, aprovações e emissão
                        de certificados.
                    </p>
                </div>
                """,
                unsafe_allow_html=True,
            )
            if st.button(label, key="btn_g_exames"):
                navigate_to(destino)
