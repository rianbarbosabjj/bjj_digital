# ==============================================================================
# 8. GESTÃO FINANCEIRA E PAGAMENTOS (SPLIT 90/10)
# ==============================================================================

def calcular_split_pagamento(valor_total):
    """
    Calcula a divisão: 90% Professor, 10% Plataforma.
    """
    if not valor_total: return 0.0, 0.0
    
    valor = float(valor_total)
    parte_plataforma = valor * 0.10  # 10%
    parte_professor = valor * 0.90   # 90%
    
    return round(parte_plataforma, 2), round(parte_professor, 2)

def processar_compra_curso(usuario_id, curso_id, valor_total):
    """
    Registra a inscrição E a transação financeira separada.
    """
    db = get_db()
    
    # 1. Busca dados do curso para saber quem é o professor
    curso_ref = db.collection('cursos').document(curso_id)
    curso_doc = curso_ref.get()
    
    if not curso_doc.exists:
        return False, "Curso não encontrado."
        
    dados_curso = curso_doc.to_dict()
    professor_id = dados_curso.get('professor_id')
    
    # 2. Calcula o Split
    v_app, v_prof = calcular_split_pagamento(valor_total)
    
    try:
        batch = db.batch()
        
        # A. Criar Inscrição
        inscricao_ref = db.collection('inscricoes').document()
        batch.set(inscricao_ref, {
            "usuario_id": str(usuario_id),
            "curso_id": str(curso_id),
            "data_inscricao": firestore.SERVER_TIMESTAMP,
            "progresso": 0,
            "status": "ativo",
            "valor_pago": float(valor_total),
            "aulas_concluidas": []
        })
        
        # B. Registrar Transação Financeira (Para seu controle de saque depois)
        transacao_ref = db.collection('financeiro').document()
        batch.set(transacao_ref, {
            "tipo": "venda_curso",
            "curso_id": str(curso_id),
            "curso_titulo": dados_curso.get('titulo'),
            "comprador_id": str(usuario_id),
            "professor_id": str(professor_id),
            "valor_total": float(valor_total),
            "receita_plataforma": v_app,      # Os 10%
            "receita_professor": v_prof,      # Os 90%
            "data_venda": firestore.SERVER_TIMESTAMP,
            "status_pagamento": "aprovado"    # Em prod, viria do Webhook
        })
        
        batch.commit()
        return True, "Pagamento aprovado e inscrição realizada!"
        
    except Exception as e:
        print(f"Erro financeiro: {e}")
        return False, f"Erro ao processar: {e}"
