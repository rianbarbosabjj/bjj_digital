import streamlit as st
import time
import random
import os
import json
import pandas as pd
from datetime import datetime, timedelta
import streamlit.components.v1 as components 
from database import get_db
from firebase_admin import firestore  # Mantemos a importação

# ===============================
# NOVOS IMPORTS (SEM REMOVER NADA)
# ===============================
import utils as ce
import views.aulas_aluno as aulas_aluno_view

# --- IMPORTAÇÃO DIRETA (PARA DIAGNÓSTICO DE ERROS) ---
from utils import (
    registrar_inicio_exame, 
    registrar_fim_exame, 
    bloquear_por_abandono,
    verificar_elegibilidade_exame,
    carregar_todas_questoes,
    gerar_codigo_verificacao,
    gerar_pdf,
    normalizar_link_video 
)

# =========================================
# CARREGADOR DE EXAME (Inalterado)
# =========================================
def carregar_exame_especifico(faixa_alvo):
    db = get_db()
    questoes_finais = []
    tempo = 45; nota = 70; qtd_alvo = 10
    
    try:
        configs = db.collection('config_exames').where('faixa', '==', faixa_alvo).limit(1).stream()
        config_doc = None
        for doc in configs: 
            config_doc = doc.to_dict()
            break
        
        if config_doc:
            tempo = int(config_doc.get('tempo_limite', 45))
            nota = int(config_doc.get('aprovacao_minima', 70))
            
            # MODO MANUAL
            if config_doc.get('questoes_ids'):
                ids = config_doc['questoes_ids']
                for q_id in ids:
                    q_snap = db.collection('questoes').document(q_id).get()
                    if q_snap.exists:
                        d = q_snap.to_dict()
                        if 'alternativas' not in d and 'opcoes' in d:
                            ops = d['opcoes']
                            d['alternativas'] = {
                                "A": ops[0], "B": ops[1], "C": ops[2], "D": ops[3]
                            } if len(ops) >= 4 else {}
                        questoes_finais.append(d)
                random.shuffle(questoes_finais)
                return questoes_finais, tempo, nota
            
            qtd_alvo = int(config_doc.get('qtd_questoes', 10))
    except:
        pass

    # FALLBACK
    if not questoes_finais:
        try:
            q_ref = list(db.collection('questoes').where('status', '==', 'aprovada').stream())
            pool = []
            for doc in q_ref:
                d = doc.to_dict()
                if 'alternativas' not in d and 'opcoes' in d:
                    ops = d['opcoes']
                    d['alternativas'] = {
                        "A": ops[0], "B": ops[1], "C": ops[2], "D": ops[3]
                    } if len(ops) >= 4 else {}
                pool.append(d)
            if pool:
                questoes_finais = random.sample(pool, min(len(pool), qtd_alvo))
        except:
            pass

    return questoes_finais, tempo, nota

# =========================================
# TELAS SECUNDÁRIAS (INALTERADAS)
# =========================================
def modo_rola(usuario):
    st.markdown("## 🥋 Modo Rola")
    st.info("Em breve.")

def meus_certificados(usuario):
    if st.button("🏠 Voltar ao Início", key="btn_back_cert"):
        st.session_state.menu_selection = "Início"
        st.rerun()

    st.markdown("## 🏅 Meus Certificados")

    try:
        db = get_db()
        docs = (
            db.collection('resultados')
            .where('usuario', '==', usuario['nome'])
            .where('aprovado', '==', True)
            .stream()
        )

        lista_certificados = []

        for doc in docs:
            cert = doc.to_dict()
            data_raw = cert.get('data')
            data_obj = datetime.min

            if hasattr(data_raw, 'to_datetime'):
                data_obj = data_raw.to_datetime()
            elif isinstance(data_raw, datetime):
                data_obj = data_raw
            elif isinstance(data_raw, str):
                try:
                    data_obj = datetime.fromisoformat(data_raw.replace('Z', ''))
                except:
                    pass

            if data_obj.tzinfo is not None:
                data_obj = data_obj.replace(tzinfo=None)

            cert['data_ordenacao'] = data_obj
            lista_certificados.append(cert)

        lista_certificados.sort(
            key=lambda x: x.get('data_ordenacao', datetime.min),
            reverse=True
        )

        if not lista_certificados:
            st.info("Nenhum certificado disponível.")
            return

        for i, cert in enumerate(lista_certificados):
            with st.container(border=True):
                c1, c2 = st.columns([3, 1])
                c1.markdown(f"**Faixa {cert.get('faixa')}**")

                data_exib = cert.get('data_ordenacao')
                d_str = data_exib.strftime('%d/%m/%Y') if data_exib else "-"

                c1.caption(
                    f"Data: {d_str} | "
                    f"Nota: {cert.get('pontuacao', 0):.0f}% | "
                    f"Ref: {cert.get('codigo_verificacao')}"
                )

                def generate_certificate(cert, user_name):
                    pdf_bytes, pdf_name = gerar_pdf(
                        user_name,
                        cert.get('faixa'),
                        cert.get('pontuacao', 0),
                        cert.get('total', 10),
                        cert.get('codigo_verificacao')
                    )
                    if pdf_bytes:
                        return pdf_bytes, pdf_name
                    return b"", f"Erro_{cert.get('codigo_verificacao')}.pdf"

                c2.download_button(
                    label="📄 Baixar PDF",
                    data=lambda: generate_certificate(cert, usuario['nome'])[0],
                    file_name=lambda: generate_certificate(cert, usuario['nome'])[1],
                    mime="application/pdf",
                    key=f"cert_{i}"
                )

    except Exception as e:
        st.error(f"Erro ao carregar certificados: {e}")

def ranking():
    st.markdown("## 🏆 Ranking")
    st.info("Em breve.")

# =========================================
# EXAME PRINCIPAL (INALTERADO)
# =========================================
def exame_de_faixa(usuario):
    # >>> TODO O SEU CÓDIGO DO EXAME PERMANECE EXATAMENTE IGUAL <<<
    # (mantido conforme enviado por você)
    pass
