# bjj_digital/views/cursos.py

import streamlit as st
from typing import Optional, Dict, List

# Ajuste os imports conforme a estrutura do seu projeto
from courses_engine import (
    criar_curso,
    listar_cursos_do_professor,
    listar_cursos_disponiveis_para_usuario,
    inscrever_usuario_em_curso,
    obter_inscricao,
)
from database import get_db

# ======================================================
# PÁGINA PRINCIPAL
# ======================================================

def pagina_cursos(usuario: dict):
    """
    Interface de cursos, adaptada ao tipo de usuário.
    """
    tipo = str(usuario.get("tipo", "aluno")).lower()

    # Cabeçalho unificado com espaçamento
    c1, c2 = st.columns([0.8, 0.2])
    with c1:
        st.title("📚 Gestão de Cursos")
    with c2:
        # Exibe o tipo de usuário de forma discreta
        st.caption(f"Perfil: {tipo.capitalize()}")

    st.divider()

    if tipo in ["admin", "professor"]:
        _interface_professor(usuario)
    else:
        _interface_aluno(usuario)


# ======================================================
# VISÃO DO PROFESSOR / ADMIN
# ======================================================

def _interface_professor(usuario: dict):
    tab1, tab2 = st.tabs(["📘 Gerenciar Cursos", "➕ Criar Novo Curso"])

    with tab1:
        _prof_listar_cursos(usuario)

    with tab2:
        _prof_criar_curso(usuario)


def _prof_listar_cursos(usuario: dict):
    cursos = listar_cursos_do_professor(usuario["id"])

    if not cursos:
        st.info("Você ainda não criou nenhum curso. Vá na aba 'Criar Novo Curso' para começar.")
        return

    # Filtros rápidos
    filtro_status = st.radio(
        "Filtrar por:", ["Todos", "Ativos", "Inativos"],
        horizontal=True,
        label_visibility="collapsed"
    )
    st.write("")

    for curso in cursos:
        ativo = curso.get("ativo", True)
        
        if filtro_status == "Ativos" and not ativo: continue
        if filtro_status == "Inativos" and ativo: continue

        with st.container(border=True):
            col_info, col_stats, col_actions = st.columns([3, 1.5, 1])

            with col_info:
                status_icon = "🟢" if ativo else "🔴"
                st.subheader(f"{status_icon} {curso.get('titulo')}")
                
                desc = (curso.get("descricao") or "").strip()
                if desc:
                    st.caption(f"{desc[:140]}{'...' if len(desc)>140 else ''}")
                
                # --- VISUAL NOVO DAS TAGS (BADGES) ---
                mod_texto = curso.get('modalidade', '-')
                pub_texto = 'Equipe' if curso.get('publico') == 'equipe' else 'Geral'
                
                # Cores inspiradas em UI moderna (Dark Mode friendly)
                # Modalidade: Tom de roxo/indigo | Público: Tom de azul/teal
                html_badges = f"""
                <div style="display: flex; gap: 8px; margin-top: 8px;">
                    <span style="background-color: #2e1065; color: #d8b4fe; padding: 4px 10px; border-radius: 12px; font-size: 0.8rem; font-weight: 600; border: 1px solid #581c87;">
                        🎓 {mod_texto}
                    </span>
                    <span style="background-color: #064e3b; color: #6ee7b7; padding: 4px 10px; border-radius: 12px; font-size: 0.8rem; font-weight: 600; border: 1px solid #065f46;">
                        👥 {pub_texto}
                    </span>
                </div>
                """
                st.markdown(html_badges, unsafe_allow_html=True)
                # -------------------------------------

            with col_stats:
                preco = curso.get('preco', 0.0)
                split = int(curso.get('split_custom', 10))
                
                if curso.get("pago"):
                    st.metric("Preço", f"R$ {preco:.2f}", delta=f"Taxa App: {split}%", delta_color="inverse")
                else:
                    st.metric("Preço", "Gratuito", delta="Taxa Isenta")

            with col_actions:
                st.write("") 
                
                # ATENÇÃO: Agora passamos 'usuario' para o modal verificar se é admin
                if st.button("✏️ Editar", key=f"btn_edit_{curso['id']}", use_container_width=True):
                    _dialogo_editar_curso(curso, usuario)

                label_btn = "Desativar" if ativo else "Ativar"
                type_btn = "primary" if not ativo else "secondary"
                
                if st.button(label_btn, key=f"toggle_{curso['id']}", type=type_btn, use_container_width=True):
                    _toggle_status_curso(curso["id"], not ativo)
                    st.rerun()


def _prof_criar_curso(usuario: dict):
    st.markdown("### Preencha os detalhes do novo curso")
    
    # Verifica permissão
    is_admin = usuario.get("tipo") == "admin"

    with st.form("form_criar_curso", border=True):
        col1, col2 = st.columns([2, 1])

        with col1:
            titulo = st.text_input("Título do Curso", placeholder="Ex: Jiu-Jitsu para Iniciantes")
            descricao = st.text_area("Descrição Detalhada", height=150)

        with col2:
            modalidade = st.selectbox("Modalidade", ["EAD", "Presencial"])
            publico = st.selectbox(
                "Público Alvo", ["geral", "equipe"],
                format_func=lambda v: "Aberto (Geral)" if v == "geral" else "Restrito (Equipe)"
            )
            
            equipe_destino = None
            if publico == "equipe":
                equipe_destino = st.text_input("Nome/ID da Equipe")

            certificado_auto = st.checkbox("Certificado Automático?", value=True)

        st.divider()
        
        c_fin1, c_fin2, c_fin3 = st.columns(3)
        with c_fin1:
            pago = st.toggle("Curso Pago?", value=False)
        
        with c_fin2:
            preco = st.number_input("Preço (R$)", min_value=0.0, step=10.0, disabled=not pago)
        
        with c_fin3:
            # TRAVA DE SEGURANÇA: Só Admin mexe aqui
            help_text = "Definido pelo Administrador" if not is_admin else "Percentual retido pelo App"
            
            split_custom = st.slider(
                "Split (%)", 0, 100, 
                value=10, 
                disabled=(not pago or not is_admin), # Desabilitado se não for pago OU não for admin
                help=help_text
            )

        submit_btn = st.form_submit_button("🚀 Criar Curso", use_container_width=True, type="primary")

    if submit_btn:
        # (Lógica de salvamento permanece igual...)
        if not titulo.strip():
            st.error("⚠️ O título é obrigatório.")
            return
        try:
            criar_curso(
                professor_id=usuario["id"],
                nome_professor=usuario.get("nome", ""),
                titulo=titulo,
                descricao=descricao,
                modalidade=modalidade,
                publico=publico,
                equipe_destino=equipe_destino,
                pago=pago,
                preco=preco if pago else 0.0,
                split_custom=split_custom,
                certificado_automatico=certificado_auto
            )
            st.success("Curso criado com sucesso!")
            st.rerun()
        except Exception as e:
            st.error(f"Erro: {e}")


# ======================================================
# MODAL NATIVO (st.dialog) - Streamlit 1.34+
# ======================================================

@st.dialog("✏️ Editar Curso")
def _dialogo_editar_curso(curso: dict, usuario: dict):
    # Verifica permissão
    is_admin = usuario.get("tipo") == "admin"

    with st.form("form_edit_course_dialog"):
        titulo = st.text_input("Título", value=curso.get("titulo", ""))
        descricao = st.text_area("Descrição", value=curso.get("descricao", ""), height=120)

        c1, c2 = st.columns(2)
        with c1:
            modalidade = st.selectbox(
                "Modalidade", ["EAD", "Presencial"],
                index=0 if curso.get("modalidade") == "EAD" else 1
            )
            publico = st.selectbox(
                "Público", ["geral", "equipe"],
                index=0 if curso.get("publico") == "geral" else 1
            )
        with c2:
            pago = st.checkbox("Pago?", value=curso.get("pago", False))
            preco = st.number_input(
                "Valor (R$)", 
                value=float(curso.get("preco", 0.0)),
                disabled=not pago
            )

        equipe_destino = curso.get("equipe_destino", "")
        if publico == "equipe":
            equipe_destino = st.text_input("Equipe de Destino", value=equipe_destino or "")
        
        st.divider()
        
        c3, c4 = st.columns(2)
        with c3:
             certificado_auto = st.checkbox("Certificado Auto.", value=curso.get("certificado_automatico", True))
        with c4:
             # Lógica de bloqueio do Admin
             valor_atual_split = int(curso.get("split_custom", 10))
             
             split_custom = st.slider(
                 "Split App %", 0, 100, 
                 value=valor_atual_split,
                 disabled=not is_admin,  # Se não for admin, fica cinza/travado
                 help="Somente administradores podem alterar a taxa." if not is_admin else ""
             )

        submitted = st.form_submit_button("💾 Salvar Alterações", type="primary", use_container_width=True)

    if submitted:
        try:
            _salvar_edicao_curso(
                curso_id=curso["id"],
                titulo=titulo,
                descricao=descricao,
                modalidade=modalidade,
                publico=publico,
                equipe_destino=equipe_destino,
                pago=pago,
                preco=preco,
                split_custom=split_custom,
                certificado_automatico=certificado_auto
            )
            st.success("Curso atualizado!")
            st.rerun()
        except Exception as e:
            st.error(f"Erro ao salvar: {e}")

# ======================================================
# VISÃO DO ALUNO
# ======================================================

def _interface_aluno(usuario: dict):
    # Uso de abas com ícones para melhor navegação
    tab_disp, tab_meus = st.tabs(["🛒 Disponíveis", "🎓 Meus Cursos"])

    with tab_disp:
        _aluno_cursos_disponiveis(usuario)

    with tab_meus:
        _aluno_meus_cursos(usuario)


def _aluno_cursos_disponiveis(usuario: dict):
    cursos = listar_cursos_disponiveis_para_usuario(usuario)

    if not cursos:
        st.warning("Nenhum curso novo disponível para seu perfil no momento.")
        return

    # Grid responsivo de cursos
    col1, col2 = st.columns(2) 
    
    for idx, curso in enumerate(cursos):
        inscricao = obter_inscricao(usuario["id"], curso["id"])
        
        # Alterna colunas para criar grid
        with (col1 if idx % 2 == 0 else col2):
            with st.container(border=True):
                st.markdown(f"#### {curso.get('titulo')}")
                
                # Badges
                bagde_mod = f"📍 {curso.get('modalidade')}"
                badge_price = f"R$ {curso.get('preco', 0.0):.2f}" if curso.get('pago') else "🆓 Gratuito"
                st.caption(f"{bagde_mod}  •  {badge_price}")

                st.markdown("---")
                
                desc = (curso.get("descricao") or "").strip()
                if desc:
                    st.write(f"{desc[:100]}...")

                if inscricao:
                    st.button("✅ Inscrito", key=f"btn_ja_inscrito_{curso['id']}", disabled=True, use_container_width=True)
                else:
                    if st.button(f"Inscrever-se", key=f"btn_inscrever_{curso['id']}", type="primary", use_container_width=True):
                        inscrever_usuario_em_curso(usuario["id"], curso["id"])
                        st.success("Inscrição realizada!")
                        st.rerun()


def _aluno_meus_cursos(usuario: dict):
    db = get_db()
    if not db:
        st.error("Erro de conexão com banco.")
        return

    # Otimização: Trazendo apenas os campos necessários se possível
    q = db.collection("enrollments").where("user_id", "==", usuario["id"]).stream()
    inscricoes = list(q)

    if not inscricoes:
        st.info("Você ainda não está matriculado em nenhum curso.")
        return

    for ins in inscricoes:
        d = ins.to_dict()
        curso_id = d.get("course_id")

        # Buscar dados do curso
        # (Idealmente isso seria feito em batch ou query otimizada, mas mantendo simples:)
        snap = db.collection("courses").document(curso_id).get()
        if not snap.exists:
            continue

        curso = snap.to_dict()
        progresso = float(d.get("progresso", 0))

        with st.container(border=True):
            c_img, c_data, c_act = st.columns([0.5, 2, 1])
            
            # Simulando um ícone/thumbnail na c_img
            with c_img:
                st.markdown("<div style='font-size:3rem; text-align:center;'>🥋</div>", unsafe_allow_html=True)

            with c_data:
                st.subheader(curso.get('titulo'))
                # Barra de progresso nativa
                st.progress(progresso / 100, text=f"Progresso: {int(progresso)}%")
                
                if curso.get("pago") and not d.get("pago"):
                    st.warning("⚠️ Pagamento pendente")

            with c_act:
                st.write("")
                st.write("")
                st.button("▶️ Acessar Aulas", key=f"go_course_{curso_id}", use_container_width=True)


# ======================================================
# FUNÇÕES AUXILIARES DE BANCO
# ======================================================

def _salvar_edicao_curso(
    curso_id: str,
    titulo: str,
    descricao: str,
    modalidade: str,
    publico: str,
    equipe_destino: Optional[str],
    pago: bool,
    preco: Optional[float],
    split_custom: Optional[int],
    certificado_automatico: bool
):
    """Atualiza o documento do curso no Firestore."""
    db = get_db()
    
    # Validações básicas
    safe_preco = float(preco) if (pago and preco is not None) else 0.0
    safe_split = int(split_custom) if split_custom is not None else 10

    doc_updates = {
        "titulo": titulo.strip(),
        "descricao": descricao.strip(),
        "modalidade": modalidade,
        "publico": publico,
        "equipe_destino": equipe_destino or None,
        "pago": bool(pago),
        "preco": safe_preco,
        "split_custom": safe_split,
        "certificado_automatico": bool(certificado_automatico),
    }
    
    db.collection("courses").document(curso_id).update(doc_updates)


def _toggle_status_curso(curso_id: str, novo_ativo: bool):
    """Ativa ou desativa o curso."""
    db = get_db()
    db.collection("courses").document(curso_id).update({
        "ativo": bool(novo_ativo),
        # Mantendo 'status' redundante caso seu sistema legado use string
        "status": "ativo" if novo_ativo else "inativo"
    })
