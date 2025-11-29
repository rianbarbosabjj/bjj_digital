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
# CARREGADOR DE EXAME
# =========================================
def carregar_exame_especifico(faixa_alvo):
    db = get_db()
    faixa_norm = faixa_alvo.strip().lower()
    questoes_finais = []
    tempo = 45
    nota = 70

    configs = db.collection('config_exames').stream()
    config_achada = None
    for doc in configs:
        d = doc.to_dict()
        if d.get('faixa', '').strip().lower() == faixa_norm:
            config_achada = d
            tempo = int(d.get('tempo_limite', 45))
            nota = int(d.get('aprovacao_minima', 70))
            if d.get('questoes'): questoes_finais = d.get('questoes')
            break
            
    if not questoes_finais:
        todas_refs = db.collection('questoes').stream()
        pool = []
        for doc in todas_refs:
            q = doc.to_dict()
            q_faixa = q.get('faixa', '').strip().lower()
            if q_faixa == faixa_norm or q_faixa == 'geral': pool.append(q)
        if pool:
            qtd = int(config_achada.get('qtd_questoes', 10)) if config_achada else 10
            if len(pool) > qtd: questoes_finais = random.sample(pool, qtd)
            else: questoes_finais = pool

    if not questoes_finais:
        todas_json = carregar_todas_questoes()
        questoes_finais = [q for q in todas_json if q.get('faixa', '').lower() == faixa_norm]
        if not questoes_finais and todas_json: questoes_finais = todas_json[:10]

    return questoes_finais, tempo, nota

# =========================================
# MÓDULOS SECUNDÁRIOS
# =========================================
def modo_rola(usuario):
    st.markdown(f"## 🥋 Modo Rola - Treino Livre")
    st.info("Em breve...")

def ranking():
    st.markdown("## 🏆 Ranking da Equipe")
    st.info("O ranking será atualizado em breve.")

# =========================================
# MEUS CERTIFICADOS (CORRIGIDO)
# =========================================
def meus_certificados(usuario):
    st.markdown(f"## 🏅 Meus Certificados")
    db = get_db()
    
    # Busca no banco
    try:
        # Atenção: O campo no banco é 'usuario' (nome) ou 'usuario_id'? 
        # No exame_de_faixa estamos salvando 'usuario': usuario['nome']. Vamos buscar por nome.
        docs = db.collection('resultados')\
                 .where('usuario', '==', usuario['nome'])\
                 .where('aprovado', '==', True).stream()
        
        lista_cert = [d.to_dict() for d in docs]
    except Exception as e:
        st.error(f"Erro ao buscar certificados: {e}")
        return

    if not lista_cert:
        st.info("Você ainda não possui certificados emitidos.")
        return

    st.success(f"Você possui {len(lista_cert)} certificado(s)!")

    for i, cert in enumerate(lista_cert):
        with st.container(border=True):
            c1, c2 = st.columns([3, 2])
            
            # Data formatada
            data_str = "-"
            if cert.get('data'):
                try: data_str = cert.get('data').strftime('%d/%m/%Y')
                except: pass
            
            c1.markdown(f"### 🥋 Faixa {cert.get('faixa')}")
            c1.caption(f"Data: {data_str} | Nota: {cert.get('pontuacao')}% | Código: {cert.get('codigo_verificacao')}")
            
            # Botão de Download
            pdf_bytes, pdf_name = gerar_pdf(
                usuario_nome=usuario['nome'],
                faixa=cert.get('faixa'),
                pontuacao=cert.get('acertos', 0), # Passa acertos
                total=cert.get('total', 10),      # Passa total
                codigo=cert.get('codigo_verificacao')
            )
            
            if pdf_bytes:
                c2.download_button(
                    label="📄 Baixar PDF",
                    data=pdf_bytes,
                    file_name=pdf_name,
                    mime="application/pdf",
                    key=f"btn_cert_{i}",
                    use_container_width=True
                )
            else:
                c2.error("Erro ao gerar PDF")

# =========================================
# EXAME DE FAIXA (CORRIGIDO BOTÃO FINAL)
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
    
    # 1. CHECAGEM DE RESULTADO RECENTE (MOSTRAR BOTÃO SE ACABOU DE FAZER)
    if st.session_state.resultado_prova:
        res = st.session_state.resultado_prova
        st.balloons()
        st.success(f"PARABÉNS! Aprovado com {res['nota']:.1f}%!")
        
        # Botão de Download Imediato
        pdf_bytes, pdf_name = gerar_pdf(
            usuario['nome'], res['faixa'], res['acertos'], res['total'], res['codigo']
        )
        if pdf_bytes:
            st.download_button("📥 BAIXAR CERTIFICADO AGORA", pdf_bytes, pdf_name, "application/pdf", use_container_width=True)
        
        if st.button("Voltar ao Início"):
            st.session_state.resultado_prova = None
            st.rerun()
        return # Para a execução aqui para não mostrar o resto

    # 2. REGRAS DE BLOQUEIO
    esta_habilitado = dados.get('exame_habilitado', False)
    faixa_alvo = dados.get('faixa_exame', None)
    
    if not esta_habilitado or not faixa_alvo:
        st.warning("🔒 Nenhum exame autorizado."); return

    # Datas
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

    status_atual = dados.get('status_exame', 'pendente')
    if status_atual == 'aprovado':
        st.success(f"✅ Você já foi aprovado na Faixa {faixa_alvo}!")
        st.info("Vá em 'Meus Certificados' para baixar.")
        return
        
    if status_atual == 'bloqueado':
        st.error("🚫 Exame BLOQUEADO."); return

    # Anti-Fraude
    if dados.get("status_exame") == "em_andamento":
        if not st.session_state.exame_iniciado:
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
                lista_questoes, tempo_limite, min_aprovacao = carregar_exame_especifico(faixa_alvo)
                st.session_state.exame_iniciado = True
                st.session_state.inicio_prova = inicio_real
                st.session_state.questoes_prova = lista_questoes 
                st.session_state.params_prova = {"tempo": tempo_limite, "min_aprovacao": min_aprovacao}
                st.session_state.fim_prova_ts = inicio_real.timestamp() + (tempo_limite * 60)
                st.rerun()
            else:
                bloquear_por_abandono(usuario['id'])
                st.error("🚨 INFRAÇÃO: Sessão perdida."); st.stop()

    # 3. CARREGAMENTO
    lista_questoes, tempo_limite, min_aprovacao = carregar_exame_especifico(faixa_alvo)
    qtd_questoes = len(lista_questoes)

    # JS Anti-Cola
    if st.session_state.exame_iniciado:
        html_anti_cola = """<script>document.addEventListener("visibilitychange", function() {if (document.hidden) {document.body.innerHTML = "<h1 style='color:red;text-align:center;margin-top:20%'>🚨 BLOQUEADO 🚨</h1>";}});</script>"""
        st.components.v1.html(html_anti_cola, height=0, width=0)

    # 4. TELA DE INÍCIO
    if not st.session_state.exame_iniciado:
        st.markdown(f"### 📋 Exame de Faixa **{faixa_alvo.upper()}**")
        with st.container(border=True):
            c1, c2, c3 = st.columns(3)
            c1.markdown(f"📝 **{qtd_questoes} Questões**")
            c2.markdown(f"⏱️ **{tempo_limite} min**")
            c3.markdown(f"✅ **{min_aprovacao}%**")
            st.markdown("---")
            st.write("Regras: Sem pausa, sem consulta. Se sair da tela, bloqueia.")
            
        if qtd_questoes > 0:
            if st.button("✅ INICIAR EXAME", type="primary", use_container_width=True):
                registrar_inicio_exame(usuario['id'])
                st.session_state.exame_iniciado = True
                st.session_state.inicio_prova = datetime.now()
                st.session_state.fim_prova_ts = time.time() + (tempo_limite * 60)
                st.session_state.questoes_prova = lista_questoes 
                st.session_state.params_prova = {"tempo": tempo_limite, "min_aprovacao": min_aprovacao}
                st.rerun()
        else:
            st.warning("Erro: Sem questões.")

    # 5. PROVA EM ANDAMENTO
    else:
        questoes = st.session_state.get('questoes_prova', [])
        params = st.session_state.get('params_prova', {"tempo": 45, "min_aprovacao": 70})
        
        agora_ts = time.time()
        if 'fim_prova_ts' not in st.session_state: st.session_state.fim_prova_ts = agora_ts + (params['tempo']*60)
        
        restante = int(st.session_state.fim_prova_ts - agora_ts)
        if restante <= 0:
            st.error("Tempo esgotado!")
            registrar_fim_exame(usuario['id'], False)
            st.session_state.exame_iniciado = False
            time.sleep(3); st.rerun()

        st.metric("Tempo Restante", f"{int(restante/60)}:{restante%60:02d}")
        
        with st.form("form_exame"):
            respostas_usuario = {}
            for i, q in enumerate(questoes):
                st.markdown(f"**{i+1}. {q.get('pergunta') or 'Questão'}**")
                if q.get('imagem'): st.image(q['imagem'])
                respostas_usuario[i] = st.radio("Resp:", q.get('opcoes', ['V','F']), key=f"q_{i}", index=None)
                st.markdown("---")
            
            if st.form_submit_button("Finalizar Prova", type="primary", use_container_width=True):
                acertos = 0
                for i, q in enumerate(questoes):
                    gabarito = q.get('correta') or q.get('resposta')
                    if str(respostas_usuario.get(i)).strip().lower() == str(gabarito).strip().lower():
                        acertos += 1
                
                nota = (acertos / len(questoes)) * 100
                aprovado = nota >= params['min_aprovacao']
                
                registrar_fim_exame(usuario['id'], aprovado)
                st.session_state.exame_iniciado = False
                
                codigo = None
                if aprovado:
                    codigo = gerar_codigo_verificacao()
                    # SALVA NA SESSÃO PARA MOSTRAR NA PROXIMA TELA
                    st.session_state.resultado_prova = {
                        "nota": nota, "aprovado": True, "faixa": faixa_alvo,
                        "acertos": acertos, "total": len(questoes), "codigo": codigo
                    }
                
                # Salva no banco de resultados
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
