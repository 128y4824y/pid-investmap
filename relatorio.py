"""pages/relatorio.py — Relatório completo por estado."""
import streamlit as st
import pandas as pd

def render(persona: str):
    from scoring import PERSONAS, CAMADAS_PRIORIDADE, calcular_score, interpretar_score, ROTULOS
    from data_loader import carregar_todos, _incentivos_fiscais, _politicas_publicas, _instituicoes_pesquisa

    st.title("📊 Relatório por Estado")
    st.caption("Análise completa de um estado com todas as camadas de dados.")

    col1, col2 = st.columns(2)
    with col1:
        usar_mock = st.checkbox("Dados de demonstração", value=True)
    with col2:
        pesos = PERSONAS[persona]

    df_raw    = carregar_todos(usar_mock=usar_mock)
    df_scored = calcular_score(df_raw, pesos)
    camadas   = CAMADAS_PRIORIDADE[persona]

    estado_sel = st.selectbox("Estado para análise", df_scored["estado_nome"].tolist())
    row = df_scored[df_scored["estado_nome"] == estado_sel].iloc[0]
    uf  = row["estado_sigla"]

    # ── Score e ranking ──────────────────────────────────────
    st.markdown("---")
    c1, c2, c3 = st.columns(3)
    score = row["score_total"]
    cor   = "🟢" if score >= 65 else "🟡" if score >= 40 else "🔴"
    c1.metric(f"{cor} Score", f"{score}/100")
    c2.metric("Ranking nacional", f"#{int(row['ranking'])} de 27")
    c3.metric("Persona", persona.split()[0])

    st.markdown(interpretar_score(row, pesos, persona))

    # ── Métricas por camada (ordem da persona) ───────────────
    st.markdown("### 📐 Indicadores por camada (prioridade da sua persona)")
    cols_m = st.columns(5)
    for i, c in enumerate(camadas[:10]):
        val_norm = row.get(f"{c['var']}_norm", 0)
        val_raw  = row.get(c["var"], None)
        label    = ROTULOS.get(c["var"], c["var"])
        badge    = "✅" if val_norm >= 0.65 else "⚠️" if val_norm <= 0.30 else "🔹"
        with cols_m[i % 5]:
            st.metric(f"{badge} {label.split(' ',1)[-1][:18]}",
                      f"{val_norm*100:.0f}/100")

    # ── Gráfico radar (barras) ────────────────────────────────
    st.markdown("### 📊 Perfil por variável")
    vars_plot = {ROTULOS.get(c["var"],c["var"]): float(row.get(c["var"]+"_norm",0))
                 for c in camadas if c["var"]+"_norm" in row.index}
    st.bar_chart(pd.Series(vars_plot).rename("Score 0–1"))

    # ── Comparação com média nacional ────────────────────────
    st.markdown("### 🇧🇷 Comparação com média nacional")
    cols_norm = [c["var"]+"_norm" for c in camadas if c["var"]+"_norm" in df_scored.columns]
    media     = df_scored[cols_norm].mean()
    comp = pd.DataFrame({
        "Variável":  [ROTULOS.get(c.replace("_norm",""), c) for c in cols_norm],
        estado_sel:  [round(float(row.get(c, 0)), 3) for c in cols_norm],
        "Média BR":  [round(float(media.get(c, 0)), 3) for c in cols_norm],
    })
    st.dataframe(comp, use_container_width=True, hide_index=True)

    # ── Seções específicas por persona ───────────────────────
    if "Indústria" in persona:
        st.markdown("---")
        st.markdown("### ⚡ Energia — detalhamento")
        ca, cb, cc = st.columns(3)
        ca.metric("Potência instalada", f"{row.get('energia_potencia',0):,.0f} MW")
        cb.metric("Demanda regional",   f"{row.get('energia_demanda',0):,.0f} MW")
        cc.metric("Saldo (oferta-dem)", f"{max(0, row.get('energia_potencia',0)-row.get('energia_demanda',0)):,.0f} MW")
        st.caption("Fonte: ANEEL SIGA (capacidade instalada) + ONS API (carga verificada)")

        st.markdown("### 💧 Recursos hídricos")
        st.metric("Disponibilidade hídrica", f"{row.get('agua_disponivel',0):,.0f} m³/s")
        st.caption("Fonte: ANA/SNIRH — Conjuntura dos Recursos Hídricos 2023")

        st.markdown("### ⛏️ Minerais")
        da, db = st.columns(2)
        da.metric("Área total concessões", f"{row.get('minerais_gerais',0)/1000:,.1f} mil ha")
        db.metric("Minerais críticos",     f"{row.get('minerais_criticos',0)/1000:,.1f} mil ha")
        st.caption("Fonte: ANM SIGMINE — processos minerários ativos 2024")

        st.markdown("### 🚛 Logística integrada")
        st.metric("Score logístico (0–1)", f"{row.get('logistica_score',0):.3f}")
        st.caption("Componentes: portos 30% + ferrovias 20% + hidrovias 20% + aeroportos 15% + rodovias 15%")

    if "Gestor" in persona or "Think" in persona or "ONG" in persona:
        st.markdown("---")
        st.markdown("### 💰 Incentivos fiscais")
        df_inc = _incentivos_fiscais()
        row_inc = df_inc[df_inc["estado_sigla"] == uf]
        if not row_inc.empty:
            ri = row_inc.iloc[0]
            st.info(f"**Programa:** {ri['programa']}  \n{ri['descricao_incentivo']}")

        st.markdown("### 📜 Políticas públicas de energia")
        df_pol = _politicas_publicas()
        row_pol = df_pol[df_pol["estado_sigla"] == uf]
        if not row_pol.empty:
            rp = row_pol.iloc[0]
            st.info(f"**Score:** {rp['politicas_publicas']:.2f}/1.00  \n{rp['descricao_politica']}")

    if "Think" in persona or "ONG" in persona or "Gestor" in persona:
        st.markdown("---")
        st.markdown("### 🎓 Instituições de P&D")
        n_ies = int(row.get("instituicoes_pesquisa", 0))
        st.metric("Universidades e Institutos de Pesquisa", n_ies)
        st.caption("Fonte: MEC e-MEC 2022 + CNPq grupos de pesquisa. "
                   "Para detalhar: acessar emec.mec.gov.br e filtrar por município.")

    # ── Top 5 para mesma persona ─────────────────────────────
    st.markdown("---")
    st.markdown("### 🏆 Top 5 estados para esta persona")
    top5 = df_scored.head(5)[["ranking","estado_nome","score_total"]]
    st.dataframe(top5, use_container_width=True, hide_index=True)

    # ── Exportar ─────────────────────────────────────────────
    st.markdown("---")
    csv = df_scored.to_csv(index=False).encode("utf-8")
    st.download_button(
        "⬇️ Exportar ranking completo (CSV)",
        data=csv,
        file_name=f"investmap_{persona.split()[0].strip()}_{estado_sel}.csv",
        mime="text/csv",
    )
