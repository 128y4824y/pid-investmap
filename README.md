# PID InvestMap v3
## Motor de Decisão de Localização Industrial Verde — Hackathon E+ 2026

---

## 🚀 Como executar em 3 passos

```bash
# 1. Instalar dependências
pip install -r requirements.txt

# 2. Pré-processar dados (rodar antes do hackathon — ~5 minutos para dados rápidos)
python pre_processar_dados.py

# 3. Iniciar o app
streamlit run app.py
```

O app abre em `http://localhost:8501`

---

## 📁 Estrutura do projeto

```
pid_investmap/
│
├── app.py                    → Entrada principal + sidebar com seleção de persona
├── scoring.py                → Modelo de scoring (pesos, personas, mock de 27 estados)
├── data_loader.py            → Todas as fontes de dados (APIs + arquivos locais)
├── pre_processar_dados.py    → Script de download e pré-processamento (rodar antes)
├── requirements.txt          → Dependências Python
├── FONTES_DE_DADOS.md        → Guia completo de onde buscar cada dado
│
├── pages/
│   ├── inicio.py             → Página inicial e contexto da solução
│   ├── diagnostico.py        → Início-Meio-Fim (diagnóstico da PID)
│   ├── mapa_score.py         → Mapa interativo + ranking por persona
│   └── relatorio.py          → Relatório detalhado por estado + exportação CSV
│
└── data/                     → Arquivos pré-processados (gerados por pre_processar_dados.py)
    ├── agua_por_estado.csv
    ├── minerais_por_estado.csv
    ├── logistica_por_estado.csv
    ├── logistica_detalhada.csv
    └── politicas_por_estado.csv
```

---

## 👤 Personas e prioridade de camadas

| Persona | Camada #1 | Camada #2 | Camada #3 |
|---------|-----------|-----------|-----------|
| 🏭 Indústria | ⚡ Potência | 📊 Demanda | 💧 Água |
| 🏛️ Gestor Público | 💰 Incentivos | 📦 Exportações | 🚛 Logística |
| 🔬 Think Tank | 📜 Políticas | 🎓 P&D | 🔬 Minerais críticos |
| 🌿 ONG | 📜 Políticas | 💧 Água | 💰 Incentivos |

---

## 📊 10 dimensões de dados

| Var | Dimensão | Fonte | Status |
|-----|----------|-------|--------|
| V01 | ⚡ Potência instalada (MW) | ANEEL SIGA — CSV mensal | Baixar |
| V02 | 📊 Demanda de energia (MW) | ONS — API REST | API ativa |
| V03 | 💧 Disponibilidade hídrica | ANA SNIRH — CSV | ✅ Gerado |
| V04 | ⛏️ Minerais gerais (ha) | ANM SIGMINE — Shapefile | ✅ Gerado |
| V05 | 🔬 Minerais críticos (ha) | ANM SIGMINE filtrado | ✅ Gerado |
| V06 | 🚛 Logística integrada | DNIT+ANTAQ+ANTT — SHP | ✅ Gerado |
| V07 | 📦 Exportações (USD FOB) | ComexStat — API REST POST | API ativa |
| V08 | 💰 Incentivos fiscais | SUDENE/SUDAM/ZFM — estático | ✅ No código |
| V09 | 📜 Políticas públicas | BNDES+ANEEL — CSV | ✅ Gerado |
| V10 | 🎓 Instituições P&D | MEC e-MEC — CSV | ✅ No código |

---

## ⚠️ Nota sobre APIs externas

As APIs do ONS, ComexStat e ANEEL podem estar bloqueadas em redes restritas.
O app tem fallback automático para dados mock em todos os casos.

Para testar conectividade:
```bash
curl "https://apicarga.ons.org.br/prd/cargaverificada?dat_inicio=2025-04-01&dat_fim=2025-05-01&cod_areacarga=SE"
curl -X POST "https://api-comexstat.mdic.gov.br/states" \
     -H "Content-Type: application/json" \
     -d '{"flow":"export","monthDetail":false,"period":{"from":"2024-01","to":"2024-12"}}'
```

---

## 🎯 Cenários de demonstração (para o pitch)

**Cenário 1 — Investidor (siderurgia verde):**
- Persona: 🏭 Indústria / Investidor → Subperfil: Siderurgia / Aço
- O sistema rankeia os estados pelos dados reais de potência, minerais e logística.
- O ranking não é pré-determinado: ele é calculado automaticamente a partir dos dados.

**Cenário 2 — ONG (equidade na transição):**
- Persona: 🌿 ONG / Sociedade Civil
- O mesmo mapa, os mesmos dados — mas com pesos completamente diferentes.
- O ranking muda porque o que importa para uma ONG (políticas, água, descarbonização)
  é diferente do que importa para um investidor industrial.

*Esse é o diferencial central: a ferramenta não indica onde investir —
ela organiza os dados de forma objetiva para que cada usuário tome
sua própria decisão com base em evidências.*
