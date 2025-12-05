b
# =========================================
# 3. GESTÃO DE EXAME
# =========================================
def gestao_exame_de_faixa():
    st.markdown("<h1 style='color:#FFD700;'>⚙️ Montador de Exames</h1>", unsafe_allow_html=True)
    db = get_db()

    tab1, tab2, tab3 = st.tabs(["📝 Montar Prova", "👁️ Visualizar", "✅ Autorizar Alunos"])

    with tab1:
        st.subheader("1. Selecione a Faixa")
        faixa_sel = st.selectbox("Prova de Faixa:", FAIXAS_COMPLETAS)
        
        if 'last_faixa_sel' not in st.session_state or st.session_state.last_faixa_sel != faixa_sel:
            configs = db.collection('config_exames').where('faixa', '==', faixa_sel).limit(1).stream()
            conf_atual = {}; doc_id = None
            for d in configs: conf_atual = d.to_dict(); doc_id = d.id; break
            
            st.session_state.conf_atual = conf_atual
            st.session_state.doc_id = doc_id
            st.session_state.selected_ids = set(conf_atual.get('questoes_ids', []))
            st.session_state.last_faixa_sel = faixa_sel
        
        conf_atual = st.session_state.conf_atual
        todas_questoes = list(db.collection('questoes').stream())
        
        st.markdown("### 2. Selecione as Questões")
        c_f1, c_f2 = st.columns(2)
        filtro_nivel = c_f1.multiselect("Filtrar Nível:", NIVEIS_DIFICULDADE, default=[1,2,3,4], format_func=lambda x: MAPA_NIVEIS.get(x, str(x)))
        cats = sorted(list(set([d.to_dict().get('categoria', 'Geral') for d in todas_questoes])))
        filtro_tema = c_f2.multiselect("Filtrar Tema:", cats, default=cats)
        
        with st.container(height=500, border=True):
            count_visible = 0
            for doc in todas_questoes:
                d = doc.to_dict()
                niv = d.get('dificuldade', 1)
                cat = d.get('categoria', 'Geral')
                if niv in filtro_nivel and cat in filtro_tema:
                    count_visible += 1
                    c_chk, c_content = st.columns([1, 15])
                    is_checked = doc.id in st.session_state.selected_ids
                    
                    def update_selection(qid=doc.id):
                        if st.session_state[f"chk_{qid}"]: st.session_state.selected_ids.add(qid)
                        else: st.session_state.selected_ids.discard(qid)

                    c_chk.checkbox("", value=is_checked, key=f"chk_{doc.id}", on_change=update_selection)
                    with c_content:
                        badge = get_badge_nivel(niv)
                        autor = d.get('criado_por', '?')
                        st.markdown(f"**{badge}** | {cat} | ✍️ {autor}")
                        st.markdown(f"{d.get('pergunta')}")
                        if d.get('url_imagem'): st.image(d.get('url_imagem'), width=150)
                        
                        with st.expander("Ver Detalhes"):
                            alts = d.get('alternativas', {})
                            st.markdown(f"**A)** {alts.get('A','')} | **B)** {alts.get('B','')}")
                            st.markdown(f"**C)** {alts.get('C','')} | **D)** {alts.get('D','')}")
                            st.info(f"✅ Correta: {d.get('resposta_correta') or 'A'}")
                    st.divider()
            if count_visible == 0: st.warning("Nada encontrado.")

        total_sel = len(st.session_state.selected_ids)
        c_res1, c_res2 = st.columns([3, 1])
        c_res1.success(f"**{total_sel}** questões selecionadas para **{faixa_sel}**.")
        if total_sel > 0:
            if c_res2.button("🗑️ Limpar", key="clean_sel"):
                st.session_state.selected_ids = set(); st.rerun()
        
        st.markdown("### 3. Regras de Aplicação")
        with st.form("save_conf"):
            c1, c2 = st.columns(2)
            tempo = c1.number_input("Tempo (min):", 10, 180, int(conf_atual.get('tempo_limite', 45)))
            nota = c2.number_input("Aprovação (%):", 10, 100, int(conf_atual.get('aprovacao_minima', 70)))
            if st.form_submit_button("💾 Salvar Prova"):
                if total_sel == 0: st.error("Selecione questões.")
                else:
                    try:
                        dados = {
                            "faixa": faixa_sel, "questoes_ids": list(st.session_state.selected_ids), 
                            "qtd_questoes": total_sel, "tempo_limite": tempo, "aprovacao_minima": nota,
                            "modo_selecao": "Manual", "atualizado_em": firestore.SERVER_TIMESTAMP
                        }
                        if st.session_state.doc_id:
                            # Tenta atualizar, se falhar (doc apagado), cria novo
                            try: db.collection('config_exames').document(st.session_state.doc_id).update(dados)
                            except: db.collection('config_exames').add(dados)
                        else:
                            db.collection('config_exames').add(dados)
                        st.success("Salvo!"); time.sleep(1.5); st.rerun()
                    except Exception as e: st.error(f"Erro ao salvar: {e}")

    with tab2:
        st.write("Configurações atuais:")
        for doc in db.collection('config_exames').stream():
            d = doc.to_dict()
            with st.expander(f"✅ {d.get('faixa')} ({d.get('qtd_questoes')} questões)"):
                st.caption(f"⏱️ {d.get('tempo_limite')} min | 🎯 Min: {d.get('aprovacao_minima')}%")
                if st.button("🗑️ Excluir Config", key=f"del_conf_{doc.id}"):
                    db.collection('config_exames').document(doc.id).delete()
                    st.success("Deletado."); st.rerun()

    with tab3:
        with st.container(border=True):
            st.subheader("🗓️ Configurar Período")
            c1, c2 = st.columns(2); d_ini = c1.date_input("Início:", datetime.now(), key="data_inicio_exame")
            d_fim = c2.date_input("Fim:", datetime.now(), key="data_fim_exame")
            c3, c4 = st.columns(2); h_ini = c3.time_input("Hora Ini:", dtime(0,0)); h_fim = c4.time_input("Hora Fim:", dtime(23,59))
            dt_ini = datetime.combine(d_ini, h_ini); dt_fim = datetime.combine(d_fim, h_fim)

        st.write(""); st.subheader("Lista de Alunos")
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
                        eq_doc = db.collection('equipes').document(eid).get()
                        if eq_doc.exists: nome_eq = eq_doc.to_dict().get('nome', 'Sem Nome')
                except: pass
                d['nome_equipe'] = nome_eq
                lista_alunos.append(d)

            if not lista_alunos: st.info("Nenhum aluno cadastrado.")
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
                        
                        msg_status = "⚪ Não autorizado"
                        if status == 'aprovado': msg_status = "🏆 Aprovado"
                        elif status == 'reprovado': msg_status = "🔴 Reprovado"
                        elif status == 'bloqueado': msg_status = "⛔ Bloqueado"
                        elif habilitado:
                            msg_status = "🟢 Liberado"
                            try:
                                raw_fim = aluno.get('exame_fim')
                                if raw_fim:
                                    dt_obj = datetime.fromisoformat(raw_fim.replace('Z', '+00:00')) if isinstance(raw_fim, str) else raw_fim
                                    msg_status += f" (até {dt_obj.strftime('%d/%m %H:%M')})"
                            except: pass
                            if status == 'em_andamento': msg_status = "🟡 Em Andamento"

                        c4.write(msg_status)
                        
                        if habilitado:
                            if c5.button("⛔", key=f"off_btn_{aluno_id}"):
                                update_data = {"exame_habilitado": False, "status_exame": "pendente"}
                                for k in ["exame_inicio", "exame_fim", "faixa_exame", "motivo_bloqueio", "status_exame_em_andamento"]:
                                    if k in aluno: update_data[k] = firestore.DELETE_FIELD
                                db.collection('usuarios').document(aluno_id).update(update_data)
                                st.rerun()
                        else:
                            if c5.button("✅", key=f"on_btn_{aluno_id}"):
                                db.collection('usuarios').document(aluno_id).update({
                                    "exame_habilitado": True, "faixa_exame": fx_sel,
                                    "exame_inicio": dt_ini.isoformat(), "exame_fim": dt_fim.isoformat(),
                                    "status_exame": "pendente", "status_exame_em_andamento": False
                                })
                                st.success("Liberado!"); time.sleep(0.5); st.rerun()
                        st.markdown("---")
                    except Exception as e: st.error(f"Erro: {e}")
        except: st.error("Erro ao carregar alunos.")
