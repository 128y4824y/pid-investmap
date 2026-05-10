"""pages/diagnostico.py — Início-meio-fim da proposta."""
import streamlit as st

def render():
    st.title("🔍 Diagnóstico da PID")
    st.subheader("Início → Meio → Fim: o que está ruim, o que propomos e o que melhora")

    tab1, tab2, tab3 = st.tabs(["🔴 Início — O problema", "🟡 Meio — A solução", "🟢 Fim — O impacto"])

    with tab1:
        st.markdown("### Gaps confirmados na PID (cruzados com a lista oficial de fontes)")
        gaps = [
            ("Sem dados de demanda de energia",
             "A PID tem capacidade instalada (ANEEL SIGA), mas não mostra carga demandada (ONS) "
             "nem saldo disponível por região. Um investidor não sabe se há energia suficiente."),
            ("Sem nível de reservatórios",
             "Usinas hidráulicas existem no mapa, mas sem o volume útil atual dos reservatórios "
             "(ONS dados hidráulicos). Crítico para indústrias que dependem de energia firme."),
            ("Sem dados de água (disponibilidade hídrica)",
             "Não há informação de vazão outorgável (ANA SNIRH) por bacia ou estado. "
             "Essencial para indústrias intensivas em água (siderurgia, papel, alimentos)."),
            ("Sem minerais críticos e gerais",
             "ANM SIGMINE não está integrado. Nióbio, lítio, terras raras, grafita — "
             "minerais essenciais para baterias e energia limpa — são invisíveis na PID."),
            ("Sem infraestrutura de transportes",
             "Rodovias (DNIT), ferrovias (ANTT), hidrovias (ANTAQ), portos e aeroportos "
             "não aparecem como camada decisória. Logística é fator crítico de localização."),
            ("Sem exportações por município",
             "ComexStat não está integrado. Sem dados de vocação exportadora local "
             "é impossível saber se uma região já tem cadeia produtiva estabelecida."),
            ("Sem incentivos fiscais",
             "SUDENE, SUDAM e ZFM — os maiores incentivos fiscais do país — "
             "não aparecem na PID. Um dos fatores mais determinantes para decisão industrial."),
            ("Sem políticas públicas implementadas",
             "BNDES, leilões ANEEL, leis estaduais de H₂ verde — não há mapeamento "
             "do que já foi feito em cada estado. Think tanks e ONGs ficam sem referência."),
            ("Sem instituições de ensino e pesquisa",
             "Universidades, institutos federais e centros de P&D não estão no mapa. "
             "Essencial para investidores que precisam de mão de obra qualificada local."),
            ("Interface genérica sem perfil de usuário",
             "Todos os perfis (investidor, gestor, acadêmico, ONG) veem as mesmas camadas. "
             "Nenhuma síntese, nenhuma recomendação, nenhum ranking."),
        ]
        for titulo, desc in gaps:
            with st.expander(f"❌ {titulo}"):
                st.markdown(desc)

    with tab2:
        st.markdown("### 10 dimensões novas + motor de scoring por persona")
        solucoes = [
            ("V01 ⚡ Potência instalada","ANEEL SIGA CSV mensal — capacidade por tipo e estado."),
            ("V02 📊 Demanda de energia","ONS API REST — carga verificada semi-horária por subsistema."),
            ("V03 💧 Disponibilidade hídrica","ANA SNIRH — vazão outorgável m³/s por bacia/estado."),
            ("V04 ⛏️ Minerais gerais","ANM SIGMINE Shapefile — todas as concessões minerárias ativas."),
            ("V05 🔬 Minerais críticos","ANM SIGMINE filtrado — nióbio, lítio, terras raras, grafita, cobalto."),
            ("V06 🚛 Logística integrada","DNIT + ANTAQ + ANTT + ANAC — score composto de acesso por estado."),
            ("V07 📦 Exportações","ComexStat API POST — valor FOB por estado, município e NCM."),
            ("V08 💰 Incentivos fiscais","Tabela estática SUDENE/SUDAM/ZFM/ICMS por estado."),
            ("V09 📜 Políticas públicas","BNDES dados abertos + ANEEL leilões + legislação estadual."),
            ("V10 🎓 Instituições P&D","MEC e-MEC CSV + CNPq grupos de pesquisa por estado."),
        ]
        for titulo, desc in solucoes:
            with st.expander(titulo):
                st.markdown(desc)

        st.markdown("---")
        st.markdown("### Motor de scoring por persona")
        st.markdown("""
Além das camadas, o diferencial central é o **motor de decisão**:
o usuário seleciona sua persona e recebe automaticamente um **ranking dos estados**
com score ponderado pelas variáveis mais relevantes ao seu perfil,
justificativa em linguagem natural e comparação com a média nacional.
        """)

    with tab3:
        st.markdown("### O que melhora para cada stakeholder")
        col1, col2 = st.columns(2)
        with col1:
            st.success("**🏭 Investidor industrial**\nDecisão de localização em minutos. "
                       "Sabe exatamente onde há energia, água, logística e minerais — e qual o custo fiscal.")
            st.success("**🏛️ Gestor público**\nSabe quais indústrias têm fit com seu território "
                       "e quais políticas já existem para atrair investimento.")
        with col2:
            st.success("**🔬 Think tank / Academia**\nDados de 10 dimensões cruzados e normalizados, "
                       "prontos para análise. Sem semanas de coleta manual.")
            st.success("**🌿 ONG / Sociedade civil**\nMapa de vulnerabilidades da transição energética: "
                       "onde há maior emissão, menor cobertura de políticas e menor equidade.")
