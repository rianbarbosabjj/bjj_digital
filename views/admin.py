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

# ... (Gestão de Exame permanece igual) ...
def gestao_exame_de_faixa():
    # ... copie o código da função gestao_exame_de_faixa do admin.py anterior ou mantenha o que já está ...
    # (Para não estourar o limite de caracteres, mantive foco na gestão de questões)
    # Certifique-se de que o resto do arquivo (gestao_exame_de_faixa e gestao_usuarios) esteja presente.
    # Se precisar do arquivo admin.py 100% completo com todas as funções juntas, me avise!
    pass
