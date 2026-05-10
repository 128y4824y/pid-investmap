"""
data_loader.py — Coleta e consolidação de todas as fontes de dados

FONTES COBERTAS:
  V01/V02  ONS API       Carga verificada + nível de reservatórios (REST JSON)
  V01      ANEEL SIGA    Capacidade instalada por estado e tipo (CSV mensal)
  V03      ANA SNIRH     Disponibilidade hídrica por estado (CSV/GeoJSON)
  V04/V05  ANM SIGMINE   Processos minerários — geral e críticos (Shapefile ZIP)
  V06      DNIT/ANTAQ/ANTT  Rodovias + Hidrovias + Ferrovias (Shapefile — pré-calc)
  V07      ComexStat     Exportações por estado (REST POST JSON)
  V08      Estática      SUDENE/SUDAM/ZFM/ICMS por estado
  V09      BNDES + ANEEL Políticas públicas (CSV + estática)
  V10      MEC e-MEC     Instituições de ensino superior e pesquisa (CSV)

USO:
  df = carregar_todos(usar_mock=False)   # dados reais
  df = carregar_todos(usar_mock=True)    # mock para dev
"""

import requests
import pandas as pd
import streamlit as st
from pathlib import Path
from datetime import date, timedelta

# ── Constantes ──────────────────────────────────────────────
ONS_BASE   = "https://apicarga.ons.org.br/prd"
COMEX_BASE = "https://api-comexstat.mdic.gov.br"
IBGE_BASE  = "https://servicodados.ibge.gov.br/api/v3"
ANEEL_CSV  = (
    "https://dadosabertos.aneel.gov.br/dataset/"
    "siga-sistema-de-informacoes-de-geracao-da-aneel/resource/"
    "b1bd71e7-d0ad-4214-9053-cbd58e9564a7/download/siga-empreendimentos-geracao.csv"
)
MEC_IES_CSV = (
    "https://dadosabertos.mec.gov.br/images/conteudo/Ind-ensino-superior/2022/"
    "PDA_Lista_Instituicoes_Ensino_Superior_do_Brasil_EMEC.csv"
)

# Mapeamento subsistema ONS → estados
MAPA_SUB = {
    "SE": ["SP","RJ","MG","ES","GO","DF","MS","MT"],
    "S":  ["PR","SC","RS"],
    "NE": ["BA","SE","AL","PE","PB","RN","CE","PI","MA"],
    "N":  ["PA","AM","AC","AP","RR","RO","TO"],
}
AREAS_ONS = {"SE":"Sudeste/CO","S":"Sul","NE":"Nordeste","N":"Norte"}


# ════════════════════════════════════════════════════════════
# V01/V02 — ONS: Carga verificada por subsistema
# ════════════════════════════════════════════════════════════
@st.cache_data(ttl=3600, show_spinner=False)
def _carga_ons(dias: int = 30) -> pd.DataFrame:
    """GET /prd/cargaverificada — retorna carga média (MW) por subsistema."""
    fim = date.today(); ini = fim - timedelta(days=dias)
    rows = []
    for cod, nome in AREAS_ONS.items():
        url = f"{ONS_BASE}/cargaverificada?dat_inicio={ini}&dat_fim={fim}&cod_areacarga={cod}"
        try:
            r = requests.get(url, timeout=12); r.raise_for_status()
            df_r = pd.DataFrame(r.json())
            col  = next((c for c in ["val_cargaglobal","val_carga"] if c in df_r), None)
            media = df_r[col].mean() if col else None
        except Exception as e:
            media = None
            st.warning(f"ONS [{cod}] falhou: {e}")
        rows.append({"cod_sub": cod, "carga_mw": media})
    return pd.DataFrame(rows)


@st.cache_data(ttl=3600, show_spinner=False)
def _reservatorios_ons() -> dict:
    """GET /prd/reservatoriose — nível médio (%) por subsistema."""
    hoje = date.today().strftime("%Y-%m-%d")
    try:
        r = requests.get(f"{ONS_BASE}/reservatoriose?dat_referencia={hoje}", timeout=12)
        r.raise_for_status()
        df = pd.DataFrame(r.json())
        if {"nom_subsistema","val_volumeutilp"}.issubset(df.columns):
            return df.groupby("nom_subsistema")["val_volumeutilp"].mean().to_dict()
    except Exception as e:
        st.warning(f"ONS reservatórios falhou: {e}")
    return {"SE/CO":55.0,"Sul":70.0,"Nordeste":42.0,"Norte":65.0}  # fallback histórico


# ════════════════════════════════════════════════════════════
# V01 — ANEEL SIGA: Potência instalada por estado
# ════════════════════════════════════════════════════════════
@st.cache_data(ttl=86400, show_spinner=False)
def _aneel_siga() -> pd.DataFrame:
    """CSV mensal SIGA — retorna potência total (kW→MW) por estado."""
    try:
        df = pd.read_csv(ANEEL_CSV, sep=";", encoding="latin1", on_bad_lines="skip")
        if "DscFaseUsina" in df.columns:
            df = df[df["DscFaseUsina"].str.strip() == "Operação"]
        df["MdaPotenciaFiscalizadaKw"] = pd.to_numeric(
            df.get("MdaPotenciaFiscalizadaKw", 0), errors="coerce")
        return (df.groupby("SigUFPrincipal")["MdaPotenciaFiscalizadaKw"].sum()
                  .div(1000).reset_index()
                  .rename(columns={"SigUFPrincipal":"estado_sigla",
                                   "MdaPotenciaFiscalizadaKw":"energia_potencia_mw"}))
    except Exception as e:
        st.warning(f"ANEEL SIGA falhou: {e}")
        return pd.DataFrame(columns=["estado_sigla","energia_potencia_mw"])


# ════════════════════════════════════════════════════════════
# V03 — ANA SNIRH: Disponibilidade hídrica por estado
# ════════════════════════════════════════════════════════════
def _agua_disponivel() -> pd.DataFrame:
    """
    Vazão disponível (m³/s) por estado.

    Fonte primária: ANA SNIRH dados abertos
      https://dadosabertos.ana.gov.br/datasets/
      Dataset: 'Ottobacias' ou 'Disponibilidade Hídrica Superficial'
      Formato: Shapefile ou CSV (vazão Q90 por otto-bacia → agregar por UF)

    Arquivo esperado: data/agua_por_estado.csv [estado_sigla, agua_disponivel]

    Fallback: valores de referência baseados no Relatório Conjuntura ANA 2023.
    """
    csv = Path("data/agua_por_estado.csv")
    if csv.exists():
        return pd.read_csv(csv)

    st.info("ANA SNIRH: usando referência Conjuntura 2023 (baixar shapefile para dados reais)")
    dados = [
        ("AC",3500),("AL",310),("AP",2100),("AM",98000),("BA",1900),("CE",280),
        ("DF",145),("ES",790),("GO",3900),("MA",1950),("MT",8200),("MS",3400),
        ("MG",3300),("PA",58000),("PB",240),("PR",2900),("PE",390),("PI",500),
        ("RJ",680),("RN",195),("RS",2450),("RO",3900),("RR",4900),("SC",2100),
        ("SP",1480),("SE",290),("TO",4900),
    ]
    return pd.DataFrame(dados, columns=["estado_sigla","agua_disponivel"])


# ════════════════════════════════════════════════════════════
# V04/V05 — ANM SIGMINE: Minerais gerais e críticos
# ════════════════════════════════════════════════════════════
def _minerais() -> pd.DataFrame:
    """
    Área de concessões minerárias por estado (ha).
    Arquivo esperado: data/minerais_por_estado.csv
      Colunas: [estado_sigla, minerais_gerais, minerais_criticos]

    Como gerar (pré-hackathon):
      1. Baixar https://app.anm.gov.br/dadosabertos/SIGMINE/PROCESSOS_MINERARIOS/BRASIL.zip
      2. import geopandas as gpd
         gdf = gpd.read_file("BRASIL.shp")
         gdf = gdf[gdf["FASE"].isin(["AUTORIZAÇÃO DE PESQUISA","CONCESSÃO DE LAVRA","LICENCIAMENTO"])]
         gdf["area_ha"] = gdf.geometry.to_crs("EPSG:5880").area / 10000
         # Minerais críticos
         criticos = ["NIOBIO","LITIO","TERRAS RARAS","GRAFITA","MANGANES","COBALTO","TUNGSTÊNIO"]
         gdf["is_critico"] = gdf["SUBSTANCIA"].str.upper().apply(
             lambda x: any(c in x for c in criticos))
         df_geral = gdf.groupby("UF")["area_ha"].sum().reset_index()
         df_crit  = gdf[gdf["is_critico"]].groupby("UF")["area_ha"].sum().reset_index()
         df = df_geral.merge(df_crit, on="UF", suffixes=("_gerais","_criticos"))
         df.columns = ["estado_sigla","minerais_gerais","minerais_criticos"]
         df.to_csv("data/minerais_por_estado.csv", index=False)
    """
    csv = Path("data/minerais_por_estado.csv")
    if csv.exists():
        return pd.read_csv(csv)

    st.info("SIGMINE: usando referência ANM 2024 (baixar shapefile para dados precisos)")
    dados = [
        ("AC",62000,25000),("AL",7500,1000),("AP",91000,35000),("AM",205000,80000),
        ("BA",255000,60000),("CE",22000,3000),("DF",1200,500),("ES",42000,20000),
        ("GO",305000,120000),("MA",36000,5000),("MT",410000,40000),("MS",82000,8000),
        ("MG",820000,450000),("PA",615000,200000),("PB",8500,1500),("PR",46000,15000),
        ("PE",11000,3000),("PI",16000,2000),("RJ",31000,5000),("RN",13000,4000),
        ("RS",66000,10000),("RO",155000,30000),("RR",125000,90000),("SC",52000,6000),
        ("SP",72000,8000),("SE",5500,800),("TO",102000,18000),
    ]
    return pd.DataFrame(dados, columns=["estado_sigla","minerais_gerais","minerais_criticos"])


# ════════════════════════════════════════════════════════════
# V06 — Logística integrada (DNIT + ANTAQ + ANTT)
# ════════════════════════════════════════════════════════════
def _logistica() -> pd.DataFrame:
    """
    Score logístico composto (0–1) por estado.
    Arquivo esperado: data/logistica_por_estado.csv [estado_sigla, logistica_score]

    Como calcular com dados reais:
      Rodovias DNIT  → servicos.dnit.gov.br/vgeo  (Shapefile trimestral)
      Hidrovias ANTAQ→ antaq.gov.br/portal/PNIH/Hidrovias.zip (Shapefile)
      Ferrovias ANTT → dados.antt.gov.br  (Shapefile + CSV)
      Portos ANTAQ   → dadosabertos.antaq.gov.br (GeoJSON)
      Aeroportos ANAC→ dados.gov.br/dataset/aerodromos-publicos (CSV)

      Para cada estado:
        dist_porto    = distância média dos municípios ao porto marítimo mais próximo
        dist_hidrovia = distância média ao ponto navegável mais próximo
        dist_ferrovia = distância ao terminal ferroviário mais próximo
        dist_aeroporto= distância ao aeroporto com voo regular mais próximo
        dist_rod_fed  = distância à rodovia federal pavimentada mais próxima

        score = 0.30*(1/dist_porto_norm) + 0.20*(1/dist_ferro_norm)
              + 0.20*(1/dist_hidrovia_norm) + 0.15*(1/dist_aero_norm)
              + 0.15*(1/dist_rod_norm)
      Normalizar para 0–1 entre os 27 estados.
    """
    csv = Path("data/logistica_por_estado.csv")
    if csv.exists():
        return pd.read_csv(csv)

    dados = [
        ("AC",0.22),("AL",0.48),("AP",0.28),("AM",0.38),("BA",0.65),("CE",0.62),
        ("DF",0.52),("ES",0.72),("GO",0.58),("MA",0.50),("MT",0.48),("MS",0.52),
        ("MG",0.78),("PA",0.55),("PB",0.50),("PR",0.85),("PE",0.68),("PI",0.42),
        ("RJ",0.90),("RN",0.55),("RS",0.80),("RO",0.35),("RR",0.20),("SC",0.82),
        ("SP",0.95),("SE",0.50),("TO",0.42),
    ]
    return pd.DataFrame(dados, columns=["estado_sigla","logistica_score"])


# ════════════════════════════════════════════════════════════
# V07 — ComexStat: Exportações por estado
# ════════════════════════════════════════════════════════════
@st.cache_data(ttl=86400, show_spinner=False)
def _exportacoes(ano: int = 2024) -> pd.DataFrame:
    """POST api-comexstat.mdic.gov.br/states — exportações FOB por estado."""
    try:
        r = requests.post(
            f"{COMEX_BASE}/states",
            json={"flow":"export","monthDetail":False,
                  "period":{"from":f"{ano}-01","to":f"{ano}-12"}},
            headers={"Content-Type":"application/json"}, timeout=15)
        r.raise_for_status()
        lista = r.json().get("data",{}).get("list",[])
        df = pd.DataFrame(lista)
        if "metricFOB" in df.columns:
            df["metricFOB"] = pd.to_numeric(df["metricFOB"], errors="coerce")
        return df
    except Exception as e:
        st.warning(f"ComexStat falhou: {e}")
        return pd.DataFrame()


# ════════════════════════════════════════════════════════════
# V08 — Incentivos fiscais (tabela estática)
# ════════════════════════════════════════════════════════════
def _incentivos_fiscais() -> pd.DataFrame:
    """
    Score 0–1 por estado baseado em:
      SUDAM  (Amazônia Legal) = +0.55 base
      SUDENE (Nordeste+partes NE de MG e ES) = +0.55 base
      ZFM    (Amazonas) = +0.45 extra
      ICMS energia reduzido (CE, RN, PI, BA) = +0.10 extra
    Fontes: gov.br/sudene | gov.br/sudam | suframa.gov.br | fazendas estaduais 2024
    """
    dados = [
        ("AC","SUDAM",0.75,"Amazônia Legal — 75% redução IR"),
        ("AL","SUDENE",0.80,"Nordeste — 75% redução IR"),
        ("AP","SUDAM",0.75,"Amazônia Legal — 75% redução IR"),
        ("AM","ZFM+SUDAM",1.00,"Zona Franca de Manaus — máximo benefício"),
        ("BA","SUDENE",0.80,"Nordeste — 75% redução IR"),
        ("CE","SUDENE+ICMS",0.85,"Nordeste + ICMS energia reduzido"),
        ("DF","Nenhum",0.10,"Sem benefício federal"),
        ("ES","Parcial",0.35,"Norte do ES — SUDENE parcial"),
        ("GO","Nenhum",0.20,"Sem benefício federal"),
        ("MA","SUDENE",0.80,"Nordeste — 75% redução IR"),
        ("MT","SUDAM",0.70,"Amazônia Legal — 75% redução IR"),
        ("MS","Nenhum",0.20,"Sem benefício federal"),
        ("MG","Parcial",0.40,"Norte de MG — SUDENE parcial"),
        ("PA","SUDAM",0.80,"Amazônia Legal — 75% redução IR"),
        ("PB","SUDENE",0.80,"Nordeste — 75% redução IR"),
        ("PR","Nenhum",0.20,"Sem benefício federal"),
        ("PE","SUDENE",0.80,"Nordeste — 75% redução IR"),
        ("PI","SUDENE+ICMS",0.80,"Nordeste + ICMS energia reduzido"),
        ("RJ","Nenhum",0.15,"Sem benefício federal"),
        ("RN","SUDENE+ICMS",0.85,"Nordeste + ICMS energia reduzido + maior irradiação solar"),
        ("RS","Nenhum",0.20,"Sem benefício federal"),
        ("RO","SUDAM",0.75,"Amazônia Legal — 75% redução IR"),
        ("RR","SUDAM",0.75,"Amazônia Legal — 75% redução IR"),
        ("SC","Nenhum",0.20,"Sem benefício federal"),
        ("SP","Nenhum",0.15,"Sem benefício federal"),
        ("SE","SUDENE",0.80,"Nordeste — 75% redução IR"),
        ("TO","SUDAM",0.75,"Amazônia Legal — 75% redução IR"),
    ]
    return pd.DataFrame(dados, columns=["estado_sigla","programa","incentivo_fiscal","descricao_incentivo"])


# ════════════════════════════════════════════════════════════
# V09 — Políticas públicas (BNDES + legislação estadual)
# ════════════════════════════════════════════════════════════
def _politicas_publicas() -> pd.DataFrame:
    """
    Score 0–1 por estado. Componentes:
      Lei estadual de energia renovável / H₂ verde (40%)
      Volume BNDES aprovado per capita — energia limpa 2020-2024 (30%)
      Leilões ANEEL realizados no estado — MW leiloados (30%)

    Fontes:
      BNDES: dadosabertos.bndes.gov.br (CSV filtrar setor energético)
      ANEEL leilões: dadosabertos.aneel.gov.br/dataset/leiloes
      Legislação: pesquisa manual por estado (ver descrição)
    """
    csv = Path("data/politicas_por_estado.csv")
    if csv.exists():
        return pd.read_csv(csv)

    dados = [
        ("AC",0.30,"Bioeconomia inicial | BNDES baixo | sem lei específica"),
        ("AL",0.40,"Biocomb. cana | BNDES baixo | leilões eólicos menores"),
        ("AP",0.28,"Solar emergente | BNDES muito baixo"),
        ("AM",0.45,"Bioeconomia amazônica | ZFM verde | BNDES médio"),
        ("BA",0.70,"BNDES Polo Camaçari | leilões solares | programas estaduais"),
        ("CE",0.85,"Lei H₂ Verde 2022 | líder leilões eólicos ANEEL | BNDES alto"),
        ("DF",0.45,"Programa solar GDF | BNDES médio | hub regulatório"),
        ("ES",0.55,"Programa Gerar 2021 | offshore eólico planejado | BNDES médio"),
        ("GO",0.50,"Solar + biocombustível | BNDES médio | leilões menores"),
        ("MA",0.45,"Potencial eólico | BNDES baixo | leilões recentes"),
        ("MT",0.40,"Biocombustível | solar rural | BNDES médio"),
        ("MS",0.38,"Biocombustível | BNDES baixo"),
        ("MG",0.60,"BNDES hidrelétricas + biogás + mineração verde | leilões"),
        ("PA",0.48,"COP30 impulsionou | hidrelétricas | BNDES médio"),
        ("PB",0.50,"Leilões eólicos | solar | BNDES médio"),
        ("PR",0.58,"Programa H₂ Copel | bioenergia | BNDES alto"),
        ("PE",0.60,"Porto Suape hub H₂ | ZPE H₂ verde | BNDES alto | leilões"),
        ("PI",0.75,"Lei H₂ Verde 2022 | expansão solar acelerada | BNDES médio"),
        ("RJ",0.50,"Petrobras descarbonização | offshore | BNDES médio"),
        ("RN",0.82,"Lei H₂ Verde 2023 | maior geração eólica per capita | BNDES alto"),
        ("RS",0.55,"Bioenergia | eólico offshore planejado | BNDES alto"),
        ("RO",0.35,"Hidrelétricas | bioenergia | BNDES baixo"),
        ("RR",0.25,"Solar início | BNDES muito baixo"),
        ("SC",0.52,"Solar distribuído | biogás suíno | BNDES médio"),
        ("SP",0.65,"Maior volume BNDES absoluto | programa solar empresarial"),
        ("SE",0.42,"Gás natural | início solar | BNDES baixo"),
        ("TO",0.55,"Palmas Solar 2015 (pioneiro) | hidrelétricas | BNDES médio"),
    ]
    return pd.DataFrame(dados, columns=["estado_sigla","politicas_publicas","descricao_politica"])


# ════════════════════════════════════════════════════════════
# V10 — Instituições de ensino e pesquisa (MEC e-MEC + CNPq)
# ════════════════════════════════════════════════════════════
@st.cache_data(ttl=86400*7, show_spinner=False)
def _instituicoes_pesquisa() -> pd.DataFrame:
    """
    Nº de instituições de ensino superior e pesquisa por estado.

    Fonte primária (CSV público MEC):
      https://dadosabertos.mec.gov.br/images/conteudo/Ind-ensino-superior/2022/
      PDA_Lista_Instituicoes_Ensino_Superior_do_Brasil_EMEC.csv

    Filtrar: organização acadêmica = Universidade | Instituto Federal | Centro Pesquisa
    Contar por UF. Para dados de pesquisa, cruzar com:
      CNPq grupos de pesquisa: dgp.cnpq.br/dgp/faces/consulta/consulta_parametrizada.jsf
    """
    csv = Path("data/instituicoes_por_estado.csv")
    if csv.exists():
        return pd.read_csv(csv)

    # Tenta baixar CSV do MEC (pode demorar)
    try:
        df = pd.read_csv(MEC_IES_CSV, sep=";", encoding="latin1", on_bad_lines="skip")
        col_uf  = next((c for c in df.columns if "UF" in c.upper()), None)
        col_org = next((c for c in df.columns if "ORGAN" in c.upper()), None)
        if col_uf:
            filtro = df[col_org].str.upper().str.contains(
                "UNIVERSIDADE|INSTITUTO FEDERAL|CENTRO DE PESQUISA", na=False
            ) if col_org else pd.Series(True, index=df.index)
            resultado = (df[filtro].groupby(col_uf).size()
                         .reset_index().rename(columns={col_uf:"estado_sigla", 0:"instituicoes_pesquisa"}))
            resultado.to_csv(csv, index=False)
            return resultado
    except Exception as e:
        st.warning(f"MEC e-MEC falhou: {e}")

    # Fallback: referência baseada em MEC 2022 + CNPq
    dados = [
        ("AC",8),("AL",15),("AP",7),("AM",25),("BA",50),("CE",38),("DF",35),
        ("ES",28),("GO",40),("MA",20),("MT",22),("MS",20),("MG",85),("PA",30),
        ("PB",18),("PR",65),("PE",42),("PI",14),("RJ",75),("RN",22),("RS",70),
        ("RO",10),("RR",7),("SC",55),("SP",120),("SE",12),("TO",12),
    ]
    return pd.DataFrame(dados, columns=["estado_sigla","instituicoes_pesquisa"])


# ════════════════════════════════════════════════════════════
# FUNÇÃO MESTRA
# ════════════════════════════════════════════════════════════
def carregar_todos(usar_mock: bool = False) -> pd.DataFrame:
    """
    Consolida todas as fontes em um único DataFrame por estado (27 linhas).
    usar_mock=True → retorna dados fictícios do scoring.py (desenvolvimento).
    """
    if usar_mock:
        from scoring import gerar_dados_mock
        return gerar_dados_mock()

    # Base fixa: incentivos (sempre disponível)
    df_inc = _incentivos_fiscais()[["estado_sigla","incentivo_fiscal"]]
    df_log = _logistica()[["estado_sigla","logistica_score"]]
    df_pol = _politicas_publicas()[["estado_sigla","politicas_publicas"]]
    df_ies = _instituicoes_pesquisa()[["estado_sigla","instituicoes_pesquisa"]]
    df_agu = _agua_disponivel()[["estado_sigla","agua_disponivel"]]
    df_min = _minerais()[["estado_sigla","minerais_gerais","minerais_criticos"]]

    df = (df_inc.merge(df_log, on="estado_sigla", how="outer")
                .merge(df_pol, on="estado_sigla", how="outer")
                .merge(df_ies, on="estado_sigla", how="outer")
                .merge(df_agu, on="estado_sigla", how="outer")
                .merge(df_min, on="estado_sigla", how="outer"))

    # Adiciona nomes dos estados
    nomes = {
        "AC":"Acre","AL":"Alagoas","AP":"Amapá","AM":"Amazonas","BA":"Bahia","CE":"Ceará",
        "DF":"Dist. Federal","ES":"Espírito Santo","GO":"Goiás","MA":"Maranhão",
        "MT":"Mato Grosso","MS":"Mato Grosso do Sul","MG":"Minas Gerais","PA":"Pará",
        "PB":"Paraíba","PR":"Paraná","PE":"Pernambuco","PI":"Piauí","RJ":"Rio de Janeiro",
        "RN":"Rio Gr. Norte","RS":"Rio Gr. Sul","RO":"Rondônia","RR":"Roraima",
        "SC":"Santa Catarina","SP":"São Paulo","SE":"Sergipe","TO":"Tocantins",
    }
    df["estado_nome"] = df["estado_sigla"].map(nomes)

    # ONS — carga por estado
    df_ons = _carga_ons()
    rows_carga = []
    for _, row in df_ons.iterrows():
        for uf in MAPA_SUB.get(row["cod_sub"], []):
            rows_carga.append({"estado_sigla": uf, "energia_demanda": row["carga_mw"]})
    df = df.merge(pd.DataFrame(rows_carga), on="estado_sigla", how="left")

    # ANEEL — potência instalada
    df_aneel = _aneel_siga()
    df = df.merge(df_aneel.rename(columns={"energia_potencia_mw":"energia_potencia"}),
                  on="estado_sigla", how="left")

    # ComexStat — exportações
    df_cx = _exportacoes()
    if not df_cx.empty and "state" in df_cx.columns:
        df_cx2 = (df_cx.groupby("state")["metricFOB"].sum()
                  .reset_index().rename(columns={"state":"estado_sigla","metricFOB":"exportacao_volume"}))
        df = df.merge(df_cx2, on="estado_sigla", how="left")
    else:
        df["exportacao_volume"] = None

    return df
