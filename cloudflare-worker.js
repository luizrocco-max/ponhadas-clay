/**
 * Ponhada's Clay League — Worker de publicação (Cloudflare)
 * ────────────────────────────────────────────────────────────────────────────
 * Recebe do site: { password, dados } e, se a senha bater, grava o
 * data/ranking_data.json no repositório do GitHub. O token do GitHub fica
 * escondido aqui (nunca no site).
 *
 * Variáveis (no painel do Worker → Settings → Variables and Secrets):
 *   ADMIN_PASSWORD  (Secret) — a senha única do organizador
 *   GITHUB_TOKEN    (Secret) — token fine-grained com Contents: Read and write no repo
 *   GITHUB_REPO     (Text)   — luizrocco-max/ponhadas-clay
 */

const DATA_PATH = "data/ranking_data.json";
const ALLOW_ORIGINS = [
  "https://ponhadasclay.com.br",
  "https://www.ponhadasclay.com.br",
  "https://luizrocco-max.github.io",
];

function corsHeaders(origin) {
  const allow = ALLOW_ORIGINS.includes(origin) ? origin : ALLOW_ORIGINS[0];
  return {
    "Access-Control-Allow-Origin": allow,
    "Access-Control-Allow-Methods": "POST, OPTIONS",
    "Access-Control-Allow-Headers": "Content-Type",
    "Access-Control-Max-Age": "86400",
  };
}

function json(obj, status, cors) {
  return new Response(JSON.stringify(obj), {
    status,
    headers: { "Content-Type": "application/json", ...cors },
  });
}

function b64(str) {
  const bytes = new TextEncoder().encode(str);
  let bin = "";
  for (const b of bytes) bin += String.fromCharCode(b);
  return btoa(bin);
}

export default {
  async fetch(request, env) {
    const origin = request.headers.get("Origin") || "";
    const cors = corsHeaders(origin);

    if (request.method === "OPTIONS") return new Response(null, { status: 204, headers: cors });
    if (request.method !== "POST") return json({ ok: false, error: "Método não permitido" }, 405, cors);

    let body;
    try { body = await request.json(); }
    catch (e) { return json({ ok: false, error: "JSON inválido" }, 400, cors); }

    const { password, dados } = body || {};
    if (!password || password !== env.ADMIN_PASSWORD)
      return json({ ok: false, error: "Senha incorreta" }, 401, cors);
    if (!dados || !Array.isArray(dados.turnos))
      return json({ ok: false, error: "Dados inválidos" }, 400, cors);

    const repo = env.GITHUB_REPO;
    const url = `https://api.github.com/repos/${repo}/contents/${DATA_PATH}`;
    const ghHeaders = {
      "Authorization": `token ${env.GITHUB_TOKEN}`,
      "Accept": "application/vnd.github+json",
      "User-Agent": "ponhadas-publish-worker",
    };

    // pega o sha atual do arquivo (necessário para atualizar)
    let sha = null;
    const getR = await fetch(url, { headers: ghHeaders });
    if (getR.ok) { sha = (await getR.json()).sha; }

    const putBody = {
      message: `update: ranking ${dados.gerado_em || ""}`,
      content: b64(JSON.stringify(dados, null, 2)),
    };
    if (sha) putBody.sha = sha;

    const putR = await fetch(url, {
      method: "PUT",
      headers: ghHeaders,
      body: JSON.stringify(putBody),
    });
    if (!putR.ok) {
      let msg = "";
      try { msg = (await putR.json()).message || ""; } catch (e) {}
      return json({ ok: false, error: `GitHub: ${putR.status} ${msg}` }, 502, cors);
    }
    return json({ ok: true }, 200, cors);
  },
};
