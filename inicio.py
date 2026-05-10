"""pages/inicio.py"""
import streamlit as st

def render(persona: str):
    st.title("⚡ PID InvestMap")
    st.subheader("Motor de Decisão de Localização Industrial Verde")

    st.markdown(f"**Persona ativa:** {persona}")
    st.markdown("---")

    col1, col2 = st.columns(2)
    with col1:
        st.error("❌ **PID hoje**\n\nRepositório de dados passivos. Sem síntese, sem recomendação por perfil, sem 7 das camadas que propomos.")
    with col2:
        st.success("✅ **PID + InvestMap**\n\nMotor de decisão: selecione sua persona, o sistema rankeia as melhores regiões com justificativa baseada em dados públicos verificáveis.")

    st.info(
        "🔍 **Transparência metodológica:** o ranking é calculado automaticamente "
        "a partir dos dados oficiais de cada estado. A ferramenta não pré-determina "
        "vencedores — cada usuário ajusta os pesos e interpreta os resultados conforme "
        "suas próprias prioridades."
    )
    st.markdown("---")
    st.markdown("### 10 dimensões de dados — todas ausentes na PID atual")

    dados = [
        ("⚡","Potência instalada","Capacidade por tipo de fonte e estado","ANEEL SIGA — CSV mensal"),
        ("📊","Demanda de energia","Carga verificada por subsistema e horário","ONS API — REST JSON"),
        ("💧","Disponibilidade hídrica","Vazão outorgável por bacia/estado (m³/s)","ANA SNIRH — CSV/GeoJSON"),
        ("⛏️","Minerais gerais","Concessões minerárias ativas (área em ha)","ANM SIGMINE — Shapefile ZIP"),
        ("🔬","Minerais críticos","Nióbio, lítio, terras raras, grafita, cobalto","ANM SIGMINE — filtrado"),
        ("🚛","Logística integrada","Score: portos + ferrovias + hidrovias + aeroportos","DNIT+ANTAQ+ANTT — SHP"),
        ("📦","Exportações","Valor FOB por estado/município e produto (NCM)","ComexStat — REST POST"),
        ("💰","Incentivos fiscais","SUDENE, SUDAM, ZFM, ICMS energia por estado","Tabela estática"),
        ("📜","Políticas públicas","Leis estaduais + BNDES + leilões ANEEL","BNDES API + ANEEL CSV"),
        ("🎓","Instituições P&D","Universidades e institutos de pesquisa por estado","MEC e-MEC — CSV"),
    ]

    cols = st.columns(2)
    for i, (icon, titulo, desc, fonte) in enumerate(dados):
        with cols[i % 2]:
            st.info(f"**{icon} {titulo}**\n\n{desc}\n\n`{fonte}`")

    st.markdown("---")
    st.markdown("### Como usar")
    st.markdown("""
1. **Selecione sua persona** no menu lateral — ela define a ordem de prioridade das camadas e os pesos do scoring.
2. Vá para **🗺️ Mapa de Score** e veja o mapa colorido automaticamente pela camada mais relevante ao seu perfil.
3. Ajuste os pesos via sliders para calibrar o scoring à sua necessidade específica.
4. Use **📊 Relatório por Estado** para análise detalhada com todas as fontes identificadas.
    """)
