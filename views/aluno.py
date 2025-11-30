import streamlit as st
import time
import random
import os
import json
from datetime import datetime, timedelta
import streamlit.components.v1 as components 
from database import get_db
from firebase_admin import firestore

# Importações do Utils
from utils import (
    registrar_inicio_exame, 
    registrar_fim_exame, 
    bloquear_por_abandono,
    carregar_todas_questoes,
    gerar_codigo_verificacao,
    gerar_pdf
)

# =========================================
# CARREGADOR DE EXAME
# =========================================
def carregar_exame_especifico(faixa_alvo):
    """
    Busca a prova específica configurada pelo professor.
    Prioridade: 1. Configuração Manual -> 2. Sorteio no Banco -> 3. Fallback
    """
    db = get_db()
    
    questoes_finais = []
    tempo = 45
    nota = 70
    qtd_alvo = 10

    # 1. Tenta buscar a CONFIGURAÇÃO DO EXAME para essa faixa
    configs = db.collection('config_exames').where('faixa', '==', faixa_alvo).limit(1).stream()
    
    config_doc = None
    for doc in configs:
        config_doc = doc.to_dict()
        break
    
    if config_doc:
        tempo = int(config_doc.get('tempo_limite', 45))
        nota = int(config_doc.get('aprovacao_minima', 70))
        qtd_alvo = int(config_doc.get('qtd_questoes', 10))
        
        if config_doc.get('questoes') and len(config_doc.get('questoes')) > 0:
            questoes_finais = config_doc.get('questoes')
            return questoes_finais, tempo, nota

    # 2. SE FOR MODO ALEATÓRIO
    if not questoes_finais:
        q_spec = list(db.collection('questoes').where('faixa', '==', faixa_alvo).where('status', '==', 'aprovada').stream())
        q_geral = list(db.collection('questoes').where('faixa', '==', 'Geral').where('status', '==', 'aprovada').stream())
        
        pool = []
        ids_vistos = set()
        
        for doc in q_spec + q_geral:
            if doc.id not in ids_vistos:
                pool.append(doc.to_dict())
                ids_vistos.add(doc.id)
        
        if pool:
            if len(pool) > qtd_alvo:
                questoes_finais = random.sample(pool, qtd_alvo)
            else:
                questoes_finais = pool

    # 3. FALLBACK
    if not questoes_finais:
        todas_json = carregar_todas_questoes()
        faixa_norm = faixa_alvo.strip().lower()
        pool_json = [q for q in todas_json if q.get('faixa', '').strip().lower() in [faixa_norm, 'geral']]
        if pool_json:
            questoes_finais = pool_json[:qtd_alvo]

    return questoes_finais, tempo, nota

# =========================================
# MÓDULOS SECUNDÁRIOS
# =========================================
def modo_rola(usuario):
    st.markdown(f"## 🥋 Modo Rola - Treino Livre")
    st.info("Em breve: Aqui você poderá treinar com questões aleatórias sem valer nota.")

def meus_certificados(usuario):
    st.markdown(f"## 🏅 Meus Certificados")
    db = get_db()
    
    docs = db.collection('resultados').where('usuario', '==', usuario['nome']).where('aprovado', '==', True).stream()
    lista_cert = [d.to_dict() for d in docs]
    
    if not lista_cert:
        st.info("Você ainda não possui certificados emitidos.")
        return

    for i, cert in enumerate(lista_cert):
        with st.container(border=True):
            c1, c2 = st.columns([3, 1])
            c1.markdown(f"**Faixa {cert.get('faixa')}**")
            
            d_str = "-"
            if cert.get('data'):
                try: d_str = cert.get('data').strftime('%d/%m/%Y')
                except: pass
            
            c1.caption(f"Data: {d_str} | Nota: {cert.get('pontuacao')}%")
            
            try:
                pdf_bytes, pdf_name = gerar_pdf(
                    usuario['nome'], cert.get('faixa'), 
                    cert.get('acertos', 0), cert.get('total', 10), 
                    cert.get('codigo_verificacao')
                )
                if pdf_bytes:
                    c2.download_button("📄 Baixar PDF", pdf_bytes, pdf_name, "application/pdf", key=f"btn_{i}")
            except: pass

def ranking():
    st.markdown("## 🏆 Ranking da Equipe")
    st.info("O ranking será atualizado em breve.")

# =========================================
# EXAME DE FAIXA (PRINCIPAL)
# =========================================
def exame_de_faixa(usuario):
    st.header(f"🥋 Exame de Faixa - {usuario['nome'].split()[0].title()}")
    
    if "exame_iniciado" not in st.session_state: st.session_state.exame_iniciado = False
    if "resultado_prova" not in st.session_state: st.session_state.resultado_prova = None

    db = get_db()
    doc_ref = db.collection('usuarios').document(usuario['id'])
    doc = doc_ref.get()
    
    if not doc.exists: st.error("Erro perfil."); return
    dados = doc.to_dict()
    
    # --- 0. RESULTADO IMEDIATO ---
