# 🎯 Ponhada's Clay League CCTSP — Ranking oficial

Dashboard interativo do ranking da liga. O **organizador** faz upload da planilha
e publica; **qualquer pessoa com o link** vê o ranking do turno, a temporada e o
Hall of Fame — de qualquer celular ou computador, sem instalar nada.

---

## Como funciona a pontuação (Regulamento Oficial)

- **Turnos mensais.** Vale a **maior passada** de cada atirador no mês.
- **Pontuação base** = `seus pratos ÷ pratos do líder × 100` (o líder faz 100%).
- **Handicap** só para quem está **abaixo de 93%** do líder:
  `bônus (pratos) = (diferença até 100% em p.p.) ÷ 10 × HC`, com **HC = 3/5/7**
  para provas de **50/75/100** pratos. A diferença usa a **média dos últimos 3
  turnos** do atirador. Os pratos de bônus somam ao resultado e recalcula-se o %.
- **Desempate no turno:** mais **postos fechados**, depois melhor no último posto.
- **Hall of Fame (Atirador do Ano):** mais **vitórias**; empate → mais **pódios**.

---

## 📋 Passo a passo para publicar (uma vez só)

### 1. Criar o repositório no GitHub
1. Acesse **https://github.com/new**
2. Nome: `ponhadas-clay` (pode ser **Private**) → **Create repository**
3. Suba **todos os arquivos desta pasta** (botão *Add file → Upload files*, ou via Git).

### 2. Publicar no Streamlit Community Cloud (grátis)
1. Acesse **https://share.streamlit.io** e entre com sua conta do GitHub.
2. **Create app → Deploy a public app from GitHub**.
3. Preencha:
   - **Repository:** `seu-usuario/ponhadas-clay`
   - **Branch:** `main`
   - **Main file path:** `ponhadas_clay.py`
4. Clique em **Advanced settings → Secrets** e cole (troque os valores):
   ```toml
   ADMIN_PASSWORD = "sua-senha-secreta"
   GITHUB_TOKEN = "ghp_xxxxxxxx"
   GITHUB_REPO  = "seu-usuario/ponhadas-clay"
   ```
5. **Deploy!** Em ~1 min você recebe a **URL pública** (ex.:
   `https://ponhadas-clay.streamlit.app`). É esse link que você compartilha.

### 3. Criar o token do GitHub (para o botão "Salvar e publicar")
1. **https://github.com/settings/tokens?type=beta** → *Generate new token (fine-grained)*.
2. **Repository access:** *Only select repositories* → escolha `ponhadas-clay`.
3. **Permissions → Repository → Contents:** **Read and write**.
4. Gere, copie o token (`ghp_...`) e cole no campo `GITHUB_TOKEN` dos Secrets.

> Sem o token, o app funciona, mas o upload vale só na sua sessão (não publica pra todos).

---

## 🔄 Para atualizar o ranking (toda semana/mês)

1. Abra a URL do app.
2. Na barra lateral, digite a **senha admin**.
3. **Suba a planilha** `.xlsx` atualizada.
4. Clique em **💾 Salvar e publicar**. Pronto — todos já veem os números novos.

Cada **aba da planilha é um turno mensal** (ex.: `julho.26`, `agosto.26`). É só ir
adicionando abas conforme a temporada avança.

---

## 🖥️ Rodar no seu computador (opcional, para testar)

```bash
pip install -r requirements.txt
# crie .streamlit/secrets.toml a partir do secrets.toml.example
streamlit run ponhadas_clay.py
```

---

## Estrutura

```
ponhadas_clay.py            # o app (interface + cálculo do ranking)
requirements.txt             # dependências
data/ranking_data.json       # dados publicados (gerados pelo upload)
.streamlit/config.toml       # tema visual
.streamlit/secrets.toml      # senhas/token (NÃO versionar — veja o .example)
```
