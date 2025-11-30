import streamlit as st
import time
import random
import os
import json
from datetime import datetime, timedelta
import streamlit.components.v1 as components 
from database import get_db
from utils import (
    registrar_inicio_exame, 
    registrar_fim_exame, 
    bloquear_por_abandono,
    carregar_todas_questoes,
    gerar_codigo_verificacao,
    gerar_pdf
)
from firebase_admin import firestore

# =========================================
# CARREGADOR DE EXAME
# =========================================
def carregar_exame_especifico(faixa_alvo):
    db = get_db()
    faixa_norm = faixa_alvo.strip().lower()
    
    questoes_finais = []
    tempo = 45
    nota = 70

    configs = db.collection('config_exames').stream()
    config_achada = None
    for doc in configs:
        d = doc.to_dict()
        if d.get('faixa', '').strip().lower() == faixa_norm:
            config_achada = d
            tempo = int(d.get('tempo_limite', 45))
            nota = int(d.get('aprovacao_minima', 70))
            if d.get('questoes'): questoes_finais = d.get('questoes')
            break
            
    if not questoes_finais:
        todas_refs = db.collection('questoes').where('status', '==', 'aprovada').stream()
        pool = []
        for doc in todas_refs:
            q = doc.to_dict()
            q_faixa = q.get('faixa', '').strip().lower()
            if q_faixa == faixa_norm or q_faixa == 'geral': pool.append(q)
        if pool:
            qtd = int(config_achada.get('qtd_questoes', 10)) if config_achada else 10
            if len(pool) > qtd: questoes_finais = random.sample(pool, qtd)
            else: questoes_finais = pool

    if not questoes_finais:
        todas_json = carregar_todas_questoes()
        questoes_finais = [q for q in todas_json if q.get('faixa', '').lower() == faixa_norm]
        if not questoes_finais and todas_json: questoes_finais = todas_json[:10]

    return questoes_finais, tempo, nota

# =========================================
# MÓDULOS SECUNDÁRIOS
# =========================================
def modo_rola(usuario):
    st.markdown(f"## 🥋 Modo Rola - Treino Livre")
    st.info("Em breve...")

def meus_certificados(usuario):
    st.markdown(f"## 🏅 Meus Certificados")
    db = get_db()
    docs = db.collection('resultados').where('usuario', '==', usuario['nome']).where('aprovado', '==', True).stream()
    lista = [d.to_dict() for d in docs]
    if not lista:
        st.info("Sem certificados.")
        return
    for cert in lista:
        with st.container(border=True):
            st.write(f"Faixa {cert.get('faixa')} | {cert.get('pontuacao')}%")

def ranking():
    st.markdown("## 🏆 Ranking")
    st.info("Em breve.")

# =========================================
# EXAME DE FAIXA (COM DEBUG)
# =========================================
def exame_de_faixa(usuario):
    st.header(f"🥋 Exame de Faixa - {usuario['nome'].split()[0].title()}")
    
    # --- ÁREA DE DIAGNÓSTICO (DEBUG) ---
    # Isso vai mostrar o que o sistema está vendo de verdade
    db = get_db()
    doc_ref = db.collection('usuarios').document(usuario['id'])
    doc = doc_ref.get()
    dados = doc.to_dict()

    with st.expander("🕵️‍♂️ DADOS REAIS DO BANCO (DEBUG)", expanded=True):
        st.json({
            "Nome": dados.get('nome'),
            "Habilitado": dados.get('exame_habilitado'),
            "Data Fim (Banco)": dados.get('exame_fim'),
            "Status": dados.get('status_exame')
        })
    # ------------------------------------

    if "exame_iniciado" not in st.session_state: st.session_state.exame_iniciado = False

    esta_habilitado = dados.get('exame_habilitado', False)
    faixa_alvo = dados.get('faixa_exame', None)
    
    if not esta_habilitado or not faixa_alvo:
        st.warning("🔒 Nenhum exame autorizado.")
        return

    # Datas (UTC-3)
    try:
        data_inicio = dados.get('exame_inicio')
        data_fim = dados.get('exame_fim')
        
        # Horário de Brasília Atual
        agora = datetime.utcnow() - timedelta(hours=3)
        
        if isinstance(data_inicio, str): data_inicio = datetime.fromisoformat(data_inicio)
        if isinstance(data_fim, str): data_fim = datetime.fromisoformat(data_fim)
        
        # Garante que as datas do banco não tenham fuso para comparar matematicamente
        if data_inicio: data_inicio = data_inicio.replace(tzinfo=None)
        if data_fim: data_fim = data_fim.replace(tzinfo=None)
        
        if data_inicio and agora < data_inicio:
            st.warning(f"⏳ Início: {data_inicio.strftime('%d/%m/%Y %H:%M')}"); return
        
        if data_fim and agora > data_fim:
            st.error(f"🚫 O prazo expirou em: **{data_fim.strftime('%d/%m/%Y %H:%M')}**")
            st.info(f"Horário de Brasília agora: {agora.strftime('%d/%m/%Y %H:%M')}")
            return
    except Exception as e: st.error(f"Erro data: {e}")

    # Status
    status = dados.get('status_exame', 'pendente')
    if status == 'aprovado': st.success("✅ Aprovado!"); return
    if status == 'bloqueado': st.error("🚫 Bloqueado."); return

    # Anti-Fraude
    if dados.get("status_exame") == "em_andamento" and not st.session_state.exame_iniciado:
        inicio_real = dados.get("inicio_exame_temp")
        recuperavel = False
        if inicio_real:
            try:
                if isinstance(inicio_real, str): inicio_real = datetime.fromisoformat(inicio_real)
                inicio_real = inicio_real.replace(tzinfo=None)
                # Tolerância de 2 min
                if (datetime.utcnow() - timedelta(hours=3) - inicio_real).total_seconds() < 120: recuperavel = True
            except: pass
        
        if recuperavel:
            st.toast("Restaurando sessão...")
            l, t, m = carregar_exame_especifico(faixa_alvo)
            st.session_state.exame_iniciado = True
            st.session_state.inicio_prova = inicio_real
            st.session_state.questoes_prova = l
            st.session_state.params_prova = {"tempo": t, "min": m}
            st.session_state.fim_prova_ts = inicio_real.timestamp() + (t*60)
            st.rerun()
        else:
            bloquear_por_abandono(usuario['id'])
            st.error("🚨 Bloqueado (Fuga)."); st.stop()

    # Carregamento
    lista_questoes, tempo_limite, min_aprovacao = carregar_exame_especifico(faixa_alvo)
    qtd = len(lista_questoes)

    if st.session_state.exame_iniciado:
        components.v1.html("""<script>document.addEventListener("visibilitychange", function() {if(document.hidden){document.body.innerHTML="<h1 style='color:red;text-align:center;margin-top:20%'>BLOQUEADO</h1>"}});</script>""", height=0)

    # Tela Inicial
    if not st.session_state.exame_iniciado:
        st.markdown(f"### Exame Faixa **{faixa_alvo.upper()}**")
        with st.container(border=True):
            c1,c2,c3 = st.columns(3)
            c1.markdown(f"📝 **{qtd} Questões**")
            c2.markdown(f"⏱️ **{tempo_limite} min**")
            c3.markdown(f"✅ **{min_aprovacao}%**")
            st.markdown("---")
            st.write("Não saia da tela.")
        
        if qtd > 0:
            if st.button("✅ INICIAR EXAME", type="primary", use_container_width=True):
                registrar_inicio_exame(usuario['id'])
                st.session_state.exame_iniciado = True
                st.session_state.inicio_prova = datetime.utcnow() - timedelta(hours=3)
                st.session_state.fim_prova_ts = time.time() + (tempo_limite*60)
                st.session_state.questoes_prova = lista_questoes
                st.session_state.params_prova = {"tempo": tempo_limite, "min": min_aprovacao}
                st.rerun()
        else: st.warning("Sem questões.")

    # Prova
    else:
        questoes = st.session_state.get('questoes_prova', [])
        params = st.session_state.get('params_prova', {})
        
        restante = int(st.session_state.fim_prova_ts - time.time())
        if restante <= 0:
            st.error("Tempo esgotado!"); registrar_fim_exame(usuario['id'], False); st.session_state.exame_iniciado=False; time.sleep(3); st.rerun()

        st.metric("Tempo", f"{int(restante/60)}:{restante%60:02d}")
        
        with st.form("prova"):
            respostas = {}
            for i, q in enumerate(questoes):
                st.markdown(f"**{i+1}. {q.get('pergunta','?')}**")
                if q.get('imagem'): st.image(q['imagem'])
                respostas[i] = st.radio("R:", q.get('opcoes',['V','F']), key=f"q{i}", label_visibility="collapsed")
                st.markdown("---")
            
            if st.form_submit_button("Finalizar", type="primary"):
                acertos = 0
                for i, q in enumerate(questoes):
                    certa = q.get('correta') or q.get('resposta')
                    if str(respostas.get(i)).strip() == str(certa).strip(): acertos += 1
                
                nota = (acertos/len(questoes))*100
                aprovado = nota >= params['min']
                registrar_fim_exame(usuario['id'], aprovado)
                st.session_state.exame_iniciado = False
                
                cod = None
                if aprovado:
                    cod = gerar_codigo_verificacao()
                    st.session_state.resultado_prova = {"nota": nota, "aprovado": True, "faixa": faixa_alvo, "acertos": acertos, "total": len(questoes), "codigo": cod}
                
                try:
                    db.collection('resultados').add({
                        "usuario": usuario['nome'], "faixa": faixa_alvo, "pontuacao": nota,
                        "acertos": acertos, "total": len(questoes), "aprovado": aprovado,
                        "codigo_verificacao": cod, "data": firestore.SERVER_TIMESTAMP
                    })
                except: pass
                
                if not aprovado: st.error(f"Reprovado. {nota:.0f}%"); time.sleep(4)
                st.rerun()
