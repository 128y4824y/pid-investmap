"""PID InvestMap v3 — app.py"""
import streamlit as st

st.set_page_config(
    page_title="PID InvestMap",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded",
)

from scoring import PERSONAS, CAMADAS_PRIORIDADE

# ── Sidebar ─────────────────────────────────────────────────
with st.sidebar:
    st.title("⚡ PID InvestMap")
    st.caption("Motor de Decisão Industrial Verde — E+ 2026")
    st.markdown("---")

    # Seleção de persona — define camadas prioritárias na visualização
    persona = st.selectbox(
        "👤 Selecione sua persona",
        options=list(PERSONAS.keys()),
        help="A persona define quais dados aparecem primeiro e os pesos do scoring.",
    )

    # Descrição resumida por persona
    descricoes = {
        "🏭 Indústria / Investidor":
            "Prioriza energia, água, logística e minerais. Ideal para decidir onde instalar uma planta industrial.",
        "🏛️ Gestor Público":
            "Prioriza incentivos fiscais, políticas e exportações. Ideal para atrair investimentos ao território.",
        "🔬 Think Tank / Academia":
            "Prioriza políticas públicas e P&D. Ideal para análises de gaps na transição energética.",
        "🌿 ONG / Sociedade Civil":
            "Prioriza políticas, água e distribuição de incentivos. Ideal para monitorar equidade na transição.",
    }
    st.info(descricoes.get(persona, ""))

    st.markdown("---")

    pagina = st.radio(
        "Navegação",
        ["🏠 Início", "🔍 Diagnóstico da PID", "🗺️ Mapa de Score", "📊 Relatório por Estado"],
    )

    st.markdown("---")
    st.markdown("**Camadas ativas** (prioridade ↓)")
    camadas = CAMADAS_PRIORIDADE[persona]
    for c in camadas[:5]:
        st.markdown(f"`{c['prioridade']}` {c['label']}")
    st.caption(f"+ {len(camadas)-5} camadas adicionais")

# ── Roteamento ───────────────────────────────────────────────
if pagina == "🏠 Início":
    from pages.inicio import render; render(persona)
elif pagina == "🔍 Diagnóstico da PID":
    from pages.diagnostico import render; render()
elif pagina == "🗺️ Mapa de Score":
    from pages.mapa_score import render; render(persona)
elif pagina == "📊 Relatório por Estado":
    from pages.relatorio import render; render(persona)
