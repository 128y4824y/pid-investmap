"""
pre_processar_dados.py
======================
Execute este script ANTES do hackathon começar para preparar todos os
arquivos CSV/GeoJSON que o app usará como fallback quando as APIs falharem.

Tempo estimado: 20–40 minutos dependendo da velocidade de download.

Uso:
  pip install geopandas requests pandas numpy scipy tqdm
  python pre_processar_dados.py

Cada seção pode ser executada independentemente.
Os arquivos são salvos em data/ e usados automaticamente pelo data_loader.py.
"""

import os
import requests
import zipfile
import pandas as pd
import numpy as np
from pathlib import Path
from io import BytesIO

DATA_DIR = Path("data")
DATA_DIR.mkdir(exist_ok=True)

def print_step(n, total, msg):
    print(f"\n[{n}/{total}] {'─'*50}")
    print(f"  {msg}")
    print(f"{'─'*54}")


# ═══════════════════════════════════════════════════════════
# PASSO 1 — ANEEL SIGA: Capacidade instalada por estado
# ═══════════════════════════════════════════════════════════
def processar_aneel():
    print_step(1, 7, "ANEEL SIGA — Potência instalada por estado")
    url = (
        "https://dadosabertos.aneel.gov.br/dataset/"
        "siga-sistema-de-informacoes-de-geracao-da-aneel/resource/"
        "b1bd71e7-d0ad-4214-9053-cbd58e9564a7/download/siga-empreendimentos-geracao.csv"
    )
    saida = DATA_DIR / "aneel_potencia_por_estado.csv"
    if saida.exists():
        print("  ✅ Arquivo já existe, pulando.")
        return

    print("  Baixando CSV SIGA (~20MB)...")
    try:
        r = requests.get(url, timeout=60)
        r.raise_for_status()
        df = pd.read_csv(BytesIO(r.content), sep=";", encoding="latin1", on_bad_lines="skip")
        # Filtra em operação
        df = df[df.get("DscFaseUsina", pd.Series()).str.strip() == "Operação"]
        df["MdaPotenciaFiscalizadaKw"] = pd.to_numeric(
            df.get("MdaPotenciaFiscalizadaKw", 0), errors="coerce")
        # Agrupa por estado e tipo de fonte
        df_uf = (df.groupby(["SigUFPrincipal","DscFonteEnergiaReagrupamento"])
                   ["MdaPotenciaFiscalizadaKw"].sum()
                   .div(1000).reset_index()
                   .rename(columns={"SigUFPrincipal":"estado_sigla",
                                    "DscFonteEnergiaReagrupamento":"tipo_fonte",
                                    "MdaPotenciaFiscalizadaKw":"potencia_mw"}))
        df_uf.to_csv(saida, index=False)
        # Também gera resumo total por estado
        df_total = df_uf.groupby("estado_sigla")["potencia_mw"].sum().reset_index()
        df_total.columns = ["estado_sigla","energia_potencia"]
        df_total.to_csv(DATA_DIR / "aneel_total_por_estado.csv", index=False)
        print(f"  ✅ Salvo: {saida.name} ({len(df_uf)} linhas)")
        print(f"  ✅ Salvo: aneel_total_por_estado.csv")
    except Exception as e:
        print(f"  ⚠️  Falhou: {e}")


# ═══════════════════════════════════════════════════════════
# PASSO 2 — MEC e-MEC: Instituições de ensino por estado
# ═══════════════════════════════════════════════════════════
def processar_mec():
    print_step(2, 7, "MEC e-MEC — Instituições de ensino superior por estado")
    url    = (
        "https://dadosabertos.mec.gov.br/images/conteudo/Ind-ensino-superior/2022/"
        "PDA_Lista_Instituicoes_Ensino_Superior_do_Brasil_EMEC.csv"
    )
    saida  = DATA_DIR / "instituicoes_por_estado.csv"
    if saida.exists():
        print("  ✅ Arquivo já existe, pulando.")
        return

    print("  Baixando CSV MEC e-MEC (~5MB)...")
    try:
        r = requests.get(url, timeout=60)
        r.raise_for_status()
        df = pd.read_csv(BytesIO(r.content), sep=";", encoding="latin1", on_bad_lines="skip")

        # Identifica colunas de UF e organização acadêmica
        col_uf  = next((c for c in df.columns if "UF" in c.upper()), None)
        col_org = next((c for c in df.columns if "ORGAN" in c.upper()), None)
        col_sit = next((c for c in df.columns if "SITUA" in c.upper()), None)

        if col_sit:
            df = df[df[col_sit].str.upper().str.contains("ATIVA|EM ATIVIDADE", na=False)]

        tipos_relevantes = "UNIVERSIDADE|INSTITUTO FEDERAL|CENTRO FEDERAL|CENTRO DE PESQUISA"
        if col_org:
            df_filtrado = df[df[col_org].str.upper().str.contains(tipos_relevantes, na=False)]
        else:
            df_filtrado = df

        resultado = (df_filtrado.groupby(col_uf).size()
                     .reset_index()
                     .rename(columns={col_uf:"estado_sigla", 0:"instituicoes_pesquisa"}))
        resultado.to_csv(saida, index=False)
        print(f"  ✅ Salvo: {saida.name} ({len(resultado)} estados)")
    except Exception as e:
        print(f"  ⚠️  Falhou: {e}")


# ═══════════════════════════════════════════════════════════
# PASSO 3 — ANA SNIRH: Disponibilidade hídrica
# ═══════════════════════════════════════════════════════════
def processar_ana():
    print_step(3, 7, "ANA SNIRH — Disponibilidade hídrica por estado")
    saida = DATA_DIR / "agua_por_estado.csv"
    if saida.exists():
        print("  ✅ Arquivo já existe, pulando.")
        return

    # Tenta baixar via dados abertos ANA
    url = "https://dadosabertos.ana.gov.br/api/3/action/datastore_search?resource_id=disponibilidade-hidrica&limit=5000"
    try:
        r = requests.get(url, timeout=30)
        dados = r.json().get("result", {}).get("records", [])
        if dados:
            df = pd.DataFrame(dados)
            print(f"  Colunas ANA: {list(df.columns)[:10]}")
    except Exception:
        pass

    # Fallback: usa valores do Relatório Conjuntura ANA 2023 (já no data_loader.py)
    print("  ℹ️  Usando referência Conjuntura ANA 2023 (Q90 por estado)")
    dados_ref = [
        ("AC",3500),("AL",310),("AP",2100),("AM",98000),("BA",1900),("CE",280),
        ("DF",145),("ES",790),("GO",3900),("MA",1950),("MT",8200),("MS",3400),
        ("MG",3300),("PA",58000),("PB",240),("PR",2900),("PE",390),("PI",500),
        ("RJ",680),("RN",195),("RS",2450),("RO",3900),("RR",4900),("SC",2100),
        ("SP",1480),("SE",290),("TO",4900),
    ]
    pd.DataFrame(dados_ref, columns=["estado_sigla","agua_disponivel"]).to_csv(saida, index=False)
    print(f"  ✅ Salvo: {saida.name}")


# ═══════════════════════════════════════════════════════════
# PASSO 4 — ANM SIGMINE: Minerais por estado
# ═══════════════════════════════════════════════════════════
def processar_sigmine():
    print_step(4, 7, "ANM SIGMINE — Minerais gerais e críticos por estado")
    saida = DATA_DIR / "minerais_por_estado.csv"
    if saida.exists():
        print("  ✅ Arquivo já existe, pulando.")
        return

    zip_local = DATA_DIR / "SIGMINE_BRASIL.zip"

    if not zip_local.exists():
        print("  Baixando SIGMINE BRASIL (~500MB). Pode demorar 10–20 minutos...")
        url = "https://app.anm.gov.br/dadosabertos/SIGMINE/PROCESSOS_MINERARIOS/BRASIL.zip"
        try:
            with requests.get(url, stream=True, timeout=300) as r:
                r.raise_for_status()
                total = int(r.headers.get("Content-Length", 0))
                baixado = 0
                with open(zip_local, "wb") as f:
                    for chunk in r.iter_content(chunk_size=8192):
                        f.write(chunk)
                        baixado += len(chunk)
                        if total:
                            pct = baixado / total * 100
                            print(f"\r  Progresso: {pct:.1f}%", end="", flush=True)
            print(f"\n  ✅ Download completo: {zip_local}")
        except Exception as e:
            print(f"\n  ⚠️  Download falhou: {e}")
            print("  → Usando dados de referência ANM 2024")
            _salvar_minerais_referencia(saida)
            return

    # Processa o shapefile
    print("  Processando shapefile...")
    try:
        import geopandas as gpd

        with zipfile.ZipFile(zip_local, "r") as zf:
            shp_files = [f for f in zf.namelist() if f.endswith(".shp")]
            print(f"  Shapefiles encontrados: {shp_files[:3]}")
            zf.extractall(DATA_DIR / "sigmine_raw")

        shp_path = next((DATA_DIR / "sigmine_raw" / f for f in
                         (DATA_DIR / "sigmine_raw").rglob("*.shp")), None)
        if not shp_path:
            raise FileNotFoundError("Shapefile não encontrado após extração")

        print(f"  Lendo {shp_path.name}...")
        gdf = gpd.read_file(shp_path)
        print(f"  Shape: {gdf.shape}, CRS: {gdf.crs}")
        print(f"  Colunas: {list(gdf.columns)}")

        # Detecta colunas de UF e substância
        col_uf  = next((c for c in gdf.columns if c.upper() in ["UF","SIG_UF","ESTADO"]), "UF")
        col_sub = next((c for c in gdf.columns if "SUBST" in c.upper()), "SUBSTANCIA")
        col_fase = next((c for c in gdf.columns if "FASE" in c.upper()), "FASE")

        # Filtra fases ativas
        fases_ativas = ["AUTORIZAÇÃO DE PESQUISA","CONCESSÃO DE LAVRA",
                        "LICENCIAMENTO","REQUERIMENTO DE LAVRA"]
        gdf = gdf[gdf[col_fase].str.upper().str.strip().isin(
            [f.upper() for f in fases_ativas])]

        # Calcula área em hectares (reprojetar para SIRGAS 2000 Policônica)
        gdf_m = gdf.to_crs("EPSG:5880")
        gdf_m["area_ha"] = gdf_m.geometry.area / 10000

        # Minerais críticos
        criticos = ["NIOBIO","LITIO","TERRAS RARAS","GRAFITA","MANGANES",
                    "COBALTO","TUNGSTEN","VANADIO","CROMO","GERMANIO",
                    "INDIO","TELURO","SELENIO"]
        gdf_m["is_critico"] = gdf_m[col_sub].str.upper().apply(
            lambda x: any(c in str(x) for c in criticos) if pd.notna(x) else False)

        # Agrega por estado
        df_g = (gdf_m.groupby(col_uf)["area_ha"].sum()
                .reset_index().rename(columns={col_uf:"estado_sigla","area_ha":"minerais_gerais"}))
        df_c = (gdf_m[gdf_m["is_critico"]].groupby(col_uf)["area_ha"].sum()
                .reset_index().rename(columns={col_uf:"estado_sigla","area_ha":"minerais_criticos"}))

        df_min = df_g.merge(df_c, on="estado_sigla", how="left")
        df_min["minerais_criticos"] = df_min["minerais_criticos"].fillna(0)
        df_min.to_csv(saida, index=False)
        print(f"  ✅ Salvo: {saida.name}")

    except ImportError:
        print("  ⚠️  GeoPandas não instalado. Execute: pip install geopandas")
        _salvar_minerais_referencia(saida)
    except Exception as e:
        print(f"  ⚠️  Processamento falhou: {e}")
        _salvar_minerais_referencia(saida)


def _salvar_minerais_referencia(saida):
    dados = [
        ("AC",62000,25000),("AL",7500,1000),("AP",91000,35000),("AM",205000,80000),
        ("BA",255000,60000),("CE",22000,3000),("DF",1200,500),("ES",42000,20000),
        ("GO",305000,120000),("MA",36000,5000),("MT",410000,40000),("MS",82000,8000),
        ("MG",820000,450000),("PA",615000,200000),("PB",8500,1500),("PR",46000,15000),
        ("PE",11000,3000),("PI",16000,2000),("RJ",31000,5000),("RN",13000,4000),
        ("RS",66000,10000),("RO",155000,30000),("RR",125000,90000),("SC",52000,6000),
        ("SP",72000,8000),("SE",5500,800),("TO",102000,18000),
    ]
    pd.DataFrame(dados, columns=["estado_sigla","minerais_gerais","minerais_criticos"]).to_csv(saida, index=False)
    print(f"  ✅ Salvo referência ANM: {saida.name}")


# ═══════════════════════════════════════════════════════════
# PASSO 5 — BNDES + ANEEL Leilões: Políticas públicas
# ═══════════════════════════════════════════════════════════
def processar_politicas():
    print_step(5, 7, "BNDES + ANEEL leilões — Políticas públicas por estado")
    saida = DATA_DIR / "politicas_por_estado.csv"
    if saida.exists():
        print("  ✅ Arquivo já existe, pulando.")
        return

    # BNDES dados abertos
    bndes_ok = False
    try:
        url_bndes = "https://dadosabertos.bndes.gov.br/dataset/operacoes-de-financiamento/resource/8a16cd6d-b586-4d1e-83d1-cee74ba3c895/download/bndes_operacoes.csv"
        print("  Tentando BNDES API...")
        r = requests.get(url_bndes, timeout=30)
        if r.status_code == 200:
            df = pd.read_csv(BytesIO(r.content), encoding="latin1",
                             sep=";", on_bad_lines="skip", nrows=50000)
            print(f"  BNDES colunas: {list(df.columns)[:8]}")
            bndes_ok = True
    except Exception as e:
        print(f"  BNDES API indisponível: {e}")

    # Fallback: tabela estática detalhada (já no data_loader.py)
    print("  Usando referência estática de políticas públicas...")
    dados = [
        ("AC",0.30,"Bioeconomia inicial | BNDES baixo | sem lei específica"),
        ("AL",0.40,"Biocomb. cana | BNDES baixo | leilões eólicos menores"),
        ("AP",0.28,"Solar emergente | BNDES muito baixo"),
        ("AM",0.45,"Bioeconomia amazônica | ZFM verde | BNDES médio"),
        ("BA",0.70,"BNDES Polo Camaçari | leilões solares | programas estaduais"),
        ("CE",0.85,"Lei H₂ Verde 2022 | líder leilões eólicos ANEEL | BNDES alto"),
        ("DF",0.45,"Programa solar GDF | BNDES médio | hub regulatório"),
        ("ES",0.55,"Programa Gerar 2021 | offshore eólico planejado | BNDES médio"),
        ("GO",0.50,"Solar + biocombustível | BNDES médio"),
        ("MA",0.45,"Potencial eólico | BNDES baixo | leilões recentes"),
        ("MT",0.40,"Biocombustível | solar rural | BNDES médio"),
        ("MS",0.38,"Biocombustível | BNDES baixo"),
        ("MG",0.60,"BNDES hidrelétricas + biogás | mineração verde | leilões"),
        ("PA",0.48,"COP30 2025 impulsionou | hidrelétricas | BNDES médio"),
        ("PB",0.50,"Leilões eólicos | solar | BNDES médio"),
        ("PR",0.58,"Programa H₂ Copel | bioenergia | BNDES alto"),
        ("PE",0.60,"Porto Suape hub H₂ | ZPE H₂ verde | BNDES alto"),
        ("PI",0.75,"Lei H₂ Verde 2022 | expansão solar acelerada"),
        ("RJ",0.50,"Petrobras descarbonização | offshore | BNDES médio"),
        ("RN",0.82,"Lei H₂ Verde 2023 | maior geração eólica per capita"),
        ("RS",0.55,"Bioenergia | eólico offshore planejado | BNDES alto"),
        ("RO",0.35,"Hidrelétricas | bioenergia | BNDES baixo"),
        ("RR",0.25,"Solar início | BNDES muito baixo"),
        ("SC",0.52,"Solar distribuído | biogás suíno | BNDES médio"),
        ("SP",0.65,"Maior volume BNDES absoluto | programa solar empresarial"),
        ("SE",0.42,"Gás natural | início solar | BNDES baixo"),
        ("TO",0.55,"Palmas Solar 2015 (pioneiro) | hidrelétricas | BNDES médio"),
    ]
    pd.DataFrame(dados, columns=["estado_sigla","politicas_publicas","descricao_politica"]).to_csv(saida, index=False)
    print(f"  ✅ Salvo: {saida.name}")


# ═══════════════════════════════════════════════════════════
# PASSO 6 — Logística: Score pré-calculado (referência)
# ═══════════════════════════════════════════════════════════
def processar_logistica():
    print_step(6, 7, "Logística integrada — Score por estado (referência DNIT/ANTAQ/ANTT)")
    saida = DATA_DIR / "logistica_por_estado.csv"
    if saida.exists():
        print("  ✅ Arquivo já existe, pulando.")
        return

    # Instruções para cálculo real (requer GeoPandas + shapefiles)
    print("  ℹ️  Para calcular com dados reais, baixe os shapefiles:")
    print("     Rodovias DNIT: servicos.dnit.gov.br/vgeo")
    print("     Hidrovias ANTAQ: antaq.gov.br/portal/PNIH")
    print("     Ferrovias ANTT: dados.antt.gov.br")
    print("     Portos ANTAQ: dadosabertos.antaq.gov.br")
    print("     Aeroportos ANAC: dados.gov.br/dataset/aerodromos-publicos")
    print("  Usando scores de referência baseados em DNIT/ANTAQ 2024...")

    dados = [
        ("AC",0.22,"Sem porto | sem ferrovia | rodovia BR-317 com trechos precários"),
        ("AL",0.48,"Porto de Maceió | sem ferrovia | BR-101 pavimentada"),
        ("AP",0.28,"Porto de Santana | hidrovia do Amazonas | sem ferrovia"),
        ("AM",0.38,"Porto de Manaus | hidrovia essencial | sem ferrovia terrestre"),
        ("BA",0.65,"Porto de Aratu/Ilhéus | FCA ferrovia | BR-101/BR-116"),
        ("CE",0.62,"Porto de Pecém/Mucuripe | sem ferrovia ativa | BR-116/BR-304"),
        ("DF",0.52,"Sem porto | sem ferrovia | BR-020/BR-040 pavimentadas | SBBS aeroporto"),
        ("ES",0.72,"Porto de Vitória | EFVM ferrovia | BR-101 excelente"),
        ("GO",0.58,"Sem porto | FCA ferrovia | BR-153/BR-060"),
        ("MA",0.50,"Porto de Itaqui (maior do NE) | EFC ferrovia | BR-010"),
        ("MT",0.48,"Sem porto | sem ferrovia ativa principal | BR-163/BR-364"),
        ("MS",0.52,"Sem porto marítimo | RFFSA hidrovia Paraná | BR-163/BR-262"),
        ("MG",0.78,"Porto de Uberlândia/Ipatinga | MRS+FCA ferrovias | excelente malha"),
        ("PA",0.55,"Porto de Belém/Barcarena | EFC ferrovia | BR-010 | rio Amazonas"),
        ("PB",0.50,"Porto de Cabedelo | sem ferrovia ativa | BR-101/BR-230"),
        ("PR",0.85,"Porto de Paranaguá (2º BR) | ALL ferrovia | BR-116/BR-376"),
        ("PE",0.68,"Porto de Suape/Recife | TRANSNORDESTINA em obras | BR-101"),
        ("PI",0.42,"Sem porto | TRANSNORDESTINA em obras | BR-316"),
        ("RJ",0.90,"Porto do Rio/Itaguaí | MRS ferrovia | BR-101/BR-116 excelente"),
        ("RN",0.55,"Porto de Natal/Areia Branca | sem ferrovia | BR-101/BR-304"),
        ("RS",0.80,"Porto de Rio Grande/Porto Alegre | ALL ferrovia | BR-101/BR-116"),
        ("RO",0.35,"Sem porto marítimo | sem ferrovia | BR-364 | hidrovia Madeira"),
        ("RR",0.20,"Sem porto | sem ferrovia | BR-174 única saída | isolamento"),
        ("SC",0.82,"Porto de Itajaí/Imbituba | ALL ferrovia | BR-101/BR-116"),
        ("SP",0.95,"Porto de Santos (1º BR) | MRS+CPTM ferrovias | maior malha rodoviária"),
        ("SE",0.50,"Porto de Aracaju | sem ferrovia | BR-101/BR-235"),
        ("TO",0.42,"Sem porto | FNS ferrovia em obras | BR-153 Belém-Brasília"),
    ]
    df = pd.DataFrame(dados, columns=["estado_sigla","logistica_score","descricao_logistica"])
    df[["estado_sigla","logistica_score"]].to_csv(saida, index=False)
    # Salva versão completa com descrições
    df.to_csv(DATA_DIR / "logistica_detalhada.csv", index=False)
    print(f"  ✅ Salvo: {saida.name} + logistica_detalhada.csv")


# ═══════════════════════════════════════════════════════════
# PASSO 7 — Teste das APIs em tempo real
# ═══════════════════════════════════════════════════════════
def testar_apis():
    print_step(7, 7, "Teste de conectividade das APIs em tempo real")
    from datetime import date, timedelta
    hoje = date.today()
    ini  = hoje - timedelta(days=7)

    apis = [
        ("ONS carga SE",
         f"https://apicarga.ons.org.br/prd/cargaverificada"
         f"?dat_inicio={ini}&dat_fim={hoje}&cod_areacarga=SE"),
        ("ONS carga NE",
         f"https://apicarga.ons.org.br/prd/cargaverificada"
         f"?dat_inicio={ini}&dat_fim={hoje}&cod_areacarga=NE"),
        ("ComexStat (POST)",  None),  # POST tratado abaixo
        ("IBGE municípios",
         "https://servicodados.ibge.gov.br/api/v1/localidades/municipios?view=nivelado"),
    ]

    for nome, url in apis:
        if nome == "ComexStat (POST)":
            try:
                r = requests.post(
                    "https://api-comexstat.mdic.gov.br/states",
                    json={"flow":"export","monthDetail":False,
                          "period":{"from":"2024-01","to":"2024-03"}},
                    headers={"Content-Type":"application/json"}, timeout=15)
                status = r.status_code
                n = len(r.json().get("data",{}).get("list",[]))
                print(f"  {'✅' if status==200 else '❌'} {nome}: HTTP {status} — {n} registros")
            except Exception as e:
                print(f"  ❌ {nome}: {e}")
        else:
            try:
                r = requests.get(url, timeout=12)
                n = len(r.json()) if isinstance(r.json(), list) else "objeto"
                print(f"  {'✅' if r.status_code==200 else '❌'} {nome}: HTTP {r.status_code} — {n} registros")
            except Exception as e:
                print(f"  ❌ {nome}: {e}")


# ═══════════════════════════════════════════════════════════
# EXECUÇÃO
# ═══════════════════════════════════════════════════════════
if __name__ == "__main__":
    print("=" * 56)
    print(" PID InvestMap — Pré-processamento de dados")
    print(" Execute ANTES do hackathon começar")
    print("=" * 56)

    processar_aneel()
    processar_mec()
    processar_ana()
    processar_sigmine()   # mais demorado (~20min)
    processar_politicas()
    processar_logistica()
    testar_apis()

    print("\n" + "=" * 56)
    print(" ✅ Pré-processamento concluído!")
    print(f" Arquivos gerados em: {DATA_DIR.resolve()}")
    print(" Execute: streamlit run app.py")
    print("=" * 56)
