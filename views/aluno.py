import streamlit as st
import time
import uuid
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
    gerar_codigo_verificacao,
    gerar_pdf
)
from firebase_admin import firestore

# =========================================
# FUNÇÕES DE CARREGAMENTO (ORIGINAIS RESTAURADAS)
# =========================================
@st.cache_data(ttl=300) 
def carregar_questoes_firestore():
    """Carrega questões do Modo Rola"""
    db = get_db()
    todas_questoes = []
    try:
        docs_questoes = list(db.collection('questoes').stream())
        if docs_questoes:
            for d in docs_questoes:
                q = d.to_dict()
                if q.get('status', 'aprovada') == 'aprovada':
                    todas_questoes.append(q)
    except: pass
    
    # Fallback local
    if not todas_questoes and os.path.exists("questions"):
        for f in os.listdir("questions"):
            if f.endswith(".json"):
                try:
                    with open(f"questions/{f}", "r", encoding="utf-8") as file:
                        q_list = json.load(file)
                        tema_nome = f.replace(".json", "")
                        for q in q_list: q['tema'] = tema_nome; todas_questoes.append(q)
                except: continue
    return todas_questoes

@st.cache_data(ttl=300)
def carregar_exame_firestore(faixa_sel):
    """
    Carrega o exame específico da faixa (questões e tempo)
    Exatamente como funcionava no código original.
    """
    db = get_db()
    
    # Tenta buscar pelo nome da faixa (ex: "Preta")
    doc_ref = db.collection('exames').document(faixa_sel)
    doc_exame = doc_ref.get()
    dados_exame = doc_exame.to_dict() if doc_exame.exists else {}
    
    # Se não achar, tenta buscar em arquivo JSON local (fallback)
    if not dados_exame:
        json_path = f"exames/faixa_{faixa_sel.lower()}.json"
        if os.path.exists(json_path):
            try:
                with open(json_path, "r", encoding="utf-8") as f: 
                    dados_exame = json.load(f)
            except: pass
            
    return dados_exame

# =========================================
# MODO ROLA (TREINO LIVRE)
# =========================================
def modo_rola(usuario_logado):
    st.markdown("<h1 style='color:#FFD700;'>🤼 Modo Rola - Treino Livre</h1>", unsafe_allow_html=True)
    
    todas_questoes = carregar_questoes_firestore()

    if not todas_questoes:
        st.warning("Banco de questões vazio.")
        return

    temas = sorted(list(set(q.get('tema', 'Geral') for q in todas_questoes)))
    temas.insert(0, "Todos os Temas")

    col1, col2 = st.columns(2)
    with col1: tema = st.selectbox("Selecione o tema:", temas)
    with col2: faixa = st.selectbox("Sua faixa:", ["Branca", "Cinza", "Amarela", "Laranja", "Verde", "Azul", "Roxa", "Marrom", "Preta"])

    if st.button("Iniciar Treino 🤼", use_container_width=True):
        if tema == "Todos os Temas":
            questoes_selecionadas = todas_questoes
        else:
            questoes_selecionadas = [q for q in todas_questoes if q.get('tema') == tema]

        if not questoes_selecionadas:
            st.error("Nenhuma questão encontrada.")
            return

        random.shuffle(questoes_selecionadas)
        questoes_treino = questoes_selecionadas[:10] 
        
        st.markdown("---")
        with st.form("form_treino"):
            respostas_usuario = {}
            for i, q in enumerate(questoes_treino, 1):
                st.markdown(f"**{i}.** {q.get('pergunta', 'Sem enunciado')}")
                if q.get("imagem"): st.image(q["imagem"])
                
                respostas_usuario[i] = st.radio(f"Opções {i}", options=q.get('opcoes', []), key=f"q_{i}", index=None, label_visibility="collapsed")
                st.markdown("---")
            
            enviar = st.form_submit_button("Finalizar Treino", use_container_width=True, type="primary")

        if enviar:
            acertos = 0
            for i, q in enumerate(questoes_treino, 1):
                resp = respostas_usuario.get(i)
                # Comparação segura
                if str(resp) == str(q.get('resposta')) or str(resp) == str(q.get('correta')): 
                    acertos += 1
            
            total = len(questoes_treino)
            percentual = int((acertos / total) * 100) if total > 0 else 0
            
            st.balloons()
            st.success(f"Treino concluído! {acertos}/{total} ({percentual}%).")

# =========================================
# EXAME DE FAIXA (LÓGICA UNIFICADA E ROBUSTA)
# =========================================
def exame_de_faixa(usuario_logado):
    st.markdown("<h1 style='color:#FFD700;'>🥋 Exame de Faixa</h1>", unsafe_allow_html=True)
    db = get_db()

    # 1. Carrega dados do usuário para verificar permissão
    doc_ref = db.collection('usuarios').document(usuario_logado['id'])
    doc = doc_ref.get()
    if not doc.exists:
        st.error("Erro de perfil.")
        return
    dados_usuario = doc.to_dict()

    # 2. Verifica Status (Bloqueio/Aprovação)
    status_atual = dados_usuario.get('status_exame', 'pendente')
    if status_atual == 'bloqueado':
        st.error("🚫 Exame BLOQUEADO (Saída de página ou infração).")
        st.warning("Contate seu professor para desbloqueio.")
        return
    if status_atual == 'aprovado':
        st.success("✅ Você já foi aprovado neste exame!")
        return
    
    # Se estava em andamento e recarregou a página -> BLOQUEIA
    if dados_usuario.get("status_exame") == "em_andamento":
        bloquear_por_abandono(usuario_logado['id'])
        st.error("🚨 INFRAÇÃO: Saída da página durante a prova.")
        st.stop()

    # 3. Verifica Autorização do Professor
    # O professor define 'exame_habilitado' = True e 'faixa_exame' = 'Preta' (por exemplo)
    if not dados_usuario.get('exame_habilitado'):
        st.warning("🔒 Nenhum exame autorizado pelo professor.")
        return

    faixa_sel = dados_usuario.get('faixa_exame')
    if not faixa_sel:
        st.warning("Erro: O professor autorizou mas não definiu a faixa do exame.")
        return

    # 4. Verifica Datas
    try:
        agora = datetime.now()
        ini_str = dados_usuario.get('exame_inicio')
        fim_str = dados_usuario.get('exame_fim')
        
        # Converte strings ISO se necessário
        if isinstance(ini_str, str): ini = datetime.fromisoformat(ini_str)
        else: ini = ini_str # Já é timestamp ou datetime
            
        if isinstance(fim_str, str): fim = datetime.fromisoformat(fim_str)
        else: fim = fim_str

        # Remove timezone para comparar (naive)
        if ini: ini = ini.replace(tzinfo=None)
        if fim: fim = fim.replace(tzinfo=None)

        if ini and agora < ini:
            st.warning(f"⏳ O exame só começa em {ini.strftime('%d/%m/%Y %H:%M')}")
            return
        if fim and agora > fim:
            st.error(f"🚫 O prazo expirou em {fim.strftime('%d/%m/%Y %H:%M')}")
            return
    except Exception as e:
        # Se der erro de data, mas está autorizado, segue (fail-open para não travar)
        print(f"Aviso data: {e}")

    # --- 5. CARREGA A PROVA (USANDO A FUNÇÃO ORIGINAL QUE FUNCIONAVA) ---
    dados_exame = carregar_exame_firestore(faixa_sel)
    
    if not dados_exame:
        st.error(f"⚠️ Erro: O conteúdo da prova '{faixa_sel}' não foi encontrado no sistema.")
        return

    lista_questoes = dados_exame.get('questoes', [])
    tempo_limite = int(dados_exame.get('tempo_limite', 60))
    min_aprovacao = int(dados_exame.get('aprovacao_minima', 70))

    if not lista_questoes:
        st.warning("Esta prova está vazia. Avise seu professor.")
        return

    # --- 6. TELA DE INSTRUÇÕES (COM ANTI-COLA) ---
    
    # Script JS Anti-Fraude
    html_anti_cola = """
    <script>
    document.addEventListener("visibilitychange", function() {
        if (document.hidden) {
            document.body.innerHTML = "<h1 style='color:red; text-align:center; margin-top:20%'>🚨 BLOQUEADO POR MUDANÇA DE ABA 🚨</h1>";
        }
    });
    </script>
    """
    st.components.v1.html(html_anti_cola, height=0, width=0)

    if 'prova_iniciada' not in st.session_state: st.session_state.prova_iniciada = False

    if not st.session_state.prova_iniciada:
        st.markdown(f"### 📋 Exame de Faixa **{faixa_sel}**")
        
        with st.container(border=True):
            c1, c2, c3 = st.columns(3)
            c1.markdown(f"📝 **{len(lista_questoes)} Questões**")
            c2.markdown(f"⏱️ **{tempo_limite} min**")
            c3.markdown(f"✅ **{min_aprovacao}%**")
            
            st.markdown("---")
            st.markdown("""
            **ATENÇÃO:**
            * O cronômetro não pausa.
            * Proibido mudar de aba (Bloqueio Imediato).
            * Reprovação exige espera de 72h (salvo liberação do professor).
            """)
            
            if st.button("✅ INICIAR EXAME AGORA", type="primary", use_container_width=True):
                registrar_inicio_exame(usuario_logado['id'])
                st.session_state.prova_iniciada = True
                # Define fim absoluto baseado no tempo atual do servidor
                st.session_state.fim_prova_ts = time.time() + (tempo_limite * 60)
                st.rerun()
        return

    # --- 7. PROVA EM ANDAMENTO ---
    
    # Cálculo do Tempo
    agora_ts = time.time()
    restante_sec = int(st.session_state.fim_prova_ts - agora_ts)
    tempo_esgotado = restante_sec <= 0

    if not tempo_esgotado:
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
        
        with st.form(key="form_prova"):
            respostas = {}
            for i, q in enumerate(lista_questoes, 1):
                st.markdown(f"**{i}.** {q.get('pergunta', 'Questão')}")
                if q.get("imagem"): st.image(q["imagem"])
                
                respostas[i] = st.radio("Resposta:", q.get('opcoes', []), key=f"r_{i}", index=None)
                st.markdown("---")
            
            finalizar = st.form_submit_button("Finalizar Exame 🏁", type="primary", use_container_width=True)
            
            if finalizar:
                acertos = 0
                for i, q in enumerate(lista_questoes, 1):
                    resp_user = respostas.get(i)
                    gabarito = q.get('resposta') or q.get('correta')
                    # Comparação flexível
                    if resp_user and str(resp_user).strip() == str(gabarito).strip():
                        acertos += 1
                
                percentual = int((acertos / len(lista_questoes)) * 100)
                aprovado = percentual >= min_aprovacao
                
                registrar_fim_exame(usuario_logado['id'], aprovado)
                st.session_state.prova_iniciada = False
                
                # Salva Resultado Detalhado
                codigo = None
                if aprovado:
                    codigo = gerar_codigo_verificacao()
                    st.balloons()
                    st.success(f"PARABÉNS! Aprovado com {percentual}%!")
                else:
                    st.error(f"Reprovado. Nota: {percentual}%.")
                
                # Salva no banco de resultados (histórico)
                try:
                    db.collection('resultados').add({
                        "usuario": usuario_logado["nome"],
                        "faixa": faixa_sel,
                        "pontuacao": percentual,
                        "acertos": acertos,
                        "total": len(lista_questoes),
                        "aprovado": aprovado,
                        "codigo_verificacao": codigo,
                        "data": firestore.SERVER_TIMESTAMP
                    })
                except: pass
                
                time.sleep(4)
                st.rerun()

    else:
        st.error("⌛ TEMPO ESGOTADO!")
        registrar_fim_exame(usuario_logado['id'], False)
        st.session_state.prova_iniciada = False
        time.sleep(3)
        st.rerun()

# =========================================
# RANKING E CERTIFICADOS
# =========================================
def ranking():
    st.markdown("<h1 style='color:#FFD700;'>🏆 Ranking</h1>", unsafe_allow_html=True)
    db = get_db()
    docs = db.collection('rola_resultados').stream()
    data = [d.to_dict() for d in docs]
    if not data: st.info("Ranking vazio."); return
    df = pd.DataFrame(data)
    if 'usuario' in df.columns:
        rdf = df.groupby("usuario", as_index=False).agg(media=("percentual", "mean"), total=("usuario", "count")).sort_values("media", ascending=False)
        st.dataframe(rdf, use_container_width=True)

def meus_certificados(usuario_logado):
    st.markdown("<h1 style='color:#FFD700;'>📜 Meus Certificados</h1>", unsafe_allow_html=True)
    db = get_db()
    # Filtra apenas aprovados
    docs = db.collection('resultados').where('usuario', '==', usuario_logado['nome']).where('aprovado', '==', True).stream()
    lista = [d.to_dict() for d in docs]
    
    if not lista: 
        st.info("Você ainda não possui certificados.")
        return

    for i, c in enumerate(lista):
        with st.container(border=True):
            c1, c2 = st.columns([3, 1])
            c1.markdown(f"**Faixa {c.get('faixa')}**")
            c1.caption(f"Código: {c.get('codigo_verificacao')} | Nota: {c.get('pontuacao')}%")
            
            if c2.button("📄 Baixar PDF", key=f"pdf_{i}"):
                try:
                    p_bytes, p_name = gerar_pdf(
                        usuario_logado['nome'], c.get('faixa'), 
                        c.get('acertos',0), c.get('total',10), 
                        c.get('codigo_verificacao','-')
                    )
                    st.download_button("Clique para Salvar", p_bytes, p_name, "application/pdf", key=f"dl_{i}")
                except: st.error("Erro ao gerar PDF.")
