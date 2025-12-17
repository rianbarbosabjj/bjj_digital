import streamlit as st
import time
import pandas as pd
from datetime import datetime
import utils as ce
import views.aulas as aulas_view 
import re

try:
    from config import COR_FUNDO, COR_TEXTO, COR_DESTAQUE, COR_BOTAO, COR_HOVER
except ImportError:
    COR_FUNDO, COR_TEXTO, COR_DESTAQUE, COR_BOTAO, COR_HOVER = "#0e2d26", "#FFFFFF", "#FFD770", "#078B6C", "#FFD770"

def pagina_cursos(usuario):
    if 'cursos_view' not in st.session_state:
        st.session_state['cursos_view'] = 'lista'
    if 'curso_selecionado' not in st.session_state:
        st.session_state['curso_selecionado'] = None
    if 'editando_curso' not in st.session_state:
        st.session_state['editando_curso'] = False

    # Roteamento
    if st.session_state['cursos_view'] == 'conteudo':
        if st.session_state['curso_selecionado']:
            aulas_view.gerenciar_conteudo_curso(st.session_state['curso_selecionado'], usuario)
        else:
            st.session_state['cursos_view'] = 'lista'
            st.rerun()

    elif st.session_state['cursos_view'] == 'detalhe':
        exibir_detalhes_curso(usuario)

    else:
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
                
                # --- Gestão Compartilhada por CPF ---
                st.markdown("---")
                st.markdown("###### Gestão Compartilhada (Opcional)")
                st.caption("Digite os CPFs dos professores auxiliares (um por linha ou separado por vírgula):")
                cpfs_input = st.text_area("CPFs dos Editores", height=68, placeholder="Ex: 111.222.333-44\n555.666.777-88")
                
                st.markdown("---")
                preco = st.number_input("Preço (R$)", 0.0, step=10.0)
                
                if st.form_submit_button("Criar Curso"):
                    # Processamento dos CPFs
                    ids_editores = []
                    cpfs_nao_encontrados = []
                    
                    if cpfs_input:
                        # Separa por quebra de linha ou vírgula
                        lista_cpfs_raw = re.split(r'[,\n]', cpfs_input)
                        for cpf_raw in lista_cpfs_raw:
                            cpf_limpo = cpf_raw.strip()
                            if cpf_limpo:
                                user_encontrado = ce.buscar_usuario_por_cpf(cpf_limpo)
                                if user_encontrado:
                                    if user_encontrado['id'] != usuario['id']: # Não adiciona a si mesmo
                                        ids_editores.append(user_encontrado['id'])
                                else:
                                    cpfs_nao_encontrados.append(cpf_limpo)
                    
                    if cpfs_nao_encontrados:
                        st.warning(f"⚠️ Alguns CPFs não foram encontrados e ignorados: {', '.join(cpfs_nao_encontrados)}")
                    
                    # Criação
                    publico_val = 'equipe' if "Restrito" in publico_sel else 'todos'
                    equipe_dest = usuario.get('equipe', '') if publico_val == 'equipe' else ''
                    
                    ce.criar_curso(
                        usuario['id'], 
                        usuario['nome'], 
                        usuario.get('equipe',''), 
                        titulo, 
                        desc, 
                        modalidade,     
                        publico_val,    
                        equipe_dest,    
                        True, 
                        preco, 
                        False, 
                        False, 
                        10, 
                        'iniciante',
                        editores_ids=ids_editores
                    )
                    st.success("Curso criado com sucesso!")
                    time.sleep(1.5)
                    st.rerun()
    
    st.markdown("---")
    
    # --- LISTAGEM ---
    cursos = ce.listar_cursos_do_professor(usuario['id'])
    
    if not cursos:
        st.info("Nenhum curso encontrado.")
        return

    for c in cursos:
        with st.container(border=True):
            col1, col2 = st.columns([4, 1])
            with col1:
                mod_badge = f"<span style='background:#333; padding:2px 6px; border-radius:4px; font-size:0.7em; margin-right:5px'>{c.get('modalidade','EAD')}</span>"
                role_badge = ""
                if c.get('papel') == 'Editor':
                    role_badge = f"<span style='background:{COR_DESTAQUE}; color:#000; padding:2px 6px; border-radius:4px; font-size:0.7em'>Editor Convidado</span>"
                
                st.markdown(f"### {c.get('titulo')} {mod_badge} {role_badge}", unsafe_allow_html=True)
                st.caption(c.get('descricao', '')[:100] + "...")
            with col2:
                if st.button("Ver Detalhes", key=f"btn_ver_{c['id']}", use_container_width=True):
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
            # === MODO DE EDIÇÃO ===
            if st.session_state['editando_curso']:
                with st.container(border=True):
                    st.markdown("##### ✏️ Editando Curso")
                    
                    # Carrega editores atuais se ainda não estiverem no estado
                    if 'editores_temp_ids' not in st.session_state:
                        st.session_state['editores_temp_ids'] = curso.get('editores_ids', [])

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

                    # --- Gestão de Editores (Interativa) ---
                    st.markdown("---")
                    st.markdown("###### Professores Auxiliares")
                    
                    # Listar Atuais
                    lista_detalhada = ce.obter_nomes_usuarios(st.session_state['editores_temp_ids'])
                    
                    if lista_detalhada:
                        for editor in lista_detalhada:
                            c_ed_nome, c_ed_btn = st.columns([4, 1])
                            c_ed_nome.text(f"👤 {editor['nome']} ({editor['cpf']})")
                            if c_ed_btn.button("Remover", key=f"rm_ed_{editor['id']}"):
                                st.session_state['editores_temp_ids'].remove(editor['id'])
                                st.rerun()
                    else:
                        st.caption("Nenhum professor auxiliar definido.")

                    # Adicionar Novo
                    c_add_cpf, c_add_btn = st.columns([3, 1])
                    novo_cpf_editor = c_add_cpf.text_input("Adicionar por CPF", placeholder="Digite o CPF")
                    if c_add_btn.button("Buscar e Add"):
                        user_found = ce.buscar_usuario_por_cpf(novo_cpf_editor)
                        if user_found:
                            if user_found['id'] not in st.session_state['editores_temp_ids'] and user_found['id'] != usuario['id']:
                                st.session_state['editores_temp_ids'].append(user_found['id'])
                                st.success(f"Adicionado: {user_found['nome']}")
                                time.sleep(1)
                                st.rerun()
                            else:
                                st.warning("Usuário já adicionado ou é o dono.")
                        else:
                            st.error("CPF não encontrado.")
                    
                    st.markdown("---")

                    if st.button("💾 Salvar Todas Alterações", type="primary"):
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
                            # Limpa variável temporária
                            if 'editores_temp_ids' in st.session_state: del st.session_state['editores_temp_ids']
                            time.sleep(1)
                            st.rerun()
                        else:
                            st.error("Erro ao atualizar.")
            
            # === MODO DE VISUALIZAÇÃO ===
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
                publico_display = "Restrito à Equipe" if curso.get('publico') == 'equipe' else "Aberto a Todos"
                c5.markdown(f"**Público:** {publico_display}")
                
                # Exibir Editores
                if curso.get('editores_ids'):
                    st.markdown("---")
                    st.markdown("**Professores Auxiliares:**")
                    nomes_editores = ce.obter_nomes_usuarios(curso['editores_ids'])
                    for ed in nomes_editores:
                        st.caption(f"• {ed['nome']}")

    # --- ABA FINANCEIRO ---
    with tab_alunos:
        st.markdown("### 📊 Indicadores")
        
        with st.spinner("Carregando dados..."):
            alunos = ce.listar_alunos_inscritos(curso['id'])
        
        total_alunos = len(alunos)
        preco_curso = float(curso.get('preco', 0))
        is_pago = curso.get('pago', False) or (preco_curso > 0)
        
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
        st.markdown("### 📋 Lista de Chamada")
        
        if alunos:
            df_alunos = pd.DataFrame(alunos)
            st.dataframe(
                df_alunos, 
                use_container_width=True,
                hide_index=True
            )
        else:
            st.info("Ainda não há alunos inscritos.")
