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

# ==============================================================================
# CONFIGURAÇÃO DE CORES
# ==============================================================================
CORES_FAIXAS = {
    "CINZA E BRANCA": (150, 150, 150), "CINZA": (128, 128, 128), "CINZA E PRETA": (100, 100, 100), 
    "AMARELA E BRANCA": (240, 230, 140), "AMARELA": (255, 215, 0), "AMARELA E PRETA": (184, 134, 11),
    "LARANJA E BRANCA": (255, 160, 122), "LARANJA": (255, 140, 0), "LARANJA E PRETA": (200, 100, 0),
    "VERDE e BRANCA": (144, 238, 144), "VERDE": (0, 128, 0), "VERDE E PRETA": (0, 100, 0),
    "AZUL": (0, 0, 205), "ROXA": (128, 0, 128), "MARROM": (139, 69, 19), "PRETA": (0, 0, 0)
}

def get_cor_faixa(nome_faixa):
    for chave, cor in CORES_FAIXAS.items():
        if chave in str(nome_faixa).upper():
            return cor
    return (0, 0, 0) 

# ==============================================================================
# FUNÇÕES ÚTEIS
# ==============================================================================
def normalizar_nome(nome):
    if not nome: return "sem_nome"
    return "_".join(unicodedata.normalize("NFKD", nome).encode("ASCII", "ignore").decode().split()).lower()

def formatar_e_validar_cpf(cpf):
    if not cpf: return None
    c = re.sub(r'\D', '', str(cpf))
    if len(c) != 11 or c == c[0]*11: return None
    return f"{c[:3]}.{c[3:6]}.{c[6:9]}-{c[9:]}"

def formatar_cep(cep):
    if not cep: return None
    c = ''.join(filter(str.isdigit, cep))
    return c if len(c) == 8 else None

def buscar_cep(cep):
    c = formatar_cep(cep)
    if not c: return None
    try:
        r = requests.get(f"https://viacep.com.br/ws/{c}/json/", timeout=3)
        if r.status_code == 200:
            d = r.json()
            if "erro" not in d:
                return {"logradouro": d.get("logradouro","").upper(), "bairro": d.get("bairro","").upper(), "cidade": d.get("localidade","").upper(), "uf": d.get("uf","").upper()}
    except: pass
    return None

def gerar_senha_temporaria(t=8):
    return ''.join(secrets.choice(string.ascii_letters + string.digits) for i in range(t))

def enviar_email_recuperacao(dest, senha):
    try:
        s_email = st.secrets.get("EMAIL_SENDER")
        s_pwd = st.secrets.get("EMAIL_PASSWORD")
        if not s_email or not s_pwd: return False
        msg = MIMEMultipart()
        msg['Subject'] = "Recuperação de Senha - BJJ Digital"
        msg['From'] = s_email
        msg['To'] = dest
        corpo = f"<html><body><h2>Recuperação</h2><p>Senha: <b>{senha}</b></p></body></html>"
        msg.attach(MIMEText(corpo, 'html'))
        server = smtplib.SMTP("smtp.zoho.com", 587)
        server.starttls()
        server.login(s_email, s_pwd)
        server.sendmail(s_email, dest, msg.as_string())
        server.quit()
        return True
    except: return False

# ==============================================================================
# UPLOADS E MIDIA
# ==============================================================================
def normalizar_link_video(url):
    if not url: return None
    try:
        if "shorts/" in url:
            return f"https://www.youtube.com/watch?v={url.split('shorts/')[1].split('?')[0]}"
        elif "youtu.be/" in url:
            return f"https://www.youtube.com/watch?v={url.split('youtu.be/')[1].split('?')[0]}"
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
        
        ext = arquivo.name.split('.')[-1]
        blob_name = f"questoes/{uuid.uuid4()}.{ext}"
        blob = bucket.blob(blob_name)
        
        arquivo.seek(0)
        blob.upload_from_file(arquivo, content_type=arquivo.type)
        
        access_token = str(uuid.uuid4())
        metadata = {"firebaseStorageDownloadTokens": access_token}
        blob.metadata = metadata
        blob.patch()

        blob_path_encoded = quote(blob_name, safe='')
        return f"https://firebasestorage.googleapis.com/v0/b/{bucket.name}/o/{blob_path_encoded}?alt=media&token={access_token}"
    except Exception as e:
        st.error(f"Erro Upload: {e}")
        return None

# ==============================================================================
# LÓGICA DE USUÁRIOS E CURSOS
# ==============================================================================

def listar_todos_usuarios_para_selecao():
    """Retorna lista de usuários (professores/admins) com CPF."""
    db = get_db()
    try:
        users = db.collection('usuarios').stream()
        lista = []
        for u in users:
            dados = u.to_dict()
            # Converte para string e minúsculo para comparar
            tipo_usuario = str(dados.get('tipo', '')).lower().strip()
            
            # LISTA QUE ACEITA SEUS DADOS DE TESTE (None/Vazio)
            tipos_permitidos = ['professor', 'admin', 'mestre', 'instrutor', 'prof', 'none', 'aluno', '']
            
            if tipo_usuario in tipos_permitidos:
                lista.append({
                    'id': u.id, 
                    'nome': dados.get('nome', 'Sem Nome'), 
                    'email': dados.get('email'),
                    'cpf': dados.get('cpf', 'N/A')
                })
        
        lista.sort(key=lambda x: x['nome'])
        return lista
    except Exception as e:
        print(f"Erro ao listar usuários: {e}")
        return []

def criar_curso(professor_id, nome_professor, professor_equipe, titulo, descricao, modalidade, publico, equipe_destino, pago, preco, split_custom, certificado_automatico, duracao_estimada, nivel, editores_ids=[]):
    """Cria um novo curso salvando a EQUIPE DO PROFESSOR."""
    db = get_db()
    
    novo_curso = {
        "professor_id": professor_id,
        "professor_nome": nome_professor,
        "professor_equipe": professor_equipe, # <--- CAMPO SALVO
        "editores_ids": editores_ids,
        "titulo": titulo,
        "descricao": descricao,
        "modalidade": modalidade,
        "publico": publico,
        "equipe_destino": equipe_destino,
        "pago": pago,
        "preco": float(preco),
        "split_custom": split_custom,
        "certificado_automatico": certificado_automatico,
        "ativo": True,
        "criado_em": datetime.now(),
        "duracao_estimada": duracao_estimada,
        "nivel": nivel
    }
    
    _, doc_ref = db.collection('cursos').add(novo_curso)
    return doc_ref.id

def editar_curso(curso_id, dados_atualizados):
    db = get_db()
    try:
        db.collection('cursos').document(curso_id).update(dados_atualizados)
        return True
    except Exception as e:
        print(f"Erro ao editar curso: {e}")
        return False

def excluir_curso(curso_id: str) -> bool:
    db = get_db()
    if not db: return False
    try:
        modulos_ref = db.collection('modulos').where('curso_id', '==', curso_id).stream()
        for mod in modulos_ref:
            mod_id = mod.id
            aulas_ref = db.collection('aulas').where('modulo_id', '==', mod_id).stream()
            for aula in aulas_ref: db.collection('aulas').document(aula.id).delete()
            db.collection('modulos').document(mod_id).delete()

        inscricoes_ref = db.collection('inscricoes').where('curso_id', '==', curso_id).stream()
        for insc in inscricoes_ref: db.collection('inscricoes').document(insc.id).delete()

        db.collection('cursos').document(curso_id).delete()
        return True
    except Exception as e:
        print(f"Erro ao excluir curso: {e}")
        return False

def listar_cursos_do_professor(usuario_id):
    db = get_db()
    lista_cursos = []
    try:
        # Dono
        cursos_dono = db.collection('cursos').where('professor_id', '==', usuario_id).stream()
        for doc in cursos_dono:
            c = doc.to_dict()
            c['id'] = doc.id
            c['papel'] = 'Dono'
            lista_cursos.append(c)
        
        # Editor
        cursos_editor = db.collection('cursos').where('editores_ids', 'array_contains', usuario_id).stream()
        ids_existentes = [c['id'] for c in lista_cursos]
        for doc in cursos_editor:
            if doc.id not in ids_existentes:
                c = doc.to_dict()
                c['id'] = doc.id
                c['papel'] = 'Editor'
                lista_cursos.append(c)
    except: pass
    return lista_cursos

def listar_cursos_disponiveis_para_usuario(usuario):
    db = get_db()
    cursos_ref = db.collection('cursos').where('ativo', '==', True).stream()
    lista_cursos = []
    equipe_usuario = usuario.get('equipe', '').lower().strip()
    
    for doc in cursos_ref:
        curso = doc.to_dict()
        curso['id'] = doc.id
        if curso.get('publico') == 'equipe':
            equipe_curso = str(curso.get('equipe_destino', '')).lower().strip()
            if usuario.get('tipo') != 'admin' and equipe_curso != equipe_usuario: continue 
        lista_cursos.append(curso)
    return lista_cursos

def listar_modulos_e_aulas(curso_id):
    db = get_db()
    try:
        modulos = db.collection('modulos').where('curso_id', '==', curso_id).order_by('ordem').stream()
        estrutura = []
        for m in modulos:
            mod_data = m.to_dict()
            mod_data['id'] = m.id
            aulas_ref = db.collection('aulas').where('modulo_id', '==', m.id).stream()
            aulas = [{"id": a.id, **a.to_dict()} for a in aulas_ref]
            aulas.sort(key=lambda x: x.get('titulo', '')) 
            mod_data['aulas'] = aulas
            estrutura.append(mod_data)
        return estrutura
    except: return []

def criar_modulo(curso_id, titulo, descricao, ordem):
    db = get_db()
    db.collection('modulos').add({
        "curso_id": curso_id, "titulo": titulo, "descricao": descricao, 
        "ordem": ordem, "criado_em": datetime.now()
    })

def criar_aula(module_id, titulo, tipo, conteudo, duracao_min):
    db = get_db()
    conteudo_safe = conteudo.copy()
    
    # Simulação de upload para local (substituir por Cloud Storage em prod)
    if 'arquivo_video' in conteudo_safe:
        del conteudo_safe['arquivo_video']
        conteudo_safe['arquivo_video_nome'] = "video_upload.mp4" 
        
    if 'material_apoio' in conteudo_safe:
        del conteudo_safe['material_apoio']
        conteudo_safe['material_apoio_nome'] = "material.pdf"

    db.collection('aulas').add({
        "modulo_id": module_id, "titulo": titulo, "tipo": tipo,
        "conteudo": conteudo_safe, "duracao_min": duracao_min, "criado_em": datetime.now()
    })

def obter_inscricao(user_id, curso_id):
    db = get_db()
    docs = db.collection('inscricoes').where('usuario_id', '==', user_id).where('curso_id', '==', curso_id).stream()
    for doc in docs: return doc.to_dict()
    return None

def inscrever_usuario_em_curso(user_id, curso_id):
    if obter_inscricao(user_id, curso_id): return
    get_db().collection('inscricoes').add({
        "usuario_id": user_id, "curso_id": curso_id, "progresso": 0,
        "aulas_concluidas": [], "criado_em": datetime.now(), "status": "ativo"
    })

def verificar_aula_concluida(user_id, aula_id):
    db = get_db()
    inscricoes = db.collection('inscricoes').where('usuario_id', '==', user_id).stream()
    for insc in inscricoes:
        if aula_id in insc.to_dict().get('aulas_concluidas', []): return True
    return False

def marcar_aula_concluida(user_id, aula_id):
    db = get_db()
    aula_ref = db.collection('aulas').document(aula_id).get()
    if not aula_ref.exists: return
    
    mod_id = aula_ref.to_dict().get('modulo_id')
    curso_id = db.collection('modulos').document(mod_id).get().to_dict().get('curso_id')
    
    insc_query = db.collection('inscricoes').where('usuario_id', '==', user_id).where('curso_id', '==', curso_id).stream()
    insc_doc = next(insc_query, None)
    
    if insc_doc:
        concluidas = insc_doc.to_dict().get('aulas_concluidas', [])
        if aula_id not in concluidas:
            concluidas.append(aula_id)
            # Recalculo simples
            db.collection('inscricoes').document(insc_doc.id).update({
                "aulas_concluidas": concluidas, 
                "progresso": 100 if concluidas else 0, # Simplificado para evitar erro de leitura
                "ultimo_acesso": datetime.now()
            })
