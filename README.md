# 🎯 Ponhada's Clay League CCTSP — Ranking oficial

Dashboard **estático** do ranking da liga, publicado no **GitHub Pages**.
Qualquer pessoa com o link vê o ranking do turno, a temporada e o Hall of Fame —
de qualquer celular ou computador, sem instalar nada. O **organizador** sobe a
planilha e publica direto pelo próprio site.

É um único arquivo (`index.html`) com HTML + CSS + JavaScript: o cálculo do
ranking roda no navegador, então não precisa de servidor.

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

## 📋 Publicar no GitHub Pages (uma vez só)

1. Suba os arquivos deste repositório para o GitHub (branch `main`).
2. No repositório, vá em **Settings → Pages**.
3. Em **Source**, escolha **Deploy from a branch** → Branch **`main`** / pasta **`/ (root)`** → **Save**.
4. Em ~1 min o GitHub gera a URL pública, ex.:
   `https://SEU-USUARIO.github.io/ponhadas-clay/`.

### Domínio próprio (opcional)

Ainda em **Settings → Pages → Custom domain**, digite `ponhadasclay.com.br` e
salve. Depois, no seu registrador, aponte o DNS para o GitHub Pages:

- Um registro **CNAME** de `www` → `SEU-USUARIO.github.io`, **ou**
- Registros **A** do apex para os IPs do GitHub Pages
  (`185.199.108.153`, `185.199.109.153`, `185.199.110.153`, `185.199.111.153`).

O GitHub cria e mantém o certificado HTTPS automaticamente.

---

## 🔄 Atualizar o ranking (toda semana/mês)

1. Abra a URL do site.
2. Clique no botão **⚙️** (canto inferior direito) → **Área do organizador**.
3. **Suba a planilha** `.xlsx` atualizada e clique em **Processar planilha**
   (o ranking já atualiza na sua tela).
4. Para publicar **para todos**, cole um **GitHub token** e clique em
   **💾 Publicar no GitHub**. Em ~1 min o Pages reflete os números novos.

Cada **aba da planilha é um turno mensal** (ex.: `julho.26`, `agosto.26`). É só
ir adicionando abas conforme a temporada avança.

### Criar o token do GitHub (para publicar)

1. **https://github.com/settings/tokens?type=beta** → *Generate new token (fine-grained)*.
2. **Repository access:** *Only select repositories* → escolha `ponhadas-clay`.
3. **Permissions → Repository → Contents:** **Read and write**.
4. Gere e copie o token — você o cola no campo da área do organizador na hora de publicar.

> O token **não** fica salvo no site: vive só no seu navegador, durante a publicação.
> Sem token, o upload vale só na sua sessão (não publica pra todos).

---

## 🖥️ Testar no seu computador (opcional)

Como o site lê `data/ranking_data.json` via `fetch`, abra por um servidor local
(não por `file://`):

```bash
python3 -m http.server 8000
# depois acesse http://localhost:8000
```

---

## Estrutura

```
index.html               # o app inteiro (interface + cálculo do ranking, em JS)
data/ranking_data.json   # dados publicados (gerados pelo upload da planilha)
.nojekyll                # serve o site sem processamento Jekyll
.gitignore               # ignora planilhas locais e arquivos temporários
```
