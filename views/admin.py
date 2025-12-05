import streamlit as st
import pandas as pd
import bcrypt
import time 
import io 
from datetime import datetime, date, time as dtime 
from database import get_db, OPCOES_SEXO
from firebase_admin import firestore

# Importa o Dashboard separado
from views.dashboard_admin import render_dashboard_geral

# Importa utils com a nova função de IA
try:
    from utils import (
        carregar_todas_questoes, 
        salvar_questoes, 
        fazer_upload_midia, 
        normalizar_link_video, 
        verificar_duplicidade_ia 
    )
except ImportError:
    def carregar_todas_questoes(): return []
    def salvar_questoes(t, q): pass
    def fazer_upload_midia(f): return None
    def normalizar_link_video(u): return u
    def verificar_duplicidade_ia(n, l, t=0.85): return False, None

# --- CONSTANTES ---
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
# GESTÃO DE USUÁRIOS (TAB INTERNA)
# =========================================
def gestao_usuarios_tab():
    db = get_db()
    users = [d.to_dict() | {"id": d.id} for d in db.collection('usuarios').stream()]
    if not users: st.warning("Vazio."); return
    
    df = pd.DataFrame(users)
    c1, c2 = st.columns(2)
    filtro_nome = c1.text_input("🔍 Buscar Nome/Email:")
    filtro_tipo = c2.multiselect("Filtrar Tipo:", df['tipo_usuario'].unique() if 'tipo_usuario' in df.columns else [])

    if filtro_nome:
        df = df[df['nome'].str.contains(filtro_nome.upper()) | df['email'].str.contains(filtro_nome.lower())]
    if filtro_tipo:
        df = df[df['tipo_usuario'].isin(filtro_tipo)]

    cols_show = ['nome', 'email', 'tipo_usuario', 'faixa_atual', 'sexo']
    for c in cols_show: 
        if c not in df.columns: df[c] = "-"
    
    st.dataframe(df[cols_show], use_container_width=True, hide_index=True)
    
    st.markdown("---")
    st.subheader("🛠️ Editar Usuário")
    
    opcoes = df.to_dict('records')
    sel = st.selectbox("Selecione para editar:", opcoes, format_func=lambda x: f"{x.get('nome')} | {x.get('tipo_usuario')}")
    
    if sel:
        with st.form(f"edt_{sel['id']}"):
            c1, c2 = st.columns(2)
            nm = c1.text_input("Nome:", value=sel.get('nome',''))
            tp = c2.selectbox("Tipo:", ["aluno","professor","admin"], index=["aluno","professor","admin"].index(sel.get('tipo_usuario','aluno')))
            
            c3, c4 = st.columns(2)
            fx = c3.selectbox("Faixa:", ["Branca"] + FAIXAS_COMPLETAS, index=(["Branca"] + FAIXAS_COMPLETAS).index(sel.get('faixa_atual', 'Branca')) if sel.get('faixa_atual') in FAIXAS_COMPLETAS else 0)
            
            idx_s = 0
            if sel.get('sexo') in OPCOES_SEXO: idx_s = OPCOES_SEXO.index(sel.get('sexo'))
            sexo_edit = c4.selectbox("Sexo:", OPCOES_SEXO, index=idx_s)
            
            val_n = None
            if sel.get('data_nascimento'):
                try: val_n = datetime.fromisoformat(sel.get('data_nascimento')).date()
                except: pass
            nasc_edit = st.date_input("Nascimento:", value=val_n, min_value=date(1940,1,1), max_value=date.today(), format="DD/MM/YYYY")

            pwd = st.text_input("Nova Senha (opcional):", type="password")
            
            if st.form_submit_button("Salvar Alterações"):
                upd = {
                    "nome": nm.upper(), "tipo_usuario": tp, "faixa_atual": fx,
                    "sexo": sexo_edit, "data_nascimento": nasc_edit.isoformat() if nasc_edit else None
                }
                if pwd: 
                    upd["senha"] = bcrypt.hashpw(pwd.encode(), bcrypt.gensalt()).decode()
                    upd["precisa_trocar_senha"] = True
                
                db.collection('usuarios').document(sel['id']).update(upd)
                st.success("Salvo!"); time.sleep(1); st.rerun()
                
        if st.button("🗑️ Excluir Usuário", key=f"del_{sel['id']}"):
            db.collection('usuarios').document(sel['id']).delete()
            st.warning("Usuário excluído."); st.rerun()

# =========================================
# GESTÃO DE QUESTÕES (Mantido para acesso externo)
# =========================================
def gestao_questoes_tab():
    db = get_db()
    user = st.session_state.usuario
    tab1, tab2 = st.tabs(["📚 Listar/Editar", "➕ Adicionar Nova"])

    with tab1:
        q_ref = list(db.collection('questoes').stream())
        c1, c2 = st.columns(2)
        termo = c1.text_input("🔍 Buscar Questão:")
        filt_n = c2.multiselect("Nível:", NIVEIS_DIFICULDADE)
        
        q_filtro = []
        for doc in q_ref:
            d = doc.to_dict(); d['id'] = doc.id
            if termo and termo.lower() not in d.get('pergunta','').lower(): continue
            if filt_n and d.get('dificuldade',1) not in filt_n: continue
            q_filtro.append(d)
            
        if not q_filtro: st.info("Nada encontrado.")
        else:
            st.caption(f"{len(q_filtro)} questões encontradas")
            for q in q_filtro:
                with st.container(border=True):
                    ch, cb = st.columns([5, 1])
                    bdg = get_badge_nivel(q.get('dificuldade',1))
                    ch.markdown(f"**{bdg}** | {q.get('categoria','Geral')} | ✍️ {q.get('criado_por','?')}")
                    ch.markdown(f"##### {q.get('pergunta')}")
                    
                    if q.get('url_imagem'): ch.image(q.get('url_imagem'), width=150)
                    if cb.button("✏️", key=f"ed_{q['id']}"): st.session_state['edit_q'] = q['id']
                
                if st.session_state.get('edit_q') == q['id']:
                    with st.container(border=True):
                        st.markdown("#### ✏️ Editando")
                        with st.form(f"f_ed_{q['id']}"):
                            perg = st.text_area("Enunciado:", value=q.get('pergunta',''))
                            c_img, c_vid = st.columns(2)
                            up_img = c_img.file_uploader("Nova Imagem:", type=["jpg","png"], key=f"u_i_{q['id']}")
                            url_i_at = q.get('url_imagem','')
                            up_vid = c_vid.file_uploader("Novo Vídeo:", type=["mp4","mov"], key=f"u_v_{q['id']}")
                            url_v_manual = c_vid.text_input("Link Externo:", value=q.get('url_video',''))
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
                                if up_img: fin_img = fazer_upload_midia(up_img)
                                fin_vid = url_v_manual
                                if up_vid: fin_vid = fazer_upload_midia(up_vid)
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

    with tab2:
        sub_tab_manual, sub_tab_lote = st.tabs(["✍️ Manual (Uma)", "📂 Em Lote (Várias)"])
        with sub_tab_manual:
            with st.form("new_q"):
                st.markdown("#### Nova Questão")
                perg = st.text_area("Enunciado:")
                c1, c2 = st.columns(2)
                up_img = c1.file_uploader("Imagem:", type=["jpg","png"])
                up_vid = c2.file_uploader("Vídeo:", type=["mp4"])
                link_vid = c2.text_input("Link YouTube:")
                c3, c4 = st.columns(2)
                dif = c3.selectbox("Nível:", NIVEIS_DIFICULDADE)
                cat = c4.text_input("Categoria:", "Geral")
                ca, cb_col = st.columns(2); cc, cd = st.columns(2)
                alt_a = ca.text_input("A)"); alt_b = cb_col.text_input("B)")
                alt_c = cc.text_input("C)"); alt_d = cd.text_input("D)")
                correta = st.selectbox("Correta:", ["A","B","C","D"])
                
                if st.form_submit_button("💾 Cadastrar"):
                    if perg and alt_a and alt_b:
                        # --- BLOCO DE IA / ANTI-DUPLICIDADE ---
                        with st.spinner("🤖 A IA está verificando duplicidade semântica..."):
                            all_qs_snap = list(db.collection('questoes').stream())
                            lista_qs = [d.to_dict() for d in all_qs_snap]
                            is_dup, dup_msg = verificar_duplicidade_ia(perg, lista_qs, threshold=0.85)
                            
                            if is_dup:
                                st.error("⚠️ Bloqueado: A IA detectou uma questão semanticamente idêntica!")
                                st.warning(f"Similar encontrada: {dup_msg}")
                                st.info("Altere a redação se for uma questão realmente nova.")
                                st.stop()
                        # --------------------------------------

                        f_img = fazer_upload_midia(up_img) if up_img else None
                        f_vid = fazer_upload_midia(up_vid) if up_vid else link_vid
                        db.collection('questoes').add({
                            "pergunta": perg, "dificuldade": dif, "categoria": cat,
                            "url_imagem": f_img, "url_video": f_vid,
                            "alternativas": {"A":alt_a, "B":alt_b, "C":alt_c, "D":alt_d},
                            "resposta_correta": correta, "status": "aprovada",
                            "criado_por": user.get('nome', 'Admin'), "data_criacao": firestore.SERVER_TIMESTAMP
                        })
                        st.success("Sucesso! Questão cadastrada."); time.sleep(1); st.rerun()
                    else:
                        st.warning("Preencha dados básicos.")
        
        with sub_tab_lote:
             st.info("Utilize esta opção para carregar uma planilha (Excel ou CSV).")
             col_info, col_btn = st.columns([3, 1])
             df_modelo = pd.DataFrame({
                "pergunta": ["Qual a cor da faixa inicial?"], "alt_a": ["Branca"], "alt_b": ["Azul"], "alt_c": ["Preta"], "alt_d": ["Rosa"],
                "correta": ["A"], "dificuldade": [1], "categoria": ["História"]
             })
             csv_buffer = io.StringIO()
             df_modelo.to_csv(csv_buffer, index=False)
             col_btn.download_button("⬇️ Modelo CSV", data=csv_buffer.getvalue(), file_name="modelo.csv", mime="text/csv")
             arquivo = st.file_uploader("Upload CSV/XLSX:", type=["csv", "xlsx"])
             if arquivo:
                 if st.button("🚀 Importar"):
                     st.success("Importação simulada.")

# =========================================
# GESTÃO DE EXAMES (Mantido para acesso externo)
# =========================================
def gestao_exames_tab():
    st.markdown("### ⚙️ Montador de Exames")
    db = get_db()
    tab1, tab2, tab3 = st.tabs(["📝 Montar Prova", "👁️ Visualizar Configs", "✅ Autorizar Alunos"])
    
    with tab1:
        st.subheader("Configurar Prova por Faixa")
        faixa_sel = st.selectbox("Faixa Alvo:", FAIXAS_COMPLETAS)
        configs = list(db.collection('config_exames').where('faixa', '==', faixa_sel).limit(1).stream())
        conf_atual = configs[0].to_dict() if configs else {}
        doc_id = configs[0].id if configs else None
        if 'sel_ids' not in st.session_state: st.session_state.sel_ids = set(conf_atual.get('questoes_ids', []))

        c1, c2 = st.columns(2)
        tempo = c1.number_input("Tempo (min):", 10, 180, int(conf_atual.get('tempo_limite', 45)))
        nota = c2.number_input("Aprovação (%):", 10, 100, int(conf_atual.get('aprovacao_minima', 70)))
        
        st.write("Selecione as questões abaixo:")
        all_q = list(db.collection('questoes').stream())
        cf1, cf2 = st.columns(2)
        filtro_dif = cf1.multiselect("Dificuldade:", NIVEIS_DIFICULDADE, default=[1,2])
        filtro_cat = cf2.text_input("Filtrar Categoria:")
        
        with st.container(height=400, border=True):
            for doc in all_q:
                d = doc.to_dict()
                if d.get('dificuldade',1) not in filtro_dif: continue
                if filtro_cat and filtro_cat.lower() not in d.get('categoria','').lower(): continue
                chk = st.checkbox(f"{d.get('pergunta')} ({d.get('categoria')})", value=(doc.id in st.session_state.sel_ids), key=f"ex_{doc.id}")
                if chk: st.session_state.sel_ids.add(doc.id)
                else: st.session_state.sel_ids.discard(doc.id)
        
        if st.button("💾 Salvar Configuração"):
            dados = {"faixa": faixa_sel, "questoes_ids": list(st.session_state.sel_ids), "qtd_questoes": len(st.session_state.sel_ids), "tempo_limite": tempo, "aprovacao_minima": nota, "atualizado_em": firestore.SERVER_TIMESTAMP}
            if doc_id: db.collection('config_exames').document(doc_id).update(dados)
            else: db.collection('config_exames').add(dados)
            st.success("Salvo!"); st.rerun()

    with tab2:
        st.write("Configurações Salvas:")
        for d in db.collection('config_exames').stream():
            dt = d.to_dict()
            with st.expander(f"Faixa {dt.get('faixa')}"):
                st.write(f"Questões: {dt.get('qtd_questoes')} | Tempo: {dt.get('tempo_limite')}m")
                if st.button("Excluir", key=f"del_c_{d.id}"):
                    db.collection('config_exames').document(d.id).delete(); st.rerun()

    with tab3:
        st.subheader("Liberação de Exame")
        c1, c2 = st.columns(2)
        d_ini = c1.date_input("Início:", datetime.now(), format="DD/MM/YYYY")
        d_fim = c2.date_input("Fim:", datetime.now(), format="DD/MM/YYYY")
        dt_ini = datetime.combine(d_ini, dtime(0,0)); dt_fim = datetime.combine(d_fim, dtime(23,59))

        alunos = list(db.collection('usuarios').where('tipo_usuario', '==', 'aluno').stream())
        if not alunos: st.info("Sem alunos.")
        else:
            for doc in alunos:
                a = doc.to_dict()
                c1, c2, c3 = st.columns([3, 2, 1])
                c1.write(f"**{a.get('nome')}** ({a.get('faixa_atual')})")
                c2.write(f"Status: {a.get('status_exame', 'pendente')}")
                if a.get('exame_habilitado'):
                    if c3.button("Bloquear", key=f"blk_{doc.id}"):
                        db.collection('usuarios').document(doc.id).update({"exame_habilitado": False}); st.rerun()
                else:
                    fx_alvo = c2.selectbox("Faixa Exame:", FAIXAS_COMPLETAS, key=f"fx_{doc.id}")
                    if c3.button("Liberar", key=f"lib_{doc.id}"):
                        db.collection('usuarios').document(doc.id).update({"exame_habilitado": True, "faixa_exame": fx_alvo, "exame_inicio": dt_ini.isoformat(), "exame_fim": dt_fim.isoformat(), "status_exame": "pendente", "status_exame_em_andamento": False}); st.success("Liberado!"); st.rerun()
                st.divider()

# =========================================
# CONTROLADOR PRINCIPAL (ATUALIZADO)
# =========================================
def gestao_questoes(): gestao_questoes_tab()
def gestao_exame_de_faixa(): gestao_exames_tab()

def gestao_usuarios(usuario_logado):
    st.markdown(f"<h1 style='color:#FFD700;'>Gestão e Estatísticas</h1>", unsafe_allow_html=True)
    
    # Menu simplificado, sem questões e exames (já estão na sidebar)
    menu = st.radio("", ["📊 Dashboard", "👥 Usuários"], 
                    horizontal=True, label_visibility="collapsed")
    st.markdown("---")
    
    if menu == "📊 Dashboard": render_dashboard_geral()
    elif menu == "👥 Usuários": gestao_usuarios_tab()
