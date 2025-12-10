import streamlit as st
import pandas as pd
import time
from database import get_db
from firebase_admin import firestore
# Importamos o dashboard para usar dentro da aba
from views import dashboard 

# =========================================
# HELPER: DECORAR FAIXAS E CARGOS
# =========================================
def get_faixa_decorada(faixa):
    """Adiciona emojis combinados para representar faixas mistas e sólidas"""
    f = str(faixa).lower().strip()
    
    # 1. Faixas Mistas (Infantil/Juvenil) - Verificamos estas PRIMEIRO
    if "cinza" in f and "branca" in f: return f"🔘⚪ {faixa}"
    if "cinza" in f and "preta" in f:  return f"🔘⚫ {faixa}"
    
    if "amarela" in f and "branca" in f: return f"🟡⚪ {faixa}"
    if "amarela" in f and "preta" in f:  return f"🟡⚫ {faixa}"
    
    if "laranja" in f and "branca" in f: return f"🟠⚪ {faixa}"
    if "laranja" in f and "preta" in f:  return f"🟠⚫ {faixa}"
    
    if "verde" in f and "branca" in f: return f"🟢⚪ {faixa}"
    if "verde" in f and "preta" in f:  return f"🟢⚫ {faixa}"

    # 2. Faixas Sólidas
    if "branca" in f: return f"⚪ {faixa}"
    if "cinza" in f:  return f"🔘 {faixa}"
    if "amarela" in f: return f"🟡 {faixa}"
    if "laranja" in f: return f"🟠 {faixa}"
    if "verde" in f:  return f"🟢 {faixa}"
    if "azul" in f:   return f"🔵 {faixa}"
    if "roxa" in f:   return f"🟣 {faixa}"
    if "marrom" in f: return f"🟤 {faixa}"
    if "preta" in f:  return f"⚫ {faixa}"

    # Fallback
    return f"🥋 {faixa}"

def get_cargo_decorado(cargo):
    if cargo == "Líder": return "👑 Professor Responsável"
    if cargo == "Delegado": return "🛡️ Professor Delegado"
    return "🥋 Professor Adjunto"

# =========================================
# FUNÇÃO: GESTÃO DE EQUIPES (COM TOTAIS)
# =========================================
def gestao_equipes():
    db = get_db()
    user = st.session_state.usuario
    user_id = user['id']

    # --- 1. IDENTIFICAR O CONTEXTO DO PROFESSOR ---
    vinc = list(db.collection('professores').where('usuario_id', '==', user_id).where('status_vinculo', '==', 'ativo').limit(1).stream())
    
    if not vinc:
        st.error("⛔ Você não possui vínculo ativo com nenhuma equipe.")
        return

    dados_prof = vinc[0].to_dict()
    meu_equipe_id = dados_prof.get('equipe_id')
    sou_responsavel = dados_prof.get('eh_responsavel', False)
    sou_delegado = dados_prof.get('pode_aprovar', False) 

    # Busca nome da equipe
    nome_equipe = "Minha Equipe"
    if meu_equipe_id:
        eq_doc = db.collection('equipes').document(meu_equipe_id).get()
        if eq_doc.exists:
            nome_equipe = eq_doc.to_dict().get('nome', 'Minha Equipe')

    # --- 2. DEFINIR NÍVEL DE PODER ---
    nivel_poder = 1
    if sou_delegado: nivel_poder = 2
    if sou_responsavel: nivel_poder = 3

    # Cabeçalho
    st.markdown(f"### 🏛️ {nome_equipe}")
    col_info1, col_info2 = st.columns([3, 1])
    col_info1.caption("Painel de Gestão de Membros e Aprovações")
    
    badge = "⭐ Auxiliar"
    if nivel_poder == 2: badge = "⭐⭐ Delegado"
    if nivel_poder == 3: badge = "⭐⭐⭐ Responsável"
    col_info2.markdown(f"**Cargo:** {badge}")

    # --- 3. ABAS DE GESTÃO ---
    abas = ["⏳ Aprovações", "👥 Membros Ativos"]
    if nivel_poder == 3:
        abas.append("🎖️ Delegar Poder")
    
    tabs = st.tabs(abas)

    # === ABA 1: APROVAÇÕES PENDENTES ===
    with tabs[0]:
        st.markdown("#### Solicitações de Entrada")
        
        # A. ALUNOS
        q_alunos = db.collection('alunos').where('equipe_id', '==', meu_equipe_id).where('status_vinculo', '==', 'pendente')
        if nivel_poder == 1:
            q_alunos = q_alunos.where('professor_id', '==', user_id)
            msg_filtro = "Seus alunos diretos"
        else:
            msg_filtro = "Todos da equipe"
            
        alunos_pend = list(q_alunos.stream())

        if alunos_pend:
            st.info(f"Alunos Pendentes: {len(alunos_pend)} ({msg_filtro})")
            for doc in alunos_pend:
                d = doc.to_dict()
                udoc = db.collection('usuarios').document(d['usuario_id']).get()
                nome_aluno = udoc.to_dict()['nome'] if udoc.exists else "Desconhecido"
                
                with st.container(border=True):
                    c1, c2, c3 = st.columns([0.6, 0.2, 0.2])
                    c1.markdown(f"**{nome_aluno}**\n\n{get_faixa_decorada(d.get('faixa_atual'))}")
                    if c2.button("✅ Aceitar", key=f"ok_al_{doc.id}"):
                        db.collection('alunos').document(doc.id).update({'status_vinculo': 'ativo'})
                        st.toast(f"{nome_aluno} aprovado!"); time.sleep(1); st.rerun()
                    if c3.button("❌ Recusar", key=f"no_al_{doc.id}"):
                        db.collection('alunos').document(doc.id).delete()
                        st.toast("Recusado."); time.sleep(1); st.rerun()
        else:
            st.success("Nenhuma pendência de aluno.")

        # B. PROFESSORES
        if nivel_poder >= 2:
            st.divider()
            st.markdown("#### Professores Pendentes")
            q_profs = db.collection('professores').where('equipe_id', '==', meu_equipe_id).where('status_vinculo', '==', 'pendente')
            profs_pend = list(q_profs.stream())
            
            if profs_pend:
                for doc in profs_pend:
                    d = doc.to_dict()
                    udoc = db.collection('usuarios').document(d['usuario_id']).get()
                    nome_prof = udoc.to_dict()['nome'] if udoc.exists else "Desconhecido"
                    
                    with st.container(border=True):
                        c1, c2, c3 = st.columns([0.6, 0.2, 0.2])
                        c1.markdown(f"**PROFESSOR: {nome_prof}**")
                        if c2.button("✅ Aceitar", key=f"ok_pr_{doc.id}"):
                            db.collection('professores').document(doc.id).update({'status_vinculo': 'ativo'})
                            st.toast("Aceito!"); time.sleep(1); st.rerun()
                        if c3.button("❌ Recusar", key=f"no_pr_{doc.id}"):
                            db.collection('professores').document(doc.id).delete()
                            st.toast("Recusado."); time.sleep(1); st.rerun()

    # === ABA 2: MEMBROS ATIVOS (COM TOTAIS) ===
    with tabs[1]:
        # 1. BUSCAR DADOS (Queries)
        # Fazemos a busca antes para poder contar e exibir os totais no topo
        profs_ativos = list(db.collection('professores').where('equipe_id', '==', meu_equipe_id).where('status_vinculo', '==', 'ativo').stream())
        alunos_ativos = list(db.collection('alunos').where('equipe_id', '==', meu_equipe_id).where('status_vinculo', '==', 'ativo').stream())

        # 2. EXIBIR TOTAIS (Métricas)
        c_tot1, c_tot2 = st.columns(2)
        c_tot1.metric("👨‍🏫 Total Professores", len(profs_ativos))
        c_tot2.metric("🥋 Total Alunos", len(alunos_ativos))
        
        st.divider()

        # 3. TABELA DE PROFESSORES
        st.markdown("#### 🥋 Quadro de Professores")
        
        lista_profs = []
        for p in profs_ativos:
            pdados = p.to_dict()
            u = db.collection('usuarios').document(pdados['usuario_id']).get()
            if u.exists:
                cargo_raw = "Auxiliar"
                if pdados.get('eh_responsavel'): cargo_raw = "Líder"
                elif pdados.get('pode_aprovar'): cargo_raw = "Delegado"
                
                lista_profs.append({
                    "Nome": u.to_dict()['nome'],
                    "Cargo": get_cargo_decorado(cargo_raw)
                })
        
        if lista_profs:
            st.dataframe(
                pd.DataFrame(lista_profs),
                use_container_width=True,
                hide_index=True,
                column_config={
                    "Nome": st.column_config.TextColumn("Professor", width="large"),
                    "Cargo": st.column_config.TextColumn("Função / Nível", width="medium"),
                }
            )
        else:
            st.info("Nenhum professor encontrado.")

        st.markdown("---")

        # 4. TABELA DE ALUNOS
        c_titulo, c_busca = st.columns([1, 1])
        c_titulo.markdown("#### 🥋 Quadro de Alunos")
        filtro = c_busca.text_input("🔍 Buscar aluno:", placeholder="Digite o nome...", label_visibility="collapsed")
        
        lista_alunos = []
        for a in alunos_ativos:
            adados = a.to_dict()
            u = db.collection('usuarios').document(adados['usuario_id']).get()
            if u.exists:
                nome_real = u.to_dict()['nome']
                # Filtro visual
                if filtro and filtro.upper() not in nome_real.upper():
                    continue

                lista_alunos.append({
                    "Nome": nome_real,
                    "Faixa": get_faixa_decorada(adados.get('faixa_atual', '-'))
                })
                
        if lista_alunos:
            df_alunos = pd.DataFrame(lista_alunos).sort_values(by="Nome")
            st.dataframe(
                df_alunos,
                use_container_width=True,
                hide_index=True,
                height=400,
                column_config={
                    "Nome": st.column_config.TextColumn("Aluno", width="large"),
                    "Faixa": st.column_config.TextColumn("Graduação Atual", width="medium"),
                }
            )
            if filtro:
                st.caption(f"Exibindo {len(df_alunos)} alunos filtrados.")
        else:
            if filtro: st.warning("Nenhum aluno encontrado.")
            else: st.warning("Ainda não há alunos ativos.")

    # === ABA 3: DELEGAR PODER ===
    if nivel_poder == 3:
        with tabs[2]:
            st.markdown("#### Gestão de Delegados")
            st.info("Limite: 2 Delegados.")
            
            profs_ativos_del = list(db.collection('professores').where('equipe_id', '==', meu_equipe_id).where('status_vinculo', '==', 'ativo').stream())
            delegados_existentes = [p for p in profs_ativos_del if p.to_dict().get('pode_aprovar') and not p.to_dict().get('eh_responsavel')]
            
            st.metric("Vagas Utilizadas", f"{len(delegados_existentes)} / 2")
            st.divider()
            
            auxiliares = [p for p in profs_ativos_del if not p.to_dict().get('eh_responsavel')]
            
            if not auxiliares:
                st.warning("Sem auxiliares disponíveis.")
            
            for doc in auxiliares:
                d = doc.to_dict()
                u = db.collection('usuarios').document(d['usuario_id']).get()
                nome = u.to_dict()['nome'] if u.exists else "..."
                is_delegado = d.get('pode_aprovar', False)
                
                c1, c2 = st.columns([3, 2])
                c1.write(f"🥋 {nome}")
                
                if is_delegado:
                    if c2.button("⬇️ Revogar", key=f"rv_{doc.id}"):
                        db.collection('professores').document(doc.id).update({'pode_aprovar': False})
                        st.rerun()
                else:
                    btn_disabled = (len(delegados_existentes) >= 2)
                    if c2.button("⬆️ Promover", key=f"pm_{doc.id}", disabled=btn_disabled):
                        db.collection('professores').document(doc.id).update({'pode_aprovar': True})
                        st.rerun()
                st.divider()

# =========================================
# FUNÇÃO: GESTÃO DE CURSOS (NOVA FUNÇÃO)
# =========================================
def gestao_cursos_tab():
    st.markdown("<h1 style='color:#FFD770;'>📚 Gestão de Cursos</h1>", unsafe_allow_html=True)
    db = get_db()
    user = st.session_state.usuario
    user_id = user['id']
    user_nome = user['nome']
    
    if str(user.get("tipo", "")).lower() not in ["admin", "professor"]:
        st.error("Acesso negado. Apenas professores e administradores podem gerenciar cursos.")
        return

    tab_list, tab_add = st.tabs(["Listar e Editar Cursos", "Criar Novo Curso"])

    with tab_add:
        # ... (Criação de Novo Curso - Mantida do passo anterior) ...
        st.markdown("#### 📝 Criar Novo Curso")
        with st.form("form_novo_curso"):
            
            # Dados básicos
            c1, c2 = st.columns(2)
            titulo = c1.text_input("Título do Curso *", max_chars=100)
            categoria = c2.text_input("Categoria (Ex: Defesa Pessoal, Posições de Guarda, etc.)", "Geral")
            
            descricao = st.text_area("Descrição Completa *", height=150)
            
            # Requisitos e Faixa Alvo
            c3, c4 = st.columns(2)
            faixa_minima = c3.selectbox("Faixa Mínima Requerida:", ["Nenhuma", "Branca", "Azul", "Roxa", "Marrom", "Preta"])
            duracao_estimada = c4.text_input("Duração Estimada (Ex: 10 horas, 3 semanas)", "Não especificada")
            
            st.markdown("---")
            st.markdown("##### 🖼️ Imagem de Capa (Opcional)")

            col_up, col_link = st.columns(2)
            up_img = col_up.file_uploader("Upload da Imagem de Capa:", type=["jpg","png", "jpeg"])
            url_capa = col_link.text_input("Ou use um Link Externo/URL (será ignorado se houver upload):")
            
            # Status e Autor
            ativo = st.checkbox("Curso Ativo (Disponível para Alunos)", value=True)
            
            if st.form_submit_button("💾 Salvar Curso", type="primary"):
                if not titulo or not descricao:
                    st.error("Preencha o Título e a Descrição.")
                else:
                    url_final = url_capa # Começa com o link (se houver)

                    if up_img:
                        from utils import fazer_upload_midia # Importação local para garantir
                        with st.spinner("Subindo imagem..."):
                            url_upload = fazer_upload_midia(up_img)
                            if url_upload:
                                url_final = url_upload
                            else:
                                st.error("Erro ao fazer upload da imagem. Use um link externo ou tente novamente.")
                                return
                    
                    try:
                        novo_curso = {
                            "titulo": titulo.upper(),
                            "descricao": descricao,
                            "categoria": categoria,
                            "faixa_minima": faixa_minima,
                            "duracao_estimada": duracao_estimada,
                            "url_capa": url_final,
                            "ativo": ativo,
                            "criado_por_id": user_id,
                            "criado_por_nome": user_nome,
                            "data_criacao": firestore.SERVER_TIMESTAMP,
                            "modulos": [],
                        }
                        
                        db.collection('cursos').add(novo_curso)
                        st.success("✅ Curso criado com sucesso! Ele aparecerá na lista abaixo.")
                        time.sleep(1.5)
                        st.rerun()
                        
                    except Exception as e:
                        st.error(f"Erro ao salvar curso: {e}")


    with tab_list:
        st.markdown("#### 📝 Cursos Existentes")
        
        # Carrega e filtra os cursos
        cursos_ref = list(db.collection('cursos').stream())
        cursos_data = [d.to_dict() | {"id": d.id} for d in cursos_ref]
        
        if str(user.get("tipo", "")).lower() != "admin":
            cursos_data = [c for c in cursos_data if c.get('criado_por_id') == user_id]

        if not cursos_data:
            st.info("Nenhum curso encontrado.")
            return

        filtro_titulo = st.text_input("🔍 Buscar por Título:", key="f_titulo_curso")
        if filtro_titulo:
            term = filtro_titulo.upper()
            cursos_data = [c for c in cursos_data if term in c.get('titulo', '').upper()]

        
        for i, curso in enumerate(cursos_data):
            # Expander para cada curso
            with st.expander(f"**{curso.get('titulo')}** | Categoria: {curso.get('categoria')} | Status: {'🟢 Ativo' if curso.get('ativo') else '🔴 Rascunho'}"):
                
                # Exibe detalhes do módulo
                st.caption(f"Criado por: {curso.get('criado_por_nome')} em {curso.get('data_criacao').strftime('%d/%m/%Y') if hasattr(curso.get('data_criacao'), 'strftime') else 'Desconhecida'}")
                st.markdown(f"**Descrição:** {curso.get('descricao')}")
                st.markdown(f"**Faixa Mínima:** {curso.get('faixa_minima')}")
                
                if curso.get('url_capa'):
                    st.image(curso.get('url_capa'), caption="Capa Atual", width=200)

                st.markdown("---")
                
                # =================================================================
                # NOVO BLOCO: GESTÃO DA PROVA DO CURSO
                # =================================================================
                st.subheader("📝 Avaliação do Curso")
                
                # 1. Busca a configuração de prova existente para este curso (subcoleção 'provas_curso')
                prova_ref = db.collection('cursos').document(curso['id']).collection('provas_curso').document('config')
                prova_doc = prova_ref.get()
                conf_prova = prova_doc.to_dict() if prova_doc.exists else {}
                
                tab_montar, tab_liberar = st.tabs(["🔨 Montar Prova", "✅ Liberar Alunos"])

                with tab_montar:
                    st.markdown("##### 1. Configuração da Prova")
                    
                    # Carrega todas as questões (aprovadas) para seleção
                    todas_questoes_aprovadas = list(db.collection('questoes').where('status', '==', 'aprovada').stream())
                    mapa_questoes = {d.id: d.to_dict() for d in todas_questoes_aprovadas}
                    
                    # Usa session state para a seleção de IDs, garantindo persistência no formulário
                    selected_ids_key = f'selected_ids_{curso["id"]}'
                    if selected_ids_key not in st.session_state:
                        st.session_state[selected_ids_key] = set(conf_prova.get('questoes_ids', []))

                    with st.form(f"form_montar_prova_{curso['id']}"):
                        
                        q_sel = len(st.session_state[selected_ids_key])
                        st.success(f"**{q_sel}** questões selecionadas atualmente.")

                        # Interface de seleção (Simplificada, como em admin.gestao_exame_de_faixa)
                        with st.expander("Clique para selecionar/remover questões"):
                            c_f1, c_f2 = st.columns(2)
                            # Adicionar filtros aqui, se necessário (nível/categoria)
                            
                            for qid, qdata in mapa_questoes.items():
                                is_checked = qid in st.session_state[selected_ids_key]
                                
                                # Cria uma função de callback para atualizar o set
                                def update_selection_curso(qid=qid):
                                    if st.session_state[f"chk_curso_{qid}_{curso['id']}"]:
                                        st.session_state[selected_ids_key].add(qid)
                                    else:
                                        st.session_state[selected_ids_key].discard(qid)

                                c_chk, c_content = st.columns([1, 15])
                                c_chk.checkbox("", value=is_checked, key=f"chk_curso_{qid}_{curso['id']}", on_change=update_selection_curso)
                                with c_content:
                                    st.caption(f"ID: {qid[:4]} | Nível: {qdata.get('dificuldade', 1)}")
                                    st.markdown(f"*{qdata.get('pergunta')}*")
                                    st.markdown("---")


                        st.markdown("##### 2. Regras da Avaliação")
                        c1, c2 = st.columns(2)
                        tempo = c1.number_input("Tempo (min):", 10, 180, int(conf_prova.get('tempo_limite', 30)), key=f"t_lim_{curso['id']}")
                        nota = c2.number_input("Aprovação (%):", 10, 100, int(conf_prova.get('aprovacao_minima', 70)), key=f"n_min_{curso['id']}")

                        if st.form_submit_button("💾 Salvar Prova do Curso", type="primary"):
                            if len(st.session_state[selected_ids_key]) == 0:
                                st.error("Selecione questões para a prova.")
                            else:
                                try:
                                    dados_prova = {
                                        "curso_id": curso['id'], 
                                        "titulo": f"Prova: {curso['titulo']}",
                                        "questoes_ids": list(st.session_state[selected_ids_key]), 
                                        "qtd_questoes": len(st.session_state[selected_ids_key]), 
                                        "tempo_limite": tempo, 
                                        "aprovacao_minima": nota, 
                                        "atualizado_em": firestore.SERVER_TIMESTAMP
                                    }
                                    
                                    prova_ref.set(dados_prova) # Cria ou sobrescreve o documento 'config'
                                    st.success("✅ Prova do curso salva/atualizada!")
                                    time.sleep(1.5); st.rerun()

                                except Exception as e:
                                    st.error(f"Erro ao salvar prova: {e}")
                
                with tab_liberar:
                    st.markdown("##### 3. Liberar Prova para Alunos")
                    
                    if not conf_prova:
                        st.warning("Monte a prova na aba 'Montar Prova' antes de liberar.")
                        
                    elif conf_prova.get('qtd_questoes', 0) == 0:
                        st.warning("A prova está vazia (0 questões).")
                    
                    else:
                        st.info(f"Prova disponível: {conf_prova.get('qtd_questoes')} questões | Min. {conf_prova.get('aprovacao_minima')}%")
                        
                        # Interface de liberação
                        st.divider()
                        
                        # Aqui você listaria os alunos desta equipe para liberar individualmente
                        st.caption("A liberação será implementada na próxima etapa, juntamente com a matrícula do aluno.")
                        
                        # --- EXIBIÇÃO DE ALUNOS ATUALMENTE MATRICULADOS E SEU STATUS ---
                        
                        # Para fins de demonstração da estrutura, vamos manter uma mensagem provisória:
                        st.markdown("**Status dos Alunos** (A ser implementado):")
                        st.code("Consulta ao status de matrícula do aluno na subcoleção 'matriculas_curso'...")

                # ... (restante do código do expander - Módulos, Edição de Metadados) ...
                st.markdown("---")
                
                # Adicionar e Gerenciar Módulos
                st.subheader("🛠️ Módulos e Aulas")
                
                modulos = curso.get('modulos', [])
                if not modulos:
                    st.warning("Nenhum módulo cadastrado neste curso.")
                else:
                    st.dataframe(
                        pd.DataFrame(modulos),
                        use_container_width=True,
                        hide_index=True,
                        column_config={
                            "titulo_modulo": "Módulo/Capítulo",
                            "aulas": st.column_config.ListColumn("Total de Aulas", width="small", help="Quantidade de Aulas (Itens na Lista)"),
                            "descricao_modulo": st.column_config.TextColumn("Descrição")
                        }
                    )
                
                # Formulário de Adição de Módulo
                with st.form(f"form_mod_{curso['id']}"):
                    st.markdown("##### ➕ Adicionar/Editar Módulo")
                    m_titulo = st.text_input("Título do Módulo:", key=f"mt_{i}")
                    m_desc = st.text_area("Descrição do Módulo:", key=f"md_{i}")
                    
                    aulas_raw = st.text_area("Aulas (Uma por linha: Ex: 'Pegada Cruzada', 'Defesa de Queda'):", height=100, key=f"aulas_{i}")
                    
                    if st.form_submit_button("✅ Salvar Módulo/Atualizar Curso"):
                        if m_titulo:
                            
                            aulas_list = [a.strip() for a in aulas_raw.split('\n') if a.strip()]
                            
                            novo_modulo = {
                                "titulo_modulo": m_titulo,
                                "descricao_modulo": m_desc,
                                "aulas": aulas_list,
                            }
                            
                            modulos_existentes = curso.get('modulos', [])
                            encontrado = False
                            for j, mod in enumerate(modulos_existentes):
                                if mod.get('titulo_modulo', '').upper() == m_titulo.upper():
                                    modulos_existentes[j] = novo_modulo
                                    encontrado = True
                                    break
                            
                            if not encontrado:
                                modulos_existentes.append(novo_modulo)
                                
                            db.collection('cursos').document(curso['id']).update({"modulos": modulos_existentes})
                            st.success(f"Módulo '{m_titulo}' atualizado/adicionado.")
                            time.sleep(1.5); st.rerun()

                        else:
                            st.error("O Título do Módulo é obrigatório.")
                        
                # Botões de Ação do Curso (Edição Rápida)
                c_act1, c_act2, c_act3 = st.columns(3)
                if c_act1.button("✏️ Editar Metadados", key=f"edt_cur_{curso['id']}"):
                    st.session_state[f"edit_mode_{curso['id']}"] = True
                
                if c_act2.button(f"{'🔴 Desativar' if curso.get('ativo') else '🟢 Ativar'}", key=f"stt_cur_{curso['id']}"):
                    db.collection('cursos').document(curso['id']).update({"ativo": not curso.get('ativo')})
                    st.toast("Status atualizado."); time.sleep(1); st.rerun()
                    
                if c_act3.button("🗑️ Deletar Curso", key=f"del_cur_{curso['id']}", type="primary"):
                    db.collection('cursos').document(curso['id']).delete()
                    st.toast("Curso deletado."); time.sleep(1); st.rerun()

                # Formulário de edição de Metadados (oculto por padrão)
                if st.session_state.get(f"edit_mode_{curso['id']}"):
                    st.markdown("---")
                    st.markdown("##### Edição Rápida de Metadados")
                    with st.form(f"form_edit_meta_{curso['id']}"):
                        n_titulo = st.text_input("Título", value=curso.get('titulo'))
                        n_desc = st.text_area("Descrição", value=curso.get('descricao'))
                        n_cat = st.text_input("Categoria", value=curso.get('categoria'))
                        n_faixa = st.selectbox("Faixa Mínima", ["Nenhuma", "Branca", "Azul", "Roxa", "Marrom", "Preta"], index=["Nenhuma", "Branca", "Azul", "Roxa", "Marrom", "Preta"].index(curso.get('faixa_minima')))
                        n_dur = st.text_input("Duração Estimada", value=curso.get('duracao_estimada'))
                        
                        if st.form_submit_button("💾 Salvar Edição"):
                            db.collection('cursos').document(curso['id']).update({
                                "titulo": n_titulo.upper(),
                                "descricao": n_desc,
                                "categoria": n_cat,
                                "faixa_minima": n_faixa,
                                "duracao_estimada": n_dur
                            })
                            st.session_state.pop(f"edit_mode_{curso['id']}")
                            st.success("Metadados atualizados."); time.sleep(1.5); st.rerun()
                            
# =========================================
# FUNÇÃO PRINCIPAL: PAINEL DO PROFESSOR (ATUALIZADA)
# =========================================
def painel_professor():
    st.markdown("<h1 style='color:#FFD770;'>👨‍🏫 Painel do Professor</h1>", unsafe_allow_html=True)
    
    if st.button("🏠 Voltar ao Início", key="btn_voltar_prof"):
        st.session_state.menu_selection = "Início"; st.rerun()

    # Note que agora temos 3 abas, a Gestão de Cursos é a segunda.
    tab1, tab2, tab3 = st.tabs(["👥 Gestão de Equipe", "📚 Gestão de Cursos", "📊 Estatísticas & Dashboard"])
    
    with tab1:
        gestao_equipes()
               
    with tab2:
        dashboard.dashboard_professor()
