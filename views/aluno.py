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
    normalizar_nome
)

# =========================================
# CARREGADOR DE EXAME
# =========================================
def carregar_exame_especifico(faixa_alvo):
    db = get_db()
    faixa_norm = faixa_alvo.strip().lower()
    
    questoes_finais = []
    tempo = 45
    nota = 70

    # 1. Configurações
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
            
    # 2. Banco geral
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

    # 3. Fallback
    if not questoes_finais:
        todas_json = carregar_todas_questoes()
        questoes_finais = [q for q in todas_json if q.get('faixa', '').lower() == faixa_norm]
        if not questoes_finais and todas_json:
             questoes_finais = todas_json[:10]

    return questoes_finais, tempo, nota

# =========================================
# MÓDULOS SECUNDÁRIOS
# =========================================
def modo_rola(usuario):
    st.markdown(f"## 🥋 Modo Rola - Treino Livre")
    st.info("Em breve.")

def meus_certificados(usuario):
    st.markdown(f"## 🏅 Meus Certificados")
    st.info("Nenhum certificado disponível.")

def ranking():
    st.markdown("## 🏆 Ranking")
    st.info("O ranking será atualizado em breve.")

# =========================================
# EXAME DE FAIXA (COM DIAGNÓSTICO)
# =========================================
def exame_de_faixa(usuario):
    st.header(f"🥋 Exame de Faixa - {usuario['nome'].split()[0].title()}")
    
    db = get_db()
    doc_ref = db.collection('usuarios').document(usuario['id'])
    doc = doc_ref.get()
    
    if not doc.exists:
        st.error("Erro ao carregar perfil.")
        return
        
    dados = doc.to_dict()
    
    # --- ÁREA DE DEBUG (Apagaremos isso depois) ---
    with st.expander("🛠️ DADOS TÉCNICOS (DEBUG) - Tire print se der erro", expanded=True):
        st.write(f"**ID Usuário:** {usuario['id']}")
        st.json(dados) # Isso vai mostrar EXATAMENTE o que tem no banco
    # -----------------------------------------------

    # Verifica campos esperados
    esta_habilitado = dados.get('exame_habilitado')
    faixa_alvo = dados.get('faixa_exame')
    
    # Tenta ser flexível: se 'exame_habilitado' não existir, tenta verificar datas
    if not esta_habilitado:
        # Check secundário: Se tem data de início e fim definidas, consideramos habilitado
        if dados.get('exame_inicio') and dados.get('exame_fim'):
            esta_habilitado = True

    if not esta_habilitado or not faixa_alvo:
        st.warning("🔒 Nenhum exame autorizado pelo professor.")
        st.caption(f"Status técnico: Habilitado={esta_habilitado}, Faixa={faixa_alvo}")
        return

    # Verificação de Prazo
    try:
        data_inicio = dados.get('exame_inicio')
        data_fim = dados.get('exame_fim')
        agora = datetime.now()
        
        if isinstance(data_inicio, str): data_inicio = datetime.fromisoformat(data_inicio)
        if isinstance(data_fim, str): data_fim = datetime.fromisoformat(data_fim)
        
        if data_inicio: data_inicio = data_inicio.replace(tzinfo=None)
        if data_fim: data_fim = data_fim.replace(tzinfo=None)
        
        if data_inicio and agora < data_inicio:
            st.warning(f"⏳ O exame começa em {data_inicio.strftime('%d/%m/%Y %H:%M')}")
            return
        if data_fim and agora > data_fim:
            st.error(f"🚫 Prazo expirado em {data_fim.strftime('%d/%m/%Y %H:%M')}")
            return
            
    except Exception as e:
        st.error(f"Erro de data: {e}")

    # Verifica status
    status_atual = dados.get('status_exame', 'pendente')
    if status_atual == 'aprovado':
        st.success("✅ Você já foi aprovado!")
        return
    if status_atual == 'bloqueado':
        st.error("🚫 Exame BLOQUEADO.")
        return

    # Se estiver em andamento, bloqueia (Anti-fraude)
    if dados.get("status_exame") == "em_andamento":
        bloquear_por_abandono(usuario['id'])
        st.error("🚨 DETECÇÃO DE INFRAÇÃO: Saída da página.")
        st.stop()

    # Carrega Exame
    lista_questoes, tempo_limite, min_aprovacao = carregar_exame_especifico(faixa_alvo)
    qtd_questoes = len(lista_questoes)

    # JS Anti-Cola
    html_anti_cola = """
    <script>
    document.addEventListener("visibilitychange", function() {
        if (document.hidden) {
            document.body.innerHTML = "<h1 style='color:red; text-align:center; margin-top:20%'>🚨 BLOQUEADO 🚨</h1>";
        }
    });
    </script>
    """
    st.components.v1.html(html_anti_cola, height=0, width=0)

    if "exame_iniciado" not in st.session_state:
        st.session_state.exame_iniciado = False

    if not st.session_state.exame_iniciado:
        st.markdown(f"### 📋 Exame de Faixa **{faixa_alvo.upper()}**")
        with st.container(border=True):
            c1, c2, c3 = st.columns(3)
            c1.markdown(f"📝 **{qtd_questoes} Questões**")
            c2.markdown(f"⏱️ **{tempo_limite} min**")
            c3.markdown(f"✅ **{min_aprovacao}%**")
            
            st.markdown("---")
            st.write("Clique abaixo para iniciar.")
            
        if qtd_questoes > 0:
            if st.button("✅ INICIAR EXAME", type="primary", use_container_width=True):
                registrar_inicio_exame(usuario['id'])
                st.session_state.exame_iniciado = True
                st.session_state.inicio_prova = datetime.now()
                st.session_state.questoes_prova = lista_questoes 
                st.session_state.params_prova = {"tempo": tempo_limite, "min_aprovacao": min_aprovacao}
                st.rerun()
        else:
            st.warning(f"Erro: Sem questões para faixa {faixa_alvo}.")

    else:
        questoes = st.session_state.get('questoes_prova', [])
        params = st.session_state.get('params_prova', {"tempo": 45, "min_aprovacao": 70})
        
        agora = datetime.now()
        inicio = st.session_state.get('inicio_prova', agora)
        decorrido = (agora - inicio).total_seconds() / 60
        tempo_restante = params['tempo'] - decorrido
        
        if tempo_restante <= 0:
            st.error("Tempo esgotado!")
            registrar_fim_exame(usuario['id'], False)
            st.session_state.exame_iniciado = False
            time.sleep(3); st.rerun()

        st.metric("Tempo", f"{int(tempo_restante)} min")
        
        with st.form("form_exame"):
            respostas_usuario = {}
            for i, q in enumerate(questoes):
                st.markdown(f"**{i+1}. {q.get('pergunta', '...') or q.get('enunciado', '...')}**")
                respostas_usuario[i] = st.radio("Resp:", q.get('opcoes', ['V','F']), key=f"q_{i}")
                st.markdown("---")
            
            if st.form_submit_button("Finalizar", type="primary"):
                acertos = 0
                for i, q in enumerate(questoes):
                    # Comparação simples para debug
                    if str(respostas_usuario.get(i))[0] == str(q.get('correta') or q.get('resposta'))[0]:
                        acertos += 1
                
                nota = (acertos / len(questoes)) * 100
                aprovado = nota >= params['min_aprovacao']
                registrar_fim_exame(usuario['id'], aprovado)
                st.session_state.exame_iniciado = False
                if aprovado: st.success("Aprovado!")
                else: st.error("Reprovado.")
                time.sleep(3); st.rerun()
