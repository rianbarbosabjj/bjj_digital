import streamlit as st
from fpdf import FPDF
from PIL import Image
import sqlite3
import json
import random
import os
import qrcode
import unicodedata
import pandas as pd
import plotly.express as px
from datetime import datetime

# =========================================
# CONFIGURAÇÕES GERAIS
# =========================================
st.set_page_config(page_title="BJJ Digital", page_icon="🥋", layout="wide")

COR_FUNDO = "#0e2d26"
COR_TEXTO = "#FFFFFF"
COR_DESTAQUE = "#FFD700"
COR_BOTAO = "#078B6C"
COR_HOVER = "#FFD700"

st.markdown(f"""
    <style>
    body {{
        background-color: {COR_FUNDO};
        color: {COR_TEXTO};
        font-family: 'Poppins', sans-serif;
    }}
    .stButton>button {{
        background: linear-gradient(90deg, {COR_BOTAO}, #056853);
        color: white;
        font-weight: bold;
        border: none;
        padding: 0.6em 1.2em;
        border-radius: 10px;
        transition: 0.3s;
    }}
    .stButton>button:hover {{
        background: {COR_HOVER};
        color: {COR_FUNDO};
    }}
    h1, h2, h3 {{
        color: {COR_DESTAQUE};
        text-align: center;
        font-weight: 700;
    }}
    </style>
""", unsafe_allow_html=True)

# =========================================
# BANCO DE DADOS
# =========================================
DB_PATH = os.path.join("database", "bjj_digital.db")

def criar_banco():
    os.makedirs("database", exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute('''CREATE TABLE IF NOT EXISTS resultados (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        usuario TEXT,
        modo TEXT,
        tema TEXT,
        faixa TEXT,
        pontuacao INTEGER,
        tempo TEXT,
        data DATETIME DEFAULT CURRENT_TIMESTAMP,
        codigo_verificacao TEXT
    )''')

    cursor.execute('''CREATE TABLE IF NOT EXISTS config_exame (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        faixa TEXT,
        questoes_json TEXT,
        professor TEXT,
        data_config DATETIME DEFAULT CURRENT_TIMESTAMP
    )''')

    conn.commit()
    conn.close()

try:
    criar_banco()
except Exception as e:
    st.error(f"Erro ao criar o banco de dados: {e}")

# =========================================
# FUNÇÕES AUXILIARES
# =========================================
def carregar_questoes(tema):
    path = f"questions/{tema}.json"
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    return []

def gerar_codigo_unico():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM resultados")
    total = cursor.fetchone()[0] + 1
    conn.close()
    ano = datetime.now().year
    return f"BJJDIGITAL-{ano}-{total:05d}"

def salvar_resultado(usuario, modo, tema, faixa, pontuacao, tempo, codigo):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO resultados (usuario, modo, tema, faixa, pontuacao, tempo, codigo_verificacao)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (usuario, modo, tema, faixa, pontuacao, tempo, codigo))
    conn.commit()
    conn.close()

def exportar_certificados_json():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        SELECT usuario, faixa, pontuacao, modo, tema, data, codigo_verificacao
        FROM resultados
    """)
    registros = cursor.fetchall()
    conn.close()

    certificados = [
        {
            "codigo": codigo,
            "usuario": usuario,
            "faixa": faixa,
            "pontuacao": pontuacao,
            "modo": modo,
            "tema": tema,
            "data": data
        }
        for usuario, faixa, pontuacao, modo, tema, data, codigo in registros
    ]
    os.makedirs("certificados", exist_ok=True)
    with open("certificados/certificados.json", "w", encoding="utf-8") as f:
        json.dump(certificados, f, ensure_ascii=False, indent=2)

def gerar_qrcode(codigo):
    os.makedirs("certificados/qrcodes", exist_ok=True)
    caminho_qr = os.path.abspath(f"certificados/qrcodes/{codigo}.png")
    url_verificacao = f"https://bjjdigital.netlify.app/verificar?codigo={codigo}"
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_H,
        box_size=8,
        border=2,
    )
    qr.add_data(url_verificacao)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white").convert("RGB")
    img.save(caminho_qr)
    return caminho_qr

def normalizar_nome(nome):
    nfkd = unicodedata.normalize("NFKD", nome)
    return "".join([c for c in nfkd if not unicodedata.combining(c)]).lower().replace(" ", "_")

# =========================================
# GERAÇÃO DE PDF (FINAL COM QUEBRA DE LINHA)
# =========================================
def gerar_pdf(usuario, faixa, pontuacao, total, codigo, professor=None):
    """
    Gera o certificado com um design moderno e elementos antifalsificação.
    """
    pdf = FPDF("L", "mm", "A4") 
    pdf.set_auto_page_break(False)
    pdf.add_page()
    pdf.set_font("Helvetica") 

    # ========================
    # CORES E CONFIGURAÇÕES
    # ========================
    dourado_claro = (255, 215, 0) # Dourado mais vivo
    dourado_escuro = (184, 134, 11) # Dourado mais escuro
    preto_texto = (30, 30, 30) # Um preto mais suave
    cinza_claro = (230, 230, 230)
    cinza_fundo = (245, 245, 245) # Quase branco

    percentual = int((pontuacao / total) * 100)
    data_hora = datetime.now().strftime("%d/%m/%Y %H:%M")

    # ==============================================
    # FUNDO MODERNO E ELEMENTOS GRÁFICOS (Antifalsificação)
    # ==============================================
    # Fundo principal
    pdf.set_fill_color(*cinza_fundo)
    pdf.rect(0, 0, 297, 210, "F")

    # Borda externa com gradiente simulado
    pdf.set_draw_color(*dourado_escuro)
    pdf.set_line_width(1.5)
    pdf.rect(5, 5, 287, 200, "D") # Borda externa mais fina

    pdf.set_draw_color(*dourado_claro)
    pdf.set_line_width(0.7)
    pdf.rect(8, 8, 281, 194, "D") # Borda interna mais fina

    # Padrão Guilloché simulado (linhas repetitivas em segundo plano)
    pdf.set_draw_color(220, 220, 220) # Cor cinza bem claro para o padrão
    pdf.set_line_width(0.1)
    for i in range(0, 210, 10):
        pdf.line(0, i, 297, i + 50)
        pdf.line(i, 0, i + 50, 210)

    # Marca d'água de texto semi-transparente
    pdf.set_font("Arial", "B", 80)
    pdf.set_text_color(200, 200, 200) # Cinza claro
    pdf.rotate(45, 297/2, 210/2) # Gira o texto 45 graus
    pdf.text(120, 80, "BJJ DIGITAL")
    pdf.rotate(0, 297/2, 210/2) # Reseta a rotação
    pdf.set_text_color(*preto_texto) # Volta para a cor de texto padrão

    # Elementos geométricos de canto (superior direito e inferior esquerdo)
    pdf.set_fill_color(*dourado_claro)
    pdf.ellipse(250, 0, 50, 30, 'F') # Canto superior direito
    pdf.set_fill_color(*dourado_escuro)
    pdf.ellipse(0, 180, 50, 30, 'F') # Canto inferior esquerdo


    # ========================
    # TÍTULO PRINCIPAL
    # ========================
    pdf.set_font("Helvetica", "B", 26) # Título maior
    pdf.set_text_color(*dourado_escuro) # Dourado mais escuro para destaque
    pdf.set_y(25) 
    pdf.cell(0, 10, "CERTIFICADO DE EXAME TEÓRICO DE FAIXA", align="C")

    # ========================
    # LOGO BJJ DIGITAL (TOP)
    # ========================
    logo_top_path = "assets/logo_bjjdigital_top.png" 
    if os.path.exists(logo_top_path):
        pdf.image(logo_top_path, x=(297-35)/2, y=45, w=35) # Logo um pouco maior

    # ========================
    # TEXTO: "Certificamos que o(a) aluno(a)"
    # ========================
    pdf.set_font("Helvetica", "", 16) # Texto um pouco maior
    pdf.set_text_color(*preto_texto)
    pdf.set_y(80) 
    pdf.cell(0, 8, "Certificamos que o(a) aluno(a)", align="C")

    # ========================
    # NOME DO ALUNO
    # ========================
    pdf.set_font("Helvetica", "B", 32) # Nome maior e mais impactante
    pdf.set_text_color(*dourado_claro) 
    pdf.set_y(95) 
    pdf.cell(0, 12, usuario.upper(), align="C")

    # ========================
    # TEXTO: "concluiu o exame teórico..."
    # ========================
    cores_faixa = {
        "Cinza": (169, 169, 169), "Amarela": (255, 215, 0), "Laranja": (255, 140, 0),
        "Verde": (0, 128, 0), "Azul": (30, 144, 255), "Roxa": (128, 0, 128),
        "Marrom": (139, 69, 19), "Preta": (0, 0, 0)
    }
    cor_faixa = cores_faixa.get(faixa, (0, 0, 0))

    # --- LINHA 1 (Texto + Faixa + Texto) ---
    texto_inicial = "concluiu o exame teórico para a faixa "
    texto_faixa = faixa.upper()
    texto_final = f" obtendo {percentual}% de aproveitamento,"

    pdf.set_font("Helvetica", "", 15)
    largura_inicial = pdf.get_string_width(texto_inicial)
    pdf.set_font("Helvetica", "B", 15)
    largura_faixa = pdf.get_string_width(texto_faixa)
    pdf.set_font("Helvetica", "", 15)
    largura_final = pdf.get_string_width(texto_final)
    
    largura_total_linha1 = largura_inicial + largura_faixa + largura_final
    x_inicial_linha1 = (297 - largura_total_linha1) / 2
    
    pdf.set_y(120) # Ajuste de posição Y
    pdf.set_x(x_inicial_linha1)
    
    pdf.set_font("Helvetica", "", 15)
    pdf.set_text_color(*preto_texto)
    pdf.cell(largura_inicial, 8, texto_inicial)
    
    pdf.set_font("Helvetica", "B", 15)
    pdf.set_text_color(*cor_faixa)
    pdf.cell(largura_faixa, 8, texto_faixa)
    
    pdf.set_font("Helvetica", "", 15)
    pdf.set_text_color(*preto_texto)
    pdf.cell(largura_final, 8, texto_final)

    # --- LINHA 2 (Data) ---
    pdf.set_font("Helvetica", "", 15)
    pdf.set_text_color(*preto_texto)
    pdf.set_y(127) # Ajuste de posição Y
    pdf.cell(0, 8, f"realizado em {data_hora}.", align="C")

    # ========================
    # RESULTADO
    # ========================
    resultado = "APROVADO" if pontuacao >= (total * 0.6) else "REPROVADO"
    pdf.set_font("Helvetica", "B", 24) # Resultado maior
    pdf.set_text_color(*dourado_escuro)
    pdf.set_y(140) 
    pdf.cell(0, 10, resultado, align="C")

    
    # ===========================================
    # SEÇÃO INFERIOR (Layout de 3 colunas + Selo Dourado)
    # ===========================================
    y_base_inferior = 165 # Linha de alinhamento principal, um pouco mais abaixo
    
    # --- Coluna Esquerda: SELO OFICIAL (dourado e circular) ---
    seal_path = "assets/logo_seal.png" 
    if os.path.exists(seal_path):
        # Selo à esquerda, um pouco maior e alinhado
        pdf.image(seal_path, x=20, y=y_base_inferior - 10, w=35, h=35)
    
    # Microtexto de segurança (abaixo do selo ou em alguma área discreta)
    pdf.set_font("Arial", "", 3) # MUITO PEQUENO
    pdf.set_text_color(150, 150, 150) # Cinza para ser discreto
    pdf.text(20, y_base_inferior + 30, "Este certificado é emitido digitalmente. Verifique a autenticidade via QR Code.")


    # --- Coluna Central: ASSINATURA ---
    if professor:
        nome_normalizado = normalizar_nome(professor) # Reutilizando sua função
        assinatura_path = f"assets/assinaturas/{nome_normalizado}.png"
        
        if os.path.exists(assinatura_path):
            pdf.image(assinatura_path, x=(297-70)/2, y=y_base_inferior - 18, w=70) # Assinatura um pouco maior

    pdf.set_draw_color(*dourado_claro) # Linha da assinatura mais clara
    pdf.set_line_width(0.5)
    x_linha_assinatura = (297 - 80) / 2 # Linha de 80mm
    pdf.line(x_linha_assinatura, y_base_inferior, x_linha_assinatura + 80, y_base_inferior)

    pdf.set_font("Helvetica", "B", 13) # Nome do professor em negrito
    pdf.set_text_color(*preto_texto)
    pdf.set_y(y_base_inferior + 2) 
    pdf.cell(0, 8, professor.upper() if professor else "NOME DO PROFESSOR", align="C") # Exibe o nome do professor ou placeholder
    
    pdf.set_font("Helvetica", "", 10)
    pdf.set_text_color(*dourado_escuro)
    pdf.set_y(y_base_inferior + 8) 
    pdf.cell(0, 6, "Assinatura do Professor Responsável", align="C")

    # --- Coluna Direita: QR CODE E CÓDIGO ---
    # Gerar QR Code (mantém a sua função, apenas ajuste a posição)
    caminho_qr = gerar_qrcode(codigo) # Usando a sua função auxiliar para gerar e salvar

    qr_w = 35 # QR Code um pouco maior
    x_qr = 297 - 25 - qr_w 
    y_qr = y_base_inferior - 10 # Alinhado com o selo
    
    pdf.image(caminho_qr, x=x_qr, y=y_qr, w=qr_w)

    pdf.set_font("Helvetica", "I", 10) # Código um pouco maior
    pdf.set_text_color(*preto_texto)
    pdf.set_xy(x_qr, y_qr + qr_w + 1)
    pdf.cell(qr_w, 5, f"Código: {codigo}", align="C")

    # ========================
    # RODAPÉ FINAL (Mantido como estava, mas com cor ajustada)
    # ========================
    pdf.set_font("Helvetica", "I", 9)
    pdf.set_text_color(*dourado_escuro)
    pdf.set_y(195) 
    pdf.cell(0, 6, "Plataforma Oficial BJJ Digital - Projeto Resgate GFTeam IAPC de Irajá", align="C")


    # ========================
    # SALVAR PDF FINAL
    # ========================
    os.makedirs("relatorios", exist_ok=True)
    caminho_pdf = os.path.abspath(f"relatorios/Certificado_{usuario}_{faixa}.pdf")
    pdf.output(caminho_pdf)
    return caminho_pdf
    
# =========================================
# MODO EXAME DE FAIXA (DOWNLOAD PERSISTENTE)
# =========================================
def modo_exame():
    st.markdown("<h1 style='color:#FFD700;'>🏁 Exame de Faixa</h1>", unsafe_allow_html=True)
    faixas = ["Cinza", "Amarela", "Laranja", "Verde", "Azul", "Roxa", "Marrom", "Preta"]
    faixa = st.selectbox("Selecione a faixa:", faixas)
    usuario = st.text_input("Nome do aluno:")
    professor = st.text_input("Nome do professor responsável:")
    tema = "regras"

    if "exame_iniciado" not in st.session_state:
        st.session_state.exame_iniciado = False
        st.session_state.respostas = {}
        st.session_state.certificado_path = None

    if not st.session_state.exame_iniciado:
        if st.button("Iniciar Exame"):
            questoes = carregar_questoes(tema)
            if not questoes:
                st.error("Nenhuma questão encontrada para o tema selecionado.")
                return
            random.shuffle(questoes)
            st.session_state.questoes = questoes[:5]
            st.session_state.exame_iniciado = True
            st.rerun()

    if st.session_state.exame_iniciado:
        questoes = st.session_state.questoes
        total = len(questoes)
        for i, q in enumerate(questoes, 1):
            st.markdown(f"### {i}. {q['pergunta']}")
            resp = st.radio("Escolha:", q["opcoes"], key=f"resp_{i}", index=None)
            st.session_state.respostas[f"resp_{i}"] = resp

        if st.button("Finalizar Exame"):
            pontuacao = sum(
                1 for i, q in enumerate(questoes, 1)
                if st.session_state.respostas.get(f"resp_{i}", "").startswith(q["resposta"])
            )
            codigo = gerar_codigo_unico()
            salvar_resultado(usuario, "Exame", tema, faixa, pontuacao, "00:05:00", codigo)
            exportar_certificados_json()
            caminho_pdf = gerar_pdf(usuario, faixa, pontuacao, total, codigo, professor)
            st.session_state.certificado_path = caminho_pdf
            st.rerun()

    if st.session_state.get("certificado_path"):
        caminho_pdf = st.session_state.certificado_path
        st.success(f"🎉 Certificado de {usuario.upper() if usuario else 'ALUNO'} ({faixa}) gerado com sucesso!")
        try:
            with open(caminho_pdf, "rb") as f:
                pdf_bytes = f.read()
            st.download_button(
                label="📄 Baixar Certificado",
                data=pdf_bytes,
                file_name=os.path.basename(caminho_pdf),
                mime="application/pdf",
                use_container_width=True
            )
        except Exception as e:
            st.error(f"⚠️ Erro ao preparar o download: {e}")

# =========================================
# HISTÓRICO DE CERTIFICADOS
# =========================================
def painel_certificados():
    st.markdown("<h1 style='color:#FFD700;'>📜 Histórico de Certificados</h1>", unsafe_allow_html=True)
    nome = st.text_input("Digite seu nome completo:")
    if st.button("🔍 Buscar"):
        conn = sqlite3.connect(DB_PATH)
        df = pd.read_sql_query("SELECT * FROM resultados ORDER BY data DESC", conn)
        conn.close()
        df = df[df["usuario"].str.contains(nome, case=False, na=False)]
        if df.empty:
            st.info("Nenhum certificado encontrado.")
        else:
            st.success(f"Foram encontrados {len(df)} registro(s).")
            st.dataframe(df[["usuario","faixa","pontuacao","data","codigo_verificacao"]])

# =========================================
# DASHBOARD DO PROFESSOR
# =========================================
def dashboard_professor():
    st.markdown("<h1 style='color:#FFD700;'>📈 Dashboard do Professor</h1>", unsafe_allow_html=True)
    abas = st.tabs(["📊 Indicadores", "📋 Histórico"])

    with abas[0]:
        conn = sqlite3.connect(DB_PATH)
        df = pd.read_sql_query("SELECT * FROM resultados", conn)
        conn.close()

        if df.empty:
            st.info("Nenhum exame registrado ainda.")
            return

        total, media = len(df), df["pontuacao"].mean()
        taxa = (df[df["pontuacao"] >= 3].shape[0] / total) * 100
        aprovados = df[df["pontuacao"] >= 3].shape[0]
        reprovados = total - aprovados

        col1, col2, col3 = st.columns(3)
        col1.metric("Total de Exames", total)
        col2.metric("Média de Pontuação", f"{media:.2f}")
        col3.metric("Taxa de Aprovação", f"{taxa:.1f}%")

        col1, col2 = st.columns(2)
        with col1:
            fig1 = px.bar(df, x="faixa", color="faixa",
                          title="Distribuição de Exames por Faixa",
                          color_discrete_sequence=px.colors.sequential.YlGn)
            st.plotly_chart(fig1, use_container_width=True)
        with col2:
            fig2 = px.pie(names=["Aprovados", "Reprovados"], values=[aprovados, reprovados],
                          title="Taxa de Aprovação", color_discrete_sequence=["#FFD700", "#0e2d26"])
            st.plotly_chart(fig2, use_container_width=True)

    with abas[1]:
        st.markdown("### 📋 Histórico de Exames")
        conn = sqlite3.connect(DB_PATH)
        df = pd.read_sql_query("SELECT usuario, faixa, pontuacao, data, codigo_verificacao FROM resultados", conn)
        conn.close()
        st.dataframe(df)
        csv = df.to_csv(index=False).encode("utf-8")
        st.download_button("📤 Exportar CSV", csv, "relatorio_exames.csv", "text/csv")

# =========================================
# MENU PRINCIPAL
# =========================================
def main():
    st.sidebar.image("assets/logo.png", use_container_width=True)
    st.sidebar.markdown("<h3 style='color:#FFD700;'>Plataforma BJJ Digital</h3>", unsafe_allow_html=True)
    menu = st.sidebar.radio("Navegar:", [
        "🏁 Exame de Faixa",
        "📜 Histórico de Certificados",
        "📈 Dashboard do Professor"
    ])
    if menu == "🏁 Exame de Faixa":
        modo_exame()
    elif menu == "📜 Histórico de Certificados":
        painel_certificados()
    elif menu == "📈 Dashboard do Professor":
        dashboard_professor()

if __name__ == "__main__":
    main()
