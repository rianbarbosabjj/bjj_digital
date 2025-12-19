import streamlit as st
import time
import pandas as pd
from datetime import datetime
import utils as ce
from views import aulas_professor as aulas_view
import re

try:
    from config import COR_FUNDO, COR_TEXTO, COR_DESTAQUE, COR_BOTAO, COR_HOVER
except ImportError:
    COR_FUNDO, COR_TEXTO, COR_DESTAQUE, COR_BOTAO, COR_HOVER = "#0e2d26", "#FFFFFF", "#FFD770", "#078B6C", "#FFD770"

def pagina_cursos_professor(usuario):
    st.title("📚 Gestão de Cursos (Professor)")

    # =========================
    # CONTROLE DE ESTADO
    # =========================
    if 'cursos_view' not in st.session_state:
        st.session_state['cursos_view'] = 'lista'

    if 'curso_selecionado' not in st.session_state:
        st.session_state['curso_selecionado'] = None

    if 'editando_curso' not in st.session_state:
        st.session_state['editando_curso'] = False

    # =========================
    # ROTEAMENTO DE TELAS (SEGURO)
    # =========================
    view = st.session_state['cursos_view']

    if view == 'conteudo':
        curso = st.session_state.get('curso_selecionado')
        if curso:
            try:
                aulas_view.gerenciar_conteudo_curso(curso, usuario)
            except Exception as e:
                st.error("Erro ao carregar o gerenciador de aulas.")
                st.caption(str(e))
                st.session_state['cursos_view'] = 'lista'
                st.rerun()
        else:
            st.session_state['cursos_view'] = 'lista'
            st.rerun()
        return

    if view == 'detalhe':
        if st.session_state.get('curso_selecionado'):
            exibir_detalhes_curso(usuario)
        else:
            st.session_state['cursos_view'] = 'lista'
            st.rerun()
        return

    # PADRÃO
    listar_cursos(usuario)


def listar_cursos(usuario):
    st.subheader("Meus Cursos")
    
    # --- FORMULÁRIO DE CRIAÇÃO ---
    if usuario.get('tipo') in ['admin', 'professor', 'mestre']:
        with st.expander("Novo Curso"):
            with st.form("form_curso"):
                titulo = st.text_input("Título")
                desc = st.text_area("Descrição")
                
                c1, c2 = st.columns(2)
                modalidade = c1.selectbox("Modalidade", ["EAD", "Presencial", "Híbrido"])
                publico_sel = c2.selectbox("Público Alvo", ["Aberto a Todos", "Restrito à Minha Equipe"])
                
                st.markdown("---")
                st.markdown("###### Gestão Compartilhada (Opcional)")
                st.caption("Digite os CPFs dos professores auxiliares (um por linha):")
                cpfs_input = st.text_area("CPFs dos Editores", height=68, placeholder="Ex: 111.222.333-44")
                
                st.markdown("---")
                preco = st.number_input("Preço (R$)", 0.0, step=10.0)
                
                if st.form_submit_button("Criar Curso"):
                    ids_editores = []
                    if cpfs_input:
                        lista_cpfs_raw = re.split(r'[,\n]', cpfs_input)
                        for cpf_raw in lista_cpfs_raw:
                            cpf_limpo = cpf_raw.strip()
                            if cpf_limpo:
                                user_encontrado = ce.buscar_usuario_por_cpf(cpf_limpo)
                                if user_encontrado and user_encontrado['id'] != usuario['id']:
                                    ids_editores.append(user_encontrado['id'])
                    
                    publico_val = 'equipe' if "Restrito" in publico_sel else 'todos'
                    equipe_dest = usuario.get('equipe', '') if publico_val == 'equipe' else ''
                    
                    ce.criar_curso(
                        usuario['id'], usuario['nome'], usuario.get('equipe',''), titulo, desc, 
                        modalidade, publico_val, equipe_dest, True, preco, 
                        False, False, 10, 'iniciante', editores_ids=ids_editores
                    )
                    st.success("Curso criado com sucesso!")
                    time.sleep(1)
                    st.rerun()
    
    st.markdown("---")
    
    # --- LISTAGEM COM RENDIMENTO ---
    cursos = ce.listar_cursos_do_professor(usuario['id'])
    
    if not cursos:
        st.info("Nenhum curso encontrado.")
        return

    # Estilo para os cards
    st.markdown(f"""
    <style>
    .metric-card {{
        background: rgba(255,255,255,0.05); border-radius: 6px; padding: 5px 10px;
        text-align: center; border: 1px solid rgba(255,255,255,0.1);
    }}
    .metric-value {{ font-weight: bold; color: {COR_DESTAQUE}; font-size: 1rem; }}
    .metric-label {{ font-size: 0.75rem; color: #aaa; text-transform: uppercase; }}
    </style>
    """, unsafe_allow_html=True)

    for c in cursos:
        # Busca inscritos para calcular rendimento na listagem
        inscritos = ce.listar_alunos_inscritos(c['id'])
        qtd_alunos = len(inscritos)
        preco_curso = float(c.get('preco', 0))
        faturamento = qtd_alunos * preco_curso
        
        with st.container(border=True):
            # Layout: Texto | Métricas | Botão
            col_txt, col_metrics, col_btn = st.columns([3, 2, 1])
            
            with col_txt:
                mod_badge = f"<span style='background:#333; padding:2px 6px; border-radius:4px; font-size:0.7em; margin-right:5px'>{c.get('modalidade','EAD')}</span>"
                role_badge = f"<span style='background:{COR_DESTAQUE}; color:#000; padding:2px 6px; border-radius:4px; font-size:0.7em'>Editor</span>" if c.get('papel') == 'Editor' else ""
                
                st.markdown(f"### {c.get('titulo')} {mod_badge} {role_badge}", unsafe_allow_html=True)
                st.caption(c.get('descricao', '')[:90] + "...")
            
            with col_metrics:
                # Exibição do Rendimento Rápido
                cm1, cm2 = st.columns(2)
                with cm1:
                    st.markdown(f"""
                    <div class="metric-card">
                        <div class="metric-value">{qtd_alunos}</div>
                        <div class="metric-label">Alunos</div>
                    </div>
                    """, unsafe_allow_html=True)
                with cm2:
                    txt_fatura = f"R$ {faturamento:,.0f}" if preco_curso > 0 else "GRÁTIS"
                    st.markdown(f"""
                    <div class="metric-card">
                        <div class="metric-value">{txt_fatura}</div>
                        <div class="metric-label">Rendimento</div>
                    </div>
                    """, unsafe_allow_html=True)

            with col_btn:
                st.markdown("<br>", unsafe_allow_html=True)
                if st.button("Gerenciar", key=f"btn_ver_{c['id']}", use_container_width=True):
                    st.session_state['curso_selecionado'] = c
                    st.session_state['cursos_view'] = 'detalhe'
                    st.session_state['editando_curso'] = False
                    st.rerun()

def exibir_detalhes_curso(usuario):
    curso = st.session_state['curso_selecionado']
    
    if st.button("← Voltar à Lista"):
        st.session_state['cursos_view'] = 'lista'
        st.rerun()

    st.title(curso.get('titulo', 'Curso Sem Nome'))
    
    tab_sobre, tab_alunos = st.tabs(["📝 Visão Geral", "👥 Alunos & Rendimento"])
    
    # --- ABA GERAL ---
    with tab_sobre:
        col_actions, col_info = st.columns([1, 2])
        
        with col_actions:
            st.markdown("#### Ações")
            if st.button("➕ Gerenciar Conteúdo/Aulas", type="primary", use_container_width=True):
                st.session_state['cursos_view'] = 'conteudo'
                st.rerun()
            
            st.markdown("<br>", unsafe_allow_html=True)
            if st.button("✏️ Editar Informações", use_container_width=True):
                st.session_state['editando_curso'] = not st.session_state['editando_curso']
                st.rerun()
            
            eh_dono = curso.get('professor_id') == usuario['id']
            if eh_dono:
                if st.button("🗑️ Excluir Curso", type="secondary", use_container_width=True):
                     if ce.excluir_curso(curso['id']):
                         st.session_state['cursos_view'] = 'lista'
                         st.rerun()
            else:
                st.info("Apenas o dono pode excluir o curso.")

        with col_info:
            if st.session_state['editando_curso']:
                with st.container(border=True):
                    st.markdown("##### ✏️ Editando Curso")
                    if 'editores_temp_ids' not in st.session_state:
                        st.session_state['editores_temp_ids'] = curso.get('editores_ids', [])

                    with st.form("form_editar_curso"):
                        novo_titulo = st.text_input("Título", value=curso.get('titulo', ''))
                        nova_desc = st.text_area("Descrição", value=curso.get('descricao', ''))
                        
                        c_ed1, c_ed2 = st.columns(2)
                        opcoes_mod = ["EAD", "Presencial", "Híbrido"]
                        idx_mod = opcoes_mod.index(curso.get('modalidade')) if curso.get('modalidade') in opcoes_mod else 0
                        nova_mod = c_ed1.selectbox("Modalidade", opcoes_mod, index=idx_mod)
                        
                        opcoes_pub = ["Aberto a Todos", "Restrito à Minha Equipe"]
                        idx_pub = 1 if curso.get('publico') == 'equipe' else 0
                        novo_pub_sel = c_ed2.selectbox("Público", opcoes_pub, index=idx_pub)
                        
                        novo_preco = st.number_input("Preço (R$)", value=float(curso.get('preco', 0.0)), step=10.0)

                        if st.form_submit_button("💾 Salvar Alterações"):
                            novo_pub_val = 'equipe' if "Restrito" in novo_pub_sel else 'todos'
                            equipe_dest = usuario.get('equipe', '') if novo_pub_val == 'equipe' else ''

                            dados_atualizados = {
                                "titulo": novo_titulo,
                                "descricao": nova_desc,
                                "modalidade": nova_mod,
                                "publico": novo_pub_val,
                                "equipe_destino": equipe_dest,
                                "preco": novo_preco,
                                "pago": novo_preco > 0,
                                "editores_ids": st.session_state['editores_temp_ids']
                            }
                            
                            sucesso = ce.editar_curso(curso['id'], dados_atualizados)
                            if sucesso:
                                st.success("Curso atualizado!")
                                curso.update(dados_atualizados)
                                st.session_state['curso_selecionado'] = curso
                                st.session_state['editando_curso'] = False
                                if 'editores_temp_ids' in st.session_state: del st.session_state['editores_temp_ids']
                                time.sleep(1)
                                st.rerun()
                            else:
                                st.error("Erro ao atualizar.")
                    
                    # Gestão de Editores Fora do Form
                    st.markdown("---")
                    st.markdown("###### Professores Auxiliares")
                    lista_detalhada = ce.obter_nomes_usuarios(st.session_state['editores_temp_ids'])
                    for editor in lista_detalhada:
                        c_nm, c_rm = st.columns([4, 1])
                        c_nm.text(f"👤 {editor['nome']}")
                        if c_rm.button("Remover", key=f"rm_ed_{editor['id']}"):
                            st.session_state['editores_temp_ids'].remove(editor['id'])
                            st.rerun()
                            
                    c_cpf, c_add = st.columns([3, 1])
                    cpf_input = c_cpf.text_input("Adicionar CPF")
                    if c_add.button("Add"):
                        u_found = ce.buscar_usuario_por_cpf(cpf_input)
                        if u_found and u_found['id'] != usuario['id']:
                            if u_found['id'] not in st.session_state['editores_temp_ids']:
                                st.session_state['editores_temp_ids'].append(u_found['id'])
                                st.rerun()

            else:
                st.markdown(f"**Descrição:**\n{curso.get('descricao', 'Sem descrição')}")
                st.markdown("---")
                c1, c2, c3 = st.columns(3)
                c1.markdown(f"**Professor:** {curso.get('professor_nome', '-')}")
                c2.markdown(f"**Equipe:** {curso.get('professor_equipe', '-')}")
                c3.markdown(f"**Preço:** R$ {curso.get('preco', 0):.2f}")
                
                st.markdown("<br>", unsafe_allow_html=True)
                c4, c5 = st.columns(3)[:2]
                c4.markdown(f"**Modalidade:** {curso.get('modalidade', 'EAD')}")
                pub_txt = "Restrito à Equipe" if curso.get('publico') == 'equipe' else "Aberto a Todos"
                c5.markdown(f"**Público:** {pub_txt}")
                
                if curso.get('editores_ids'):
                    st.caption(f"Professores auxiliares: {len(curso['editores_ids'])}")

    # --- ABA FINANCEIRO ---
    with tab_alunos:
        st.markdown("### 📊 Performance Financeira")
        
        with st.spinner("Calculando rendimentos..."):
            alunos = ce.listar_alunos_inscritos(curso['id'])
        
        total_alunos = len(alunos)
        preco_curso = float(curso.get('preco', 0))
        is_pago = curso.get('pago', False) or (preco_curso > 0)
        
        # Dashboard de Rendimento
        col_metrics = st.columns(3)
        col_metrics[0].metric("Total de Alunos", total_alunos, border=True)
        
        if is_pago:
            rendimento_real = total_alunos * preco_curso
            col_metrics[1].metric("Valor Unitário", f"R$ {preco_curso:.2f}", border=True)
            col_metrics[2].metric("Rendimento Alcançado", f"R$ {rendimento_real:,.2f}", border=True)
        else:
            col_metrics[1].metric("Tipo", "Gratuito", border=True)
            col_metrics[2].metric("Rendimento", "R$ 0,00", border=True)

        st.markdown("---")
        st.markdown("### 📋 Alunos Matriculados")
        
        if alunos:
            df_alunos = pd.DataFrame(alunos)
            st.dataframe(df_alunos, use_container_width=True, hide_index=True)
        else:
            st.info("Ainda não há alunos inscritos.")
