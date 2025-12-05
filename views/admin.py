import streamlit as st
import pandas as pd
import bcrypt
import random
import time 
import io  # Necessário para baixar o modelo CSV
from datetime import datetime, time as dtime 
from database import get_db
from firebase_admin import firestore

# Importa a nova função normalizadora
try:
    from utils import carregar_todas_questoes, salvar_questoes, fazer_upload_midia, normalizar_link_video
except ImportError:
    def carregar_todas_questoes(): return []
    def salvar_questoes(t, q): pass
    def fazer_upload_midia(f): return None
    def normalizar_link_video(u): return u

FAIXAS_COMPLETAS = [
    " ", "Cinza e Branca", "Cinza", "Cinza e Preta",
    "Amarela e Branca", "Amarela", "Amarela e Preta",
    "Laranja e Branca", "Laranja", "Laranja e Preta",
    "Verde e Branca", "Verde", "Verde e Preta",
    "Azul", "Roxa", "Marrom", "Preta"
]

NIVEIS_DIFICULDADE = [1, 2, 3, 4]
MAPA_NIVEIS = {1: "🟢 Fácil", 2: "🔵 Médio", 3: "🟠 Difícil", 4: "🔴 Muito Difícil"}

def get_badge_nivel(n): return MAPA_NIVEIS.get(n, "⚪ ?")

# =========================================
# 1. GESTÃO DE USUÁRIOS
# =========================================
def gestao_usuarios(usuario_logado):
    if st.button("🏠 Voltar ao Início", key="btn_voltar_adm"):
        st.session_state.menu_selection = "Início"; st.rerun()

    st.markdown("<h1 style='color:#FFD700;'>👥 Usuários</h1>", unsafe_allow_html=True)
    db = get_db()
    users = [d.to_dict() | {"id": d.id} for d in db.collection('usuarios').stream()]
    if not users: st.warning("Vazio."); return
    df = pd.DataFrame(users)
    cols = ['nome', 'email', 'tipo_usuario', 'faixa_atual']
    for c in cols:
        if c not in df.columns: df[c] = "-"
    st.dataframe(df[cols], use_container_width=True, hide_index=True)
    
    st.markdown("---")
    st.subheader("🛠️ Editar")
    sel = st.selectbox("Usuário:", users, format_func=lambda x: f"{x.get('nome')} ({x.get('email')})")
    if sel:
        with st.form(f"edt_{sel['id']}"):
            nm = st.text_input("Nome:", value=sel.get('nome',''))
            tp = st.selectbox("Tipo:", ["aluno","professor","admin"], index=["aluno","professor","admin"].index(sel.get('tipo_usuario','aluno')))
            fx = st.selectbox("Faixa:", ["Branca"] + FAIXAS_COMPLETAS, index=(["Branca"] + FAIXAS_COMPLETAS).index(sel.get('faixa_atual', 'Branca')) if sel.get('faixa_atual') in FAIXAS_COMPLETAS else 0)
            pwd = st.text_input("Nova Senha:", type="password")
            if st.form_submit_button("Salvar"):
                upd = {"nome": nm.upper(), "tipo_usuario": tp, "faixa_atual": fx}
                if pwd: upd["senha"] = bcrypt.hashpw(pwd.encode(), bcrypt.gensalt()).decode(); upd["precisa_trocar_senha"] = True
                db.collection('usuarios').document(sel['id']).update(upd)
                st.success("Salvo!"); time.sleep(1); st.rerun()
        if st.button("🗑️ Excluir", key=f"del_{sel['id']}"):
            db.collection('usuarios').document(sel['id']).delete()
            st.warning("Excluído."); st.rerun()

# =========================================
# 2. GESTÃO DE QUESTÕES (CORRIGIDO E ATUALIZADO)
# =========================================
def gestao_questoes():
    st.markdown("<h1 style='color:#FFD700;'>📝 Banco de Questões</h1>", unsafe_allow_html=True)
    db = get_db()
    user = st.session_state.usuario
    
    # --- CORREÇÃO DE PERMISSÃO ---
    # Verifica 'tipo_usuario' OU 'tipo' para garantir compatibilidade
    tipo_perm = str(user.get("tipo_usuario", user.get("tipo", ""))).lower()

    if tipo_perm not in ["admin", "professor"]:
        st.error(f"Acesso negado. Seu perfil ({tipo_perm}) não tem permissão.")
        return

    tab1, tab2 = st.tabs(["📚 Listar/Editar", "➕ Adicionar Nova"])

    # --- LISTAR ---
    with tab1:
        q_ref = list(db.collection('questoes').stream())
        c1, c2 = st.columns(2)
        termo = c1.text_input("🔍 Buscar:")
        filt_n = c2.multiselect("Nível:", NIVEIS_DIFICULDADE)
        
        q_filtro = []
        for doc in q_ref:
            d = doc.to_dict(); d['id'] = doc.id
            if termo and termo.lower() not in d.get('pergunta','').lower(): continue
            if filt_n and d.get('dificuldade',1) not in filt_n: continue
            q_filtro.append(d)
            
        if not q_filtro: st.info("Nada encontrado.")
        else:
            st.caption(f"{len(q_filtro)} questões")
            for q in q_filtro:
                with st.container(border=True):
                    ch, cb = st.columns([5, 1])
                    bdg = get_badge_nivel(q.get('dificuldade',1))
                    ch.markdown(f"**{bdg}** | {q.get('categoria','Geral')} | ✍️ {q.get('criado_por','?')}")
                    ch.markdown(f"##### {q.get('pergunta')}")
                    
                    # --- PREVIEW ---
                    if q.get('url_imagem'): ch.image(q.get('url_imagem'), width=150)
                    
                    if q.get('url_video'):
                        link_limpo = normalizar_link_video(q.get('url_video'))
                        try:
                            ch.video(link_limpo)
                        except:
                            ch.markdown(f"🔗 [Ver Vídeo Externo]({q.get('url_video')})")
                    
                    with ch.expander("Alternativas"):
                        alts = q.get('alternativas', {})
                        st.write(f"A) {alts.get('A','')} | B) {alts.get('B','')}")
                        st.write(f"C) {alts.get('C','')} | D) {alts.get('D','')}")
                        st.success(f"Correta: {q.get('resposta_correta')}")
                    
                    if cb.button("✏️", key=f"ed_{q['id']}"): st.session_state['edit_q'] = q['id']
                
                # --- EDITAR ---
                if st.session_state.get('edit_q') == q['id']:
                    with st.container(border=True):
                        st.markdown("#### ✏️ Editando")
                        with st.form(f"f_ed_{q['id']}"):
                            perg = st.text_area("Enunciado:", value=q.get('pergunta',''))
                            
                            st.markdown("🖼️ **Mídia**")
                            c_img, c_vid = st.columns(2)
                            up_img = c_img.file_uploader("Nova Imagem:", type=["jpg","png"], key=f"u_i_{q['id']}")
                            url_i_at = q.get('url_imagem','')
                            if url_i_at: c_img.caption("Imagem atual salva.")
                            
                            up_vid = c_vid.file_uploader("Novo Vídeo (MP4):", type=["mp4","mov"], key=f"u_v_{q['id']}")
                            url_v_at = q.get('url_video','')
                            url_v_manual = c_vid.text_input("Ou Link Externo:", value=url_v_at)
                            
                            c1, c2 = st.columns(2)
                            dif = c1.selectbox("Nível:", NIVEIS_DIFICULDADE, index=NIVEIS_DIFICULDADE.index(q.get('dificuldade',1)))
                            cat = c2.text_input("Categoria:", value=q.get('categoria','Geral'))
                            
                            alts = q.get('alternativas',{})
                            ca, cb_col = st.columns(2); cc, cd = st.columns(2)
                            rA = ca.text_input("A)", alts.get('A','')); rB = cb_col.text_input("B)", alts.get('B',''))
                            rC = cc.text_input("C)", alts.get('C','')); rD = cd.text_input("D)", alts.get('D',''))
                            corr = st.selectbox("Correta:", ["A","B","C","D"], index=["A","B","C","D"].index(q.get('resposta_correta','A')))
                            
                            cols = st.columns(2)
                            if cols[0].form_submit_button("💾 Salvar"):
                                fin_img = url_i_at
                                if up_img:
                                    with st.spinner("Subindo imagem..."): fin_img = fazer_upload_midia(up_img)
                                
                                fin_vid = url_v_manual
                                if up_vid:
                                    with st.spinner("Subindo vídeo..."): fin_vid = fazer_upload_midia(up_vid)
                                
                                db.collection('questoes').document(q['id']).update({
                                    "pergunta": perg, "dificuldade": dif, "categoria": cat,
                                    "url_imagem": fin_img, "url_video": fin_vid,
                                    "alternativas": {"A":rA, "B":rB, "C":rC, "D":rD},
                                    "resposta_correta": corr
                                })
                                st.session_state['edit_q'] = None; st.success("Salvo!"); time.sleep(1); st.rerun()
                                
                            if cols[1].form_submit_button("Cancelar"):
                                st.session_state['edit_q'] = None; st.rerun()
                                
                        if st.button("🗑️ Deletar", key=f"del_q_{q['id']}", type="primary"):
                            db.collection('questoes').document(q['id']).delete()
                            st.session_state['edit_q'] = None; st.success("Deletado."); st.rerun()

    # --- ADICIONAR (Unitário ou Lote) ---
    with tab2:
        sub_tab_manual, sub_tab_lote = st.tabs(["✍️ Manual (Uma)", "📂 Em Lote (Várias)"])

        # >>> OPÇÃO 1: MANUAL <<<
        with sub_tab_manual:
            with st.form("new_q"):
                st.markdown("#### Nova Questão (Individual)")
                perg = st.text_area("Enunciado:")
                st.markdown("🖼️ **Mídia**")
                c1, c2 = st.columns(2)
                up_img = c1.file_uploader("Imagem (JPG/PNG):", type=["jpg","png","jpeg"])
                up_vid = c2.file_uploader("Vídeo (MP4/MOV):", type=["mp4","mov"])
                link_vid = c2.text_input("Ou Link YouTube:")
                
                c3, c4 = st.columns(2)
                dif = c3.selectbox("Nível:", NIVEIS_DIFICULDADE)
                cat = c4.text_input("Categoria:", "Geral")
                
                st.markdown("**Alternativas:**")
                ca, cb_col = st.columns(2); cc, cd = st.columns(2)
                alt_a = ca.text_input("A)"); alt_b = cb_col.text_input("B)")
                alt_c = cc.text_input("C)"); alt_d = cd.text_input("D)")
                correta = st.selectbox("Correta:", ["A","B","C","D"])
                
                if st.form_submit_button("💾 Cadastrar"):
                    if perg and alt_a and alt_b:
                        f_img = fazer_upload_midia(up_img) if up_img else None
                        f_vid = fazer_upload_midia(up_vid) if up_vid else link_vid
                        
                        db.collection('questoes').add({
                            "pergunta": perg, "dificuldade": dif, "categoria": cat,
                            "url_imagem": f_img, "url_video": f_vid,
                            "alternativas": {"A":alt_a, "B":alt_b, "C":alt_c, "D":alt_d},
                            "resposta_correta": correta, "status": "aprovada",
                            "criado_por": user.get('nome', 'Admin'), "data_criacao": firestore.SERVER_TIMESTAMP
                        })
                        st.success("Sucesso!"); time.sleep(1); st.rerun()
                    else: st.warning("Preencha dados básicos.")

        # >>> OPÇÃO 2: EM LOTE (SOMENTE ADMIN) <<<
        with sub_tab_lote:
            # Usa a variável 'tipo_perm' que normaliza o tipo de usuário
            if tipo_perm == "admin":
                st.markdown("#### 📥 Importação em Massa")
                st.info("Utilize esta opção para carregar uma planilha (Excel ou CSV) com várias questões.")

                col_info, col_btn = st.columns([3, 1])
                col_info.markdown("**Instruções:** Baixe o modelo, preencha as questões e faça o upload.")
                
                # DataFrame Modelo
                df_modelo = pd.DataFrame({
                    "pergunta": ["Qual a cor da faixa inicial?", "Quem é o criador do Judô?"],
                    "alt_a": ["Branca", "Helio Gracie"],
                    "alt_b": ["Azul", "Jigoro Kano"],
                    "alt_c": ["Preta", "Mitsuyo Maeda"],
                    "alt_d": ["Rosa", "Conde Koma"],
                    "correta": ["A", "B"],
                    "dificuldade": [1, 2],
                    "categoria": ["História", "História"]
                })
                
                csv_buffer = io.StringIO()
                df_modelo.to_csv(csv_buffer, index=False)
                col_btn.download_button(
                    label="⬇️ Baixar Modelo CSV",
                    data=csv_buffer.getvalue(),
                    file_name="modelo_questoes.csv",
                    mime="text/csv"
                )

                st.markdown("---")
                
                arquivo = st.file_uploader("Selecione o arquivo preenchido:", type=["csv", "xlsx"])

                if arquivo:
                    try:
                        if arquivo.name.endswith('.csv'):
                            df_upload = pd.read_csv(arquivo)
                        else:
                            df_upload = pd.read_excel(arquivo)
                        
                        st.write("Pré-visualização dos dados:")
                        st.dataframe(df_upload.head(3), hide_index=True)
                        st.caption(f"Total de linhas encontradas: {len(df_upload)}")

                        cols_obrigatorias = ["pergunta", "alt_a", "alt_b", "alt_c", "alt_d", "correta"]
                        faltam = [c for c in cols_obrigatorias if c not in df_upload.columns]

                        if faltam:
                            st.error(f"O arquivo está incompleto. Faltam as colunas: {', '.join(faltam)}")
                        else:
                            if st.button("🚀 Importar Todas as Questões", type="primary"):
                                progresso = st.progress(0)
                                success_count = 0
                                error_count = 0

                                for i, row in df_upload.iterrows():
                                    try:
                                        nova_q = {
                                            "pergunta": str(row['pergunta']),
                                            "dificuldade": int(row.get('dificuldade', 1)),
                                            "categoria": str(row.get('categoria', 'Geral')),
                                            "url_imagem": None,
                                            "url_video": None,
                                            "alternativas": {
                                                "A": str(row['alt_a']), "B": str(row['alt_b']),
                                                "C": str(row['alt_c']), "D": str(row['alt_d'])
                                            },
                                            "resposta_correta": str(row['correta']).strip().upper(),
                                            "status": "aprovada",
                                            "criado_por": f"{user.get('nome', 'Admin')} (Import)",
                                            "data_criacao": firestore.SERVER_TIMESTAMP
                                        }
                                        
                                        if nova_q['resposta_correta'] not in ["A", "B", "C", "D"]:
                                            nova_q['resposta_correta'] = "A"

                                        db.collection('questoes').add(nova_q)
                                        success_count += 1
                                    except Exception as e:
                                        error_count += 1
                                        print(f"Erro na linha {i}: {e}")
                                    
                                    progresso.progress((i + 1) / len(df_upload))

                                st.success(f"Processo finalizado! {success_count} importadas com sucesso.")
                                if error_count > 0:
                                    st.warning(f"{error_count} falhas. Verifique o arquivo.")
                                time.sleep(2)
                                st.rerun()

                    except Exception as e:
                        st.error(f"Erro ao ler arquivo: {e}")
            else:
                st.warning("🔒 Esta funcionalidade é restrita aos Administradores.")

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
