import os
import re
import requests
import streamlit as st
import smtplib
import secrets
import string
import unicodedata
import random
import uuid
import json
from urllib.parse import quote
from datetime import datetime
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from fpdf import FPDF
from database import get_db
from firebase_admin import firestore, storage 

# --- CONFIGURAÇÃO ---
CORES_FAIXAS = {
    "CINZA E BRANCA": (150, 150, 150), "CINZA": (128, 128, 128), "CINZA E PRETA": (100, 100, 100), 
    "AMARELA E BRANCA": (240, 230, 140), "AMARELA": (255, 215, 0), "AMARELA E PRETA": (184, 134, 11),
    "LARANJA E BRANCA": (255, 160, 122), "LARANJA": (255, 140, 0), "LARANJA E PRETA": (200, 100, 0),
    "VERDE e BRANCA": (144, 238, 144), "VERDE": (0, 128, 0), "VERDE E PRETA": (0, 100, 0),
    "AZUL": (0, 0, 205), "ROXA": (128, 0, 128), "MARROM": (139, 69, 19), "PRETA": (0, 0, 0)
}

def get_cor_faixa(nome_faixa):
    for chave, cor in CORES_FAIXAS.items():
        if chave in str(nome_faixa).upper(): return cor
    return (0, 0, 0) 

# --- ÚTEIS ---
def normalizar_nome(nome):
    if not nome: return "sem_nome"
    return "_".join(unicodedata.normalize("NFKD", nome).encode("ASCII", "ignore").decode().split()).lower()

def formatar_e_validar_cpf(cpf):
    if not cpf: return None
    c = re.sub(r'\D', '', str(cpf))
    return f"{c[:3]}.{c[3:6]}.{c[6:9]}-{c[9:]}" if len(c) == 11 else None

def gerar_senha_temporaria(t=8):
    return ''.join(secrets.choice(string.ascii_letters + string.digits) for i in range(t))

def enviar_email_recuperacao(dest, senha):
    try:
        s_email = st.secrets.get("EMAIL_SENDER")
        s_pwd = st.secrets.get("EMAIL_PASSWORD")
        if not s_email or not s_pwd: return False
        msg = MIMEMultipart(); msg['Subject'] = "Recuperação BJJ"; msg['From'] = s_email; msg['To'] = dest
        msg.attach(MIMEText(f"Senha: {senha}", 'html'))
        server = smtplib.SMTP("smtp.zoho.com", 587); server.starttls()
        server.login(s_email, s_pwd); server.sendmail(s_email, dest, msg.as_string()); server.quit()
        return True
    except: return False

# --- UPLOAD ---
def normalizar_link_video(url):
    if not url: return None
    try:
        if "shorts/" in url: return f"https://www.youtube.com/watch?v={url.split('shorts/')[1].split('?')[0]}"
        elif "youtu.be/" in url: return f"https://www.youtube.com/watch?v={url.split('youtu.be/')[1].split('?')[0]}"
        return url
    except: return url

def fazer_upload_midia(arquivo):
    if not arquivo: return None
    try:
        bucket = storage.bucket()
        if not bucket.name:
            bucket_name = st.secrets.get("firebase", {}).get("storage_bucket")
            if not bucket_name: bucket_name = st.secrets.get("storage_bucket")
            if not bucket_name: return None
        blob = bucket.blob(f"questoes/{uuid.uuid4()}.{arquivo.name.split('.')[-1]}")
        arquivo.seek(0)
        blob.upload_from_file(arquivo, content_type=arquivo.type)
        blob.make_public()
        return blob.public_url
    except Exception as e:
        st.error(f"Erro Upload: {e}"); return None

# --- IA ---
IA_ATIVADA = False 
try:
    from sentence_transformers import SentenceTransformer
    from sklearn.metrics.pairwise import cosine_similarity
    import numpy as np
    IA_ATIVADA = True
    @st.cache_resource
    def carregar_modelo_ia(): return SentenceTransformer('paraphrase-multilingual-MiniLM-L12-v2')
    
    def verificar_duplicidade_ia(nova_pergunta, lista_existentes, threshold=0.65):
        if not lista_existentes: return False, None
        model = carregar_modelo_ia()
        emb_novo = model.encode([nova_pergunta])
        textos = [str(q.get('pergunta', '')) for q in lista_existentes]
        emb_ex = model.encode(textos)
        scores = cosine_similarity(emb_novo, emb_ex)[0]
        idx = np.argmax(scores)
        if scores[idx] >= threshold: return True, f"{textos[idx]} ({scores[idx]*100:.1f}%)"
        return False, None
except:
    def verificar_duplicidade_ia(n, l, t=0.75): return False, "IA Off"

def auditoria_ia_questao(pergunta, alternativas, correta):
    api_key = st.secrets.get("GEMINI_API_KEY")
    if not api_key: return "⚠️ Chave GEMINI_API_KEY não configurada."
    prompt = f"Analise BJJ: {pergunta} | {alternativas} | Gabarito: {correta}"
    try:
        import google.generativeai as genai
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel('models/gemini-1.5-flash')
        return model.generate_content(prompt).text
    except Exception as e: return f"Erro IA: {e}"

def auditoria_ia_openai(p, a, c): return "GPT Indisponível"

# --- CURSOS E EXAMES ---
def listar_todos_usuarios_para_selecao():
    db = get_db()
    try:
        users = db.collection('usuarios').stream()
        lista = []
        for u in users:
            d = u.to_dict()
            tp = str(d.get('tipo', '')).lower().strip()
            if tp in ['professor', 'admin', 'mestre', 'instrutor', 'none', 'aluno', '']:
                lista.append({'id': u.id, 'nome': d.get('nome', 'Sem Nome'), 'email': d.get('email'), 'cpf': d.get('cpf', 'N/A')})
        lista.sort(key=lambda x: x['nome'])
        return lista
    except: return []

def criar_curso(pid, pnome, peq, tit, desc, mod, pub, eq, pg, pr, sp, cert, dur, niv, eds=[]):
    db = get_db()
    db.collection('cursos').add({
        "professor_id": pid, "professor_nome": pnome, "professor_equipe": peq,
        "editores_ids": eds, "titulo": tit, "descricao": desc, "modalidade": mod,
        "publico": pub, "equipe_destino": eq, "pago": pg, "preco": float(pr),
        "split_custom": sp, "certificado_automatico": cert, "ativo": True,
        "criado_em": datetime.now(), "duracao_estimada": dur, "nivel": niv
    })

def editar_curso(cid, dados):
    try: get_db().collection('cursos').document(cid).update(dados); return True
    except: return False

def excluir_curso(cid):
    db = get_db(); 
    try: db.collection('cursos').document(cid).delete(); return True
    except: return False

def listar_cursos_do_professor(uid):
    db = get_db(); l = []
    try:
        for d in db.collection('cursos').where('professor_id', '==', uid).stream():
            c = d.to_dict(); c['id'] = d.id; c['papel'] = 'Dono'; l.append(c)
        for d in db.collection('cursos').where('editores_ids', 'array_contains', uid).stream():
            if d.id not in [x['id'] for x in l]:
                c = d.to_dict(); c['id'] = d.id; c['papel'] = 'Editor'; l.append(c)
    except: pass
    return l

def listar_cursos_disponiveis_para_usuario(u):
    db = get_db(); l = []
    eq_u = u.get('equipe', '').lower().strip()
    for d in db.collection('cursos').where('ativo', '==', True).stream():
        c = d.to_dict(); c['id'] = d.id
        if c.get('publico') == 'equipe' and str(c.get('equipe_destino','')).lower().strip() != eq_u and u.get('tipo') != 'admin': continue
        l.append(c)
    return l

def listar_modulos_e_aulas(cid):
    db = get_db()
    try:
        mods = db.collection('modulos').where('curso_id', '==', cid).order_by('ordem').stream()
        res = []
        for m in mods:
            md = m.to_dict(); md['id'] = m.id
            auls = list(db.collection('aulas').where('modulo_id', '==', m.id).stream())
            md['aulas'] = [{"id": a.id, **a.to_dict()} for a in auls]
            res.append(md)
        return res
    except: return []

def criar_modulo(cid, tit, desc, ord):
    get_db().collection('modulos').add({"curso_id": cid, "titulo": tit, "descricao": desc, "ordem": ord, "criado_em": datetime.now()})

def criar_aula(mid, tit, tip, cont, dur):
    cont_s = cont.copy()
    if 'arquivo_video' in cont_s: del cont_s['arquivo_video']; cont_s['arquivo_video_nome'] = 'video.mp4'
    if 'material_apoio' in cont_s: del cont_s['material_apoio']; cont_s['material_apoio_nome'] = 'file.pdf'
    get_db().collection('aulas').add({"modulo_id": mid, "titulo": tit, "tipo": tip, "conteudo": cont_s, "duracao_min": dur, "criado_em": datetime.now()})

def obter_inscricao(uid, cid):
    docs = list(get_db().collection('inscricoes').where('usuario_id', '==', uid).where('curso_id', '==', cid).stream())
    return docs[0].to_dict() if docs else None

def inscrever_usuario_em_curso(uid, cid):
    if not obter_inscricao(uid, cid):
        get_db().collection('inscricoes').add({"usuario_id": uid, "curso_id": cid, "progresso": 0, "aulas_concluidas": [], "criado_em": datetime.now()})

def verificar_aula_concluida(uid, aid):
    inscs = list(get_db().collection('inscricoes').where('usuario_id', '==', uid).stream())
    for i in inscs:
        if aid in i.to_dict().get('aulas_concluidas', []): return True
    return False

def marcar_aula_concluida(uid, aid):
    db = get_db()
    a_ref = db.collection('aulas').document(aid).get()
    if not a_ref.exists: return
    mid = a_ref.to_dict().get('modulo_id')
    cid = db.collection('modulos').document(mid).get().to_dict().get('curso_id')
    inscs = list(db.collection('inscricoes').where('usuario_id', '==', uid).where('curso_id', '==', cid).stream())
    if inscs:
        doc = inscs[0]; d = doc.to_dict(); conc = d.get('aulas_concluidas', [])
        if aid not in conc:
            conc.append(aid)
            db.collection('inscricoes').document(doc.id).update({"aulas_concluidas": conc, "progresso": 100}) # Simplificado

def verificar_elegibilidade_exame(d):
    return True, "Ok" # Simplificado para teste

def registrar_inicio_exame(uid): pass
def registrar_fim_exame(uid, aprovado): pass
def bloquear_por_abandono(uid): pass
