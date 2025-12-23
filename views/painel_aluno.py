import streamlit as st
import time
import utils as ce
import views.aulas_aluno as aulas_view

# ==================================================
# 🎨 ESTILOS CSS PERSONALIZADOS
# ==================================================
def aplicar_estilos_cards():
    st.markdown("""
    <style>
        div[data-testid="stContainer"] {
            background-color: rgba(14, 45, 38, 0.7);
            border: 1px solid rgba(255, 215, 112, 0.2);
            border-radius: 12px;
            padding: 20px;
            transition: all 0.3s ease-in-out;
        }
        div[data-testid="stContainer"]:hover {
            transform: translateY(-5px);
            border-color: #FFD770;
            box-shadow: 0 10px 20px rgba(0,0,0,0.4);
            background-color: rgba(14, 45, 38, 0.95);
        }
        .card-title {
            color: #FFD770 !important;
            font-size: 1.1rem;
            font-weight: 700;
            margin-bottom: 0.5rem;
            min-height: 50px;
        }
        .stTabs [data-baseweb="tab-list"] { gap: 10px; background-color: transparent; }
        .stTabs [data-baseweb="tab"] {
            background-color: rgba(255,255,255,0.05);
            border-radius: 8px; padding: 10px 20px; color: white;
        }
        .stTabs [aria-selected="true"] {
            background-color: #FFD770 !important; color: #0e2d26 !important; font-weight: bold;
        }
    </style>
    """, unsafe_allow_html=True)

# ==================================================
# 💰 DIÁLOGO DE CHECKOUT (CORRIGIDO)
# ==================================================
@st.dialog("🛒 Checkout Seguro")
def dialog_pagamento(curso, usuario):
    st.markdown(f"### {curso.get('titulo')}")
    valor = float(curso.get('preco', 0))
    st.markdown(f"## Total: R$ {valor:.2f}")
    
    st.divider()

    if "mp_preference_id" not in st.session_state:
        st.session_state.mp_preference_id = None
        st.session_state.mp_link = None

    if not st.session_state.mp_preference_id:
        with st.spinner("Conectando ao Mercado Pago..."):
            link, pref_id = ce.gerar_preferencia_pagamento(curso, usuario)
            if link:
                st.session_state.mp_link = link
                st.session_state.mp_preference_id = pref_id
            else:
                st.error("Erro ao conectar com o banco.")
                return

    if st.session_state.mp_link:
        st.success("Link de pagamento gerado!")
        
        # --- AVISO IMPORTANTE PARA O ALUNO ---
        st.info("""
        📝 **Como pagar sem logar:**
        1. Clique no botão abaixo.
        2. Na tela do Mercado Pago, escolha a opção **"Pagar como convidado"** ou **"Novo Cartão"** (geralmente no final da tela).
        3. Você **NÃO** precisa criar conta para pagar com Pix ou Cartão.
        """)
        # -------------------------------------
        
        st.link_button("👉 Ir para Pagamento (Pix/Cartão)", st.session_state.mp_link, type="primary", use_container_width=True)
        
        st.markdown("---")
        st.write("Após pagar, clique abaixo:")
        
        if st.button("🔄 Confirmar Pagamento", use_container_width=True):
            with st.spinner("Verificando..."):
                time.sleep(1)
                aprovado, msg = ce.verificar_status_pagamento_mp(st.session_state.mp_preference_id)
                
                if aprovado:
                    ok_db, msg_db = ce.processar_compra_curso(usuario['id'], curso['id'], valor)
                    if ok_db:
                        st.balloons()
                        st.success("Sucesso! Curso liberado.")
                        st.session_state.mp_preference_id = None
                        st.session_state.mp_link = None
                        time.sleep(3)
                        st.rerun()
                    else:
                        st.error(f"Erro no sistema: {msg_db}")
                else:
                    st.warning(f"Status: {msg}")
# ==================================================
# 🧱 GRID DE CURSOS
# ==================================================
def renderizar_grid_cursos(cursos, usuario, tipo_lista="meus"):
    if not cursos:
        msg = "Você não está inscrito em nenhum curso." if tipo_lista == "meus" else "Nenhum curso novo disponível."
        st.info(msg)
        return

    colunas_grid = st.columns(3)
    
    for index, curso in enumerate(cursos):
        coluna_atual = colunas_grid[index % 3]
        
        with coluna_atual:
            with st.container(border=True):
                st.markdown(f"<div style='font-size: 2rem; margin-bottom: 10px;'>🥋</div>", unsafe_allow_html=True)
                
                titulo = curso.get('titulo', 'Sem Título')
                desc = curso.get('descricao', '') or ''
                if len(desc) > 80: desc = desc[:80] + "..."
                
                st.markdown(f"<div class='card-title'>{titulo}</div>", unsafe_allow_html=True)
                st.caption(desc)
                st.write("") 
                
                if tipo_lista == "meus":
                    progresso = curso.get('progresso', 0)
                    st.progress(progresso / 100)
                    st.caption(f"{progresso}% Concluído")
                    
                    if st.button("▶ Continuar", key=f"go_{curso['id']}", use_container_width=True):
                        st.session_state["curso_aluno_selecionado"] = curso
                        st.session_state["view_aluno"] = "aulas"
                        st.rerun()
                        
                else: # NOVOS CURSOS
                    info = []
                    if curso.get('duracao_estimada'): info.append(f"⏱ {curso['duracao_estimada']}")
                    if curso.get('nivel'): info.append(f"📊 {curso['nivel']}")
                    st.caption(" • ".join(info))
                    
                    pago = curso.get('pago', False)
                    preco = float(curso.get('preco', 0))
                    
                    lbl_btn = "Inscrever-se"
                    if pago and preco > 0:
                        lbl_btn = f"Comprar (R$ {preco:.2f})"
                        
                    if st.button(lbl_btn, key=f"buy_{curso['id']}", type="primary", use_container_width=True):
                        if pago and preco > 0:
                            # LIMPEZA DE SEGURANÇA
                            if "mp_preference_id" in st.session_state:
                                del st.session_state["mp_preference_id"]
                            if "mp_link" in st.session_state:
                                del st.session_state["mp_link"]
                                
                            dialog_pagamento(curso, usuario)
                        else:
                            # Inscrição Gratuita
                            with st.spinner("Realizando matrícula..."):
                                ce.inscrever_usuario_em_curso(usuario["id"], curso["id"])
                                st.balloons()
                                st.success(f"Inscrição realizada! O curso foi movido para a aba 'Matriculados'.")
                                time.sleep(2.5)
                                st.rerun()

# ==================================================
# 🚀 FUNÇÃO PRINCIPAL
# ==================================================
def render_painel_aluno(usuario):
    aplicar_estilos_cards()

    # Roteamento para Player
    if st.session_state.get("view_aluno") == "aulas" and st.session_state.get("curso_aluno_selecionado"):
        c1, c2 = st.columns([1, 5])
        with c1:
            if st.button("⬅️ Voltar", use_container_width=True):
                st.session_state["view_aluno"] = "lista"
                st.session_state["curso_aluno_selecionado"] = None
                st.rerun()
        st.divider()
        aulas_view.pagina_aulas_aluno(st.session_state["curso_aluno_selecionado"], usuario)
        return

    # Cabeçalho
    col_texto, col_botao = st.columns([4, 1])
    with col_texto:
        st.markdown(f"""
        <div>
            <h2 style='text-align: left; color: #FFD770; margin-bottom: 0;'>📚 Meus Cursos</h2>
            <p style='color: #ccc; margin-top: 5px;'>Bem-vindo de volta, <b>{usuario.get('nome').split()[0]}</b>.</p>
        </div>
        """, unsafe_allow_html=True)
    with col_botao:
        st.write("") 
        if st.button("🏠 Voltar ao Início", use_container_width=True):
            st.session_state.menu_selection = "Início"
            st.rerun()
    
    st.write("") 

    # Abas
    tab_meus, tab_novos = st.tabs(["📚 Meus Cursos", "🚀 Catálogo de Cursos"])

    with tab_meus:
        cursos = ce.listar_cursos_inscritos(usuario["id"])
        renderizar_grid_cursos(cursos, usuario, tipo_lista="meus")

    with tab_novos:
        novos = ce.listar_cursos_disponiveis_para_aluno(usuario)
        renderizar_grid_cursos(novos, usuario, tipo_lista="novos")
