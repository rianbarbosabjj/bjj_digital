import streamlit as st
import time
import random
from datetime import datetime
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
# CARREGADOR DE EXAME (CORRIGIDO)
# =========================================
def carregar_exame_especifico(faixa_alvo):
    db = get_db()
    faixa_norm = faixa_alvo.strip().lower() # ex: "verde"
    
    questoes_finais = []
    tempo = 45
    nota = 70
    qtd_alvo = 10

    # 1. Busca Configuração (Tempo, Nota, e se tem lista fixa)
    configs = db.collection('config_exames').stream()
    config_achada = None
    
    for doc in configs:
        d = doc.to_dict()
        if d.get('faixa', '').strip().lower() == faixa_norm:
            config_achada = d
            tempo = int(d.get('tempo_limite', 45))
            nota = int(d.get('aprovacao_minima', 70))
            qtd_alvo = int(d.get('qtd_questoes', 10))
            
            # Se for Manual, as questões já estão aqui
            if d.get('questoes'):
                questoes_finais = d.get('questoes')
            break
            
    # 2. Se for Aleatório (lista vazia na config), busca no banco
    if not questoes_finais:
        # Busca questões Aprovadas
        todas_refs = db.collection('questoes').where('status', '==', 'aprovada').stream()
        pool = []
        
        for doc in todas_refs:
            q = doc.to_dict()
            q_faixa = q.get('faixa', '').strip().lower()
            
            # Pega se for da faixa exata OU Geral
            if q_faixa == faixa_norm or q_faixa == 'geral':
                pool.append(q)
        
        # Se achou algo no banco
        if pool:
            # Sorteia até a quantidade alvo
            if len(pool) > qtd_alvo:
                questoes_finais = random.sample(pool, qtd_alvo)
            else:
                questoes_finais = pool

    # 3. Fallback JSON (Se o banco estiver vazio)
    if not questoes_finais:
        todas_json = carregar_todas_questoes()
        pool_json = [q for q in todas_json if q.get('faixa', '').lower() in [faixa_norm, 'geral']]
        if pool_json:
            questoes_finais = pool_json[:qtd_alvo]

    return questoes_finais, tempo, nota

# =========================================
# EXAME DE FAIXA
# =========================================
def exame_de_faixa(usuario):
    st.header(f"🥋 Exame de Faixa - {usuario['nome'].split()[0].title()}")
    
    if "exame_iniciado" not in st.session_state: st.session_state.exame_iniciado = False

    db = get_db()
    doc = db.collection('usuarios').document(usuario['id']).get()
    
    if not doc.exists: st.error("Erro perfil."); return
    dados = doc.to_dict()
    
    # 1. Permissão
    esta_habilitado = dados.get('exame_habilitado', False)
    faixa_alvo = dados.get('faixa_exame', None)
    
    if not esta_habilitado or not faixa_alvo:
        st.warning("🔒 Exame não autorizado.")
        st.caption("Peça ao professor para liberar na aba 'Gestão de Exame'.")
        return

    # 2. Datas
    try:
        data_inicio = dados.get('exame_inicio')
        data_fim = dados.get('exame_fim')
        agora = datetime.now()
        if isinstance(data_inicio, str): data_inicio = datetime.fromisoformat(data_inicio)
        if isinstance(data_fim, str): data_fim = datetime.fromisoformat(data_fim)
        if data_inicio: data_inicio = data_inicio.replace(tzinfo=None)
        if data_fim: data_fim = data_fim.replace(tzinfo=None)
        
        if data_inicio and agora < data_inicio:
            st.warning(f"⏳ Início: {data_inicio.strftime('%d/%m/%Y %H:%M')}"); return
        if data_fim and agora > data_fim:
            st.error("🚫 Prazo expirado."); return
    except: pass

    # 3. Status
    status = dados.get('status_exame', 'pendente')
    if status == 'aprovado':
        st.success("✅ Você já foi aprovado!"); return
    if status == 'bloqueado':
        st.error("🚫 Exame bloqueado."); return

    # Anti-fraude (Recuperação)
    if dados.get("status_exame") == "em_andamento" and not st.session_state.exame_iniciado:
        inicio_real = dados.get("inicio_exame_temp")
        recuperavel = False
        if inicio_real:
            try:
                if isinstance(inicio_real, str): inicio_real = datetime.fromisoformat(inicio_real)
                inicio_real = inicio_real.replace(tzinfo=None)
                if (datetime.now() - inicio_real).total_seconds() < 120: recuperavel = True
            except: pass
        
        if recuperavel:
            st.toast("🔄 Restaurando sessão...")
            l, t, m = carregar_exame_especifico(faixa_alvo)
            st.session_state.exame_iniciado = True
            st.session_state.inicio_prova = inicio_real
            st.session_state.questoes_prova = l
            st.session_state.params_prova = {"tempo": t, "min": m}
            st.session_state.fim_prova_ts = inicio_real.timestamp() + (t*60)
            st.rerun()
        else:
            bloquear_por_abandono(usuario['id'])
            st.error("🚨 Bloqueado por saída da página."); st.stop()

    # 4. Carregamento
    lista_questoes, tempo_limite, min_aprovacao = carregar_exame_especifico(faixa_alvo)
    qtd = len(lista_questoes)

    # JS Anti-Cola
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
            st.markdown("**ATENÇÃO:** Não saia da tela ou mude de aba.")
        
        if qtd > 0:
            if st.button("✅ INICIAR EXAME", type="primary", use_container_width=True):
                registrar_inicio_exame(usuario['id'])
                st.session_state.exame_iniciado = True
                st.session_state.inicio_prova = datetime.now()
                st.session_state.fim_prova_ts = time.time() + (tempo_limite*60)
                st.session_state.questoes_prova = lista_questoes
                st.session_state.params_prova = {"tempo": tempo_limite, "min": min_aprovacao}
                st.rerun()
        else:
            st.warning(f"⚠️ Nenhuma questão encontrada para '{faixa_alvo}'. Professor, cadastre questões para esta faixa!")

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
                    if str(respostas.get(i)).strip() == str(certa).strip(): acertos += 1
                
                nota = (acertos/len(questoes))*100
                aprovado = nota >= params['min']
                registrar_fim_exame(usuario['id'], aprovado)
                st.session_state.exame_iniciado = False
                
                if aprovado:
                    st.balloons(); st.success(f"APROVADO! {nota:.0f}%")
                    # Salva certificado
                    try:
                        cod = gerar_codigo_verificacao()
                        db.collection('resultados').add({
                            "usuario": usuario['nome'], "faixa": faixa_alvo, "pontuacao": nota,
                            "acertos": acertos, "total": len(questoes), "aprovado": True,
                            "codigo_verificacao": cod, "data": firestore.SERVER_TIMESTAMP
                        })
                    except: pass
                else:
                    st.error(f"Reprovado. {nota:.0f}%")
                
                time.sleep(5); st.rerun()

# Mantenha as outras funções (modo_rola, meus_certificados, etc)
def modo_rola(u): st.info("Em breve")
def ranking(): st.info("Em breve")
def meus_certificados(u): 
    # ... (Código de certificados que já estava ok) ...
    st.info("Use o menu anterior para ver certificados.")
