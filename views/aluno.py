import streamlit as st
import time
import random
from datetime import datetime
import pytz # Para garantir fusos horários corretos se necessário
from database import get_db
from utils import (
    registrar_inicio_exame, 
    registrar_fim_exame, 
    bloquear_por_abandono,
    carregar_todas_questoes,
    normalizar_nome
)

# =========================================
# CARREGADOR DE EXAME (INTELIGENTE)
# =========================================
def carregar_exame_especifico(faixa_alvo):
    """
    Busca as configurações e questões para a faixa que o professor liberou.
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
            # Pega questões da faixa alvo OU questões gerais
            q_faixa = q.get('faixa', '').strip().lower()
            if q_faixa == faixa_norm or q_faixa == 'geral':
                pool.append(q)
        
        if pool:
            qtd = int(config_achada.get('qtd_questoes', 10)) if config_achada else 10
            # Sorteia se tiver muitas
            if len(pool) > qtd:
                questoes_finais = random.sample(pool, qtd)
            else:
                questoes_finais = pool

    # 3. Fallback JSON local (último caso)
    if not questoes_finais:
        todas_json = carregar_todas_questoes()
        questoes_finais = [q for q in todas_json if q.get('faixa', '').lower() == faixa_norm]
        # Se ainda vazio e for teste, pega aleatórias para não travar
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
    if usuario.get('status_exame') == 'aprovado':
        st.success(f"Parabéns! Aprovado no exame para {usuario.get('faixa_atual', 'N/A')}.")
        st.info("Certificado disponível após graduação presencial.")
    else:
        st.info("Nenhum certificado disponível.")

def ranking():
    st.markdown("## 🏆 Ranking")
    st.info("O ranking será atualizado em breve.")

# =========================================
# EXAME DE FAIXA (LÓGICA CONECTADA AO PAINEL DO PROFESSOR)
# =========================================
def exame_de_faixa(usuario):
    st.header(f"🥋 Exame de Faixa - {usuario['nome'].split()[0].title()}")
    
    db = get_db()
    # Pega dados atualizados do usuário para checar a permissão
    doc_ref = db.collection('usuarios').document(usuario['id'])
    doc = doc_ref.get()
    
    if not doc.exists:
        st.error("Erro ao carregar perfil.")
        return
        
    dados = doc.to_dict()
    
    # -----------------------------------------------------------
    # 1. VERIFICAÇÃO DE AUTORIZAÇÃO (DA TELA DO PROFESSOR)
    # -----------------------------------------------------------
    
    # Verifica se foi habilitado pelo botão verde na gestão
    # Atenção aos nomes dos campos salvos pelo admin.py. Ajuste se necessário.
    esta_habilitado = dados.get('exame_habilitado', False) 
    faixa_alvo = dados.get('faixa_exame', None) # A faixa que o professor selecionou no dropdown
    
    if not esta_habilitado or not faixa_alvo:
        st.warning("🔒 Você não possui nenhum exame agendado ou autorizado no momento.")
        st.info("Entre em contato com seu professor para liberar seu acesso na 'Gestão de Exame'.")
        return

    # -----------------------------------------------------------
    # 2. VERIFICAÇÃO DE PRAZO (DATAS E HORAS)
    # -----------------------------------------------------------
    
    # Pega as datas salvas pelo professor
    try:
        data_inicio = dados.get('exame_inicio') # Timestamp ou string
        data_fim = dados.get('exame_fim')       # Timestamp ou string
        
        agora = datetime.now()
        
        # Converte se vier string ISO, ou assume datetime se vier do Firestore
        if isinstance(data_inicio, str): data_inicio = datetime.fromisoformat(data_inicio)
        if isinstance(data_fim, str): data_fim = datetime.fromisoformat(data_fim)
        
        # Remove timezone para comparação (naive) se necessário
        if data_inicio: data_inicio = data_inicio.replace(tzinfo=None)
        if data_fim: data_fim = data_fim.replace(tzinfo=None)
        
        # Lógica da Janela de Tempo
        if data_inicio and agora < data_inicio:
            st.warning(f"⏳ Seu exame está agendado, mas ainda não começou.")
            st.write(f"**Início:** {data_inicio.strftime('%d/%m/%Y às %H:%M')}")
            return
            
        if data_fim and agora > data_fim:
            st.error(f"🚫 O prazo para realizar este exame expirou.")
            st.write(f"**Venceu em:** {data_fim.strftime('%d/%m/%Y às %H:%M')}")
            return
            
    except Exception as e:
        # Se der erro na data, mas está habilitado, deixa passar (fail-open) ou bloqueia (fail-close)
        # Vamos logar e deixar passar se tiver a flag habilitado, para não travar o aluno por erro de formato
        print(f"Aviso de data: {e}")

    # -----------------------------------------------------------
    # 3. VERIFICAÇÃO DE STATUS (JÁ FEZ? ESTÁ BLOQUEADO?)
    # -----------------------------------------------------------
    status_atual = dados.get('status_exame', 'pendente')
    
    if status_atual == 'aprovado':
        st.success("✅ Você já foi aprovado neste exame!")
        return
        
    if status_atual == 'bloqueado':
        st.error("🚫 Exame BLOQUEADO por segurança (saída da aba ou interrupção).")
        st.warning("Peça para seu professor clicar no botão vermelho ⛔ na coluna 'Ação' para liberar novamente.")
        return

    if status_atual == 'reprovado':
        # Verifica carência de 72h (opcional, já que o professor pode liberar manual)
        # Se o professor re-habilitou (mudou datas), consideramos liberado.
        pass 

    # 4. Anti-Fraude (Fuga durante execução)
    if dados.get("status_exame") == "em_andamento":
        bloquear_por_abandono(usuario['id'])
        st.error("🚨 DETECÇÃO DE INFRAÇÃO: Você saiu da página durante o exame.")
        st.stop()

    # -----------------------------------------------------------
    # 5. CARREGAMENTO DO CONTEÚDO (DA FAIXA ALVO)
    # -----------------------------------------------------------
    
    # Aqui é o pulo do gato: Buscamos a prova da 'faixa_alvo' (ex: Preta), não da atual
    lista_questoes, tempo_limite, min_aprovacao = carregar_exame_especifico(faixa_alvo)
    qtd_questoes = len(lista_questoes)

    # --- JAVASCRIPT ANTI-COLA ---
    html_anti_cola = """
    <script>
    document.addEventListener("visibilitychange", function() {
        if (document.hidden) {
            document.body.innerHTML = "<h1 style='color:red; text-align:center; margin-top:20%; font-family:sans-serif;'>🚨 INFRAÇÃO DETECTADA 🚨<br>Você saiu da aba da prova. Bloqueado.</h1>";
        }
    });
    </script>
    """
    st.components.v1.html(html_anti_cola, height=0, width=0)

    # 6. TELA DE INÍCIO
    if "exame_iniciado" not in st.session_state:
        st.session_state.exame_iniciado = False

    if not st.session_state.exame_iniciado:
        
        st.markdown(f"### 📋 Exame de Faixa **{faixa_alvo.upper()}**")
        st.caption("Leia atentamente as instruções antes de iniciar")
        
        with st.container(border=True):
            c1, c2, c3 = st.columns(3)
            c1.markdown(f"📝 **{qtd_questoes} Questões**")
            c2.markdown(f"⏱️ Tempo: **{tempo_limite} min**")
            c3.markdown(f"✅ Aprovação: **{min_aprovacao}%**")
            
            st.markdown("---")
            st.markdown(f"""
            * Sua prova contém **{qtd_questoes} Questões** sobre a faixa **{faixa_alvo}**.
            * ⏱️ Tempo limite: **{tempo_limite} minutos**.
            * ✅ Nota mínima: **{min_aprovacao}%**.
            
            **ATENÇÃO:**
            * Ao clicar em **Iniciar**, o tempo começa e não para.
            * Não é permitido consulta externa.
            * **REGRAS DE SEGURANÇA:** Se mudar de aba ou minimizar, **a prova será bloqueada**.
            * **Falhas:** Se o PC desligar, contate o professor.

            **Boa prova!** 🥋
            """)

        if qtd_questoes > 0:
            if st.button("✅ Li e Concordo. INICIAR EXAME", type="primary", use_container_width=True):
                registrar_inicio_exame(usuario['id'])
                st.session_state.exame_iniciado = True
                st.session_state.inicio_prova = datetime.now()
                st.session_state.questoes_prova = lista_questoes 
                st.session_state.params_prova = {"tempo": tempo_limite, "min_aprovacao": min_aprovacao}
                st.rerun()
        else:
            st.warning(f"⚠️ Erro: Nenhuma questão encontrada para a faixa **{faixa_alvo}**. Professor, verifique o cadastro de questões.")

    # 7. O EXAME EM SI
    else:
        questoes = st.session_state.get('questoes_prova', [])
        params = st.session_state.get('params_prova', {"tempo": 45, "min_aprovacao": 70})
        
        agora = datetime.now()
        inicio = st.session_state.get('inicio_prova', agora)
        decorrido = (agora - inicio).total_seconds() / 60
        tempo_restante = params['tempo'] - decorrido
        
        if tempo_restante <= 0:
            st.error("⌛ Tempo esgotado!")
            registrar_fim_exame(usuario['id'], False)
            st.session_state.exame_iniciado = False
            time.sleep(3)
            st.rerun()

        cols = st.columns([3, 1])
        cols[0].info(f"📝 Prova Faixa {faixa_alvo} - **Não mude de aba!**")
        
        mins = int(tempo_restante)
        segs = int((tempo_restante - mins) * 60)
        cols[1].metric("Tempo Restante", f"{mins}:{segs:02d}")
        
        with st.form("form_exame"):
            respostas_usuario = {}
            for i, q in enumerate(questoes):
                # Suporte a diferentes chaves de pergunta
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
                
                if aprovado:
                    st.balloons()
                    st.success(f"PARABÉNS! Aprovado com {nota_final:.1f}%!")
                    st.info("Certificado disponível no menu.")
                else:
                    st.error(f"Reprovado. Sua nota foi {nota_final:.1f}%.")
                    st.info("Aguarde o professor liberar uma nova tentativa.")
                
                time.sleep(5)
                st.rerun()
