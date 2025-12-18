import streamlit as st
import time
from typing import Dict
import utils as ce 

# Configuração de Cores
try:
    from config import COR_FUNDO, COR_TEXTO, COR_DESTAQUE, COR_BOTAO, COR_HOVER
except ImportError:
    COR_FUNDO, COR_TEXTO, COR_DESTAQUE, COR_BOTAO, COR_HOVER = (
        "#0e2d26", "#FFFFFF", "#FFD770", "#078B6C", "#FFD770"
    )

# ======================================================
# ESTILOS
# ======================================================
def aplicar_estilos_aulas():
    css = """
    <style>
    .streamlit-expanderHeader {{
        background-color: #163E33 !important;
        border: 1px solid rgba(255, 215, 112, 0.2) !important;
        border-radius: 8px !important;
        color: {cor_destaque} !important;
        font-size: 1.1rem !important;
        font-weight: 600 !important;
    }}
    .aula-strip {{
        background: rgba(255, 255, 255, 0.03);
        border-left: 4px solid {cor_botao};
        padding: 12px 15px;
        margin-bottom: 8px;
        border-radius: 0 6px 6px 0;
        display: flex; align-items: center; justify-content: space-between;
    }}
    .badge-tipo {{
        font-size: 0.75rem; padding: 4px 8px; border-radius: 12px;
        font-weight: bold; text-transform: uppercase; margin-right: 10px;
        min-width: 60px; text-align: center;
    }}
    .badge-misto {{ background: rgba(255,215,112,0.2); color:#FFD770; border:1px solid #FFD770; }}
    .badge-video {{ background: rgba(52,152,219,0.2); color:#3498db; border:1px solid #3498db; }}
    .badge-imagem {{ background: rgba(155,89,182,0.2); color:#9b59b6; border:1px solid #9b59b6; }}
    .badge-texto {{ background: rgba(46,204,113,0.2); color:#2ecc71; border:1px solid #2ecc71; }}
    </style>
    """.format(cor_destaque=COR_DESTAQUE, cor_botao=COR_BOTAO)

    st.markdown(css, unsafe_allow_html=True)

# ======================================================
# GERENCIADOR DE CONTEÚDO
# ======================================================
def gerenciar_conteudo_curso(curso: Dict, usuario: Dict):
    aplicar_estilos_aulas()

    try:
        modulos = ce.listar_modulos_e_aulas(curso["id"]) or []
    except Exception:
        modulos = []

    total_aulas = sum(len(m.get("aulas", [])) for m in modulos)

    # Header
    c1, c2, c3 = st.columns([1, 4, 2])
    with c1:
        if st.button("⬅ Voltar", use_container_width=True):
            st.session_state["cursos_view"] = "detalhe"
            st.rerun()
    with c2:
        st.subheader(f"Conteúdo: {curso.get('titulo','Curso')}")
    with c3:
        st.markdown(
            f"""
            <div style="text-align:right; font-size:0.9rem; color:#aaa;">
                📦 Módulos: <b style="color:{COR_DESTAQUE}">{len(modulos)}</b> |
                🎬 Aulas: <b style="color:{COR_DESTAQUE}">{total_aulas}</b>
            </div>
            """,
            unsafe_allow_html=True,
        )

    st.markdown("---")
    # ============================
    # PROGRESSO DO ALUNO (V2)
    # ============================
    try:
        prog = ce.obter_progresso_curso(usuario.get("id"), curso.get("id"))
        progresso_pct = prog.get("progresso_percentual", 0)
        st.progress(progresso_pct / 100)
        st.caption(f"Progresso no curso: {progresso_pct}%")
    except Exception as e:
        print(f"[PROGRESSO_UI] erro: {e}")
        
    # ======================================================
    # CRIAR MÓDULO
    # ======================================================
    with st.expander("✨ Criar Novo Módulo"):
        with st.form("new_mod_form", clear_on_submit=True):
            t_mod = st.text_input("Nome do Módulo")
            d_mod = st.text_area("Descrição")

            if st.form_submit_button("🚀 Criar Módulo", type="primary"):
                if t_mod:
                    ce.criar_modulo(curso["id"], t_mod, d_mod, len(modulos) + 1)
                    st.toast("Módulo criado!", icon="✅")
                    time.sleep(1)
                    st.rerun()
                else:
                    st.warning("Título obrigatório.")

    if not modulos:
        st.info("Comece criando o primeiro módulo.")
        return

    st.markdown("### 📚 Grade Curricular")

    # ======================================================
    # LISTAGEM DE MÓDULOS
    # ======================================================
    for i, mod in enumerate(modulos):
        mod_id = str(mod.get("id"))
        mod_titulo = mod.get("titulo", "Sem título")
        aulas = mod.get("aulas", [])

        with st.expander(f"{i+1}. {mod_titulo} ({len(aulas)} aulas)"):
            for aula in aulas:
                tp = aula.get("tipo", "texto")
                titulo_aula = aula.get("titulo", "Sem título")
                dur = aula.get("duracao_min", 0)

                badge = {
                    "misto": ("✨", "badge-misto", "FLEX"),
                    "video": ("🎥", "badge-video", "VÍDEO"),
                    "imagem": ("🖼️", "badge-imagem", "IMG"),
                    "texto": ("📝", "badge-texto", "TEXTO"),
                }.get(tp, ("📝", "badge-texto", "TEXTO"))

                st.markdown(
                    f"""
                    <div class="aula-strip">
                        <div>
                            <span class="badge-tipo {badge[1]}">{badge[2]}</span>
                            {titulo_aula}
                        </div>
                        <div style="font-size:0.8rem; color:#aaa;">⏱ {dur} min</div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )

            # ======================================================
            # ADICIONAR AULA
            # ======================================================
            if st.checkbox(f"➕ Adicionar Aula em '{mod_titulo}'", key=f"chk_{mod_id}"):
                with st.container(border=True):
                    tit_aula = st.text_input("Título da Aula", key=f"tit_{mod_id}")
                    tipo_aula = st.selectbox(
                        "Tipo",
                        ["misto", "video", "imagem", "texto"],
                        key=f"tipo_{mod_id}",
                    )
                    dur_aula = st.number_input(
                        "Duração (min)",
                        1,
                        180,
                        10,
                        key=f"dur_{mod_id}",
                    )

                    conteudo = {}
                    blocos_para_salvar = []

                    # === MODO MISTO ===
                    if tipo_aula == "misto":
                        key_blocos = f"blocos_{mod_id}"
                        if key_blocos not in st.session_state:
                            st.session_state[key_blocos] = []

                        b1, b2, b3 = st.columns(3)
                        if b1.button("📝 Texto", key=f"bt_txt_{mod_id}"):
                            st.session_state[key_blocos].append({"tipo": "texto"})
                        if b2.button("🖼️ Imagem", key=f"bt_img_{mod_id}"):
                            st.session_state[key_blocos].append({"tipo": "imagem"})
                        if b3.button("🎥 Vídeo", key=f"bt_vid_{mod_id}"):
                            st.session_state[key_blocos].append({"tipo": "video"})

                        for idx, bloco in enumerate(st.session_state[key_blocos]):
                            if bloco["tipo"] == "texto":
                                txt = st.text_area(
                                    "Texto",
                                    key=f"txt_{mod_id}_{idx}",
                                )
                                blocos_para_salvar.append(
                                    {"tipo": "texto", "conteudo": txt}
                                )
                            elif bloco["tipo"] == "imagem":
                                arq = st.file_uploader(
                                    "Imagem",
                                    type=["jpg", "png"],
                                    key=f"img_{mod_id}_{idx}",
                                )
                                blocos_para_salvar.append(
                                    {"tipo": "imagem", "arquivo": arq}
                                )
                            elif bloco["tipo"] == "video":
                                lnk = st.text_input(
                                    "Link do vídeo",
                                    key=f"vid_{mod_id}_{idx}",
                                )
                                blocos_para_salvar.append(
                                    {"tipo": "video", "url_link": lnk}
                                )

                    # === MODOS SIMPLES ===
                    elif tipo_aula == "texto":
                        conteudo["texto"] = st.text_area("Texto")

                    elif tipo_aula == "video":
                        conteudo["url"] = st.text_input("Link do vídeo")

                    elif tipo_aula == "imagem":
                        conteudo["url"] = st.text_input("Link da imagem")

                    # ======================================================
                    # SALVAR AULA (LEGADO + V2)
                    # ======================================================
                    if st.button("💾 Salvar Aula", type="primary", use_container_width=True):
                        # --- LEGADO ---
                        if tipo_aula == "misto":
                            ce.criar_aula_mista(
                                mod_id,
                                tit_aula,
                                blocos_para_salvar,
                                dur_aula,
                            )
                        else:
                            ce.criar_aula(
                                mod_id,
                                tit_aula,
                                tipo_aula,
                                conteudo,
                                dur_aula,
                            )

                        # --- V2 ---
                        try:
                            blocos_v2 = (
                                blocos_para_salvar
                                if tipo_aula == "misto"
                                else (
                                    [{"tipo": "texto", "conteudo": conteudo.get("texto", "")}]
                                    if tipo_aula == "texto"
                                    else [{"tipo": tipo_aula, "url_link": conteudo.get("url")}]
                                )
                            )

                            ce.criar_aula_v2(
                                curso_id=curso["id"],
                                modulo_id=mod_id,
                                titulo=tit_aula,
                                tipo=tipo_aula,
                                blocos=blocos_v2,
                                duracao_min=dur_aula,
                                autor_id=usuario.get("id"),
                                autor_nome=usuario.get("nome"),
                            )
                        except Exception as e:
                            print(f"[AULAS_V2] erro: {e}")

                        st.toast("Aula salva!", icon="💾")
                        time.sleep(1)
                        st.rerun()


def pagina_aulas(usuario: dict):
    st.warning("Acesse via Gerenciador de Cursos.")
