import streamlit as st
import pandas as pd
import bcrypt
import random
import time 
from datetime import datetime, time as dtime # CORREÇÃO CRÍTICA: 'dtime' evita conflito com o comando 'time.sleep'
from database import get_db
from firebase_admin import firestore
# Certifique-se de que essas funções existem no seu utils.py, senão o código falha
try:
    from utils import carregar_todas_questoes, salvar_questoes
except ImportError:
    # Fallback simples caso utils não tenha as funções
    def carregar_todas_questoes(): return []
    def salvar_questoes(t, q): pass

# =========================================
# LISTA PADRÃO DE FAIXAS (GLOBAL)
# =========================================
FAIXAS_COMPLETAS = [
    "Cinza e Branca", "Cinza", "Cinza e Preta",
    "Amarela e Branca", "Amarela", "Amarela e Preta",
    "Laranja e Branca", "Laranja", "Laranja e Preta",
    "Verde e Branca", "Verde", "Verde e Preta",
    "Azul", "Roxa", "Marrom", "Preta"
]

# =========================================
# 1. GESTÃO DE USUÁRIOS
# =========================================
def gestao_usuarios(usuario_logado):
    st.markdown("<h1 style='color:#FFD700;'>👥 Gestão de Usuários</h1>", unsafe_allow_html=True)
    db = get_db()
    
    users_ref = db.collection('usuarios').stream()
    lista_users = []
    
    for doc in users_ref:
        d = doc.to_dict()
        user_safe = {
            "id": doc.id,
            "nome": d.get('nome', 'Sem Nome'),
            "email": d.get('email', '-'),
            "cpf": d.get('cpf', '-'),
            "tipo_usuario": d.get('tipo_usuario', 'aluno'),
            "equipe": d.get('equipe', '-'),
            "status_exame": d.get('status_exame', 'N/A')
        }
        lista_users.append(user_safe)
        
    df = pd.DataFrame(lista_users)
    
    if not df.empty:
        st.dataframe(df, use_container_width=True, hide_index=True)
        
        # Mudar Tipo de Usuário
        st.subheader("Alterar Permissões")
        c1, c2, c3 = st.columns([2, 1, 1])
        user_sel = c1.selectbox("Selecionar Usuário:", df['nome'].tolist())
        novo_tipo = c2.selectbox("Novo Tipo:", ["aluno", "professor", "admin"])
        
        if c3.button("Atualizar Tipo"):
            uid = df[df['nome'] == user_sel]['id'].values[0]
            db.collection('usuarios').document(uid).update({"tipo_usuario": novo_tipo})
            st.success(f"Permissão de {user_sel} alterada para {novo_tipo}!")
            time.sleep(1) # Agora funciona sem conflito
            st.rerun()

# =========================================
# 2. GESTÃO DE QUESTÕES
# =========================================
def gestao_questoes():
    st.markdown("<h1 style='color:#FFD700;'>📝 Gestão de Questões</h1>", unsafe_allow_html=True)
    db = get_db()

    tab1, tab2 = st.tabs(["📚 Banco de Questões", "➕ Adicionar Nova"])

    # --- TAB 1: LISTAR/EDITAR ---
    with tab1:
        questoes = carregar_todas_questoes()
        
        if not questoes:
            st.info("Nenhuma questão cadastrada no banco.")
        else:
            lista_q = []
            for q in questoes:
                lista_q.append({
                    "id": q.get("id"),
                    "pergunta": q.get("pergunta"),
                    "faixa": q.get("faixa", "Geral"),
                    "resposta_correta": q.get("resposta_correta") or q.get("resposta"),
                    "status": q.get("status", "aprovada")
                })
            
            df = pd.DataFrame(lista_q)
            
            # Edição na Tabela
            st.data_editor(
                df,
                column_config={
                    "status": st.column_config.SelectboxColumn(
                        "Status", options=["aprovada", "pendente", "arquivada"]
                    )
                },
                use_container_width=True,
                hide_index=True,
                key="editor_questoes"
            )
            
            # Deletar Questão
            st.markdown("---")
            col_del, _ = st.columns([1, 3])
            q_to_del = col_del.selectbox("Selecionar para Excluir:", df["pergunta"].unique(), key="sel_del")
            if col_del.button("🗑️ Excluir Questão", type="primary"):
                try:
                    docs = db.collection('questoes').where('pergunta', '==', q_to_del).stream()
                    for doc in docs:
                        doc.reference.delete()
                    st.success("Questão excluída!")
                    time.sleep(1)
                    st.rerun()
                except Exception as e:
                    st.error(f"Erro ao excluir: {e}")

    # --- TAB 2: ADICIONAR NOVA ---
    with tab2:
        with st.form("form_add_q"):
            pergunta = st.text_area("Enunciado da Pergunta:")
            c1, c2 = st.columns(2)
            faixa = c1.selectbox("Nível da Faixa:", ["Todas"] + FAIXAS_COMPLETAS)
            categoria = c2.text_input("Categoria (ex: Regras, História):", "Geral")
            
            st.markdown("**Alternativas:**")
            alt_a = st.text_input("A)")
            alt_b = st.text_input("B)")
            alt_c = st.text_input("C)")
            alt_d = st.text_input("D)")
            
            correta = st.selectbox("Qual a correta?", ["A", "B", "C", "D"])
            
            if st.form_submit_button("💾 Salvar Questão"):
                if pergunta and alt_a and alt_b:
                    nova_q = {
                        "pergunta": pergunta,
                        "faixa": faixa,
                        "categoria": categoria,
                        "alternativas": {
                            "A": alt_a, "B": alt_b, "C": alt_c, "D": alt_d
                        },
                        "resposta_correta": correta,
                        "status": "aprovada",
                        "data_criacao": firestore.SERVER_TIMESTAMP
                    }
                    db.collection('questoes').add(nova_q)
                    st.success("Questão adicionada com sucesso!")
                    time.sleep(1)
                    st.rerun()
                else:
                    st.warning("Preencha pelo menos a pergunta e duas alternativas.")

# =========================================
# 3. GESTÃO DE EXAMES
# =========================================
def gestao_exame_de_faixa():
    st.markdown("<h1 style='color:#FFD700;'>📜 Gestão de Exame</h1>", unsafe_allow_html=True)
    db = get_db()

    tab1, tab2, tab3 = st.tabs(["📝 Criar e Editar Provas", "👁️ Visualizar Provas", "✅ Autorizar Alunos"])

    # --- ABA 1: EDITOR DE PROVAS ---
    with tab1:
        st.subheader("Configurar Regras da Prova")
        faixa_config = st.selectbox("Selecione a Faixa:", ["Todas"] + FAIXAS_COMPLETAS, key="faixa_config")
        
        config_ref = db.collection('config_exames').where('faixa', '==', faixa_config).stream()
        config_atual = {}
        doc_id_config = None
        for doc in config_ref:
            config_atual = doc.to_dict()
            doc_id_config = doc.id
            break
            
        if faixa_config == "Todas":
            snapshots = list(db.collection('questoes').where('status', '==', 'aprovada').stream())
        else:
            s1 = list(db.collection('questoes').where('faixa', '==', faixa_config).where('status', '==', 'aprovada').stream())
            s2 = list(db.collection('questoes').where('faixa', '==', 'Geral').where('status', '==', 'aprovada').stream())
            snapshots = s1 + s2

        questoes_map = {}
        for doc in snapshots:
            d = doc.to_dict(); d['id'] = doc.id
            questoes_map[doc.id] = d
        lista_questoes_obj = list(questoes_map.values())
            
        qtd_disponivel = len(lista_questoes_obj)
        st.info(f"Questões disponíveis: **{qtd_disponivel}**")
        
        modo_atual = config_atual.get('modo_selecao', "🎲 Aleatório (Sorteio)")
        modo_selecao = st.radio("Modo de Seleção:", ["🎲 Aleatório (Sorteio)", "🖐️ Manual (Fixa)"], 
                               index=0 if "Aleatório" in modo_atual else 1, key="modo_selecao")
        
        questoes_escolhidas_manual = []
        qtd_final = 0
        
        if modo_selecao == "🖐️ Manual (Fixa)":
            if qtd_disponivel == 0:
                st.warning("Não há questões para selecionar.")
            else:
                st.markdown("##### Selecione as questões:")
                ids_salvos = set()
                if config_atual.get('questoes'):
                    for q_salva in config_atual['questoes']:
                        if q_salva.get('id'): ids_salvos.add(q_salva.get('id'))
                        else: ids_salvos.add(q_salva.get('pergunta'))

                with st.container(height=400):
                    for i, q in enumerate(lista_questoes_obj):
                        is_checked = (q.get('id') in ids_salvos) or (q.get('pergunta') in ids_salvos)
                        c_chk, c_txt = st.columns([0.5, 10])
                        selecionado = c_chk.checkbox("", value=is_checked, key=f"chk_{faixa_config}_{q.get('id','no_id')}_{i}")
                        if selecionado: questoes_escolhidas_manual.append(q)
                        with c_txt:
                            st.markdown(f"**{q.get('pergunta')}**")
                            st.caption(f"✅ {q.get('resposta')} | Autor: {q.get('criado_por', '?')}")
                            st.markdown("---")
                qtd_final = len(questoes_escolhidas_manual)
                st.success(f"**{qtd_final}** questões selecionadas.")
        
        st.markdown("---")
        c1, c2, c3 = st.columns(3)
        tempo = c1.number_input("⏱️ Tempo (min):", min_value=10, value=int(config_atual.get('tempo_limite', 45)), key="tempo_exame")
        nota = c3.number_input("✅ Nota Mínima (%):", min_value=50, max_value=100, 
                              value=int(config_atual.get('aprovacao_minima', 70)), key="nota_minima")
        
        if modo_selecao == "🎲 Aleatório (Sorteio)":
            max_val = max(qtd_disponivel, 1)
            val_padrao = int(config_atual.get('qtd_questoes', min(10, max_val)))
            qtd_final = c2.number_input("📝 Qtd. Questões:", min_value=1, max_value=max_val, 
                                       value=min(val_padrao, max_val), key="qtd_questoes")
        else:
            c2.text_input("📝 Qtd. Questões:", value=qtd_final, disabled=True, key="qtd_manual")

        st.write("")
        if st.button("💾 Salvar Configuração", type="primary", key="salvar_config"):
            dados_config = {
                "faixa": faixa_config, 
                "tempo_limite": tempo, 
                "qtd_questoes": qtd_final,
                "aprovacao_minima": nota, 
                "modo_selecao": modo_selecao,
                "atualizado_em": firestore.SERVER_TIMESTAMP
            }
            if modo_selecao == "🖐️ Manual (Fixa)":
                if not questoes_escolhidas_manual: 
                    st.error("Selecione pelo menos uma questão para o modo manual.")
                else:
                    dados_config['questoes'] = questoes_escolhidas_manual
                    if doc_id_config: db.collection('config_exames').document(doc_id_config).update(dados_config)
                    else: db.collection('config_exames').add(dados_config)
                    st.success(f"Salvo para Faixa {faixa_config}!")
                    time_lib.sleep(1)
                    st.rerun()
            else:
                dados_config['questoes'] = [] 
                if doc_id_config: db.collection('config_exames').document(doc_id_config).update(dados_config)
                else: db.collection('config_exames').add(dados_config)
                st.success(f"Salvo para Faixa {faixa_config}!")
                time_lib.sleep(1)
                st.rerun()

    # --- ABA 2: VISUALIZAR PROVAS ---
    with tab2:
        st.subheader("Status das Provas Cadastradas")
        configs_stream = db.collection('config_exames').stream()
        mapa_configs = {}
        for doc in configs_stream:
            d = doc.to_dict()
            mapa_configs[d.get('faixa')] = d

        categorias = {
            "🔘 Cinza": ["Cinza e Branca", "Cinza", "Cinza e Preta"],
            "🟡 Amarela": ["Amarela e Branca", "Amarela", "Amarela e Preta"],
            "🟠 Laranja": ["Laranja e Branca", "Laranja", "Laranja e Preta"],
            "🟢 Verde": ["Verde e Branca", "Verde", "Verde e Preta"],
            "🔵 Azul": ["Azul"], "🟣 Roxa": ["Roxa"], "🟤 Marrom": ["Marrom"], "⚫ Preta": ["Preta"]
        }

        abas_cores = st.tabs(list(categorias.keys()))
        for aba, (cor_nome, lista_faixas) in zip(abas_cores, categorias.items()):
            with aba:
                for f_nome in lista_faixas:
                    data = mapa_configs.get(f_nome)
                    if data:
                        modo = data.get('modo_selecao', 'Sorteio')
                        qtd = data.get('qtd_questoes', 0)
                        tempo = data.get('tempo_limite', 0)
                        nota = data.get('aprovacao_minima', 0)
                        with st.expander(f"✅ {f_nome} ({modo} | {qtd} questões)"):
                            st.caption(f"⏱️ Tempo: {tempo} min | 🎯 Mínimo: {nota}%")
                            if modo == "🖐️ Manual (Fixa)" and data.get('questoes'):
                                for i, q in enumerate(data['questoes'], 1):
                                    st.markdown(f"**{i}. {q.get('pergunta')}**")
                                    st.caption(f"Resposta: {q.get('resposta')}")
                                    st.markdown("---")
                            elif modo == "🎲 Aleatório (Sorteio)":
                                st.info(f"Sorteia {qtd} questões.")
                    else:
                        st.warning(f"⚠️ {f_nome} não configurada.")

    # --- ABA 3: AUTORIZAR ALUNOS (CORREÇÃO DE FUSO AQUI) ---
    with tab3:
        with st.container(border=True):
            st.subheader("🗓️ Configurar Período")
            c1, c2 = st.columns(2)
            d_inicio = c1.date_input("Início:", datetime.now(), key="data_inicio_exame")
            d_fim = c2.date_input("Fim:", datetime.now(), key="data_fim_exame")
            c3, c4 = st.columns(2)
            h_inicio = c3.time_input("Hora Início:", time(0, 0), key="hora_inicio_exame")
            h_fim = c4.time_input("Hora Fim:", time(23, 59), key="hora_fim_exame")
            
            # Cria objetos datetime baseados no input (Considera hora local de quem está operando)
            dt_inicio = datetime.combine(d_inicio, h_inicio)
            dt_fim = datetime.combine(d_fim, h_fim)

        st.write("") 
        st.subheader("Lista de Alunos")
        
        try:
            alunos_ref = db.collection('usuarios').where('tipo_usuario', '==', 'aluno').stream()
            lista_alunos = []
            
            for doc in alunos_ref:
                d = doc.to_dict(); d['id'] = doc.id
                nome_eq = "Sem Equipe"
                try:
                    vinculo = list(db.collection('alunos').where('usuario_id', '==', doc.id).limit(1).stream())
                    if vinculo:
                        eid = vinculo[0].to_dict().get('equipe_id')
                        if eid:
                            eq_doc = db.collection('equipes').document(eid).get()
                            if eq_doc.exists: nome_eq = eq_doc.to_dict().get('nome', 'Sem Nome')
                except: pass
                d['nome_equipe'] = nome_eq
                lista_alunos.append(d)

            if not lista_alunos: 
                st.info("Nenhum aluno cadastrado.")
            else:
                cols = st.columns([3, 2, 2, 3, 1])
                cols[0].markdown("**Aluno**")
                cols[1].markdown("**Equipe**")
                cols[2].markdown("**Exame**")
                cols[3].markdown("**Status**")
                cols[4].markdown("**Ação**")
                st.markdown("---")

                for aluno in lista_alunos:
                    try:
                        aluno_id = aluno.get('id', 'unknown')
                        aluno_nome = aluno.get('nome', 'Sem Nome')
                        faixa_exame_atual = aluno.get('faixa_exame', '')
                        
                        c1, c2, c3, c4, c5 = st.columns([3, 2, 2, 3, 1])
                        c1.write(f"**{aluno_nome}**")
                        c2.write(aluno.get('nome_equipe', 'Sem Equipe'))
                        
                        idx = FAIXAS_COMPLETAS.index(faixa_exame_atual) if faixa_exame_atual in FAIXAS_COMPLETAS else 0
                        fx_sel = c3.selectbox("Faixa", FAIXAS_COMPLETAS, index=idx, key=f"fx_select_{aluno_id}", label_visibility="collapsed")
                        
                        habilitado = aluno.get('exame_habilitado', False)
                        status = aluno.get('status_exame', 'pendente')
                        
                        if habilitado:
                            msg = "🟢 Liberado"
                            try:
                                raw_fim = aluno.get('exame_fim')
                                if raw_fim:
                                    if isinstance(raw_fim, str):
                                        dt_obj = datetime.fromisoformat(raw_fim.replace('Z', '+00:00'))
                                        msg += f" (até {dt_obj.strftime('%d/%m/%Y %H:%M')})"
                            except: pass
                            
                            if status == 'aprovado': msg = "🏆 Aprovado"
                            elif status == 'bloqueado': msg = "⛔ Bloqueado"
                            elif status == 'reprovado': msg = "🔴 Reprovado"
                            elif status == 'em_andamento': msg = "🟡 Em Andamento"
                            
                            c4.write(msg)
                            if c5.button("⛔", key=f"off_btn_{aluno_id}"):
                                update_data = {"exame_habilitado": False, "status_exame": "pendente"}
                                for campo in ["exame_inicio", "exame_fim", "faixa_exame", "motivo_bloqueio", "status_exame_em_andamento"]:
                                    if campo in aluno: update_data[campo] = firestore.DELETE_FIELD
                                db.collection('usuarios').document(aluno_id).update(update_data)
                                st.rerun()
                        else:
                            c4.write("⚪ Não autorizado")
                            if c5.button("✅", key=f"on_btn_{aluno_id}"):
                                db.collection('usuarios').document(aluno_id).update({
                                    "exame_habilitado": True,
                                    "faixa_exame": fx_sel,
                                    
                                    # --- CORREÇÃO PRINCIPAL AQUI ---
                                    # Antes estava: firestore.SERVER_TIMESTAMP (Hora de Londres/UTC)
                                    # Agora: dt_inicio.isoformat() (Hora que você escolheu no input)
                                    "exame_inicio": dt_inicio.isoformat(), 
                                    
                                    "exame_fim": dt_fim.isoformat(),
                                    "status_exame": "pendente",
                                    "status_exame_em_andamento": False
                                })
                                st.success(f"Liberado!")
                                time_lib.sleep(0.5)
                                st.rerun()
                        st.markdown("---")
                    except Exception as e:
                        st.error(f"Erro aluno: {e}")
        except Exception as e:
            st.error(f"Erro lista: {e}")

