"""
courses_engine.py
Motor de lógica para gerenciamento de cursos, módulos e aulas do BJJ Digital.
"""

import streamlit as st
import os
from datetime import datetime
from database import get_db
import uuid

# ==============================================================================
# FUNÇÕES DE USUÁRIOS E PERMISSÕES
# ==============================================================================

def listar_todos_usuarios_para_selecao():
    """Retorna uma lista simples de usuários (professores/admins) para serem editores."""
    db = get_db()
    try:
        users = db.collection('usuarios').stream()
        lista = []
        for u in users:
            dados = u.to_dict()
            # Filtra apenas quem é professor ou admin
            if dados.get('tipo') in ['professor', 'admin']:
                lista.append({
                    'id': u.id, 
                    'nome': dados.get('nome', 'Sem Nome'), 
                    'email': dados.get('email')
                })
        return lista
    except Exception as e:
        print(f"Erro ao listar usuários: {e}")
        return []

# ==============================================================================
# FUNÇÕES DE CURSO (CRUD)
# ==============================================================================

def criar_curso(professor_id, nome_professor, titulo, descricao, modalidade, publico, equipe_destino, pago, preco, split_custom, certificado_automatico, editores_ids=[]):
    """Cria um novo curso no banco de dados com suporte a editores."""
    db = get_db()
    
    novo_curso = {
        "professor_id": professor_id,
        "professor_nome": nome_professor,
        "editores_ids": editores_ids, # Lista de IDs de editores
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
        "duracao_estimada": "A definir",
        "nivel": "Todos os Níveis"
    }
    
    _, doc_ref = db.collection('cursos').add(novo_curso)
    return doc_ref.id

def editar_curso(curso_id, dados_atualizados):
    """Atualiza os dados de um curso existente."""
    db = get_db()
    try:
        db.collection('cursos').document(curso_id).update(dados_atualizados)
        return True
    except Exception as e:
        print(f"Erro ao editar curso: {e}")
        return False

def excluir_curso(curso_id: str) -> bool:
    """
    Exclui um curso e todos os seus dados associados (módulos, aulas, inscrições).
    """
    db = get_db()
    if not db:
        print("Erro: Sem conexão com banco de dados.")
        return False

    try:
        print(f"--- Iniciando exclusão do curso ID: {curso_id} ---")

        # 1. Excluir Aulas e Módulos
        modulos_ref = db.collection('modulos').where('curso_id', '==', curso_id).stream()
        
        for mod in modulos_ref:
            mod_id = mod.id
            
            # Deletar aulas associadas ao módulo
            aulas_ref = db.collection('aulas').where('modulo_id', '==', mod_id).stream()
            for aula in aulas_ref:
                db.collection('aulas').document(aula.id).delete()
            
            # Deleta o módulo
            db.collection('modulos').document(mod_id).delete()

        # 2. Excluir Inscrições
        inscricoes_ref = db.collection('inscricoes').where('curso_id', '==', curso_id).stream()
        for insc in inscricoes_ref:
            db.collection('inscricoes').document(insc.id).delete()

        # 3. Excluir o curso
        db.collection('cursos').document(curso_id).delete()
        
        return True

    except Exception as e:
        print(f"❌ ERRO CRÍTICO ao excluir curso: {e}")
        return False

def listar_cursos_do_professor(usuario_id):
    """Lista cursos onde o usuário é DONO ou EDITOR."""
    db = get_db()
    lista_cursos = []
    
    try:
        # 1. Cursos onde ele é o dono
        cursos_dono = db.collection('cursos').where('professor_id', '==', usuario_id).stream()
        for doc in cursos_dono:
            c = doc.to_dict()
            c['id'] = doc.id
            c['papel'] = 'Dono'
            lista_cursos.append(c)
            
        # 2. Cursos onde ele é editor (array-contains)
        cursos_editor = db.collection('cursos').where('editores_ids', 'array_contains', usuario_id).stream()
        
        ids_existentes = [c['id'] for c in lista_cursos]
        
        for doc in cursos_editor:
            if doc.id not in ids_existentes:
                c = doc.to_dict()
                c['id'] = doc.id
                c['papel'] = 'Editor'
                lista_cursos.append(c)
    except Exception as e:
        print(f"Erro ao listar cursos: {e}")
            
    return lista_cursos

def listar_cursos_disponiveis_para_usuario(usuario):
    """
    Lista cursos disponíveis para o aluno (filtra por equipe se necessário).
    """
    db = get_db()
    cursos_ref = db.collection('cursos').where('ativo', '==', True).stream()
    
    lista_cursos = []
    equipe_usuario = usuario.get('equipe', '').lower().strip()
    
    for doc in cursos_ref:
        curso = doc.to_dict()
        curso['id'] = doc.id
        
        # Filtro de visibilidade
        if curso.get('publico') == 'equipe':
            equipe_curso = str(curso.get('equipe_destino', '')).lower().strip()
            # Se for admin, vê tudo. Se não, tem que ser da mesma equipe.
            if usuario.get('tipo') != 'admin' and equipe_curso != equipe_usuario:
                continue 
                
        lista_cursos.append(curso)
        
    return lista_cursos

# ==============================================================================
# FUNÇÕES DE MÓDULOS E AULAS
# ==============================================================================

def listar_modulos_do_curso(curso_id):
    """Retorna apenas a lista de módulos."""
    db = get_db()
    try:
        modulos = db.collection('modulos')\
            .where('curso_id', '==', curso_id)\
            .order_by('ordem')\
            .stream()
        return [{"id": m.id, **m.to_dict()} for m in modulos]
    except Exception as e:
        print(f"Erro ao listar módulos: {e}")
        return []

def listar_modulos_e_aulas(curso_id):
    """Retorna estrutura completa: Módulos com suas respectivas Aulas."""
    db = get_db()
    
    modulos = listar_modulos_do_curso(curso_id)
    estrutura_completa = []
    
    for mod in modulos:
        aulas_ref = db.collection('aulas')\
            .where('modulo_id', '==', mod['id'])\
            .stream()
            
        # Ordenação manual se necessário, ou pelo titulo
        aulas_lista = [{"id": a.id, **a.to_dict()} for a in aulas_ref]
        # Ordenar aulas por título ou ordem se tiver
        aulas_lista.sort(key=lambda x: x.get('titulo', '')) 
        
        mod['aulas'] = aulas_lista
        estrutura_completa.append(mod)
        
    return estrutura_completa

def criar_modulo(curso_id, titulo, descricao, ordem):
    """Cria um novo módulo."""
    db = get_db()
    db.collection('modulos').add({
        "curso_id": curso_id,
        "titulo": titulo,
        "descricao": descricao,
        "ordem": ordem,
        "criado_em": datetime.now()
    })

def criar_aula(module_id, titulo, tipo, conteudo, duracao_min):
    """Cria uma nova aula (salva arquivos localmente para teste)."""
    db = get_db()
    
    # === LÓGICA DE UPLOAD ===
    upload_dir = "uploads"
    if not os.path.exists(upload_dir):
        os.makedirs(upload_dir)

    # 1. Vídeo
    if tipo == 'video' and conteudo.get('tipo_video') == 'upload':
        arquivo = conteudo.get('arquivo_video')
        if arquivo:
            # Em produção, usar storage na nuvem
            # Aqui, salvamos apenas para não quebrar a lógica
            pass # O Streamlit FileUploader já segura o buffer

    # === SALVAR NO BANCO ===
    # Convertemos uploads em algo serializável ou ignoramos bytes
    conteudo_safe = conteudo.copy()
    if 'arquivo_video' in conteudo_safe:
        # Remover o objeto de arquivo pois não salva no Firestore
        # Em produção, substituiria pela URL do storage
        del conteudo_safe['arquivo_video']
        conteudo_safe['arquivo_video_nome'] = "video_upload.mp4" 
        
    if 'material_apoio' in conteudo_safe:
        del conteudo_safe['material_apoio']
        conteudo_safe['material_apoio_nome'] = "arquivo.pdf"

    db.collection('aulas').add({
        "modulo_id": module_id,
        "titulo": titulo,
        "tipo": tipo,
        "conteudo": conteudo_safe,
        "duracao_min": duracao_min,
        "criado_em": datetime.now()
    })

# ==============================================================================
# FUNÇÕES DE INSCRIÇÃO E PROGRESSO
# ==============================================================================

def obter_inscricao(user_id, curso_id):
    """Verifica se existe inscrição."""
    db = get_db()
    docs = db.collection('inscricoes')\
        .where('usuario_id', '==', user_id)\
        .where('curso_id', '==', curso_id)\
        .stream()
    for doc in docs:
        return doc.to_dict()
    return None

def inscrever_usuario_em_curso(user_id, curso_id):
    """Cria o registro de inscrição."""
    db = get_db()
    if obter_inscricao(user_id, curso_id):
        return
    db.collection('inscricoes').add({
        "usuario_id": user_id,
        "curso_id": curso_id,
        "progresso": 0,
        "aulas_concluidas": [],
        "criado_em": datetime.now(),
        "status": "ativo"
    })

def verificar_aula_concluida(user_id, aula_id):
    """Checa se aula está concluída."""
    db = get_db()
    inscricoes = db.collection('inscricoes').where('usuario_id', '==', user_id).stream()
    for insc in inscricoes:
        dados = insc.to_dict()
        if aula_id in dados.get('aulas_concluidas', []):
            return True
    return False

def marcar_aula_concluida(user_id, aula_id):
    """Marca aula como concluída."""
    db = get_db()
    
    # Descobre o curso da aula
    aula_ref = db.collection('aulas').document(aula_id).get()
    if not aula_ref.exists: return
    
    modulo_id = aula_ref.to_dict().get('modulo_id')
    mod_ref = db.collection('modulos').document(modulo_id).get()
    curso_id = mod_ref.to_dict().get('curso_id')
    
    # Busca inscrição
    inscricao_query = db.collection('inscricoes')\
        .where('usuario_id', '==', user_id)\
        .where('curso_id', '==', curso_id)\
        .stream()
    
    insc_doc = None
    for d in inscricao_query:
        insc_doc = d
        break
        
    if not insc_doc: return
        
    # Atualiza
    dados_insc = insc_doc.to_dict()
    concluidas = dados_insc.get('aulas_concluidas', [])
    
    if aula_id not in concluidas:
        concluidas.append(aula_id)
        
        # Recalcula progresso
        total_aulas = 0
        mods = listar_modulos_e_aulas(curso_id)
        for m in mods: total_aulas += len(m['aulas'])
            
        progresso_pct = (len(concluidas) / total_aulas) * 100 if total_aulas > 0 else 0
        if progresso_pct > 100: progresso_pct = 100
        
        db.collection('inscricoes').document(insc_doc.id).update({
            "aulas_concluidas": concluidas,
            "progresso": progresso_pct,
            "ultimo_acesso": datetime.now()
        })
