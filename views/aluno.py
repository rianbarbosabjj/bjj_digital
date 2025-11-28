import streamlit as st
import time
import random
from datetime import datetime, timedelta
from database import get_db
from utils import (
    verificar_elegibilidade_exame, 
    registrar_inicio_exame, 
    registrar_fim_exame, 
    bloquear_por_abandono,
    carregar_todas_questoes, 
    normalizar_nome
)

def modo_rola(usuario):
    st.markdown(f"## 🥋 Modo Rola - Treino Livre")
    st.info("Em breve: Aqui você poderá treinar com questões aleatórias sem valer nota.")

def meus_certificados(usuario):
    st.markdown(f"## 🏅 Meus Certificados")
    db = get_db()
    
    if usuario.get('status_exame') == 'aprovado':
        st.success(f"Parabéns! Você foi aprovado no exame de faixa {usuario.get('faixa_atual', 'N/A')}.")
        st.info("O download do certificado oficial estará disponível após a graduação presencial.")
    else:
        st.info("Você ainda não possui certificados emitidos nesta plataforma.")

def ranking():
    st.markdown("## 🏆 Ranking da Equipe")
    st.info("O ranking será atualizado conforme os alunos realizarem os exames.")

# =========================================
# LÓGICA DO EXAME DE FAIXA
# =========================================
def exame_de_faixa(usuario):
    st.header(f"🥋 Exame de Faixa - {usuario['nome'].split()[0].title()}")
    
    # 1. Busca dados frescos do aluno no banco
    db = get_db()
    doc = db.collection('usuarios').document(usuario['id']).get()
    dados_atualizados = doc.to_dict()
    faixa_aluno = dados_atualizados.get('faixa_atual', 'Branca')
    
    # 2. Verifica regras de elegibilidade (72h, Bloqueio, etc)
    pode_fazer, msg = verificar_elegibilidade_exame(dados_atualizados)
    
    if not pode_fazer:
        st.warning(msg)
        st.caption("Se precisar de ajuda, contate seu professor.")
        return

    # 3. Detector de "Fuga" (Anti-Cheat no carregamento)
    if dados_atualizados.get("status_exame") == "em_andamento":
        bloquear_por_abandono(usuario['id'])
        st.error("🚨 DETECÇÃO DE INFRAÇÃO: Você saiu da página ou recarregou durante o exame.")
        st.warning("Seu exame foi bloqueado. Solicite o desbloqueio ao professor.")
        st.stop()

    # --- BUSCAR CONFIGURAÇÃO DO EXAME (CRIADO PELO PROFESSOR) ---
    # Tenta achar uma config específica para a faixa do aluno
    config_ref = db.collection('config_exames').where('faixa', '==', faixa_aluno).limit(1).stream()
    config_prova = None
    
    # Valores Padrão (Caso o professor não tenha configurado ainda)
    tempo_limite = 45
    qtd_questoes = 10
    porcentagem_aprovacao = 70
    
    for doc in config_ref:
        config_prova = doc.to_dict()
        # Se achou, substitui os valores padrão pelos do banco
        tempo_limite = int(config_prova.get('tempo_limite', 45))
        qtd_questoes = int(config_prova.get('qtd_questoes', 10))
        porcentagem_aprovacao = int(config_prova.get('aprovacao_minima', 70))
        break

    # --- JAVASCRIPT ANTI-FRAUDE ---
    html_anti_cola = """
    <script>
    document.addEventListener("visibilitychange", function() {
        if (document.hidden) {
            document.body.innerHTML = "<h1 style='color:red; text-align:center; margin-top:20%; font-family:sans-serif;'>🚨 INFRAÇÃO DETECTADA 🚨<br><br>Você saiu da aba da prova.<br>Isso viola as regras de segurança.<br><br>Atualize a página para ver seu status.</h1>";
        }
    });
    </script>
    """
    st.components.v1.html(html_anti_cola, height=0, width=0)

    # --- SELEÇÃO DAS QUESTÕES ---
    todas_questoes = carregar_todas_questoes()
    
    # 1. Tenta filtrar questões da faixa do aluno (se o JSON tiver esse campo)
    questoes_da_faixa = [q for q in todas_questoes if q.get('faixa', '').lower() == faixa_aluno.lower()]
    
    # 2. Se não tiver questões específicas da faixa, usa o banco geral
    banco_questoes = questoes_da_faixa if questoes_da_faixa else todas_questoes
    
    # 3. Seleciona a quantidade definida pelo professor
    if len(banco_questoes) >= qtd_questoes:
        lista_questoes = random.sample(banco_questoes, qtd_questoes)
    else:
        # Se tiver menos questões do que o pedido, usa todas as disponíveis
        lista_questoes = banco_questoes

    # Se a lista estiver vazia (erro no cadastro de questões)
    if not lista_questoes:
        qtd_questoes = 0

    # 4. TELA DE INÍCIO (INSTRUÇÕES)
    if "exame_iniciado" not in st.session_state:
        st.session_state.exame_iniciado = False

    if not st.session_state.exame_iniciado:
        
        st.markdown("### 📋 Leia atentamente as instruções antes de iniciar")
        
        with st.container(border=True):
            # Layout das Métricas
            c1, c2, c3 = st.columns(3)
            c1.markdown(f"📝 **{len(lista_questoes)} Questões**")
            c2.markdown(f"⏱️ Tempo: **{tempo_limite} min**")
            c3.markdown(f"✅ Aprovação: **{porcentagem_aprovacao}%**")
            
            st.markdown("---")
            
            # Texto Personalizado Dinâmico
            st.markdown(f"""
            * Sua prova contém **{len(lista_questoes)} Questões**
            * ⏱️ O tempo limite para finalização do exame é de **{tempo_limite} minutos**
            * ✅ Para ser aprovado, você precisa acertar no mínimo **{porcentagem_aprovacao}%** do exame
            
            **ATENÇÃO:**
            * Após clicar em **✅ Iniciar exame**, não será possível pausar ou interromper o cronômetro.
            * Se o tempo acabar antes de você finalizar, você será considerado **reprovado**.
            * Não é permitido consulta a materiais externos.
            * Esteja em um lugar confortável e silencioso para ajudar na sua concentração.
            
            **REGRAS DE SEGURANÇA:**
            * 🚫 **Não saia desta tela:** Se mudar de aba ou minimizar, **a prova será bloqueada**.
            * ⏳ **Tentativa Única:** Se reprovar, aguarde **72 horas**.
            * 🔌 **Falhas:** Se o PC desligar, peça desbloqueio ao professor.

            **Boa prova!** 🥋
            """)

        # Botão de Início
        if st.button("✅ Li e Concordo. INICIAR EXAME", type="primary", use_container_width=True):
            if len(lista_questoes) == 0:
                st.warning("Erro: Nenhuma questão carregada para sua faixa. Contate o professor.")
            else:
                registrar_inicio_exame(usuario['id'])
                st.session_state.exame_iniciado = True
                st.session_state.inicio_prova = datetime.now()
                # Salva as questões sorteadas na sessão
                st.session_state.questoes_prova = lista_questoes 
                # Salva parametros da prova na sessão
                st.session_state.params_prova = {
                    "tempo": tempo_limite, 
                    "min_aprovacao": porcentagem_aprovacao
                }
                st.rerun()
    
    # 5. O EXAME EM SI (QUANDO INICIADO)
    else:
        questoes = st.session_state.get('questoes_prova', [])
        params = st.session_state.get('params_prova', {"tempo": 45, "min_aprovacao": 70})
        
        # Timer
        agora = datetime.now()
        inicio = st.session_state.get('inicio_prova', agora)
        decorrido = (agora - inicio).total_seconds() / 60
        tempo_restante = params['tempo'] - decorrido
        
        if tempo_restante <= 0:
            st.error("Tempo esgotado!")
            registrar_fim_exame(usuario['id'], False)
            st.session_state.exame_iniciado = False
            st.rerun()

        # Cabeçalho do Exame
        cols = st.columns([3, 1])
        cols[0].info(f"📝 Prova Faixa {faixa_aluno} - **Não mude de aba!**")
        
        # Cor do timer (Amarelo se < 5 min, Vermelho se < 1 min)
        cor_timer = "normal"
        if tempo_restante < 1: cor_timer = "off" # vermelho no st.metric
        elif tempo_restante < 5: cor_timer = "off" 
        
        cols[1].metric("Tempo Restante", f"{int(tempo_restante)} min")
        
        with st.form("form_exame"):
            respostas_usuario = {}
            
            for i, q in enumerate(questoes):
                st.markdown(f"**{i+1}. {q.get('pergunta', 'Pergunta sem texto')}**")
                
                opcoes = q.get('opcoes', ['Verdadeiro', 'Falso'])
                # Dica: Se quiser embaralhar as opções, faça antes de exibir
                
                respostas_usuario[i] = st.radio(
                    "Sua resposta:", 
                    opcoes, 
                    key=f"q_{i}", 
                    index=None, 
                    label_visibility="collapsed"
                )
                st.markdown("---")
            
            enviar = st.form_submit_button("Finalizar Prova", type="primary", use_container_width=True)
            
            if enviar:
                # Validação: Obrigatório responder tudo?
                # if any(respostas_usuario.get(i) is None for i in range(len(questoes))):
                #     st.warning("Responda todas as questões.")
                # else:
                
                acertos = 0
                for i, q in enumerate(questoes):
                    if respostas_usuario.get(i) == q.get('correta'):
                        acertos += 1
                
                nota_final = (acertos / len(questoes)) * 100
                aprovado = nota_final >= params['min_aprovacao']
                
                registrar_fim_exame(usuario['id'], aprovado)
                st.session_state.exame_iniciado = False
                
                if aprovado:
                    st.balloons()
                    st.success(f"PARABÉNS! Aprovado com {nota_final:.1f}%!")
                    st.info("Seu certificado já está disponível no menu 'Meus Certificados'.")
                else:
                    st.error(f"Reprovado. Sua nota foi {nota_final:.1f}%. Necessário: {params['min_aprovacao']}%.")
                    st.info("Aguarde 72h para nova tentativa.")
                
                time.sleep(5)
                st.rerun()
