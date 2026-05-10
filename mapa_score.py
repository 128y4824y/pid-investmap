"""pages/mapa_score.py — Mapa interativo com camadas priorizadas por persona."""
import streamlit as st
import pandas as pd
import numpy as np

def render(persona: str):
    from scoring import (PERSONAS, CAMADAS_PRIORIDADE, PERFIS_INDUSTRIA,
                         calcular_score, interpretar_score, ROTULOS)
    from data_loader import carregar_todos

    st.title("🗺️ Mapa de Score")
    st.caption(f"Persona ativa: **{persona}** — camadas e pesos ajustados ao seu perfil.")
    st.caption(
        "ℹ️ O ranking é calculado exclusivamente com base nos dados oficiais de cada estado. "
        "Nenhum estado é pré-determinado como favorito. Ajuste os pesos para refletir suas prioridades."
    )

    # ── Painel lateral de controles ─────────────────────────
    col_ctrl, col_main = st.columns([1, 2.5])

    with col_ctrl:
        usar_mock = st.checkbox("Dados de demonstração", value=True,
                                help="Desmarque para buscar dados reais das APIs.")

        # Subperfil industrial (só para persona Indústria)
        subperfil = None
        if "Indústria" in persona:
            subperfil = st.selectbox("Tipo de indústria", list(PERFIS_INDUSTRIA.keys()))

        # Camada visual principal
        camadas = CAMADAS_PRIORIDADE[persona]
        opcoes_camada = [c["label"] for c in camadas]
        camada_sel = st.selectbox(
            "Camada visualizada no mapa",
            options=opcoes_camada,
            index=0,
            help="A persona pré-ordena as camadas mais relevantes para você. "
                 "A camada #1 aparece por padrão.",
        )
        var_mapa = next(c["var"] for c in camadas if c["label"] == camada_sel)

        st.markdown("---")
        st.markdown("**Ajuste de pesos** *(opcional)*")
        pesos = PERSONAS[persona].copy()
        if subperfil:
            pesos = PERFIS_INDUSTRIA[subperfil].copy()

        pesos_ajustados = {}
        for c in camadas:
            var = c["var"]
            pesos_ajustados[var] = st.slider(
                ROTULOS[var], 0.0, 1.0, float(pesos.get(var, 0)),
                0.05, key=f"w_{var}"
            )

    # ── Carrega dados e calcula score ────────────────────────
    with st.spinner("Carregando dados..."):
        df_raw    = carregar_todos(usar_mock=usar_mock)
        df_scored = calcular_score(df_raw, pesos_ajustados)

    # ── Mapa choropleth ─────────────────────────────────────
    with col_main:
        # Coluna a colorir no mapa
        col_norm = f"{var_mapa}_norm"
        if col_norm not in df_scored.columns:
            st.warning(f"Coluna {col_norm} não disponível. Usando score_total.")
            col_norm = "score_total"
            df_scored["_map_val"] = df_scored["score_total"]
        else:
            df_scored["_map_val"] = df_scored[col_norm] * 100

        try:
            import folium
            import requests as req_mod
            from streamlit.components.v1 import html as st_html

            GEOJSON_URL = (
                "https://raw.githubusercontent.com/codeforamerica/"
                "click_that_hood/master/public/data/brazil-states.geojson"
            )
            try:
                geo = req_mod.get(GEOJSON_URL, timeout=10).json()
            except Exception:
                geo = None

            if geo:
                m = folium.Map(location=[-14, -52], zoom_start=4, tiles="CartoDB positron")
                folium.Choropleth(
                    geo_data=geo,
                    data=df_scored,
                    columns=["estado_sigla", "_map_val"],
                    key_on="feature.properties.sigla",
                    fill_color="YlOrRd",
                    fill_opacity=0.8,
                    line_opacity=0.3,
                    legend_name=camada_sel,
                    nan_fill_color="lightgray",
                ).add_to(m)
                folium.GeoJson(
                    geo,
                    tooltip=folium.GeoJsonTooltip(
                        fields=["sigla","nome"], aliases=["UF:","Estado:"]),
                ).add_to(m)
                st_html(m._repr_html_(), height=460)
            else:
                st.info("GeoJSON dos estados não carregado. Veja o ranking abaixo.")

        except ImportError:
            st.info("Folium não instalado. Execute: pip install folium")

    # ── Ranking ─────────────────────────────────────────────
    st.markdown("---")
    st.markdown(f"### 🏆 Top 10 — {camada_sel}")

    cols_norm = [c["var"]+"_norm" for c in camadas if c["var"]+"_norm" in df_scored.columns]
    df_show = df_scored[["ranking","estado_nome","score_total"] + cols_norm].head(10).copy()
    df_show.columns = (["Pos.","Estado","Score (0–100)"] +
                       [ROTULOS.get(c.replace("_norm",""), c) for c in cols_norm])

    st.dataframe(
        df_show.style.background_gradient(subset=["Score (0–100)"], cmap="YlOrRd"),
        use_container_width=True,
    )

    # ── Detalhe do estado ────────────────────────────────────
    st.markdown("---")
    st.markdown("### 🔍 Detalhamento por estado")
    estado_sel = st.selectbox("Selecione um estado", df_scored["estado_nome"].tolist())
    row = df_scored[df_scored["estado_nome"] == estado_sel].iloc[0]
    st.markdown(interpretar_score(row, pesos_ajustados, persona))

    # Gráfico de barras das variáveis normalizadas
    vars_plot = {
        ROTULOS.get(c["var"], c["var"]): float(row.get(c["var"]+"_norm", 0))
        for c in camadas if c["var"]+"_norm" in row.index
    }
    if vars_plot:
        st.bar_chart(pd.Series(vars_plot).rename("Score normalizado (0–1)"))

    # Destaque de camadas extras (infraestrutura detalhada para Indústria)
    if "Indústria" in persona:
        st.markdown("---")
        st.markdown("### 🏭 Infraestrutura industrial local")
        c1, c2, c3 = st.columns(3)
        with c1:
            st.metric("⚡ Potência instalada",
                      f"{row.get('energia_potencia', 0):,.0f} MW")
            st.metric("📊 Demanda regional",
                      f"{row.get('energia_demanda', 0):,.0f} MW")
        with c2:
            st.metric("💧 Disponib. hídrica",
                      f"{row.get('agua_disponivel', 0):,.0f} m³/s")
            st.metric("🚛 Score logístico",
                      f"{row.get('logistica_score', 0):.2f}/1.00")
        with c3:
            st.metric("⛏️ Minerais gerais",
                      f"{row.get('minerais_gerais', 0)/1000:,.0f} mil ha")
            st.metric("🔬 Minerais críticos",
                      f"{row.get('minerais_criticos', 0)/1000:,.0f} mil ha")
