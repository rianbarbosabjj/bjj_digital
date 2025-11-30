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
# CARREGADOR DE EXAME (INTELIGENTE)
# =========================================
def carregar_exame_especifico(faixa_alvo):
    """
    Busca a prova específica configurada pelo professor.
    Retorna: (lista_questoes, tempo_limite, nota_minima)
    """
    db = get_db()
    faixa_norm = faixa_alvo.strip().lower()
    
    questoes_finais = []
    tempo = 45
    nota = 70
    qtd_alvo = 10

    # 1. Busca Configuração (Manual ou Sorteio)
    configs = db.collection('config_exames').where('faixa', '==', faixa_alvo).limit(1).stream()
    
    config_achada = None
    for doc in configs:
        d = doc.to_dict()
        # Garante que é a faixa certa
        if d.get('faixa') == faixa_alvo:
            config_achada = d
            tempo = int(d.get('tempo_limite', 45))
            nota = int(d.get('aprovacao_minima', 70))
            qtd_alvo = int(d.get('qtd_questoes', 10))
            
            # Se for Modo Manual, as questões já estão salvas na lista
            if d.get('questoes'):
                questoes_finais = d.get('questoes')
            break
            
    # 2. Se não achou questões (Modo Aleatório ou Sem Config), busca no banco
    if not questoes_finais:
        # Pega todas as aprovadas
        todas_refs = db.collection('questoes').where('status', '==', 'aprovada').stream()
        pool = []
        
        for doc in todas_refs:
            q = doc.to_dict()
            q_faixa = q.get('faixa', '').strip().lower()
            # Filtra: Faixa Específica OU Geral
            if q_faixa == faixa_norm or q_faixa == 'geral':
                pool.append(q)
        
        # Sorteia
        if pool:
            if len(pool) > qtd_alvo:
                questoes_finais = random.sample(pool, qtd_alvo)
            else:
                questoes_finais = pool

    # 3. Fallback (JSON Local) - Último recurso se o banco falhar
    if not questoes_finais:
        todas_json = carregar_todas_questoes()
        pool_json = [q for q in todas_json if q.get('faixa', '').lower() in [faixa_norm, 'geral']]
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
    
    # Busca resultados aprovados
    docs = db.collection('resultados').where('usuario', '==', usuario['nome']).where('aprovado', '==', True).stream()
    lista_cert = [d.to_dict() for d in docs]
    
    if not lista_cert:
        st.info("Você ainda não possui certificados emitidos.")
        return

    for i, cert in enumerate(lista_cert):
        with st.container(border=True):
            c1, c2 = st.columns([3, 1])
            c1.markdown(f"**Faixa {cert.get('faixa')}**")
            data_str = cert.get('data').strftime('%d/%m/%Y') if cert.get('data') else '-'
            c1.caption(f"Data: {data_str} | Nota: {cert.get('pontuacao')}%")
            
            # Botão Download
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
    
    # Inicializa sessão
    if "exame_iniciado" not in st.session_state: st.session_state.exame_iniciado = False
    if "resultado_prova" not in st.session_state: st.session_state.resultado_prova = None

    db = get_db()
    doc_ref = db.collection('usuarios').document(usuario['id'])
    doc = doc_ref.get()
    
    if not doc.exists: st.error("Erro perfil."); return
    dados = doc.to_dict()
    
    # --- 0. MOSTRAR RESULTADO IMEDIATO (Se acabou de terminar) ---
    if st.session_state.resultado_prova:
        res = st.session_state.resultado_prova
        st.balloons()
        st.success(f"PARABÉNS! Aprovado com {res['nota']:.1f}%!")
        
        p_bytes, p_name = gerar_pdf(usuario['nome'], res['faixa'], res['acertos'], res['total'], res['codigo'])
        if p_bytes:
            st.download_button("📥 BAIXAR CERTIFICADO AGORA", p_bytes, p_name, "application/pdf", use_container_width=True)
        
        if st.button("Voltar ao Início"):
            st.session_state.resultado_prova = None
            st.rerun()
        return # Para aqui

    # --- 1. VERIFICAÇÃO DE PERMISSÕES ---
    esta_habilitado = dados.get('exame_habilitado', False)
    faixa_alvo = dados.get('faixa_exame', None)
    
    if not esta_habilitado or not faixa_alvo:
        st.warning("🔒 Nenhum exame autorizado pelo professor.")
        st.caption("Aguarde a liberação na área de Gestão de Exames.")
        return

    # --- 2. VERIFICAÇÃO DE PRAZO (COM AJUSTE DE FUSO HORÁRIO) ---
    try:
        data_inicio = dados.get('exame_inicio')
        data_fim = dados.get('exame_fim')
        
        # Ajuste para Horário de Brasília (-3h em relação ao servidor UTC)
        agora = datetime.now() - timedelta(hours=3)
        
        if isinstance(data_inicio, str): data_inicio = datetime.fromisoformat(data_inicio)
        if isinstance(data_fim, str): data_fim = datetime.fromisoformat(data_fim)
        
        if data_inicio: data_inicio = data_inicio.replace(tzinfo=None)
        if data_fim: data_fim = data_fim.replace(tzinfo=None)
        
        if data_inicio and agora < data_inicio:
            st.warning(f"⏳ O exame estará liberado a partir de: **{data_inicio.strftime('%d/%m/%Y às %H:%M')}**")
            return
            
        if data_fim and agora > data_fim:
            st.error(f"🚫 O prazo para este exame expirou em: **{data_fim.strftime('%d/%m/%Y às %H:%M')}**")
            st.caption(f"Horário atual do sistema: {agora.strftime('%d/%m/%Y %H:%M')}")
            return
            
    except Exception as e:
        # Log interno apenas, fail-open para não travar o aluno por erro de conversão
        print(f"Aviso data: {e}")

    # --- 3. VERIFICAÇÃO DE STATUS ---
    status_atual = dados.get('status_exame', 'pendente')
    if status_atual == 'aprovado':
        st.success(f"✅ Você já foi aprovado na Faixa {faixa_alvo}!")
        st.info("Acesse 'Meus Certificados' para baixar.")
        return
    if status_atual == 'bloqueado':
        st.error("🚫 Exame BLOQUEADO por segurança.")
        st.warning("Motivo: Saída da página ou interrupção. Contate o professor.")
        return

    # ==============================================================================
    # 4. LÓGICA DE RECUPERAÇÃO INTELIGENTE (ANTI-FRAUDE TOLERANTE)
    # ==============================================================================
    if dados.get("status_exame") == "em_andamento":
        
        # Se a sessão local diz que NÃO começou, mas o banco diz que SIM...
        if not st.session_state.exame_iniciado:
            inicio_real = dados.get("inicio_exame_temp")
            recuperavel = False
            
            if inicio_real:
                try:
                    if isinstance(inicio_real, str): inicio_real = datetime.fromisoformat(inicio_real)
                    inicio_real = inicio_real.replace(tzinfo=None)
                    # Se passou menos de 2 minutos, restaura
                    if (datetime.now() - inicio_real).total_seconds() < 120:
                        recuperavel = True
                except: pass
            
            if recuperavel:
                st.toast("🔄 Restaurando sessão do exame...")
                # Recarrega dados
                l_questoes, t_limite, m_aprov = carregar_exame_especifico(faixa_alvo)
                
                # Restaura Sessão
                st.session_state.exame_iniciado = True
                st.session_state.inicio_prova = inicio_real
                st.session_state.questoes_prova = l_questoes 
                st.session_state.params_prova = {"tempo": t_limite, "min_aprovacao": m_aprov}
                st.session_state.fim_prova_ts = inicio_real.timestamp() + (t_limite * 60)
                st.rerun()
            else:
                bloquear_por_abandono(usuario['id'])
                st.error("🚨 DETECÇÃO DE INFRAÇÃO: Sessão perdida ou saída da página.")
                st.stop()

    # --- 5. CARREGAMENTO INICIAL ---
    lista_questoes, tempo_limite, min_aprovacao = carregar_exame_especifico(faixa_alvo)
    qtd_questoes = len(lista_questoes)

    # JS Anti-Cola (Ativo apenas durante a prova)
    if st.session_state.exame_iniciado:
        components.v1.html("""<script>document.addEventListener("visibilitychange", function() {if(document.hidden){document.body.innerHTML="<h1 style='color:red;text-align:center;margin-top:20%'>🚨 BLOQUEADO POR MUDANÇA DE ABA 🚨</h1>"}});</script>""", height=0)

    # --- 6. TELA DE INSTRUÇÕES ---
    if not st.session_state.exame_iniciado:
        st.markdown(f"### 📋 Exame de Faixa **{faixa_alvo.upper()}**")
        
        with st.container(border=True):
            c1, c2, c3 = st.columns(3)
            c1.markdown(f"📝 **{qtd_questoes} Questões**")
            c2.markdown(f"⏱️ **{tempo_limite} min**")
            c3.markdown(f"✅ **{min_aprovacao}%**")
            st.markdown("---")
            st.markdown("""
            **ATENÇÃO:**
            * O cronômetro não para.
            * Proibido mudar de aba (Bloqueio Imediato).
            * Reprovação exige espera de 72h (salvo liberação do professor).
            """)
        
        if qtd_questoes > 0:
            if st.button("✅ Li e Concordo. INICIAR EXAME", type="primary", use_container_width=True):
                registrar_inicio_exame(usuario['id'])
                st.session_state.exame_iniciado = True
                st.session_state.inicio_prova = datetime.now()
                st.session_state.fim_prova_ts = time.time() + (tempo_limite * 60)
                st.session_state.questoes_prova = lista_questoes
                st.session_state.params_prova = {"tempo": tempo_limite, "min_aprovacao": min_aprovacao}
                st.rerun()
        else:
            st.warning(f"⚠️ Erro: Nenhuma questão encontrada para **{faixa_alvo}**. Professor, verifique o cadastro.")

    # --- 7. PROVA EM ANDAMENTO ---
    else:
        questoes = st.session_state.get('questoes_prova', [])
        params = st.session_state.get('params_prova', {"tempo": 45, "min_aprovacao": 70})
        
        # Timer
        agora_ts = time.time()
        if 'fim_prova_ts' not in st.session_state: # Fallback de segurança
            st.session_state.fim_prova_ts = agora_ts + (params['tempo']*60)
            
        restante = int(st.session_state.fim_prova_ts - agora_ts)
        
        if restante <= 0:
            st.error("Tempo esgotado!")
            registrar_fim_exame(usuario['id'], False)
            st.session_state.exame_iniciado = False
            time.sleep(3); st.rerun()

        # Display Timer
        st.components.v1.html(
            f"""<div style="background:#0e2d26; border:2px solid #FFD700; border-radius:10px; padding:10px; text-align:center; color:#FFD700; font-family:sans-serif; font-size:24px; font-weight:bold;"><span id="timer">...</span></div><script>var t={restante};setInterval(function(){{if(t<=0){{document.getElementById('timer').innerHTML="FIM";return}}var m=Math.floor(t/60);var s=t%60;document.getElementById('timer').innerHTML="⏱️ "+(m<10?"0"+m:m)+":"+(s<10?"0"+s:s);t--;}},1000);</script>""", 
            height=70
        )
        
        with st.form("prova"):
            respostas = {}
            for i, q in enumerate(questoes):
                st.markdown(f"**{i+1}. {q.get('pergunta', '?')}**")
                if q.get('imagem'): st.image(q['imagem'])
                respostas[i] = st.radio("R:", q.get('opcoes', ['V','F']), key=f"q_{i}", label_visibility="collapsed")
                st.markdown("---")
            
            if st.form_submit_button("Finalizar Prova", type="primary", use_container_width=True):
                acertos = 0
                for i, q in enumerate(questoes):
                    gabarito = q.get('correta') or q.get('resposta')
                    # Comparação segura (string vs string, sem espaços)
                    if str(respostas.get(i)).strip().lower() == str(gabarito).strip().lower():
                        acertos += 1
                
                nota = (acertos / len(questoes)) * 100
                aprovado = nota >= params['min_aprovacao']
                
                registrar_fim_exame(usuario['id'], aprovado)
                st.session_state.exame_iniciado = False
                
                # Salva resultado
                codigo = None
                if aprovado:
                    codigo = gerar_codigo_verificacao()
                    st.session_state.resultado_prova = {
                        "nota": nota, "aprovado": True, "faixa": faixa_alvo,
                        "acertos": acertos, "total": len(questoes), "codigo": codigo
                    }
                
                try:
                    db.collection('resultados').add({
                        "usuario": usuario['nome'], "faixa": faixa_alvo, "pontuacao": nota,
                        "acertos": acertos, "total": len(questoes), "aprovado": aprovado,
                        "codigo_verificacao": codigo, "data": firestore.SERVER_TIMESTAMP
                    })
                except: pass
                
                if not aprovado:
                    st.error(f"Reprovado. Nota: {nota:.1f}%.")
                    time.sleep(4)
                
                st.rerun()
