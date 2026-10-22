"""Biometria facial (no próprio aparelho) e Lia por voz.

Dois componentes Streamlit (st.components.v2), que rodam no navegador:

* ``portao``: ao abrir um menu protegido, liga a câmera frontal e procura um rosto por 3 segundos.
  Achou → libera a tela. Não achou (ou sem câmera) → pede a senha de acesso.
* ``lia_voz``: botão LIA. A pessoa fala o comando ("pagar o piscineiro 300 reais"); a Lia preenche
  o pagamento e, ao mesmo tempo, procura o rosto por 3 segundos. Sem rosto (dirigindo, celular na
  mochila…), a Lia fala e pede a senha de acesso por voz. Depois lê os dados, pede "ok" ou "seguir"
  e só então manda a operação para o app executar.

LGPD: a detecção roda no navegador (face-api, servido de /app/static/faceapi). Nenhuma imagem é
gravada ou enviada ao servidor. No protótipo a checagem é de presença de rosto, não de identidade;
no app real seria comparada com a biometria cadastrada.
"""
from __future__ import annotations

import streamlit as st

SENHA_ACESSO = "1234"  # senha fictícia do protótipo (mostrada na tela)
SEGUNDOS_ROSTO = 3

# --------------------------------------------------------------------------------------------- CSS
CSS = """
:host { display: block; }
* { box-sizing: border-box; font-family: inherit; }
.sa-bio { background: #F5F7FB; border: 1px solid #DCE3F0; border-radius: 16px; padding: 16px; text-align: center; color: #1F2430; }
.cam { position: relative; width: 132px; height: 132px; margin: 4px auto 10px auto; }
.cam video { width: 132px; height: 132px; object-fit: cover; border-radius: 50%; background: #00226B; transform: scaleX(-1); display: block; }
.cam .anel { position: absolute; inset: -6px; border-radius: 50%; border: 4px solid #EC7000; border-right-color: transparent;
             animation: gira 1s linear infinite; }
.cam.ok .anel { border-color: #1B8A4A; animation: none; }
.cam.falhou .anel { border-color: #8A8F98; animation: none; }
.cam .icone { position: absolute; inset: 0; display: flex; align-items: center; justify-content: center; font-size: 44px; }
@keyframes gira { to { transform: rotate(360deg); } }
.titulo { font-weight: 700; color: #00226B; font-size: 1.02rem; }
.sub { color: #5B6472; font-size: 0.86rem; margin-top: 2px; }
.lgpd { color: #7A8391; font-size: 0.72rem; margin-top: 10px; line-height: 1.35; }
.senha { display: flex; gap: 8px; justify-content: center; margin-top: 12px; }
input { font-size: 1rem; padding: 9px 12px; border: 1.5px solid #B9C3D6; border-radius: 12px; width: 100%; outline: none; background: white; }
input:focus { border-color: #EC7000; }
.senha input { width: 120px; text-align: center; letter-spacing: 0.4em; }
button { font-size: 0.92rem; font-weight: 700; border-radius: 999px; padding: 9px 18px; cursor: pointer; border: 1.5px solid #EC7000;
         background: #EC7000; color: white; white-space: nowrap; }
button.sec { background: white; color: #00226B; border-color: #B9C3D6; }
button:disabled { opacity: 0.5; }
.erro { color: #C62828; font-size: 0.84rem; margin-top: 6px; min-height: 1em; }
.escondido { display: none !important; }

/* Lia por voz */
.lia { text-align: left; }
.lia .topo { display: flex; align-items: center; gap: 12px; }
.lia .mic { width: 64px; height: 64px; border-radius: 50%; padding: 0; font-size: 0.95rem; letter-spacing: 0.04em;
            background: linear-gradient(135deg, #EC7000, #C25C00); box-shadow: 0 6px 16px rgba(236,112,0,0.35); flex-shrink: 0; }
.lia .mic.ativo { animation: pulsa 1.2s ease-in-out infinite; }
@keyframes pulsa { 50% { box-shadow: 0 0 0 10px rgba(236,112,0,0.15); } }
.lia .chamada b { color: #00226B; }
.lia .chamada .sub { margin: 0; }
.balao { background: white; border: 1px solid #DCE3F0; border-radius: 14px 14px 14px 4px; padding: 9px 12px; margin-top: 12px;
         font-size: 0.92rem; color: #1F2430; }
.balao .quem { font-size: 0.72rem; font-weight: 700; color: #EC7000; text-transform: uppercase; letter-spacing: 0.06em; }
.voce { background: #00226B; color: white; border-radius: 14px 14px 4px 14px; padding: 8px 12px; margin: 10px 0 0 auto;
        width: fit-content; max-width: 90%; font-size: 0.9rem; }
.voce:empty { display: none; }
.op { display: flex; gap: 12px; align-items: center; margin-top: 12px; }
.op .cam { width: 76px; height: 76px; margin: 0; flex-shrink: 0; }
.op .cam video { width: 76px; height: 76px; }
.op .cam .icone { font-size: 28px; }
.ficha { flex: 1; background: white; border: 1px solid #E6E8EE; border-left: 5px solid #EC7000; border-radius: 12px; padding: 8px 12px; min-width: 0; }
.ficha .linha { display: flex; justify-content: space-between; gap: 8px; font-size: 0.84rem; padding: 2px 0; }
.ficha .linha span { color: #7A8391; }
.ficha .linha b { color: #00226B; text-align: right; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.ficha .linha.valor b { font-size: 1.05rem; }
.status { font-size: 0.8rem; color: #5B6472; margin-top: 6px; }
.status.ok { color: #1B8A4A; font-weight: 700; }
.status.alerta { color: #C25C00; font-weight: 700; }
.entrada { display: flex; gap: 8px; margin-top: 10px; align-items: center; }
.entrada button.falar { padding: 9px 12px; }
.botoes { display: flex; gap: 8px; margin-top: 10px; }
.botoes button { flex: 1; }

/* tema escuro (tela de entrada, antes do login) */
.sa-bio.escuro { background: rgba(255,255,255,0.06); border-color: rgba(255,255,255,0.14); color: #F2F4F8; }
.sa-bio.escuro .titulo, .sa-bio.escuro .chamada b { color: white; }
.sa-bio.escuro .sub, .sa-bio.escuro .lgpd { color: #B8C0D4; }
.sa-bio.escuro .balao { background: rgba(255,255,255,0.08); border-color: rgba(255,255,255,0.16); color: white; }
.sa-bio.escuro .voce { background: #EC7000; }
.sa-bio.escuro .ficha { background: rgba(255,255,255,0.08); border-color: rgba(255,255,255,0.16); }
.sa-bio.escuro .ficha .linha span { color: #B8C0D4; }
.sa-bio.escuro .ficha .linha b { color: white; }
.sa-bio.escuro .status { color: #B8C0D4; }
.sa-bio.escuro .status.ok { color: #5FD08E; }
.sa-bio.escuro .status.alerta { color: #FFB066; }
.sa-bio.escuro button.sec { background: transparent; color: white; border-color: rgba(255,255,255,0.4); }
.sa-bio.escuro input { background: rgba(255,255,255,0.95); }
"""

# ---------------------------------------------------------------------------------- JS comum
JS_COMUM = r"""
const G = (window.__saBio = window.__saBio || {});
const norm = (t) => (t || "").toLowerCase().normalize("NFD").replace(/[̀-ͯ]/g, "");
const espera = (ms) => new Promise((r) => setTimeout(r, ms));
const brl = (v) => "R$ " + Number(v).toLocaleString("pt-BR", { minimumFractionDigits: 2, maximumFractionDigits: 2 });

// detector de rosto (face-api, carregado uma vez por página, a partir de /app/static)
function carregarDetector() {
  if (!G.det) {
    G.det = (async () => {
      const base = new URL("app/static/faceapi/", document.baseURI).href;
      const src = await (await fetch(base + "face-api.esm.js")).text();
      const url = URL.createObjectURL(new Blob([src], { type: "text/javascript" }));
      const fa = await import(url);
      // WebGL (rápido, celulares) com CPU de reserva; o backend wasm exigiria servir arquivos .wasm
      for (const be of ["webgl", "cpu"]) { try { if (await fa.tf.setBackend(be)) break; } catch (e) {} }
      await fa.tf.ready();
      await fa.nets.tinyFaceDetector.loadFromUri(base + "model");
      return fa;
    })().catch((e) => { G.det = null; G.detErro = String(e); return null; });
  }
  return G.det;
}

// liga a câmera frontal e procura um rosto por `ms`; nada é gravado nem enviado
async function verificarRosto(video, ms, aoContar) {
  if (window.__saRostoTeste !== undefined) {           // gancho de teste automatizado
    await espera(400); return { ok: !!window.__saRostoTeste, motivo: "teste" };
  }
  let stream = null;
  try {
    stream = await navigator.mediaDevices.getUserMedia({ video: { facingMode: "user", width: { ideal: 320 }, height: { ideal: 240 } }, audio: false });
  } catch (e) { await espera(ms); return { ok: false, motivo: "camera" }; }
  video.muted = true; video.setAttribute("playsinline", ""); video.srcObject = stream;
  try { await video.play(); } catch (e) {}
  for (let i = 0; i < 30 && video.readyState < 2; i++) await espera(100);
  const fa = await Promise.race([carregarDetector(), espera(8000).then(() => null)]);
  const fim = Date.now() + ms;
  let ok = false;
  while (Date.now() < fim) {
    aoContar && aoContar(Math.ceil((fim - Date.now()) / 1000));
    if (fa) {
      try {
        const d = await fa.detectSingleFace(video, new fa.TinyFaceDetectorOptions({ inputSize: 224, scoreThreshold: 0.5 }));
        if (d) { ok = true; break; }
      } catch (e) {}
    }
    await espera(150);
  }
  stream.getTracks().forEach((t) => t.stop());
  video.srcObject = null;
  return { ok, motivo: ok ? "rosto" : (fa ? "sem_rosto" : "detector") };
}
"""

# ------------------------------------------------------------------------------- portão (menus)
HTML_PORTAO = """
<div class="sa-bio">
  <div class="cam"><video playsinline muted></video><div class="anel"></div><div class="icone escondido"></div></div>
  <div class="titulo">Olhe para a câmera</div>
  <div class="sub">Confirmando que é você para abrir <b class="tela"></b>…</div>
  <div class="pedido escondido">
    <div class="senha"><input type="password" inputmode="numeric" maxlength="4" placeholder="••••" autocomplete="off">
      <button class="entrar">Entrar</button></div>
    <div class="erro"></div>
    <button class="sec repetir" style="margin-top:6px">Tentar o rosto de novo</button>
  </div>
  <div class="lgpd">🔒 A verificação roda só no seu aparelho: nenhuma imagem é gravada ou enviada (LGPD).<br>
    Protótipo: detecta um rosto diante da câmera; o app real compararia com a sua biometria cadastrada.</div>
</div>
"""

JS_PORTAO = JS_COMUM + r"""
export default function (component) {
  const { parentElement: raiz, data, setTriggerValue } = component;
  const $ = (s) => raiz.querySelector(s);
  if (raiz.__iniciado) return;
  raiz.__iniciado = true;
  if (data.tema === "escuro") $(".sa-bio").classList.add("escuro");
  carregarDetector();
  $(".tela").textContent = data.rotulo || data.tela;
  const cam = $(".cam"), icone = $(".icone"), titulo = $(".titulo"), sub = $(".sub");
  const pedido = $(".pedido"), campo = $("input"), erro = $(".erro");

  async function escanear() {
    pedido.classList.add("escondido"); cam.className = "cam"; icone.classList.add("escondido");
    titulo.textContent = "Olhe para a câmera";
    const r = await verificarRosto($("video"), data.segundos * 1000,
      (s) => { sub.innerHTML = `Verificando seu rosto… <b>${s}s</b>`; });
    if (r.ok) {
      cam.className = "cam ok"; icone.textContent = "✅"; icone.classList.remove("escondido");
      titulo.textContent = "Rosto confirmado"; sub.textContent = "Abrindo…";
      await espera(450);
      setTriggerValue("liberado", { tela: data.tela, metodo: "rosto" });
    } else {
      cam.className = "cam falhou"; icone.textContent = "🔑"; icone.classList.remove("escondido");
      titulo.textContent = "Não reconhecemos seu rosto";
      sub.textContent = r.motivo === "camera" ? "Câmera indisponível ou sem permissão. Digite sua senha de acesso."
                                              : "Digite sua senha de acesso para continuar.";
      sub.innerHTML += ` <span style="color:#7A8391">(protótipo: ${data.senha})</span>`;
      pedido.classList.remove("escondido"); campo.value = ""; erro.textContent = ""; campo.focus();
    }
  }
  function entrar() {
    if (campo.value === data.senha) setTriggerValue("liberado", { tela: data.tela, metodo: "senha" });
    else { erro.textContent = "Senha incorreta. Tente de novo."; campo.value = ""; campo.focus(); }
  }
  $(".entrar").onclick = entrar;
  campo.onkeydown = (e) => { if (e.key === "Enter") entrar(); };
  $(".repetir").onclick = escanear;
  escanear();
}
"""

# ------------------------------------------------------------------------------------- Lia voz
HTML_VOZ = """
<div class="sa-bio lia">
  <div class="topo">
    <button class="mic" title="Falar com a Lia">🎙️<br>LIA</button>
    <div class="chamada"><b>Toque e fale com a Lia</b>
      <div class="sub">Ex.: “pagar o piscineiro 300 reais”, “pagar a conta de luz”</div></div>
  </div>
  <div class="painel escondido">
    <div class="balao"><div class="quem">Lia</div><div class="fala"></div></div>
    <div class="voce"></div>
    <div class="op escondido">
      <div class="cam"><video playsinline muted></video><div class="anel"></div><div class="icone escondido"></div></div>
      <div class="ficha">
        <div class="linha"><span>Operação</span><b class="f-tipo">—</b></div>
        <div class="linha"><span>Para</span><b class="f-para">—</b></div>
        <div class="linha"><span>Chave</span><b class="f-chave">—</b></div>
        <div class="linha valor"><span>Valor</span><b class="f-valor">—</b></div>
        <div class="status"></div>
      </div>
    </div>
    <div class="entrada escondido"><input autocomplete="off"><button class="falar sec" title="Responder por voz">🎤</button><button class="enviar">OK</button></div>
    <div class="botoes escondido"><button class="confirmar">Confirmar</button><button class="sec cancelar">Cancelar</button></div>
    <div class="erro"></div>
  </div>
</div>
"""

JS_VOZ = JS_COMUM + r"""
const NUM = {zero:0,um:1,uma:1,dois:2,duas:2,tres:3,quatro:4,cinco:5,seis:6,sete:7,oito:8,nove:9,dez:10,onze:11,doze:12,
  treze:13,quatorze:14,catorze:14,quinze:15,dezesseis:16,dezessete:17,dezoito:18,dezenove:19,vinte:20,trinta:30,quarenta:40,
  cinquenta:50,sessenta:60,setenta:70,oitenta:80,noventa:90,cem:100,cento:100,duzentos:200,duzentas:200,trezentos:300,
  trezentas:300,quatrocentos:400,quinhentos:500,seiscentos:600,setecentos:700,oitocentos:800,novecentos:900};
const DIG = {zero:"0",um:"1",uma:"1",dois:"2",duas:"2",tres:"3",quatro:"4",cinco:"5",seis:"6",meia:"6",sete:"7",oito:"8",nove:"9"};
const SINONIMOS = {luz:"enel",energia:"enel",internet:"vivo",fibra:"vivo",condominio:"condominio",academia:"academia",ipva:"ipva"};
const SIM = /\b(ok|okay|okey|oquei|seguir|segue|sigo|siga|confirm\w*|sim|pode|manda|vai|isso)\b/;
const NAO = /\b(nao|cancel\w*|pare|para tudo|desist\w*)\b/;

function valorDe(t) {
  const n = norm(t);
  const m = n.match(/(\d{1,3}(?:\.\d{3})+|\d+)(?:,(\d{1,2}))?/);
  if (m) return parseFloat(m[1].replace(/\./g, "") + "." + (m[2] || "0"));
  let melhor = null, tot = 0, cur = 0, emNumero = false;
  const fecha = () => { if (emNumero) { const v = tot + cur; if (melhor === null || v > melhor) melhor = v; } tot = 0; cur = 0; emNumero = false; };
  for (const w of n.split(/[^a-z]+/)) {
    if (w in NUM) { cur += NUM[w]; emNumero = true; }
    else if (w === "mil") { tot += (cur || 1) * 1000; cur = 0; emNumero = true; }
    else if (w === "e" && emNumero) { /* "trezentos e cinquenta" */ }
    else fecha();
  }
  fecha();
  return melhor;
}
function digitos(t) {
  let s = "";
  for (const w of norm(t).split(/(\d)|[^a-z0-9]+/).filter(Boolean)) { if (/^\d$/.test(w)) s += w; else if (DIG[w]) s += DIG[w]; }
  return s;
}
// valor para a Lia falar: "300 reais", "119 reais e 90 centavos"
function valorFalado(v) {
  const r = Math.floor(v), c = Math.round((v - r) * 100);
  return r.toLocaleString("pt-BR") + (r === 1 ? " real" : " reais") + (c ? ` e ${c} centavos` : "");
}
const cap = (s) => s.replace(/\b\w/g, (c) => c.toUpperCase());
function destinoDe(t, contatos, contas) {
  const n = " " + norm(t) + " ";
  for (const c of contas) {
    const p = norm(c.descricao).split(/[^a-z0-9]+/)[0];
    if (p.length >= 3 && n.includes(" " + p)) return { tipo: "conta", conta: c };
  }
  for (const [k, v] of Object.entries(SINONIMOS)) {
    if (n.includes(" " + k + " ")) { const c = contas.find((c) => norm(c.descricao).includes(v)); if (c) return { tipo: "conta", conta: c }; }
  }
  for (const ct of contatos) {
    const toks = norm(ct.nome).replace(/\(.*?\)/g, " ").split(/[^a-z0-9]+/).filter((w) => w.length >= 3);
    const extras = norm((ct.nome.match(/\((.*?)\)/) || ["", ""])[1]).split(/[^a-z0-9]+/).filter((w) => w.length >= 4 && w !== "seu" && w !== "dona");
    if (toks.concat(extras).some((w) => n.includes(" " + w))) return { tipo: "pix", contato: ct };
  }
  const m = norm(t).match(/\b(?:para|pra|pro|ao|a|o)\s+([a-z]+(?:\s+[a-z]+)?)/);
  const ign = /^(conta|valor|pix|de|reais|um|uma)$/;
  if (m && !ign.test(m[1].split(" ")[0])) {
    const nome = m[1].split(/\s+/).filter((w) => !ign.test(w) && !(w in NUM)).join(" ");
    if (nome) return { tipo: "pix", contato: { nome: cap(nome), chave: "nova chave — confirmar", banco: "", novo: true } };
  }
  return null;
}

export default function (component) {
  const { parentElement: raiz, data, setTriggerValue } = component;
  raiz.__data = data; raiz.__set = setTriggerValue;
  if (raiz.__iniciado) return;
  raiz.__iniciado = true;
  const $ = (s) => raiz.querySelector(s);
  const D = () => raiz.__data;
  if (data.tema === "escuro") $(".sa-bio").classList.add("escuro");
  if (data.chamada) $(".chamada b").textContent = data.chamada;
  if (data.dica) $(".chamada .sub").textContent = data.dica;
  const SR = window.SpeechRecognition || window.webkitSpeechRecognition;
  const ui = {
    painel: $(".painel"), fala: $(".fala"), voce: $(".voce"), op: $(".op"), cam: $(".op .cam"), icone: $(".op .icone"),
    status: $(".status"), entrada: $(".entrada"), campo: $(".entrada input"), botoes: $(".botoes"), erro: $(".erro"), mic: $(".mic"),
  };
  let rodando = false;

  function falar(texto) {
    ui.fala.textContent = texto;
    return new Promise((res) => {
      if (!("speechSynthesis" in window)) return res();
      let feito = false; const fim = () => { if (!feito) { feito = true; res(); } };
      try {
        const u = new SpeechSynthesisUtterance(texto); u.lang = "pt-BR"; u.rate = 1.05;
        const voz = speechSynthesis.getVoices().find((v) => (v.lang || "").toLowerCase().startsWith("pt"));
        if (voz) u.voice = voz;
        u.onend = fim; u.onerror = fim;
        speechSynthesis.cancel(); speechSynthesis.speak(u);
      } catch (e) { fim(); }
      setTimeout(fim, 900 + texto.length * 70);
    });
  }
  function ouvir(ms = 7000) {
    return new Promise((res) => {
      if (!SR) return res(null);
      let final = "", parcial = "", feito = false;
      const r = new SR(); r.lang = "pt-BR"; r.interimResults = true; r.maxAlternatives = 1;
      const fim = () => { if (feito) return; feito = true; ui.mic.classList.remove("ativo"); try { r.stop(); } catch (e) {} res((final || parcial).trim() || null); };
      r.onresult = (e) => {
        let t = ""; for (const x of e.results) t += x[0].transcript;
        parcial = t; ui.voce.textContent = "🎤 " + t;
        if (e.results[e.results.length - 1].isFinal) final = t;
      };
      r.onerror = () => fim(); r.onend = () => fim();
      setTimeout(fim, ms);
      try { r.start(); ui.mic.classList.add("ativo"); } catch (e) { fim(); }
    });
  }
  // espera a resposta por voz OU pelo campo/botões (o que vier primeiro)
  function resposta({ placeholder = "", tipo = "text", botoes = false } = {}) {
    return new Promise((res) => {
      let feito = false;
      const entregar = (v, origem) => { if (feito || !v) return; feito = true; ui.entrada.classList.add("escondido"); ui.botoes.classList.add("escondido"); res({ v, origem }); };
      ui.campo.value = ""; ui.campo.type = tipo; ui.campo.placeholder = placeholder;
      ui.campo.inputMode = tipo === "password" ? "numeric" : "text";
      ui.entrada.classList.remove("escondido");
      ui.botoes.classList.toggle("escondido", !botoes);
      $(".enviar").onclick = () => entregar(ui.campo.value.trim(), "texto");
      ui.campo.onkeydown = (e) => { if (e.key === "Enter") entregar(ui.campo.value.trim(), "texto"); };
      $(".falar").onclick = () => ouvir().then((t) => entregar(t, "voz"));
      $(".confirmar").onclick = () => entregar("ok", "botao");
      $(".cancelar").onclick = () => entregar("cancelar", "botao");
      ouvir().then((t) => entregar(t, "voz"));
    });
  }
  function ficha(op) {
    ui.op.classList.remove("escondido");
    $(".f-tipo").textContent = op.tipo === "conta" ? "Pagar conta" : "Pix";
    $(".f-para").textContent = op.nome;
    $(".f-chave").textContent = op.chave + (op.banco ? " · " + op.banco : "");
    $(".f-valor").textContent = op.valor ? brl(op.valor) : "—";
  }
  function status(t, cls = "") { ui.status.textContent = t; ui.status.className = "status " + cls; }
  function fimFluxo() { rodando = false; ui.mic.classList.remove("ativo"); ui.entrada.classList.add("escondido"); ui.botoes.classList.add("escondido"); }

  async function fluxo() {
    if (rodando) return;
    rodando = true;
    carregarDetector();
    ui.painel.classList.remove("escondido"); ui.op.classList.add("escondido"); ui.voce.textContent = ""; ui.erro.textContent = "";
    status("");
    const d = D();
    try {
      // 1) comando
      await falar(`Oi, ${d.nome}! O que você precisa?`);
      let cmd = (await resposta({ placeholder: "Ou digite: pagar o piscineiro 300 reais" })).v;
      ui.voce.textContent = "🎤 " + cmd;
      if (NAO.test(norm(cmd))) { await falar("Tudo bem, cancelei."); return fimFluxo(); }
      let alvo = destinoDe(cmd, d.contatos, d.contas);
      let valor = valorDe(cmd);
      if (!alvo) {
        await falar("Para quem é o pagamento?");
        const r = (await resposta({ placeholder: "Nome do contato ou conta" })).v;
        ui.voce.textContent = "🎤 " + r; cmd += " para " + r;
        alvo = destinoDe(" para " + r, d.contatos, d.contas);
        if (!valor) valor = valorDe(r);
      }
      if (!alvo) { await falar("Não encontrei esse contato. Tente de novo dizendo o nome como está nos seus favoritos."); return fimFluxo(); }
      const op = alvo.tipo === "conta"
        ? { tipo: "conta", nome: alvo.conta.descricao, chave: "Conta a pagar · vence " + alvo.conta.vencimento, banco: "", valor: alvo.conta.valor, descricao: alvo.conta.descricao }
        : { tipo: "pix", nome: alvo.contato.nome, chave: alvo.contato.chave, banco: alvo.contato.banco, valor, novo: !!alvo.contato.novo };
      ficha(op);
      if (!op.valor) {
        await falar(`Qual o valor do Pix para ${op.nome.split(" (")[0]}?`);
        const r = (await resposta({ placeholder: "Valor, ex.: 300" })).v;
        ui.voce.textContent = "🎤 " + r; op.valor = valorDe(r); cmd += " " + r; ficha(op);
        if (!op.valor) { await falar("Não entendi o valor. Vamos tentar de novo?"); return fimFluxo(); }
      }
      if (op.valor > d.saldo) { status("Saldo insuficiente", "alerta"); await falar(`Seu saldo não cobre ${brl(op.valor)}. Cancelei a operação.`); return fimFluxo(); }

      // 2) rosto por 3 segundos (ao mesmo tempo em que a ficha aparece)
      ui.cam.className = "cam"; ui.icone.classList.add("escondido");
      const falaDados = `${op.tipo === "conta" ? "Pagamento de " + op.nome : "Pix para " + op.nome.split(" (")[0]}, valor de ${valorFalado(op.valor)}`;
      const rosto = await verificarRosto($(".op video"), d.segundos * 1000, (s) => status(`Validando seu rosto… ${s}s`));
      let metodo = "rosto";
      if (rosto.ok) {
        ui.cam.className = "cam ok"; ui.icone.textContent = "✅"; ui.icone.classList.remove("escondido");
        status("Rosto confirmado", "ok");
      } else {
        ui.cam.className = "cam falhou"; ui.icone.textContent = "🔑"; ui.icone.classList.remove("escondido");
        status("Rosto não identificado · validação por senha", "alerta");
        metodo = "senha";
        await falar("Não consegui identificar seu rosto. Se você estiver dirigindo ou com o celular guardado, tudo bem: diga a sua senha de acesso.");
        let certa = false;
        for (let tent = 1; tent <= 2 && !certa; tent++) {
          const r = await resposta({ placeholder: `Senha (protótipo: ${d.senha})`, tipo: "password" });
          ui.voce.textContent = r.origem === "voz" ? "🎤 ••••" : "••••";
          if (NAO.test(norm(r.v))) { await falar("Tudo bem, cancelei."); return fimFluxo(); }
          certa = digitos(r.v) === d.senha;
          if (!certa && tent === 1) await falar("Senha incorreta. Diga de novo, por favor.");
        }
        if (!certa) { status("Senha incorreta", "alerta"); await falar("Senha incorreta de novo. Por segurança, cancelei a operação."); return fimFluxo(); }
        status("Senha confirmada", "ok");
      }

      // 3) confirmação com "ok" ou "seguir"
      const aviso = op.novo ? " Atenção: é um destinatário novo." : "";
      await falar(`${metodo === "senha" ? "Senha confirmada. " : "Rosto confirmado. "}${falaDados}.${aviso} Diga ok ou seguir para confirmar.`);
      let conf = null;
      for (let tent = 1; tent <= 2 && conf === null; tent++) {
        const rr = await resposta({ placeholder: "Diga ou digite: ok / seguir / cancelar", botoes: true });
        ui.voce.textContent = (rr.origem === "voz" ? "🎤 " : "") + rr.v;
        const r = norm(rr.v);
        if (NAO.test(r)) conf = false; else if (SIM.test(r)) conf = true;
        else if (tent === 1) await falar("Não entendi. Diga ok para confirmar ou cancelar para desistir.");
      }
      if (!conf) { status("Operação cancelada", "alerta"); await falar("Tudo bem, não fiz nada."); return fimFluxo(); }

      // 4) executa no app
      status(op.tipo === "conta" ? "Conta paga ✓" : "Pix enviado ✓", "ok");
      await falar(op.tipo === "conta" ? `Pronto! ${op.nome} paga.` : `Pronto! Pix enviado para ${op.nome.split(" (")[0]}.`);
      fimFluxo();
      raiz.__set("executar", { ...op, metodo, comando: cmd, motivo_rosto: rosto.motivo });
      setTimeout(() => { if (!rodando) ui.painel.classList.add("escondido"); }, 8000);
    } catch (e) {
      ui.erro.textContent = "Algo deu errado: " + e; fimFluxo();
    }
  }
  ui.mic.onclick = fluxo;
}
"""

_portao = st.components.v2.component("sa_portao_biometria", html=HTML_PORTAO, css=CSS, js=JS_PORTAO)
_voz = st.components.v2.component("sa_lia_voz", html=HTML_VOZ, css=CSS, js=JS_VOZ)


def portao(tela: str, rotulo: str = "", tema: str = "claro", prefixo: str = "bio"):
    """Mostra a verificação de rosto da tela. Devolve {'tela', 'metodo'} quando liberar."""
    res = _portao(key=f"{prefixo}_{tela}", data={"tela": tela, "rotulo": rotulo or tela, "tema": tema,
                                                 "senha": SENHA_ACESSO, "segundos": SEGUNDOS_ROSTO},
                  on_liberado_change=lambda: None)
    return res.liberado


def lia_voz(nome: str, contatos: list[dict], contas: list[dict], saldo: float, key: str = "lia_voz",
            tema: str = "claro", chamada: str = "", dica: str = ""):
    """Botão LIA por voz. Devolve a operação confirmada (dict) no rerun em que a pessoa confirmou."""
    dados = {
        "tema": tema, "chamada": chamada, "dica": dica,
        "nome": nome, "senha": SENHA_ACESSO, "segundos": SEGUNDOS_ROSTO, "saldo": round(float(saldo), 2),
        "contatos": [{"nome": c["nome"], "chave": c["chave"], "banco": c.get("banco", "")} for c in contatos],
        "contas": [{"descricao": c["descricao"], "valor": c["valor"], "vencimento": c["vencimento"].strftime("%d/%m")}
                   for c in contas],
    }
    res = _voz(key=key, data=dados, on_executar_change=lambda: None)
    return res.executar
