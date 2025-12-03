import streamlit as st
import pandas as pd
import bcrypt
import random
import time 
from datetime import datetime, time as dtime 
from database import get_db
from firebase_admin import firestore

# Importa a nova função renomeada
try:
    from utils import carregar_todas_questoes, salvar_questoes, fazer_upload_midia
except ImportError:
    def carregar_todas_questoes(): return []
    def salvar_questoes(t, q): pass
    def fazer_upload_midia(f): return None

FAIXAS_COMPLETAS = ["Cinza", "Amarela", "Laranja", "Verde", "Azul", "Roxa", "Marrom", "Preta"]
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
# 2. GESTÃO DE QUESTÕES (IMAGEM + VÍDEO)
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
                        if "firebasestorage" in q.get('url_video') or "youtube" in q.get('url_video'):
                             ch.video(q.get('url_video'))
                        else:
                             ch.markdown(f"[Ver Vídeo]({q.get('url_video')})")
                    
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
                            
                            # UPLOAD IMAGEM
                            up_img = c_img.file_uploader("Nova Imagem:", type=["jpg","png"], key=f"u_i_{q['id']}")
                            url_i_at = q.get('url_imagem','')
                            if url_i_at: c_img.caption("Imagem atual salva.")
                            
                            # UPLOAD VÍDEO
                            up_vid = c_vid.file_uploader("Novo Vídeo (MP4):", type=["mp4","mov"], key=f"u_v_{q['id']}")
                            url_v_at = q.get('url_video','')
                            
                            # Campo manual como fallback
                            url_v_manual = c_vid.text_input("Ou Link Externo (YouTube):", value=url_v_at)
                            
                            c1, c2 = st.columns(2)
                            dif = c1.selectbox("Nível:", NIVEIS_DIFICULDADE, index=NIVEIS_DIFICULDADE.index(q.get('dificuldade',1)))
                            cat = c2.text_input("Categoria:", value=q.get('categoria','Geral'))
                            
                            alts = q.get('alternativas',{})
                            ca, cb = st.columns(2); cc, cd = st.columns(2)
                            rA = ca.text_input("A)", alts.get('A','')); rB = cb.text_input("B)", alts.get('B',''))
                            rC = cc.text_input("C)", alts.get('C','')); rD = cd.text_input("D)", alts.get('D',''))
                            corr = st.selectbox("Correta:", ["A","B","C","D"], index=["A","B","C","D"].index(q.get('resposta_correta','A')))
                            
                            cols = st.columns(2)
                            if cols[0].form_submit_button("💾 Salvar"):
                                # Processa Uploads
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

    # --- ADICIONAR ---
    with tab2:
        with st.form("new_q"):
            st.markdown("#### Nova Questão")
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
            ca, cb = st.columns(2); cc, cd = st.columns(2)
            alt_a = ca.text_input("A)"); alt_b = cb.text_input("B)")
            alt_c = cc.text_input("C)"); alt_d = cd.text_input("D)")
            corr = st.selectbox("Correta:", ["A","B","C","D"])
            
            if st.form_submit_button("💾 Cadastrar"):
                if perg and alt_a and alt_b:
                    f_img = fazer_upload_midia(up_img) if up_img else None
                    f_vid = fazer_upload_midia(up_vid) if up_vid else link_vid
                    
                    db.collection('questoes').add({
                        "pergunta": perg, "dificuldade": dif, "categoria": cat,
                        "url_imagem": f_img, "url_video": f_vid,
                        "alternativas": {"A":alt_a, "B":alt_b, "C":alt_c, "D":alt_d},
                        "resposta_correta": corr, "status": "aprovada",
                        "criado_por": user.get('nome', 'Admin'), "data_criacao": firestore.SERVER_TIMESTAMP
                    })
                    st.success("Sucesso!"); time.sleep(1); st.rerun()
                else: st.warning("Preencha dados básicos.")

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
            st.session_state.conf_atual = conf_atual; st.session_state.doc_id = doc_id
            st.session_state.selected_ids = set(conf_atual.get('questoes_ids', []))
            st.session_state.last_faixa_sel = faixa_sel
        
        conf_atual = st.session_state.conf_atual
        all_qs = list(db.collection('questoes').stream())
        
        st.markdown("### 2. Selecione as Questões")
        c1, c2 = st.columns(2)
        f_niv = c1.multiselect("Nível:", NIVEIS_DIFICULDADE, default=[1,2,3,4])
        cats = sorted(list(set([d.to_dict().get('categoria', 'Geral') for d in all_qs])))
        f_cat = c2.multiselect("Tema:", cats, default=cats)
        
        with st.container(height=500, border=True):
            vis = 0
            for doc in all_qs:
                d = doc.to_dict()
                if d.get('dificuldade',1) in f_niv and d.get('categoria','Geral') in f_cat:
                    vis += 1
                    cc, ct = st.columns([1, 15])
                    chk = cc.checkbox("", doc.id in st.session_state.selected_ids, key=f"chk_{doc.id}")
                    if chk: st.session_state.selected_ids.add(doc.id)
                    else: st.session_state.selected_ids.discard(doc.id)
                    
                    with ct:
                        st.markdown(f"**{get_badge_nivel(d.get('dificuldade',1))}** | {d.get('categoria')}")
                        st.markdown(d.get('pergunta'))
                        if d.get('url_imagem'): st.image(d.get('url_imagem'), width=100)
                        if d.get('url_video'): st.caption("📹 Tem vídeo")
                    st.divider()
            if vis == 0: st.warning("Nada encontrado.")

        tot = len(st.session_state.selected_ids)
        st.success(f"**{tot}** questões selecionadas.")
        
        with st.form("sf"):
            c1, c2 = st.columns(2)
            tmp = c1.number_input("Tempo (min):", 10, 180, int(conf_atual.get('tempo_limite', 45)))
            nota = c2.number_input("Aprovação (%):", 10, 100, int(conf_atual.get('aprovacao_minima', 70)))
            if st.form_submit_button("💾 Salvar"):
                dados = {"faixa": faixa_sel, "questoes_ids": list(st.session_state.selected_ids), "qtd_questoes": tot, "tempo_limite": tmp, "aprovacao_minima": nota, "modo_selecao": "Manual", "atualizado_em": firestore.SERVER_TIMESTAMP}
                if st.session_state.doc_id: db.collection('config_exames').document(st.session_state.doc_id).update(dados)
                else: db.collection('config_exames').add(dados)
                st.success("Salvo!"); time.sleep(1); st.rerun()

    with tab2:
        st.write("Configurações:")
        for doc in db.collection('config_exames').stream():
            d = doc.to_dict()
            with st.expander(f"✅ {d.get('faixa')} ({d.get('qtd_questoes')} questões)"):
                st.caption(f"Tempo: {d.get('tempo_limite')} min | Nota: {d.get('aprovacao_minima')}%")
                if st.button("🗑️ Excluir", key=f"d_{doc.id}"):
                    db.collection('config_exames').document(doc.id).delete(); st.rerun()

    with tab3:
        with st.container(border=True):
            st.subheader("🗓️ Agendar")
            c1, c2 = st.columns(2); di = c1.date_input("Início:", datetime.now()); df = c2.date_input("Fim:", datetime.now())
            c3, c4 = st.columns(2); hi = c3.time_input("Hora Ini:", dtime(0,0)); hf = c4.time_input("Hora Fim:", dtime(23,59))
            dti = datetime.combine(di, hi); dtf = datetime.combine(df, hf)

        st.markdown("### Alunos")
        users = db.collection('usuarios').where('tipo_usuario','==','aluno').stream()
        cols = st.columns([3,2,2,3,1])
        cols[0].write("Nome"); cols[1].write("Equipe"); cols[2].write("Exame"); cols[3].write("Status"); cols[4].write("Ação")
        st.divider()
        
        for u in users:
            d = u.to_dict(); uid = u.id
            en = "-"
            try:
                al = list(db.collection('alunos').where('usuario_id','==',uid).limit(1).stream())
                if al:
                    eid = al[0].to_dict().get('equipe_id')
                    eq = db.collection('equipes').document(eid).get()
                    if eq.exists: en = eq.to_dict().get('nome')
            except: pass

            c1, c2, c3, c4, c5 = st.columns([3,2,2,3,1])
            c1.write(d.get('nome'))
            c2.write(en)
            idx = FAIXAS_COMPLETAS.index(d.get('faixa_exame')) if d.get('faixa_exame') in FAIXAS_COMPLETAS else 0
            fx = c3.selectbox("Faixa", FAIXAS_COMPLETAS, index=idx, key=f"f_{uid}", label_visibility="collapsed")
            
            hab = d.get('exame_habilitado', False)
            stt = d.get('status_exame', 'pendente')
            msg = "⚪"
            if stt == 'aprovado': msg = "🏆 Aprovado"
            elif stt == 'reprovado': msg = "🔴 Reprovado"
            elif stt == 'bloqueado': msg = "⛔ Bloqueado"
            elif hab: msg = "🟢 Liberado"
            
            c4.write(msg)
            
            if hab:
                if c5.button("⛔", key=f"stop_{uid}"):
                    db.collection('usuarios').document(uid).update({"exame_habilitado": False, "status_exame": "pendente"})
                    st.rerun()
            else:
                if c5.button("✅", key=f"go_{uid}"):
                    db.collection('usuarios').document(uid).update({"exame_habilitado": True, "faixa_exame": fx, "exame_inicio": dti.isoformat(), "exame_fim": dtf.isoformat(), "status_exame": "pendente", "status_exame_em_andamento": False})
                    st.success("OK"); time.sleep(0.5); st.rerun()
            st.divider()
