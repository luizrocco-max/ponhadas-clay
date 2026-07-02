"""
Ponhada's Clay League CCTSP — Ranking oficial da liga
────────────────────────────────────────────────────────────────────────────
- Admin (senha): faz upload da planilha e publica os dados
- Viewer (todos): vê o ranking dos turnos, a temporada e o Hall of Fame

Regras (Regulamento Oficial da Ponhada's Clay League CCTSP):
  • Turnos MENSAIS; conta a MAIOR pontuação de cada atirador no turno (Art. 5, 7).
  • Pontuação base = percentual de acerto = pratos ÷ pratos do líder × 100 (Art. 10).
  • Pontuação final do turno = percentual + bônus de handicap (Art. 11).
  • Handicap só para quem está < 93% do líder (Art. 14).
  • Bônus = (diferença p.p. p/ 100%) ÷ 10 × HC, onde HC=3/5/7 para 50/75/100
    pratos; a diferença usa a MÉDIA dos últimos 3 turnos do atirador (Art. 15, 17).
  • Os pratos de handicap somam ao resultado; recalcula-se o percentual (Art. 15).
  • Desempate do turno: mais postos fechados, depois último posto (Art. 22).
  • Hall of Fame / Atirador do Ano: mais vitórias; empate → mais pódios (Art. 26, 30).
"""
import base64
import json
import math
from datetime import datetime
from pathlib import Path

import pandas as pd
import plotly.graph_objects as go
import requests
import streamlit as st

# ── Paleta (tema "clay & brass") ────────────────────────────────────────────
INK      = "#12160F"
FIELD    = "#1F6F43"
FIELD_D  = "#134E31"
GOLD     = "#C9A227"
SILVER   = "#9AA0A6"
BRONZE   = "#C77B3B"
CLAY     = "#E4572E"
CREAM    = "#F6F4EC"
CARD     = "#FFFFFF"
INK_TX   = "#20241C"
MUTED    = "#6B6F63"

GITHUB_DATA_PATH = "data/ranking_data.json"
HC_POR_PRATOS = {50: 3, 75: 5, 100: 7}
LIMITE_PCT = 93.0          # >= 93% do líder não recebe handicap (Art. 14)

MESES_PT = {
    "janeiro": 1, "fevereiro": 2, "março": 3, "marco": 3, "abril": 4,
    "maio": 5, "junho": 6, "julho": 7, "agosto": 8, "setembro": 9,
    "outubro": 10, "novembro": 11, "dezembro": 12,
    "jan": 1, "fev": 2, "mar": 3, "abr": 4, "mai": 5, "jun": 6,
    "jul": 7, "ago": 8, "set": 9, "out": 10, "nov": 11, "dez": 12,
}


# ════════════════════════════════════════════════════════════════════════════
# PARSING DA PLANILHA
# ════════════════════════════════════════════════════════════════════════════
def _ordem_mes(nome_aba: str):
    txt = str(nome_aba).strip().lower().replace("-", ".").replace("_", ".").replace("/", ".")
    partes = [p for p in txt.split(".") if p]
    mes = ano = None
    for p in partes:
        if p in MESES_PT:
            mes = MESES_PT[p]
        elif p.isdigit():
            n = int(p)
            if n <= 12 and mes is None:
                mes = n
            else:
                ano = n if n > 100 else 2000 + n
    return (ano or 0, mes or 0)


def parse_planilha(xls_bytes) -> dict:
    """Lê todas as abas-mês e devolve a estrutura de dados da liga."""
    xl = pd.ExcelFile(xls_bytes)
    turnos = []

    for aba in xl.sheet_names:
        df = xl.parse(aba, header=None)
        if df.empty:
            continue

        # cabeçalho (linha com "ATIRADOR")
        header_row = None
        for i in range(min(len(df), 20)):
            linha = [str(x).strip().upper() for x in df.iloc[i].tolist()]
            if "ATIRADOR" in linha:
                header_row = i
                break
        if header_row is None:
            continue  # aba de referência (ex.: "Handicap")

        cols = [str(x).strip().upper() for x in df.iloc[header_row].tolist()]
        c_at = cols.index("ATIRADOR")
        c_tot = cols.index("TOTAL") if "TOTAL" in cols else None
        c_data = c_at - 1
        postos_idx = list(range(c_at + 1, c_tot)) if c_tot else []

        # linha de máximos por posto (logo após o cabeçalho, sem nome)
        postos_max = None
        for i in range(header_row + 1, min(header_row + 4, len(df))):
            vals = [df.iat[i, j] for j in postos_idx] if postos_idx else []
            nome_cel = df.iat[i, c_at]
            if vals and all(pd.notna(v) and isinstance(v, (int, float)) for v in vals) \
               and not isinstance(nome_cel, str):
                postos_max = [int(v) for v in vals]
                break

        # pratos do turno e HC por 10 p.p.
        pratos = hc = None
        for i in range(min(len(df), 12)):
            for j in range(df.shape[1]):
                v = df.iat[i, j]
                if isinstance(v, str) and "qtde" in v.lower():
                    seq = [df.iat[i, k] for k in range(j + 1, df.shape[1])
                           if pd.notna(df.iat[i, k]) and isinstance(df.iat[i, k], (int, float))]
                    if seq:
                        pratos = int(seq[0])
                        if len(seq) > 1:
                            hc = int(seq[1])
        if pratos is None and postos_max:
            pratos = sum(postos_max)
        pratos = pratos or 75
        hc = hc or HC_POR_PRATOS.get(pratos, 5)

        registros = []
        for i in range(header_row + 1, len(df)):
            nome = df.iat[i, c_at]
            if not isinstance(nome, str) or not nome.strip():
                continue
            tot = df.iat[i, c_tot] if c_tot is not None else None
            if pd.isna(tot):
                continue
            try:
                tot = float(tot)
            except (TypeError, ValueError):
                continue
            stations = [int(df.iat[i, j]) if pd.notna(df.iat[i, j]) else 0 for j in postos_idx]
            data_val = df.iat[i, c_data] if c_data >= 0 else None
            registros.append({
                "atirador": nome.strip().upper(),
                "total": tot,
                "stations": stations,
                "data": str(data_val)[:10] if pd.notna(data_val) else "",
            })

        if registros:
            turnos.append({
                "aba": str(aba), "ordem": _ordem_mes(aba),
                "pratos": pratos, "hc": hc, "postos_max": postos_max,
                "registros": registros,
            })

    turnos.sort(key=lambda t: t["ordem"])
    return {"gerado_em": datetime.now().strftime("%d/%m/%Y %H:%M"), "turnos": turnos}


# ════════════════════════════════════════════════════════════════════════════
# MOTOR DE CÁLCULO (fiel ao regulamento)
# ════════════════════════════════════════════════════════════════════════════
def _melhor_por_atirador(turno: dict) -> dict:
    """Melhor passada de cada atirador (maior total; desempate por postos fechados)."""
    best = {}
    pm = turno.get("postos_max")
    for r in turno["registros"]:
        pf = sum(1 for s, m in zip(r["stations"], pm) if m and s >= m) if pm else 0
        cand = {**r, "postos_fechados": pf}
        cur = best.get(r["atirador"])
        if (cur is None or cand["total"] > cur["total"]
                or (cand["total"] == cur["total"] and pf > cur["postos_fechados"])):
            best[r["atirador"]] = cand
    return best


def _pct_base(turno: dict):
    """Percentual base de cada atirador (total/líder*100) + melhores + total do líder."""
    best = _melhor_por_atirador(turno)
    lider = max((b["total"] for b in best.values()), default=0)
    pcts = {a: (b["total"] / lider * 100 if lider else 0) for a, b in best.items()}
    return pcts, best, lider


def ranking_do_turno(dados: dict, k: int) -> pd.DataFrame:
    """Ranking do turno de índice k, com handicap pela média dos últimos 3 turnos."""
    turnos = dados["turnos"]
    turno = turnos[k]
    hist_pcts = [_pct_base(t)[0] for t in turnos[:k + 1]]
    _, best_k, lider_k = _pct_base(turno)
    hc = turno["hc"]

    linhas = []
    for atir, b in best_k.items():
        historico = [pc[atir] for pc in hist_pcts if atir in pc][-3:]
        media = sum(historico) / len(historico)
        handicap = 0 if media >= LIMITE_PCT else math.floor((100 - media) / 10 * hc)
        pratos_hc = b["total"] + handicap
        pct_final = pratos_hc / lider_k * 100 if lider_k else 0
        linhas.append({
            "atirador": atir,
            "total": int(b["total"]),
            "pct_base": round(b["total"] / lider_k * 100, 2) if lider_k else 0.0,
            "media_3t": round(media, 2),
            "handicap": int(handicap),
            "pratos_hc": int(pratos_hc),
            "pct_final": round(pct_final, 2),
            "postos_fechados": int(b["postos_fechados"]),
            "ult_posto": b["stations"][-1] if b["stations"] else 0,
            "passadas": sum(1 for r in turno["registros"] if r["atirador"] == atir),
        })
    df = pd.DataFrame(linhas).sort_values(
        ["pct_final", "postos_fechados", "ult_posto"], ascending=False).reset_index(drop=True)
    df.insert(0, "col", df.index + 1)
    return df


def tabela_temporada(dados: dict) -> pd.DataFrame:
    """Vitórias e pódios por atirador (Hall of Fame — Art. 26/30)."""
    linhas = []
    for k in range(len(dados["turnos"])):
        rk = ranking_do_turno(dados, k)
        if rk.empty:
            continue
        for _, r in rk.iterrows():
            linhas.append({
                "atirador": r["atirador"],
                "turno": dados["turnos"][k]["aba"],
                "vitoria": 1 if r["col"] == 1 else 0,
                "podio": 1 if r["col"] <= 3 else 0,
                "pct_final": r["pct_final"],
            })
    if not linhas:
        return pd.DataFrame(columns=["col", "atirador", "vitorias", "podios",
                                     "participacoes", "melhor_pct"])
    df = pd.DataFrame(linhas)
    agg = (df.groupby("atirador", as_index=False)
             .agg(vitorias=("vitoria", "sum"), podios=("podio", "sum"),
                  participacoes=("turno", "nunique"), melhor_pct=("pct_final", "max")))
    agg = agg.sort_values(["vitorias", "podios", "melhor_pct"],
                          ascending=False).reset_index(drop=True)
    agg.insert(0, "col", agg.index + 1)
    return agg


# ════════════════════════════════════════════════════════════════════════════
# PERSISTÊNCIA NO GITHUB
# ════════════════════════════════════════════════════════════════════════════
def _gh_headers(token):
    return {"Authorization": f"token {token}", "Accept": "application/vnd.github+json"}


def github_load(token, repo):
    if not token or not repo:
        return None, None
    url = f"https://api.github.com/repos/{repo}/contents/{GITHUB_DATA_PATH}"
    try:
        r = requests.get(url, headers=_gh_headers(token), timeout=15)
        if r.status_code == 200:
            payload = r.json()
            conteudo = base64.b64decode(payload["content"]).decode("utf-8")
            return json.loads(conteudo), payload["sha"]
    except Exception:
        pass
    return None, None


def github_save(dados, token, repo):
    if not token or not repo:
        return False
    _, sha = github_load(token, repo)
    url = f"https://api.github.com/repos/{repo}/contents/{GITHUB_DATA_PATH}"
    conteudo = base64.b64encode(
        json.dumps(dados, ensure_ascii=False, indent=2).encode("utf-8")).decode("utf-8")
    body = {"message": f"update: ranking {dados.get('gerado_em', '')}", "content": conteudo}
    if sha:
        body["sha"] = sha
    try:
        r = requests.put(url, headers=_gh_headers(token), json=body, timeout=20)
        return r.status_code in (200, 201)
    except Exception:
        return False


def load_local():
    p = Path(__file__).parent / GITHUB_DATA_PATH
    if p.exists():
        try:
            return json.loads(p.read_text(encoding="utf-8"))
        except Exception:
            return None
    return None


# ════════════════════════════════════════════════════════════════════════════
# UI
# ════════════════════════════════════════════════════════════════════════════
def _logo_b64():
    p = Path(__file__).parent / "assets" / "logo.png"
    return base64.b64encode(p.read_bytes()).decode() if p.exists() else ""


st.set_page_config(page_title="Ponhada's Clay League CCTSP", page_icon="🎯",
                   layout="wide", initial_sidebar_state="expanded")

st.markdown(f"""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&display=swap');
html, body, [class*="css"] {{ font-family:'Inter',sans-serif; }}
.stApp {{ background:{CREAM}; }}
.main .block-container {{ padding-top:0 !important; max-width:1200px; }}
#MainMenu, footer {{ visibility:hidden; }}
.podium {{ border-radius:16px; padding:1.2rem 1rem; text-align:center; color:white;
          box-shadow:0 6px 20px rgba(0,0,0,.12); }}
.medal {{ font-size:2rem; }}
.pname {{ font-weight:700; font-size:1.02rem; margin-top:.3rem; line-height:1.2; }}
.ppts {{ font-size:1.9rem; font-weight:800; margin-top:.2rem; }}
.psub {{ font-size:.78rem; opacity:.9; }}
.card {{ background:{CARD}; border-radius:14px; padding:1rem 1.2rem;
         box-shadow:0 2px 10px rgba(0,0,0,.06); }}
</style>
""", unsafe_allow_html=True)

ADMIN_PWD    = st.secrets.get("ADMIN_PASSWORD", "")
GITHUB_TOKEN = st.secrets.get("GITHUB_TOKEN", "")
GITHUB_REPO  = st.secrets.get("GITHUB_REPO", "")

_LOGO = _logo_b64()
logo_html = (f'<img src="data:image/png;base64,{_LOGO}" style="height:46px;">' if _LOGO
             else '<span style="font-size:1.7rem;">🎯</span>')
st.markdown(f"""
<div style="background:linear-gradient(135deg,{INK} 0%,{FIELD_D} 60%,{FIELD} 100%);
     padding:1.1rem 2rem; margin:0 -4rem 1.4rem -4rem; display:flex; align-items:center; gap:1.2rem;
     box-shadow:0 3px 14px rgba(0,0,0,.25);">
  {logo_html}
  <div>
    <div style="color:white; font-size:1.35rem; font-weight:800;">Ponhada's Clay League <span style="color:{GOLD};">CCTSP</span></div>
    <div style="color:#CFE3D6; font-size:.82rem;">Ranking oficial da temporada · percentual + sistema de handicap</div>
  </div>
</div>
""", unsafe_allow_html=True)

# ── Sidebar: admin + upload ─────────────────────────────────────────────────
st.sidebar.markdown("### 🔐 Área do organizador")
senha = st.sidebar.text_input("Senha admin", type="password", placeholder="••••••••")
is_admin = bool(ADMIN_PWD) and senha == ADMIN_PWD
if senha and not is_admin:
    st.sidebar.error("Senha incorreta.")

dados = None
fonte = None
if is_admin:
    st.sidebar.success("Organizador autenticado ✓")
    up = st.sidebar.file_uploader("Planilha de resultados (.xlsx)", type=["xlsx"])
    if up is not None:
        try:
            dados = parse_planilha(up.getvalue())
            fonte = "upload"
            n_t = len(dados["turnos"])
            n_r = sum(len(t["registros"]) for t in dados["turnos"])
            st.sidebar.info(f"Lido: {n_t} turno(s), {n_r} passada(s).")
        except Exception as e:
            st.sidebar.error(f"Erro ao ler a planilha: {e}")

if dados is None:
    dados = github_load(GITHUB_TOKEN, GITHUB_REPO)[0] or load_local()
    fonte = "github"

if is_admin and fonte == "upload" and dados:
    if st.sidebar.button("💾 Salvar e publicar", type="primary", width='stretch'):
        with st.spinner("Publicando no GitHub..."):
            ok = github_save(dados, GITHUB_TOKEN, GITHUB_REPO)
        if ok:
            st.sidebar.success("Publicado! Todos já veem os dados novos.")
        elif not GITHUB_TOKEN:
            st.sidebar.warning("Sem GITHUB_TOKEN — os dados valem só nesta sessão.")
        else:
            st.sidebar.error("Falha ao publicar. Confira token/repo nos secrets.")

if not dados or not dados.get("turnos"):
    st.info("🎯 Aguardando o organizador publicar os resultados. Se você é o organizador, "
            "entre com a senha e suba a planilha na barra lateral.")
    st.stop()

st.caption(f"Atualizado em: **{dados.get('gerado_em', '—')}**  ·  fonte: {fonte}")

tab_turno, tab_temp, tab_atirador, tab_regras = st.tabs(
    ["🏆 Ranking do Turno", "🏛️ Temporada / Hall of Fame", "👤 Por Atirador", "📜 Regras"])

turnos = dados["turnos"]
idx_por_aba = {t["aba"]: i for i, t in enumerate(turnos)}

# ══ TAB 1 — RANKING DO TURNO ═══════════════════════════════════════════════
with tab_turno:
    nomes = [t["aba"] for t in turnos]
    sel = st.selectbox("Turno (mês)", nomes, index=len(nomes) - 1)
    k = idx_por_aba[sel]
    turno = turnos[k]
    rk = ranking_do_turno(dados, k)

    c1, c2, c3 = st.columns(3)
    c1.metric("Pratos do turno", turno["pratos"])
    c2.metric("Handicap / 10 p.p.", turno["hc"])
    c3.metric("Atiradores", len(rk))

    st.markdown("#### Pódio")
    cores = [f"linear-gradient(135deg,{GOLD},#a9861c)",
             f"linear-gradient(135deg,{SILVER},#7d8288)",
             f"linear-gradient(135deg,{BRONZE},#9c5f2c)"]
    medalhas = ["🥇", "🥈", "🥉"]
    cols = st.columns(3)
    for i in range(min(3, len(rk))):
        r = rk.iloc[i]
        sub = f"{int(r['total'])} pratos"
        if r["handicap"]:
            sub += f" · +{int(r['handicap'])} HC"
        with cols[i]:
            st.markdown(f"""
            <div class="podium" style="background:{cores[i]};">
              <div class="medal">{medalhas[i]}</div>
              <div class="pname">{r['atirador'].title()}</div>
              <div class="ppts">{r['pct_final']:.2f}%</div>
              <div class="psub">{sub}</div>
            </div>""", unsafe_allow_html=True)

    st.markdown("#### Pontuação final (percentual com handicap)")
    rk_plot = rk.iloc[::-1]
    fig = go.Figure()
    fig.add_bar(y=rk_plot["atirador"].str.title(), x=rk_plot["pct_base"],
                orientation="h", name="% base", marker_color=FIELD,
                text=[f"{v:.0f}%" for v in rk_plot["pct_base"]], textposition="inside")
    fig.add_bar(y=rk_plot["atirador"].str.title(),
                x=(rk_plot["pct_final"] - rk_plot["pct_base"]).round(2),
                orientation="h", name="handicap", marker_color=GOLD,
                text=[f"+{(f-b):.0f}" if h else "" for f, b, h in
                      zip(rk_plot["pct_final"], rk_plot["pct_base"], rk_plot["handicap"])],
                textposition="inside")
    fig.update_layout(barmode="stack", height=70 + 42 * len(rk),
                      plot_bgcolor="white", paper_bgcolor="white",
                      margin=dict(l=10, r=20, t=10, b=10),
                      legend=dict(orientation="h", y=1.06, x=0), font=dict(color=INK_TX))
    fig.update_xaxes(showgrid=True, gridcolor="#eee", ticksuffix="%")
    st.plotly_chart(fig, width='stretch')

    st.markdown("#### Classificação completa")
    tab = rk.rename(columns={
        "col": "Col.", "atirador": "Atirador", "total": "Pratos", "pct_base": "% base",
        "media_3t": "Média 3T", "handicap": "HC (pratos)", "pct_final": "Pontuação",
        "postos_fechados": "Postos fech."})
    tab["Atirador"] = tab["Atirador"].str.title()
    tab["% base"] = tab["% base"].map(lambda v: f"{v:.2f}%")
    tab["Média 3T"] = tab["Média 3T"].map(lambda v: f"{v:.2f}%")
    tab["Pontuação"] = tab["Pontuação"].map(lambda v: f"{v:.2f}%")
    st.dataframe(tab[["Col.", "Atirador", "Pratos", "% base", "Média 3T",
                      "HC (pratos)", "Pontuação", "Postos fech."]],
                 hide_index=True, width='stretch')
    st.caption("Pontuação = percentual com handicap (Art. 11). Handicap só para quem está "
               "< 93% do líder, calculado pela média dos últimos 3 turnos (Art. 14–17). "
               "Desempate por postos fechados (Art. 22).")

# ══ TAB 2 — TEMPORADA / HALL OF FAME ═══════════════════════════════════════
with tab_temp:
    temp = tabela_temporada(dados)
    if temp.empty:
        st.info("Sem dados suficientes para a temporada.")
    else:
        campeao = temp.iloc[0]
        st.markdown(f"""
        <div class="card" style="border-left:6px solid {GOLD}; margin-bottom:1rem;">
          <div style="font-size:.85rem; color:{MUTED};">🏛️ LÍDER DA TEMPORADA · rumo ao Hall of Fame (Atirador do Ano)</div>
          <div style="font-size:1.5rem; font-weight:800; color:{INK_TX};">
            {campeao['atirador'].title()}
            <span style="color:{GOLD};"> · {int(campeao['vitorias'])} vitória(s), {int(campeao['podios'])} pódio(s)</span>
          </div>
        </div>""", unsafe_allow_html=True)

        top = temp.iloc[::-1]
        fig2 = go.Figure()
        fig2.add_bar(y=top["atirador"].str.title(), x=top["vitorias"], orientation="h",
                     marker_color=GOLD, name="Vitórias",
                     text=top["vitorias"].astype(int), textposition="outside")
        fig2.update_layout(height=90 + 40 * len(temp), plot_bgcolor="white",
                           paper_bgcolor="white", margin=dict(l=10, r=30, t=30, b=10),
                           font=dict(color=INK_TX), title="Vitórias de turno no ano")
        fig2.update_xaxes(dtick=1, showgrid=True, gridcolor="#eee")
        st.plotly_chart(fig2, width='stretch')

        t2 = temp.rename(columns={
            "col": "Pos.", "atirador": "Atirador", "vitorias": "Vitórias",
            "podios": "Pódios", "participacoes": "Turnos", "melhor_pct": "Melhor pontuação"})
        t2["Atirador"] = t2["Atirador"].str.title()
        t2["Melhor pontuação"] = t2["Melhor pontuação"].map(lambda v: f"{v:.2f}%")
        st.dataframe(t2[["Pos.", "Atirador", "Vitórias", "Pódios", "Turnos", "Melhor pontuação"]],
                     hide_index=True, width='stretch')
        st.caption("Atirador do Ano = mais vitórias; empate → mais pódios (top 3). Art. 26 e 30.")

# ══ TAB 3 — POR ATIRADOR ═══════════════════════════════════════════════════
with tab_atirador:
    todos = sorted({r["atirador"] for t in turnos for r in t["registros"]})
    atir = st.selectbox("Atirador", [a.title() for a in todos])
    alvo = atir.upper()

    hist = []
    for k in range(len(turnos)):
        rk = ranking_do_turno(dados, k)
        linha = rk[rk["atirador"] == alvo]
        if not linha.empty:
            r = linha.iloc[0]
            hist.append({"Turno": turnos[k]["aba"], "Col.": int(r["col"]),
                         "Pratos": int(r["total"]), "% base": r["pct_base"],
                         "HC": int(r["handicap"]), "Pontuação": r["pct_final"]})
    if not hist:
        st.info("Sem registros para este atirador.")
    else:
        dfh = pd.DataFrame(hist)
        c1, c2, c3 = st.columns(3)
        c1.metric("Turnos disputados", len(dfh))
        c2.metric("Melhor colocação", int(dfh["Col."].min()))
        c3.metric("Vitórias", int((dfh["Col."] == 1).sum()))

        figh = go.Figure()
        figh.add_scatter(x=dfh["Turno"], y=dfh["Pontuação"], mode="lines+markers",
                         line=dict(color=FIELD, width=3), marker=dict(size=9, color=GOLD),
                         name="Pontuação")
        figh.update_layout(height=320, plot_bgcolor="white", paper_bgcolor="white",
                           margin=dict(l=10, r=10, t=30, b=10), font=dict(color=INK_TX),
                           title="Evolução na temporada")
        figh.update_yaxes(showgrid=True, gridcolor="#eee", ticksuffix="%")
        st.plotly_chart(figh, width='stretch')

        dfh["% base"] = dfh["% base"].map(lambda v: f"{v:.2f}%")
        dfh["Pontuação"] = dfh["Pontuação"].map(lambda v: f"{v:.2f}%")
        st.dataframe(dfh, hide_index=True, width='stretch')

# ══ TAB 4 — REGRAS ═════════════════════════════════════════════════════════
with tab_regras:
    st.markdown(f"""
### 📜 Como funciona a pontuação

- **Turnos mensais.** Vale a **maior passada** de cada atirador no mês (sem limite de tentativas).
- **Pontuação base** = percentual de acerto = `seus pratos ÷ pratos do líder × 100` (o líder faz 100%).
- **Handicap** (nivelamento): só para quem está **abaixo de 93%** do líder.
  - Bônus em pratos = `(diferença em pontos percentuais até 100%) ÷ 10 × HC`,
    com **HC = 3 / 5 / 7** para provas de **50 / 75 / 100** pratos.
  - A diferença usa a **média dos últimos 3 turnos** do atirador (1º turno = só ele; 2º = média de 2; 3º+ = média de 3).
  - Os pratos de handicap somam ao resultado e recalcula-se o percentual → **essa é a pontuação final**.
- **Desempate no turno:** mais **postos fechados** (pontuação máxima no posto); depois melhor no último posto.
- **Campeão do turno:** maior pontuação final.
- **Hall of Fame (Atirador do Ano):** quem vence **mais turnos** no ciclo; empate → mais **pódios (top 3)**.

<span style="color:{MUTED}; font-size:.85rem;">Baseado no Regulamento Oficial da Ponhada's Clay League CCTSP.</span>
""", unsafe_allow_html=True)
