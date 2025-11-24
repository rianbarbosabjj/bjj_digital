import bcrypt
from database import get_db
from utils import formatar_e_validar_cpf

def autenticar_local(usuario_email_ou_cpf, senha):
    """
    Autentica o usuário verificando email ou CPF no Firestore.
    """
    db = get_db()
    cpf_formatado = formatar_e_validar_cpf(usuario_email_ou_cpf)
    
    users_ref = db.collection('usuarios')
    usuario_doc = None

    # 1. Tenta buscar por Email (ou nome de usuário se foi salvo assim)
    # No Firestore, fazemos queries baseadas em campos
    query_email = users_ref.where('email', '==', usuario_email_ou_cpf).where('auth_provider', '==', 'local').stream()
    
    for doc in query_email:
        usuario_doc = doc
        break # Pega o primeiro encontrado
    
    # 2. Se não achou por email, tenta buscar por CPF (se for válido)
    if not usuario_doc and cpf_formatado:
        query_cpf = users_ref.where('cpf', '==', cpf_formatado).where('auth_provider', '==', 'local').stream()
        for doc in query_cpf:
            usuario_doc = doc
            break
            
    # 3. Se não achou nada, tenta buscar por Nome (fallback)
    if not usuario_doc:
        query_nome = users_ref.where('nome', '==', usuario_email_ou_cpf.upper()).where('auth_provider', '==', 'local').stream()
        for doc in query_nome:
            usuario_doc = doc
            break

    # Se encontrou o usuário, verifica a senha
    if usuario_doc:
        dados = usuario_doc.to_dict()
        senha_hash = dados.get('senha')
        
        if senha_hash and bcrypt.checkpw(senha.encode(), senha_hash.encode()):
            # Retorna os dados essenciais + o ID do documento (importante para updates)
            return {
                "id": usuario_doc.id, # O ID agora é a chave do documento no Firestore
                "nome": dados.get('nome'),
                "tipo": dados.get('tipo_usuario'),
                "email": dados.get('email')
            }
        
    return None

def buscar_usuario_por_email(email_ou_cpf):
    """Busca usuário para o fluxo do Google Auth."""
    db = get_db()
    users_ref = db.collection('usuarios')
    usuario_doc = None
    
    # Busca por email
    query = users_ref.where('email', '==', email_ou_cpf).stream()
    for doc in query:
        usuario_doc = doc
        break
        
    if usuario_doc:
        dados = usuario_doc.to_dict()
        return {
            "id": usuario_doc.id,
            "nome": dados.get('nome'),
            "tipo": dados.get('tipo_usuario'),
            "perfil_completo": dados.get('perfil_completo', False),
            "email": dados.get('email')
        }
        
    return None

def criar_usuario_parcial_google(email, nome):
    """Cria o registro inicial vindo do Google."""
    db = get_db()
    
    # Prepara os dados
    novo_usuario = {
        "email": email,
        "nome": nome.upper(),
        "auth_provider": "google",
        "perfil_completo": False,
        "data_criacao": firestore.SERVER_TIMESTAMP
    }
    
    # Adiciona ao Firestore (ele gera o ID automaticamente)
    update_time, doc_ref = db.collection('usuarios').add(novo_usuario)
    
    return {
        "id": doc_ref.id, 
        "email": email, 
        "nome": nome
    }
