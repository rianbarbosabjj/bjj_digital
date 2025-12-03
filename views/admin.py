import streamlit as st
import pandas as pd
import bcrypt
import random
import time 
from datetime import datetime, time as dtime 
from database import get_db
from firebase_admin import firestore

try:
    from utils import carregar_todas_questoes, salvar_questoes, fazer_upload_imagem # Importa a nova função
except ImportError:
    def carregar_todas_questoes(): return []
    def salvar_questoes(t, q): pass
    def fazer_upload_imagem(f): return None

FAIXAS_COMPLETAS = [
    "Cinza e Branca", "Cinza", "Cinza e Preta",
    "Amarela e Branca", "Amarela", "Amarela e Preta",
    "Laranja e Branca", "Laranja", "Laranja e Preta",
    "Verde e Branca", "Verde", "Verde e Preta",
    "Azul", "Roxa", "Marrom", "Preta"
]

NIVEIS_DIFICULDADE = [1, 2, 3, 4]
MAPA_NIVEIS = {1: "🟢 Fácil", 2: "🔵 Médio", 3: "🟠 Difícil", 4: "🔴 Muito Difícil"}

def get_badge_nivel(nivel): return MAPA_NIVEIS.get(nivel, "⚪ Nível ?")

# ... (Gestão de Usuários e o resto do arquivo permanece igual, vou focar na Gestão de Questões)

# =========================================
# 2. GESTÃO DE QUESTÕES (ATUALIZADA)
# =========================================
def gestao_questoes():
    st.markdown("<h1 style='color:#FFD700;'>📝 Banco de Questões</h1>", unsafe_allow_html=True)
    db = get_db()
    
    user = st.session_state.usuario
    if str(user.get("tipo", "")).lower() not in ["admin", "professor"]:
        st.error("Acesso negado."); return

    tab1, tab2 = st.tabs(["📚 Listar/Editar", "➕ Adicionar Nova"])

    # --- LISTAR ---
    with tab1:
        questoes_ref = list(db.collection('questoes').stream())
        c_f1, c_f2 = st.columns(2)
        termo = c_f1.text_input("🔍 Buscar no enunciado:")
        filtro_n = c_f2.multiselect("Filtrar Nível:", NIVEIS_DIFICULDADE, format_func=lambda x: MAPA_NIVEIS.get(x, str(x)))

        questoes_filtradas = []
        for doc in questoes_ref:
            d = doc.to_dict(); d['id'] = doc.id
            if termo and termo.lower() not in d.get('pergunta','').lower(): continue
            if filtro_n and d.get('dificuldade', 1) not in filtro_n: continue
            questoes_filtradas.append(d)
            
        if not questoes_filtradas:
            st.info("Nenhuma questão encontrada.")
        else:
            st.caption(f"Exibindo {len(questoes_filtradas)} questões")
            for q in questoes_filtradas:
                with st.container(border=True):
                    c_head, c_btn = st.columns([5, 1])
                    nivel = get_badge_nivel(q.get('dificuldade', 1))
                    cat = q.get('categoria', 'Geral')
                    autor = q.get('criado_por', 'Desconhecido')
                    
                    c_head.markdown(f"**{nivel}** | *{cat}* | ✍️ {autor}")
                    c_head.markdown(f"##### {q.get('pergunta')}")
                    
                    if q.get('url_imagem'): c_head.image(q.get('url_imagem'), width=150)
                    if q.get('url_video'): c_head.markdown(f"📹 [Ver Vídeo]({q.get('url_video')})")

                    with c_head.expander("👁️ Ver Detalhes"):
                        # ... (exibição de alternativas igual)
                        alts = q.get('alternativas', {})
                        if not alts and 'opcoes' in q:
                            ops = q['opcoes']
                            alts = {"A": ops[0], "B": ops[1], "C": ops[2], "D": ops[3]} if len(ops)>=4 else {}
                        st.markdown(f"**A)** {alts.get('A','')} | **B)** {alts.get('B','')} | **C)** {alts.get('C','')} | **D)** {alts.get('D','')}")
                        resp = q.get('resposta_correta') or q.get('correta') or "?"
                        st.success(f"**Correta:** {resp}")

                    if c_btn.button("✏️", key=f"btn_edit_{q['id']}"):
                        st.session_state[f"editing_q"] = q['id']

                # EDIÇÃO
                if st.session_state.get("editing_q") == q['id']:
                    with st.container(border=True):
                        st.markdown("#### ✏️ Editando")
                        with st.form(f"form_edit_{q['id']}"):
                            enunciado = st.text_area("Pergunta:", value=q.get('pergunta',''))
                            
                            st.markdown("🖼️ **Mídia**")
                            c_img, c_vid = st.columns(2)
                            
                            # UPLOAD NA EDIÇÃO
                            novo_arq = c_img.file_uploader("Trocar Imagem:", type=["jpg", "png", "jpeg"], key=f"up_{q['id']}")
                            url_img_atual = q.get('url_imagem','')
                            
                            # Se não fizer upload, mantém a URL antiga (ou permite colar nova)
                            url_img_manual = c_img.text_input("Ou cole URL:", value=url_img_atual)
                            url_vid = c_vid.text_input("Vídeo (YouTube/Vimeo):", value=q.get('url_video',''))

                            c1, c2 = st.columns(2)
                            # ... (Campos de nível e categoria iguais)
                            val_dif = q.get('dificuldade', 1)
                            if not isinstance(val_dif, int): val_dif = 1
                            nv_dif = c1.selectbox("Nível:", NIVEIS_DIFICULDADE, index=NIVEIS_DIFICULDADE.index(val_dif) if val_dif in NIVEIS_DIFICULDADE else 0, format_func=lambda x: MAPA_NIVEIS.get(x, str(x)))
                            nv_cat = c2.text_input("Categoria:", value=q.get('categoria', 'Geral'))
                            
                            # ... (Alternativas e Resposta iguais)
                            alts = q.get('alternativas', {})
                            if not alts and 'opcoes' in q:
                                ops = q['opcoes']; alts = {"A": ops[0], "B": ops[1], "C": ops[2], "D": ops[3]} if len(ops)>=4 else {}
                            ca, cb = st.columns(2); cc, cd = st.columns(2)
                            rA = ca.text_input("A)", value=alts.get('A','')); rB = cb.text_input("B)", value=alts.get('B',''))
                            rC = cc.text_input("C)", value=alts.get('C','')); rD = cd.text_input("D)", value=alts.get('D',''))
                            resp_atual = q.get('resposta_correta', 'A')
                            corr = st.selectbox("Correta:", ["A","B","C","D"], index=["A","B","C","D"].index(resp_atual) if resp_atual in ["A","B","C","D"] else 0)
                            
                            cols = st.columns(2)
                            if cols[0].form_submit_button("💾 Salvar"):
                                # Lógica de Upload
                                final_url_img = url_img_manual
                                if novo_arq:
                                    uploaded_url = fazer_upload_imagem(novo_arq)
                                    if uploaded_url: final_url_img = uploaded_url
                                
                                db.collection('questoes').document(q['id']).update({
                                    "pergunta": enunciado, "dificuldade": nv_dif, "categoria": nv_cat,
                                    "url_imagem": final_url_img, "url_video": url_vid,
                                    "alternativas": {"A":rA, "B":rB, "C":rC, "D":rD},
                                    "resposta_correta": corr, "faixa": firestore.DELETE_FIELD
                                })
                                st.session_state["editing_q"] = None; st.success("Atualizado!"); time.sleep(1); st.rerun()
                            
                            if cols[1].form_submit_button("Cancelar"):
                                st.session_state["editing_q"] = None; st.rerun()
                                
                        if st.button("🗑️ Deletar", key=f"del_q_{q['id']}", type="primary"):
                            db.collection('questoes').document(q['id']).delete()
                            st.session_state["editing_q"] = None; st.success("Deletado."); st.rerun()

    # --- CRIAR ---
    with tab2:
        with st.form("new_q"):
            st.markdown("#### Nova Questão")
            pergunta = st.text_area("Enunciado:")
            
            st.markdown("🖼️ **Mídia (Opcional)**")
            cm1, cm2 = st.columns(2)
            
            # UPLOAD NA CRIAÇÃO
            arq_novo = cm1.file_uploader("Upload Imagem:", type=["jpg", "png", "jpeg"])
            url_img_manual_new = cm1.text_input("Ou URL da Imagem:", help="Se preferir link externo")
            url_vid_new = cm2.text_input("Link do Vídeo (YouTube/Vimeo):")
            
            c1, c2 = st.columns(2)
            dificuldade = c1.selectbox("Nível de Dificuldade:", NIVEIS_DIFICULDADE, format_func=lambda x: MAPA_NIVEIS.get(x, str(x)))
            categoria = c2.text_input("Categoria:", "Geral")
            
            st.markdown("**Alternativas:**")
            ca, cb = st.columns(2); cc, cd = st.columns(2)
            alt_a = ca.text_input("A)"); alt_b = cb.text_input("B)")
            alt_c = cc.text_input("C)"); alt_d = cd.text_input("D)")
            correta = st.selectbox("Correta:", ["A", "B", "C", "D"])
            
            if st.form_submit_button("💾 Cadastrar"):
                if pergunta and alt_a and alt_b:
                    # Processa Upload
                    final_url = url_img_manual_new
                    if arq_novo:
                        up_link = fazer_upload_imagem(arq_novo)
                        if up_link: final_url = up_link
                    
                    db.collection('questoes').add({
                        "pergunta": pergunta, "dificuldade": dificuldade, "categoria": categoria,
                        "url_imagem": final_url, "url_video": url_vid_new,
                        "alternativas": {"A": alt_a, "B": alt_b, "C": alt_c, "D": alt_d},
                        "resposta_correta": correta, "status": "aprovada",
                        "criado_por": user.get('nome', 'Admin'), "data_criacao": firestore.SERVER_TIMESTAMP
                    })
                    st.success("Sucesso!"); time.sleep(1); st.rerun()
                else: st.warning("Preencha enunciado e alternativas.")

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
                        # MOSTRA SE TEM MÍDIA NO SELETOR TAMBÉM
                        midias = []
                        if d.get('url_imagem'): midias.append("🖼️ Imagem")
                        if d.get('url_video'): midias.append("📹 Vídeo")
                        if midias: st.caption(" | ".join(midias))
                        
                        with st.expander("Ver Detalhes"):
                            if d.get('url_imagem'): st.image(d['url_imagem'], width=200)
                            alts = d.get('alternativas', {})
                            if not alts and 'opcoes' in d:
                                ops = d['opcoes']; alts = {"A": ops[0], "B": ops[1], "C": ops[2], "D": ops[3]} if len(ops)>=4 else {}
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
                    dados = {
                        "faixa": faixa_sel, "questoes_ids": list(st.session_state.selected_ids), 
                        "qtd_questoes": total_sel, "tempo_limite": tempo, "aprovacao_minima": nota,
                        "modo_selecao": "Manual", "atualizado_em": firestore.SERVER_TIMESTAMP
                    }
                    if st.session_state.doc_id: db.collection('config_exames').document(st.session_state.doc_id).update(dados)
                    else: db.collection('config_exames').add(dados)
                    st.success("Salvo!"); time.sleep(1.5); st.rerun()

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
            st.subheader("🗓️ Agendar")
            c1, c2 = st.columns(2); d_ini = c1.date_input("Início:", datetime.now()); d_fim = c2.date_input("Fim:", datetime.now())
            c3, c4 = st.columns(2); h_ini = c3.time_input("Hora Ini:", dtime(0,0)); h_fim = c4.time_input("Hora Fim:", dtime(23,59))
            dt_ini = datetime.combine(d_ini, h_ini); dt_fim = datetime.combine(d_fim, h_fim)

        st.markdown("### Alunos")
        users = db.collection('usuarios').where('tipo_usuario','==','aluno').stream()
        cols = st.columns([3,2,2,2,1])
        cols[0].write("**Nome**"); cols[1].write("**Equipe**"); cols[2].write("**Exame**"); cols[3].write("**Status**"); cols[4].write("**Ação**")
        st.divider()
        
        for u in users:
            d = u.to_dict(); uid = u.id
            eq_nome = "-"
            try:
                al_ref = list(db.collection('alunos').where('usuario_id','==',uid).limit(1).stream())
                if al_ref:
                    eid = al_ref[0].to_dict().get('equipe_id')
                    if eid: 
                        eq = db.collection('equipes').document(eid).get()
                        if eq.exists: eq_nome = eq.to_dict().get('nome')
            except: pass

            c1, c2, c3, c4, c5 = st.columns([3,2,2,2,1])
            c1.write(d.get('nome'))
            c2.write(eq_nome)
            idx_f = FAIXAS_COMPLETAS.index(d.get('faixa_exame')) if d.get('faixa_exame') in FAIXAS_COMPLETAS else 0
            fx = c3.selectbox("Faixa", FAIXAS_COMPLETAS, index=idx_f, key=f"f_{uid}", label_visibility="collapsed")
            
            hab = d.get('exame_habilitado', False)
            if hab:
                c4.success("Liberado")
                if c5.button("⛔", key=f"stop_{uid}"):
                    db.collection('usuarios').document(uid).update({"exame_habilitado": False, "status_exame": "pendente", "exame_inicio": firestore.DELETE_FIELD, "exame_fim": firestore.DELETE_FIELD})
                    st.rerun()
            else:
                c4.write("⚪")
                if c5.button("✅", key=f"go_{uid}"):
                    db.collection('usuarios').document(uid).update({"exame_habilitado": True, "faixa_exame": fx, "exame_inicio": dt_ini.isoformat(), "exame_fim": dt_fim.isoformat(), "status_exame": "pendente", "status_exame_em_andamento": False})
                    st.success("OK!"); time.sleep(0.5); st.rerun()
            st.divider()
