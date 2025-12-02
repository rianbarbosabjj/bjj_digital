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

# =========================================
# CARREGADOR DE EXAME (LÓGICA NOVA)
# =========================================
def carregar_exame_especifico(faixa_alvo):
    db = get_db()
    questoes_finais = []
    tempo = 45; nota = 70; qtd_alvo = 10
    
    # 1. Busca Configuração da Prova
    configs = db.collection('config_exames').where('faixa', '==', faixa_alvo).limit(1).stream()
    config_doc = None
    for doc in configs: config_doc = doc.to_dict(); break
    
    dificuldade_alvo = 1 # Default Fácil
    
    if config_doc:
        tempo = int(config_doc.get('tempo_limite', 45))
        nota = int(config_doc.get('aprovacao_minima', 70))
        qtd_alvo = int(config_doc.get('qtd_questoes', 10))
        dificuldade_alvo = int(config_doc.get('dificuldade_alvo', 1)) # Pega o nível configurado
    else:
        # Se não tiver config, tenta um mapa básico de fallback (opcional)
        if "Branca" in faixa_alvo: dificuldade_alvo = 1
        elif "Azul" in faixa_alvo: dificuldade_alvo = 2
        elif "Roxa" in faixa_alvo: dificuldade_alvo = 3
        elif "Marrom" in faixa_alvo or "Preta" in faixa_alvo: dificuldade_alvo = 4

    # 2. Busca Questões pelo NÍVEL DE DIFICULDADE
    # Traz questões do nível exato. Se quiser misturar (ex: nivel 1 e 2), precisaria de outra lógica.
    # Aqui vamos focar no nível alvo.
    q_ref = list(db.collection('questoes').where('dificuldade', '==', dificuldade_alvo).where('status', '==', 'aprovada').stream())
    
    pool = []
    ids_vistos = set()
    for doc in q_ref:
        d = doc.to_dict()
        # Tratamento de compatibilidade para alternativas antigas vs novas
        if 'alternativas' not in d and 'opcoes' in d:
            ops = d['opcoes']
            d['alternativas'] = {"A": ops[0], "B": ops[1], "C": ops[2], "D": ops[3]} if len(ops)>=4 else {}
            
        pool.append(d)
        ids_vistos.add(doc.id)

    # 3. Sorteio
    if pool:
        if len(pool) > qtd_alvo:
            questoes_finais = random.sample(pool, qtd_alvo)
        else:
            questoes_finais = pool

    return questoes_finais, tempo, nota

# =========================================
# OUTRAS TELAS (Mantidas)
# =========================================
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

# =========================================
# EXAME DE FAIXA (LÓGICA UNIFICADA)
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
    
    if st.session_state.resultado_prova:
        res = st.session_state.resultado_prova
        st.balloons(); st.success(f"Aprovado! Nota: {res['nota']:.1f}%")
        p_b, p_n = gerar_pdf(usuario['nome'], res['faixa'], res['acertos'], res['total'], res['codigo'])
        if p_b: st.download_button("📥 Baixar Certificado", p_b, p_n, "application/pdf")
        if st.button("Voltar"): st.session_state.resultado_prova = None; st.rerun()
        return

    # Verificação de Abandono / Timeout
    if dados.get("status_exame") == "em_andamento" and not st.session_state.exame_iniciado:
        is_timeout = False
        try:
            start_str = dados.get("inicio_exame_temp")
            if start_str:
                if isinstance(start_str, str): start_dt = datetime.fromisoformat(start_str.replace('Z', ''))
                else: start_dt = start_str
                _, t_lim, _ = carregar_exame_especifico(dados.get('faixa_exame'))
                limit_dt = start_dt + timedelta(minutes=t_lim)
                if datetime.utcnow() > limit_dt.replace(tzinfo=None): is_timeout = True
        except: pass

        if is_timeout:
            registrar_fim_exame(usuario['id'], False)
            st.error("⌛ TEMPO ESGOTADO!"); st.warning("Reprovado por tempo."); return
        else:
            bloquear_por_abandono(usuario['id'])
            st.error("🚨 BLOQUEADO!"); st.warning("Página recarregada ou fechada."); return

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
            st.markdown("#### Regras"); st.markdown("- Tentativa Única.\n- Não recarregue (F5).\n- Reprovação: aguardar 72h.")
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
        else: st.warning("Sem questões disponíveis para este nível.")

    else:
        qs = st.session_state.get('questoes_prova', [])
        restante = int(st.session_state.fim_prova_ts - time.time())
        if restante <= 0:
            st.error("Tempo esgotado!"); registrar_fim_exame(usuario['id'], False)
            st.session_state.exame_iniciado = False; time.sleep(2); st.rerun()

        cor = "#FFD770" if restante > 300 else "#FF4B4B"
        st.components.v1.html(f"""<div style="border:2px solid {cor};border-radius:10px;padding:10px;text-align:center;background:rgba(0,0,0,0.3);"><span style="color:white;font-family:sans-serif;">TEMPO RESTANTE</span><br><span id="t" style="color:{cor};font-family:monospace;font-size:30px;font-weight:bold;">--:--</span></div><script>var t={restante};setInterval(function(){{var m=Math.floor(t/60),s=t%60;document.getElementById('t').innerHTML=m+":"+(s<10?"0"+s:s);if(t--<=0)window.parent.location.reload();}},1000);</script>""", height=100)

        with st.form("prova"):
            resps = {}
            for i, q in enumerate(qs):
                st.markdown(f"**{i+1}. {q.get('pergunta')}**")
                # Compatibilidade com alternativas novas (dict) ou antigas (list)
                opts = []
                if 'alternativas' in q and isinstance(q['alternativas'], dict):
                    opts = [q['alternativas'].get(k) for k in ["A","B","C","D"]]
                elif 'opcoes' in q:
                    opts = q['opcoes']
                
                # Garante que options não esteja vazio
                if not opts: opts = ["Erro carregamento", "Erro", "Erro", "Erro"]

                resps[i] = st.radio("R:", opts, key=f"q{i}", label_visibility="collapsed")
                st.markdown("---")
                
            if st.form_submit_button("Finalizar"):
                acertos = 0
                for i, q in enumerate(qs):
                    # Lógica de correção para dict (A,B,C,D) ou list (Texto direto)
                    resp_aluno = str(resps.get(i)).strip().lower()
                    
                    # Tenta achar a letra correta
                    certa_bd = q.get('resposta_correta') or q.get('resposta') or q.get('correta')
                    certa_texto = ""
                    
                    # Se a resposta certa no banco for "A", "B"... converte para o texto
                    if str(certa_bd).upper() in ["A","B","C","D"] and 'alternativas' in q:
                        certa_texto = q['alternativas'].get(str(certa_bd).upper(), "").strip().lower()
                    else:
                        certa_texto = str(certa_bd).strip().lower()
                    
                    if resp_aluno == certa_texto: acertos += 1

                nota = (acertos/len(qs))*100
                aprovado = nota >= st.session_state.params_prova['min']
                registrar_fim_exame(usuario['id'], aprovado)
                st.session_state.exame_iniciado = False
                cod = gerar_codigo_verificacao() if aprovado else None
                if aprovado: st.session_state.resultado_prova = {"nota": nota, "aprovado": True, "faixa": dados.get('faixa_exame'), "acertos": acertos, "total": len(qs), "codigo": cod}
                try: db.collection('resultados').add({"usuario": usuario['nome'], "faixa": dados.get('faixa_exame'), "pontuacao": nota, "acertos": acertos, "total": len(qs), "aprovado": aprovado, "codigo_verificacao": cod, "data": firestore.SERVER_TIMESTAMP})
                except: pass
                if not aprovado: st.error(f"Reprovado. {nota:.0f}%"); time.sleep(3)
                st.rerun()
