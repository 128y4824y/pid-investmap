# GUIA DO EXECUTÁVEL — PID InvestMap
## Como instalar, rodar e distribuir o sistema
### Para quem conhece pouco de programação

---

## PARTE 1 — Instalando o que você precisa (fazer uma vez só)

### Passo 1 — Instalar o Python

O Python é a linguagem em que o sistema foi escrito.

**No Windows:**
1. Abra o navegador e acesse: **https://www.python.org/downloads/**
2. Clique no botão amarelo grande **"Download Python 3.12.x"**
3. Abra o arquivo baixado
4. ⚠️ **IMPORTANTE:** marque a caixinha **"Add Python to PATH"** antes de clicar em Install
5. Clique em **"Install Now"**
6. Aguarde terminar e clique em **"Close"**

**No Mac:**
1. Acesse **https://www.python.org/downloads/**
2. Baixe e instale o mesmo jeito

**Como confirmar que funcionou:**
- Windows: aperte `Win + R`, digite `cmd`, pressione Enter
- Mac: abra o **Terminal** (busque no Spotlight)
- Digite: `python --version` e pressione Enter
- Deve aparecer algo como: `Python 3.12.3`

---

### Passo 2 — Abrir o Terminal (onde você vai digitar os comandos)

**Windows:** Aperte `Win + R` → digite `cmd` → Enter
**Mac:** Abra o **Terminal** (busque no Spotlight com `Cmd + Espaço`)

> Você verá uma tela preta com texto. Não se preocupe — é normal.

---

### Passo 3 — Ir até a pasta do projeto

Você recebeu uma pasta chamada **`pid_investmap_v4`**. Salve ela na sua Área de Trabalho.

No terminal, digite (substitua `SeuNome` pelo seu nome de usuário):

**Windows:**
```
cd C:\Users\SeuNome\Desktop\pid_investmap_v4
```

**Mac:**
```
cd ~/Desktop/pid_investmap_v4
```

Pressione Enter. Se não aparecer nenhum erro, funcionou.

---

### Passo 4 — Instalar as dependências do sistema

Com o terminal aberto na pasta do projeto, copie e cole este comando:

```
pip install streamlit pandas numpy requests folium geopandas
```

Pressione Enter e aguarde. Vai aparecer muito texto — isso é normal. Pode demorar de 2 a 5 minutos na primeira vez.

Quando terminar, aparecerá algo como: `Successfully installed streamlit-1.xx.x ...`

---

## PARTE 2 — Rodando o sistema

### Passo 5 — Pré-processar os dados (fazer uma vez)

Ainda no terminal, dentro da pasta do projeto, digite:

```
python pre_processar_dados.py
```

Este script baixa e prepara os dados que o app usa. Aguarde terminar (3–5 minutos).

---

### Passo 6 — Iniciar o sistema

```
streamlit run app.py
```

Após alguns segundos, o seu navegador abrirá automaticamente com o sistema funcionando em:
```
http://localhost:8501
```

> Para encerrar o sistema: volte ao terminal e pressione `Ctrl + C`

---

## PARTE 3 — Três formas de distribuir o sistema

Existem três opções, do mais simples ao mais avançado:

---

### OPÇÃO A — Link online grátis (mais fácil — recomendada para o hackathon)
**Tempo: 10 minutos | Grátis | Funciona em qualquer dispositivo**

O Streamlit oferece hospedagem gratuita. Qualquer pessoa com o link acessa o sistema.

**Passo a passo:**

1. Crie uma conta gratuita em **https://github.com** (se não tiver)

2. Crie um novo repositório no GitHub:
   - Clique em **"New"** (botão verde)
   - Nome: `pid-investmap`
   - Marque **"Public"**
   - Clique em **"Create repository"**

3. Faça upload dos arquivos:
   - Clique em **"uploading an existing file"**
   - Arraste toda a pasta `pid_investmap_v4` para lá
   - Clique em **"Commit changes"**

4. Acesse **https://streamlit.io/cloud**
   - Clique em **"Sign up"** e conecte com sua conta GitHub

5. No Streamlit Cloud:
   - Clique em **"New app"**
   - Selecione seu repositório `pid-investmap`
   - Branch: `main`
   - Main file path: `app.py`
   - Clique em **"Deploy!"**

6. Aguarde 2–3 minutos. Você receberá um link do tipo:
   ```
   https://pid-investmap-suaconta.streamlit.app
   ```

✅ **Pronto!** Qualquer pessoa com esse link acessa o sistema, inclusive no celular.

---

### OPÇÃO B — Arquivo .exe para Windows (sem precisar de Python instalado)
**Tempo: 20 minutos | Funciona offline | Só para Windows**

Essa opção gera um arquivo `.exe` que qualquer pessoa pode abrir no Windows sem instalar nada.

**Passo a passo:**

1. No terminal, instale o PyInstaller:
   ```
   pip install pyinstaller
   ```

2. Crie um arquivo chamado `launcher.py` na pasta do projeto com este conteúdo:
   ```python
   import subprocess
   import sys
   import os
   import webbrowser
   import time

   def main():
       # Inicia o Streamlit em background
       proc = subprocess.Popen(
           [sys.executable, "-m", "streamlit", "run", "app.py",
            "--server.headless=true", "--server.port=8501"],
           cwd=os.path.dirname(os.path.abspath(__file__))
       )
       # Aguarda o servidor iniciar
       time.sleep(3)
       # Abre o navegador automaticamente
       webbrowser.open("http://localhost:8501")
       # Aguarda o processo terminar
       proc.wait()

   if __name__ == "__main__":
       main()
   ```

3. Gere o executável:
   ```
   pyinstaller --onefile --name "PID_InvestMap" launcher.py
   ```

4. O arquivo `.exe` estará em: `dist/PID_InvestMap.exe`

5. Para distribuir: copie a pasta inteira `pid_investmap_v4` + o arquivo `.exe` para um pendrive ou ZIP.

> ⚠️ Limitação: o destinatário precisa ter Python instalado para funcionar. Para executável 100% independente, use a Opção C.

---

### OPÇÃO C — Docker (mais robusto — recomendado para uso contínuo)
**Tempo: 30 minutos | Funciona em qualquer sistema | Requer conhecimento básico**

O Docker empacota tudo (Python, bibliotecas e código) em um único container.

1. Instale o Docker Desktop: **https://www.docker.com/products/docker-desktop/**

2. Crie um arquivo chamado `Dockerfile` na pasta do projeto:
   ```dockerfile
   FROM python:3.12-slim

   WORKDIR /app
   COPY . .

   RUN pip install --no-cache-dir streamlit pandas numpy requests \
       folium geopandas scipy

   EXPOSE 8501

   HEALTHCHECK CMD curl --fail http://localhost:8501/_stcore/health

   ENTRYPOINT ["streamlit", "run", "app.py", \
               "--server.port=8501", \
               "--server.address=0.0.0.0"]
   ```

3. No terminal, dentro da pasta do projeto:
   ```
   docker build -t pid-investmap .
   docker run -p 8501:8501 pid-investmap
   ```

4. Acesse: `http://localhost:8501`

---

## RESUMO — Qual opção usar para o hackathon?

| Situação | Opção recomendada |
|----------|------------------|
| Demo ao vivo na apresentação | **A — Streamlit Cloud** (link já aberto no navegador) |
| Deixar os juízes testarem depois | **A — Streamlit Cloud** (compartilha o link) |
| Computador sem internet | **Rodar local** (Parte 2 acima) |
| Distribuir para a empresa/instituto | **C — Docker** |

---

## SOLUÇÃO DE PROBLEMAS COMUNS

**"pip não é reconhecido"**
→ Python não foi instalado com "Add to PATH". Reinstale marcando essa opção.

**"streamlit não é reconhecido"**
→ Execute: `pip install streamlit` e tente de novo.

**"ModuleNotFoundError: No module named 'folium'"**
→ Execute: `pip install folium geopandas` e tente de novo.

**O navegador não abre sozinho**
→ Abra manualmente o navegador e acesse: `http://localhost:8501`

**Mapa aparece em branco**
→ Verifique a conexão com internet (o GeoJSON dos estados vem de uma URL externa).
→ Alternativa: marque "Dados de demonstração" no app.

**Erro na hora do deploy no Streamlit Cloud**
→ Certifique que o arquivo `requirements.txt` está na pasta com o conteúdo:
```
streamlit>=1.32.0
pandas>=2.0.0
numpy>=1.26.0
requests>=2.31.0
folium>=0.15.0
geopandas>=0.14.0
```

---

*Guia para o Hackathon E+ 2026 — PID InvestMap v4*
