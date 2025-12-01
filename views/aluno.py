import streamlit as st
import time
import random
import os
import json
from datetime import datetime, timedelta
import streamlit.components.v1 as components 
from database import get_db
from firebase_admin import firestore

from utils import (
    registrar_inicio_exame, 
    registrar_fim_exame, 
    bloquear_por_abandono,
    verificar_elegibilidade_exame,
    carregar_todas_questoes,
    gerar_codigo_verificacao,
    gerar_pdf
)

def carregar_exame_especifico(faixa_alvo):
    db = get_db()
    questoes_finais = []
    tempo = 45; nota = 70; qtd_alvo = 10

    configs = db.collection('config_exames').where('faixa', '==', faixa_alvo).limit(1).stream()
    config_doc = None
    for doc in configs: config_doc = doc.to_dict(); break
    
    if config_doc:
        tempo = int(config_doc.get('tempo_limite', 45))
        nota = int(config_doc.get('aprovacao_minima', 70))
        qtd_alvo = int(config_doc.get('qtd_questoes', 10))
        if config_doc.get('questoes'):
            return config_doc.get('questoes'), tempo, nota

    if not questoes_finais:
        q_spec = list(db.collection('questoes').where('faixa', '==', faixa_alvo).where('status', '==', 'aprovada').stream())
        q_geral = list(db.collection('questoes').where('faixa', '==', 'Geral').where('status', '==', 'aprovada').stream())
        pool = []
        seen = set()
        for doc in q_spec + q_geral:
            if doc.id not in seen: pool.append(doc.to_dict()); seen.add(doc.id)
        if pool:
            questoes_finais = random.sample(pool, qtd_alvo) if len(pool) > qtd_alvo else pool

    if not questoes_finais:
        todas = carregar_todas_questoes()
        fn = faixa_alvo.strip().lower()
        pool = [q for q in todas if q.get('faixa', '').strip().lower() in [fn, 'geral']]
        questoes_finais = pool[:qtd_alvo]

    return questoes_finais, tempo, nota

def modo_rola(usuario):
    st.markdown("## 🥋 Modo Rola"); st.info("Em breve.")

def meus_certificados(usuario):
    if st.button("🏠 Voltar ao Início", key="btn_back_cert"):
        st.session_state.menu_selection = "Início"; st.rerun()

    st.markdown("## 🏅 Meus Certificados")
    db = get_db()
    docs = db.collection('resultados').where('usuario', '==', usuario['nome']).where('aprovado', '==', True).stream()
    lista = [d.to_dict() for d in docs]
    
    if not lista: st.info("Nenhum certificado disponível."); return

    for i, cert in enumerate(lista):
        with st.container(border=True):
            c1, c2 = st.columns([3, 1])
            c1.markdown(f"**Faixa {cert.get('faixa')}**")
            d_str = cert.get('data').strftime('%d/%m/%Y') if cert.get('data') else "-"
            c1.caption(f"Data: {d_str} | Nota: {cert.get('pontuacao')}%")
            try:
                pdf_bytes, pdf_name = gerar_pdf(usuario['nome'], cert.get('faixa'), cert.get('acertos'), cert.get('total'), cert.get('codigo_verificacao'))
                if pdf_bytes: c2.download_button("📄 PDF", pdf_bytes, pdf_name, "application/pdf", key=f"d_{i}")
            except: pass

def ranking(): st.markdown("## 🏆 Ranking"); st.info("Em breve.")

def exame_de_faixa(usuario):
    st.header(f"🥋 Exame de Faixa - {usuario['nome'].split()[0].title()}")
    if "exame_iniciado" not in st.session_state: st.session_state.exame_iniciado = False
    if "resultado_prova" not in st.session_state: st.session_state.resultado_prova = None

    db = get_db()
    doc = db.collection('usuarios').document(usuario['id']).get()
    if not doc.exists: st.error("Erro perfil."); return
    dados = doc.to_dict()
    
    if st.session_state.resultado_prova:
        res = st.session_state.resultado_prova
        st.balloons(); st.success(f"Aprovado! Nota: {res['nota']:.1f}%")
        p_b, p_n = gerar_pdf(usuario['nome'], res['faixa'], res['acertos'], res['total'], res['codigo'])
        if p_b: st.download_button("📥 Baixar Certificado", p_b, p_n, "application/pdf")
        if st.button("Voltar"): st.session_state.resultado_prova = None; st.rerun()
        return

    if dados.get("status_exame") == "em_andamento" and not st.session_state.exame_iniciado:
        bloquear_por_abandono(usuario['id'])
        st.error("🚨 EXAME BLOQUEADO: Página recarregada ou fechada."); return

    if not dados.get('exame_habilitado') or not dados.get('faixa_exame'):
        st.warning("🔒 Exame não autorizado."); return

    elegivel, motivo = verificar_elegibilidade_exame(dados)
    if not elegivel:
        st.error(f"🚫 {motivo}") if "bloqueado" in motivo.lower() or "reprovado" in motivo.lower() else st.success(motivo)
        return

    try:
        dt_ini = dados.get('exame_inicio')
        if isinstance(dt_ini, str): dt_ini = datetime.fromisoformat(dt_ini.replace('Z',''))
        if dt_ini: dt_ini = dt_ini.replace(tzinfo=None)
        if dt_ini and datetime.utcnow() < dt_ini: st.warning(f"⏳ Início em: {dt_ini}"); return
    except: pass

    qs, tempo_limite, min_aprovacao = carregar_exame_especifico(dados.get('faixa_exame'))
    qtd = len(qs)

    if not st.session_state.exame_iniciado:
        st.markdown(f"### Faixa **{dados.get('faixa_exame')}**")
        with st.container(border=True):
            st.markdown("#### Regras")
            st.markdown("- Tentativa Única.\n- Não recarregue a página (F5).\n- Reprovação: aguardar 72h.")
            st.markdown("---")
            c1, c2, c3 = st.columns(3)
            c1.markdown(f"📝 **{qtd} Questões**")
            c2.markdown(f"<div style='text-align:center'>⏱️ <b>{tempo_limite} min</b></div>", unsafe_allow_html=True)
            c3.markdown(f"<div style='text-align:right'>✅ Min: <b>{min_aprovacao}%</b></div>", unsafe_allow_html=True)
        
        if qtd > 0:
            if st.button("✅ INICIAR EXAME", type="primary", use_container_width=True):
                registrar_inicio_exame(usuario['id'])
                st.session_state.exame_iniciado = True
                st.session_state.fim_prova_ts = time.time() + (tempo_limite * 60)
                st.session_state.questoes_prova = qs
                st.session_state.params_prova = {"tempo": tempo_limite, "min": min_aprovacao}
                st.rerun()
        else: st.warning("Sem questões.")
    else:
        qs = st.session_state.get('questoes_prova', [])
        restante = int(st.session_state.fim_prova_ts - time.time())
        
        if restante <= 0:
            st.error("Tempo esgotado!"); registrar_fim_exame(usuario['id'], False)
            st.session_state.exame_iniciado = False; time.sleep(2); st.rerun()

        cor = "#FFD770" if restante > 300 else "#FF4B4B"
        st.components.v1.html(f"""
        <div style="border:2px solid {cor};border-radius:10px;padding:10px;text-align:center;background:rgba(0,0,0,0.3);">
            <span style="color:white;font-family:sans-serif;">TEMPO</span><br>
            <span id="t" style="color:{cor};font-family:monospace;font-size:30px;font-weight:bold;">--:--</span>
        </div>
        <script>
            var t = {restante};
            setInterval(function(){{
                var m=Math.floor(t/60), s=t%60;
                document.getElementById('t').innerHTML = m+":"+(s<10?"0"+s:s);
                if(t--<=0) window.parent.location.reload();
            }}, 1000);
        </script>""", height=100)

        with st.form("prova"):
            resps = {}
            for i, q in enumerate(qs):
                st.markdown(f"**{i+1}. {q.get('pergunta')}**")
                if q.get('imagem'): st.image(q['imagem'])
                resps[i] = st.radio("R:", q.get('opcoes',['V','F']), key=f"q{i}", label_visibility="collapsed")
                st.markdown("---")
            if st.form_submit_button("Finalizar"):
                acertos = sum([1 for i,q in enumerate(qs) if str(resps.get(i)).strip().lower() == str(q.get('resposta')).strip().lower()])
                nota = (acertos/len(qs))*100
                aprovado = nota >= st.session_state.params_prova['min']
                registrar_fim_exame(usuario['id'], aprovado)
                st.session_state.exame_iniciado = False
                cod = gerar_codigo_verificacao() if aprovado else None
                if aprovado: st.session_state.resultado_prova = {"nota": nota, "aprovado": True, "faixa": dados.get('faixa_exame'), "acertos": acertos, "total": len(qs), "codigo": cod}
                try: db.collection('resultados').add({"usuario": usuario['nome'], "faixa": dados.get('faixa_exame'), "pontuacao": nota, "acertos": acertos, "total": len(qs), "aprovado": aprovado, "codigo_verificacao": cod, "data": firestore.SERVER_TIMESTAMP})
                except: pass
                if not aprovado: st.error("Reprovado."); time.sleep(3)
                st.rerun()
