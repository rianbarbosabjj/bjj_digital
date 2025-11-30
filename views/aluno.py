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

    # 1. Busca Configuração
    configs = db.collection('config_exames').stream()
    for doc in configs:
        d = doc.to_dict()
        if d.get('faixa', '').strip().lower() == faixa_norm:
            tempo = int(d.get('tempo_limite', 45))
            nota = int(d.get('aprovacao_minima', 70))
            if d.get('questoes'): questoes_finais = d.get('questoes')
            break
            
    # 2. Busca no banco (Aleatório)
    if not questoes_finais:
        todas_refs = db.collection('questoes').where('status', '==', 'aprovada').stream()
        pool = []
        for doc in todas_refs:
            q = doc.to_dict()
            q_faixa = q.get('faixa', '').strip().lower()
            if q_faixa == faixa_norm or q_faixa == 'geral': pool.append(q)
        
        if pool:
            qtd_alvo = int(d.get('qtd_questoes', 10)) if 'd' in locals() else 10
            if len(pool) > qtd_alvo: questoes_finais = random.sample(pool, qtd_alvo)
            else: questoes_finais = pool

    # 3. Fallback
    if not questoes_finais:
        todas_json = carregar_todas_questoes()
        pool_json = [q for q in todas_json if q.get('faixa', '').lower() in [faixa_norm, 'geral']]
        if pool_json: questoes_finais = pool_json[:10]

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
    lista = [d.to_dict() for d in docs]
    
    if not lista:
        st.info("Você ainda não possui certificados emitidos.")
        return

    for i, cert in enumerate(lista):
        with st.container(border=True):
            c1, c2 = st.columns([3, 1])
            c1.markdown(f"**Faixa {cert.get('faixa')}**")
            
            data_formatada = "-"
            if cert.get('data'):
                # Verifica se é datetime ou string e formata
                ts = cert.get('data')
                if hasattr(ts, 'strftime'):
                    data_formatada = ts.strftime('%d/%m/%Y')
                
            c1.caption(f"Data: {data_formatada} | Nota: {cert.get('pontuacao')}%")
            
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
    
    # 0. Resultado Imediato
    if st.session_state.resultado_prova:
        res = st.session_state.resultado_prova
        st.balloons()
        st.success(f"PARABÉNS! Aprovado com {res['nota']:.1f}%!")
        p_bytes, p_name = gerar_pdf(usuario['nome'], res['faixa'], res['acertos'], res['total'], res['codigo'])
        if p_bytes:
            st.download_button("📥 BAIXAR CERTIFICADO AGORA", p_bytes, p_name, "application/pdf", use_container_width=True)
        if st.button("Voltar ao Início"):
            st.session_state.resultado_prova = None; st.rerun()
        return

    # 1. Permissões
    esta_habilitado = dados.get('exame_habilitado', False)
    faixa_alvo = dados.get('faixa_exame', None)
    
    if not esta_habilitado or not faixa_alvo:
        st.warning("🔒 Nenhum exame autorizado pelo professor.")
        return

    # 2. Datas (Fuso Horário Ajustado)
    try:
        data_inicio = dados.get('exame_inicio')
        data_fim = dados.get('exame_fim')
        agora = datetime.utcnow() - timedelta(hours=3) # UTC-3 (Brasília)
        
        if isinstance(data_inicio, str): data_inicio = datetime.fromisoformat(data_inicio)
        if isinstance(data_fim, str): data_fim = datetime.fromisoformat(data_fim)
        
        if data_inicio: data_inicio = data_inicio.replace(tzinfo=None)
        if data_fim: data_fim = data_fim.replace(tzinfo=None)
        
        if data_inicio and agora < data_inicio:
            st.warning(f"⏳ O exame começa em: **{data_inicio.strftime('%d/%m/%Y %H:%M')}**")
            return
        if data_fim and agora > data_fim:
            st.error(f"🚫 O prazo expirou em: **{data_fim.strftime('%d/%m/%Y %H:%M')}**")
            return
    except: pass

    # 3. Status
    status = dados.get('status_exame', 'pendente')
    if status == 'aprovado':
        st.success(f"✅ Você já foi aprovado na Faixa {faixa_alvo}!"); return
    if status == 'bloqueado':
        st.error("🚫 Exame BLOQUEADO por segurança."); return

    # 4. Anti-Fraude (Auto-Recuperação)
    if dados.get("status_exame") == "em_andamento" and not st.session_state.exame_iniciado:
        inicio_real = dados.get("inicio_exame_temp")
        recuperavel = False
        if inicio_real:
            try:
                if isinstance(inicio_real, str): inicio_real = datetime.fromisoformat(inicio_real)
                inicio_real = inicio_real.replace(tzinfo=None)
                # Tolerância de 2 min
                if (datetime.utcnow() - timedelta(hours=3) - inicio_real).total_seconds() < 120:
                    recuperavel = True
            except: pass
        
        if recuperavel:
            st.toast("🔄 Restaurando sessão...")
            l, t, m = carregar_exame_especifico(faixa_alvo)
            st.session_state.exame_iniciado = True
            st.session_state.inicio_prova = inicio_real
            st.session_state.questoes_prova = l 
            st.session_state.params_prova = {"tempo": t, "min": m}
            st.session_state.fim_prova_ts = inicio_real.timestamp() + (t * 60)
            st.rerun()
        else:
            bloquear_por_abandono(usuario['id'])
            st.error("🚨 Bloqueado por saída da página."); st.stop()

    # 5. Carregamento
    lista_questoes, tempo_limite, min_aprovacao = carregar_exame_especifico(faixa_alvo)
    qtd = len(lista_questoes)

    # JS Anti-Cola
    if st.session_state.exame_iniciado:
        components.v1.html("""<script>document.addEventListener("visibilitychange", function() {if(document.hidden){document.body.innerHTML="<h1 style='color:red;text-align:center;margin-top:20%'>BLOQUEADO</h1>"}});</script>""", height=0)

    # Tela Inicial
    if not st.session_state.exame_iniciado:
        st.markdown(f"### 📋 Exame de Faixa **{faixa_alvo.upper()}**")
        with st.container(border=True):
            c1,c2,c3 = st.columns(3)
            c1.markdown(f"📝 **{qtd} Questões**")
            c2.markdown(f"⏱️ **{tempo_limite} min**")
            c3.markdown(f"✅ **{min_aprovacao}%**")
            st.markdown("---")
            st.markdown("""
            **ATENÇÃO:**
            * O cronômetro não para.
            * Proibido mudar de aba (Bloqueio Imediato).
            * Reprovação exige espera de 72h.
            """)
        
        if qtd > 0:
            if st.button("✅ Li e Concordo. INICIAR EXAME", type="primary", use_container_width=True):
                registrar_inicio_exame(usuario['id'])
                st.session_state.exame_iniciado = True
                st.session_state.inicio_prova = datetime.utcnow() - timedelta(hours=3)
                st.session_state.fim_prova_ts = time.time() + (tempo_limite * 60)
                st.session_state.questoes_prova = lista_questoes
                st.session_state.params_prova = {"tempo": tempo_limite, "min": min_aprovacao}
                st.rerun()
        else:
            st.warning(f"⚠️ Sem questões para **{faixa_alvo}**.")

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
            
            if st.form_submit_button("Finalizar", type="primary", use_container_width=True):
                acertos = 0
                for i, q in enumerate(questoes):
                    certa = q.get('correta') or q.get('resposta')
                    if str(respostas.get(i)).strip().lower() == str(certa).strip().lower(): acertos += 1
                
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
