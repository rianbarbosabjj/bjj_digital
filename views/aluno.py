import streamlit as st
import time
import random
import os
import json
from datetime import datetime
from database import get_db
from utils import (
    registrar_inicio_exame, 
    registrar_fim_exame, 
    bloquear_por_abandono,
    carregar_todas_questoes,
    normalizar_nome,
    gerar_codigo_verificacao
)
from firebase_admin import firestore

# =========================================
# CARREGADOR DE EXAME (INTELIGENTE)
# =========================================
def carregar_exame_especifico(faixa_alvo):
    """
    Busca a prova específica autorizada pelo professor.
    """
    db = get_db()
    faixa_norm = faixa_alvo.strip().lower()
    
    questoes_finais = []
    tempo = 45
    nota = 70

    # 1. Busca na coleção de configurações (config_exames)
    configs = db.collection('config_exames').stream()
    config_achada = None
    
    for doc in configs:
        d = doc.to_dict()
        if d.get('faixa', '').strip().lower() == faixa_norm:
            config_achada = d
            tempo = int(d.get('tempo_limite', 45))
            nota = int(d.get('aprovacao_minima', 70))
            if d.get('questoes'):
                questoes_finais = d.get('questoes')
            break
            
    # 2. Se não achou questões na config, busca no banco geral 'questoes'
    if not questoes_finais:
        todas_refs = db.collection('questoes').stream()
        pool = []
        for doc in todas_refs:
            q = doc.to_dict()
            q_faixa = q.get('faixa', '').strip().lower()
            if q_faixa == faixa_norm or q_faixa == 'geral':
                pool.append(q)
        
        if pool:
            qtd = int(config_achada.get('qtd_questoes', 10)) if config_achada else 10
            if len(pool) > qtd:
                questoes_finais = random.sample(pool, qtd)
            else:
                questoes_finais = pool

    # 3. Fallback JSON local (último caso para não travar)
    if not questoes_finais:
        todas_json = carregar_todas_questoes()
        questoes_finais = [q for q in todas_json if q.get('faixa', '').lower() == faixa_norm]
        # Se ainda vazio, pega aleatórias dummy
        if not questoes_finais and todas_json:
             questoes_finais = todas_json[:10]

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
    
    # Busca certificados no histórico
    docs = db.collection('resultados').where('usuario', '==', usuario['nome']).where('aprovado', '==', True).stream()
    lista = [d.to_dict() for d in docs]
    
    if not lista:
        st.info("Você ainda não possui certificados emitidos nesta plataforma.")
        return

    for cert in lista:
        with st.container(border=True):
            c1, c2 = st.columns([3, 1])
            c1.markdown(f"**Faixa {cert.get('faixa')}**")
            c1.caption(f"Data: {cert.get('data').strftime('%d/%m/%Y') if cert.get('data') else '-'} | Código: {cert.get('codigo_verificacao')}")
            c2.success(f"Nota: {cert.get('pontuacao')}%")

def ranking():
    st.markdown("## 🏆 Ranking da Equipe")
    st.info("O ranking será atualizado em breve.")

# =========================================
# EXAME DE FAIXA (PRINCIPAL)
# =========================================
def exame_de_faixa(usuario):
    st.header(f"🥋 Exame de Faixa - {usuario['nome'].split()[0].title()}")
    
    db = get_db()
    # Pega dados atualizados do usuário
    doc_ref = db.collection('usuarios').document(usuario['id'])
    doc = doc_ref.get()
    
    if not doc.exists:
        st.error("Erro ao carregar perfil.")
        return
        
    dados = doc.to_dict()
    
    # -----------------------------------------------------------
    # 1. VERIFICAÇÃO DE AUTORIZAÇÃO (ADMIN)
    # -----------------------------------------------------------
    esta_habilitado = dados.get('exame_habilitado', False)
    faixa_alvo = dados.get('faixa_exame', None)
    
    if not esta_habilitado or not faixa_alvo:
        st.warning("🔒 Nenhum exame autorizado pelo professor.")
        st.caption("Aguarde a liberação na área de Gestão de Exames.")
        return

    # -----------------------------------------------------------
    # 2. VERIFICAÇÃO DE PRAZO (DATAS)
    # -----------------------------------------------------------
    try:
        data_inicio = dados.get('exame_inicio')
        data_fim = dados.get('exame_fim')
        agora = datetime.now()
        
        # Parse ISO format (string -> datetime)
        if isinstance(data_inicio, str): data_inicio = datetime.fromisoformat(data_inicio)
        if isinstance(data_fim, str): data_fim = datetime.fromisoformat(data_fim)
        
        # Remove timezone para comparação segura
        if data_inicio: data_inicio = data_inicio.replace(tzinfo=None)
        if data_fim: data_fim = data_fim.replace(tzinfo=None)
        
        if data_inicio and agora < data_inicio:
            st.warning(f"⏳ O exame estará liberado a partir de: **{data_inicio.strftime('%d/%m/%Y às %H:%M')}**")
            return
            
        if data_fim and agora > data_fim:
            st.error(f"🚫 O prazo para este exame expirou em: **{data_fim.strftime('%d/%m/%Y às %H:%M')}**")
            return
            
    except Exception as e:
        print(f"Erro de data: {e}") # Log interno, não trava o aluno

    # -----------------------------------------------------------
    # 3. VERIFICAÇÃO DE STATUS
    # -----------------------------------------------------------
    status_atual = dados.get('status_exame', 'pendente')
    
    if status_atual == 'aprovado':
        st.success(f"✅ Você já foi aprovado no exame de Faixa {faixa_alvo}!")
        return
        
    if status_atual == 'bloqueado':
        st.error("🚫 Exame BLOQUEADO por segurança.")
        st.warning("Motivo: Saída da página ou interrupção. Contate o professor para desbloqueio.")
        return

    # Anti-Fraude: Se estava "em_andamento" e recarregou a página -> BLOQUEIA
    if dados.get("status_exame") == "em_andamento":
        bloquear_por_abandono(usuario['id'])
        st.error("🚨 DETECÇÃO DE INFRAÇÃO: Saída da página durante o exame.")
        st.stop()

    # -----------------------------------------------------------
    # 4. CARREGAMENTO DO EXAME
    # -----------------------------------------------------------
    lista_questoes, tempo_limite, min_aprovacao = carregar_exame_especifico(faixa_alvo)
    qtd_questoes = len(lista_questoes)

    # JS Anti-Cola
    html_anti_cola = """
    <script>
    document.addEventListener("visibilitychange", function() {
        if (document.hidden) {
            document.body.innerHTML = "<h1 style='color:red; text-align:center; margin-top:20%; font-family:sans-serif;'>🚨 BLOQUEADO POR MUDANÇA DE ABA 🚨</h1>";
        }
    });
    </script>
    """
    st.components.v1.html(html_anti_cola, height=0, width=0)

    # 5. TELA DE INÍCIO
    if "exame_iniciado" not in st.session_state:
        st.session_state.exame_iniciado = False

    if not st.session_state.exame_iniciado:
        
        st.markdown(f"### 📋 Exame de Faixa **{faixa_alvo.upper()}**")
        st.caption("Leia atentamente as instruções antes de iniciar.")
        
        with st.container(border=True):
            c1, c2, c3 = st.columns(3)
            c1.markdown(f"📝 **{qtd_questoes} Questões**")
            c2.markdown(f"⏱️ **{tempo_limite} min**")
            c3.markdown(f"✅ **{min_aprovacao}%**")
            
            st.markdown("---")
            st.markdown(f"""
            * Sua prova contém **{qtd_questoes} Questões** sobre a faixa **{faixa_alvo}**.
            * ⏱️ O tempo limite é de **{tempo_limite} minutos**.
            * ✅ Nota mínima para aprovação: **{min_aprovacao}%**.
            
            **ATENÇÃO:**
            * Após clicar em **Iniciar**, o cronômetro não para.
            * Não é permitido consulta externa.
            * **REGRAS DE SEGURANÇA:** Se mudar de aba ou minimizar, **a prova será bloqueada**.
            * **Falhas:** Se o computador desligar, peça desbloqueio ao professor.

            **Boa prova!** 🥋
            """)

        if qtd_questoes > 0:
            if st.button("✅ Li e Concordo. INICIAR EXAME", type="primary", use_container_width=True):
                registrar_inicio_exame(usuario['id'])
                st.session_state.exame_iniciado = True
                # Timestamp absoluto do fim (Current Time + Minutos)
                st.session_state.fim_prova_ts = time.time() + (tempo_limite * 60)
                
                # Salva na sessão
                st.session_state.questoes_prova = lista_questoes 
                st.session_state.params_prova = {"tempo": tempo_limite, "min_aprovacao": min_aprovacao}
                st.rerun()
        else:
            st.warning(f"⚠️ Erro: Nenhuma questão encontrada para a faixa **{faixa_alvo}**. Contate o professor.")

    # 6. O EXAME EM SI
    else:
        questoes = st.session_state.get('questoes_prova', [])
        params = st.session_state.get('params_prova', {"tempo": 45, "min_aprovacao": 70})
        
        # Cálculo do Tempo Restante (Baseado no timestamp de fim calculado no início)
        agora_ts = time.time()
        restante_sec = int(st.session_state.fim_prova_ts - agora_ts)
        tempo_esgotado = restante_sec <= 0
        
        if tempo_esgotado:
            st.error("⌛ Tempo esgotado!")
            registrar_fim_exame(usuario['id'], False)
            st.session_state.exame_iniciado = False
            time.sleep(3)
            st.rerun()

        # Cronômetro Visual (JS)
        st.components.v1.html(
            f"""
            <div style="background:#0e2d26; border:2px solid #FFD700; border-radius:10px; padding:10px; text-align:center; color:#FFD700; font-family:sans-serif; font-size:24px; font-weight:bold;">
                <span id="timer">Carregando...</span>
            </div>
            <script>
                var timeLeft = {restante_sec};
                setInterval(function() {{
                    if (timeLeft <= 0) {{ document.getElementById('timer').innerHTML = "⌛ ACABOU"; return; }}
                    var m = Math.floor(timeLeft / 60);
                    var s = timeLeft % 60;
                    document.getElementById('timer').innerHTML = "⏱️ " + (m<10?"0"+m:m) + ":" + (s<10?"0"+s:s);
                    timeLeft--;
                }}, 1000);
            </script>
            """, 
            height=70
        )
        
        with st.form("form_exame"):
            respostas_usuario = {}
            for i, q in enumerate(questoes):
                txt_p = q.get('pergunta') or q.get('enunciado') or "Questão sem texto"
                st.markdown(f"**{i+1}. {txt_p}**")
                
                if q.get('imagem'): st.image(q['imagem'])
                
                opcoes = q.get('opcoes') or q.get('alternativas') or ['Verdadeiro', 'Falso']
                respostas_usuario[i] = st.radio("Resposta:", opcoes, key=f"q_{i}", index=None, label_visibility="collapsed")
                st.markdown("---")
            
            enviar = st.form_submit_button("Finalizar Prova", type="primary", use_container_width=True)
            
            if enviar:
                acertos = 0
                for i, q in enumerate(questoes):
                    correta = q.get('correta') or q.get('resposta') or q.get('gabarito')
                    if str(respostas_usuario.get(i)).strip().lower() == str(correta).strip().lower():
                        acertos += 1
                
                nota_final = (acertos / len(questoes)) * 100
                aprovado = nota_final >= params['min_aprovacao']
                
                registrar_fim_exame(usuario['id'], aprovado)
                st.session_state.exame_iniciado = False
                
                # Salva Histórico no Banco
                try:
                    codigo = gerar_codigo_verificacao() if aprovado else None
                    db.collection('resultados').add({
                        "usuario": usuario['nome'],
                        "faixa": faixa_alvo,
                        "pontuacao": nota_final,
                        "acertos": acertos,
                        "total": len(questoes),
                        "aprovado": aprovado,
                        "codigo_verificacao": codigo,
                        "data": firestore.SERVER_TIMESTAMP
                    })
                except: pass

                if aprovado:
                    st.balloons()
                    st.success(f"PARABÉNS! Aprovado com {nota_final:.1f}%!")
                    st.info("Certificado disponível no menu.")
                else:
                    st.error(f"Reprovado. Sua nota foi {nota_final:.1f}%.")
                    st.info("Aguarde liberação do professor para nova tentativa.")
                
                time.sleep(5)
                st.rerun()
