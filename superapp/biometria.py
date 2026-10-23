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

import asyncio
import base64
import io
import math
import os
import threading
import wave

import streamlit as st

VOZ_NEURAL = "pt-BR-FranciscaNeural"  # voz feminina neural, suave (serviço de leitura do Microsoft Edge)
_TTS_CACHE: dict[str, str] = {}


def _wav_teste(texto: str) -> str:
    """Áudio curto de teste (SA_TTS_FAKE=1), para validar o fluxo sem acesso ao serviço de voz."""
    buf = io.BytesIO()
    with wave.open(buf, "wb") as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(16000)
        n = int(16000 * 0.25)
        w.writeframes(b"".join(int(3000 * math.sin(2 * math.pi * 440 * k / 16000)).to_bytes(2, "little", signed=True)
                               for k in range(n)))
    return base64.b64encode(buf.getvalue()).decode()


def voz_neural(texto: str) -> str | None:
    """MP3 (base64) da frase na voz neural; None se o serviço não responder (o app usa a voz do aparelho)."""
    if texto in _TTS_CACHE:
        return _TTS_CACHE[texto]
    if os.environ.get("SA_TTS_FAKE"):
        return _wav_teste(texto)
    try:
        import edge_tts

        async def _gerar() -> bytes:
            com = edge_tts.Communicate(texto, VOZ_NEURAL, rate="-4%", pitch="+0Hz")
            out = bytearray()
            async for ch in com.stream():
                if ch["type"] == "audio":
                    out.extend(ch["data"])
            return bytes(out)

        resultado: dict = {}

        def _rodar():
            try:
                resultado["audio"] = asyncio.run(asyncio.wait_for(_gerar(), 8))
            except Exception as e:  # noqa: BLE001
                resultado["erro"] = e

        t = threading.Thread(target=_rodar, daemon=True)
        t.start(); t.join(9)
        audio = resultado.get("audio")
        if not audio:
            return None
        b64 = base64.b64encode(audio).decode()
        if len(_TTS_CACHE) < 400:
            _TTS_CACHE[texto] = b64
        return b64
    except Exception:  # noqa: BLE001
        return None


def _ponte_tts(res, chave: str) -> None:
    """O navegador pediu uma frase: gera a voz e devolve no próximo render do componente."""
    pedido = getattr(res, "tts", None)
    if pedido and pedido.get("texto"):
        b64 = voz_neural(str(pedido["texto"])[:600])
        st.session_state[f"_tts_{chave}"] = {"id": pedido.get("id"), "b64": b64} if b64 else {"id": pedido.get("id"), "erro": True}
        st.rerun()

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
.sa-bio.escuro { background: linear-gradient(160deg, rgba(190,200,250,0.42) 0%, rgba(128,145,222,0.32) 52%, rgba(96,112,205,0.28) 100%);
  border: 1px solid rgba(176,184,202,0.42); border-top-color: rgba(222,227,238,0.72); border-left-color: rgba(200,207,222,0.62); border-bottom-color: rgba(140,150,176,0.40);
  color: #F7F8FF; -webkit-backdrop-filter: blur(24px) saturate(150%); backdrop-filter: blur(24px) saturate(150%);
  box-shadow: inset 1px 1px 0 rgba(255,255,255,0.30), inset 0 2px 6px rgba(214,220,232,0.22), inset -1px -1px 0 rgba(110,120,150,0.30), inset 0 0 26px rgba(200,208,224,0.10), 0 16px 36px rgba(0,0,30,0.45); }
.sa-bio.escuro .sub, .sa-bio.escuro .lgpd { color: #E3E8FF !important; }
.sa-bio.escuro .mic { box-shadow: 0 0 0 6px rgba(236,112,0,0.12), 0 10px 26px rgba(236,112,0,0.45), inset 0 1px 0 rgba(255,255,255,0.35); }
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

/* botão LIA em barra (tela de entrada): mesmo tamanho do Acessar, laranja, na zona do polegar */
.sa-bio.barra, .sa-bio.escuro.barra { background: transparent !important; border: none !important; box-shadow: none !important;
  -webkit-backdrop-filter: none !important; backdrop-filter: none !important; padding: 0 !important; }
.barra .topo { flex-direction: column; align-items: stretch; gap: 8px; }
.barra .chamada { text-align: center; }
.barra .chamada b { font-size: 0.95rem; }
.barra .chamada .sub { font-size: 0.78rem; line-height: 1.35; }
.barra .mic { width: 100%; height: 58px; border-radius: 18px; font-size: 1.15rem; font-weight: 800; letter-spacing: 0.06em;
  background: linear-gradient(160deg, #FF9A3D 0%, #EC7000 45%, #C25C00 100%);
  border: 1px solid rgba(255,214,176,0.55); border-top-color: rgba(255,236,220,0.85); border-bottom-color: rgba(150,70,0,0.6);
  box-shadow: inset 1px 1px 0 rgba(255,255,255,0.35), inset -1px -1px 0 rgba(120,50,0,0.35), 0 12px 28px rgba(236,112,0,0.45), 0 0 26px rgba(255,140,40,0.25) !important; }
.barra .mic.ativo { animation: pulsaBarra 1.2s ease-in-out infinite; }
@keyframes pulsaBarra { 50% { box-shadow: 0 0 0 8px rgba(236,112,0,0.18), 0 12px 28px rgba(236,112,0,0.45); } }
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

// senha falada: "um dois três quatro" ou "1234" → "1234"
const DIG = {zero:"0",um:"1",uma:"1",dois:"2",duas:"2",tres:"3",quatro:"4",cinco:"5",seis:"6",meia:"6",sete:"7",oito:"8",nove:"9"};
function digitos(t) {
  let s = "";
  for (const w of norm(t).split(/(\d)|[^a-z0-9]+/).filter(Boolean)) { if (/^\d$/.test(w)) s += w; else if (DIG[w]) s += DIG[w]; }
  return s;
}

// voz da Lia: a voz feminina mais natural disponível no aparelho (as listas mudam por sistema)
const VOZES_FEMININAS = [
  /francisca.*(natural|online|neural)/i, /thalita.*(natural|online|neural)/i, /(natural|neural).*(francisca|thalita|brenda|elza|giovanna|leila|leticia|manuela|yara)/i,
  /luciana.*(premium|aprimorad|melhorad|enhanced)/i, /google portugu[eê]s do brasil/i, /luciana/i, /francisca/i, /thalita/i,
  /maria/i, /vit[oó]ria/i, /fernanda/i, /raquel/i, /joana/i, /catarina/i, /female|feminin|mulher/i,
];
const VOZES_MASCULINAS = /felipe|daniel|antonio|ant[oô]nio|ricardo|reed|eddy|rocko|grandpa|jo[aã]o|duarte|humberto|fabio|f[aá]bio|julio|donato|nicolau|valerio|male\b|masculin/i;
let VOZ_LIA = null;
function escolherVoz() {
  if (!("speechSynthesis" in window)) return null;
  const pt = speechSynthesis.getVoices().filter((v) => /^pt/i.test(v.lang || ""));
  const br = pt.filter((v) => /br/i.test(v.lang)).concat(pt.filter((v) => !/br/i.test(v.lang)));
  for (const re of VOZES_FEMININAS) {
    const v = br.find((x) => re.test(x.name) && !VOZES_MASCULINAS.test(x.name));
    if (v) return v;
  }
  return br.find((x) => !VOZES_MASCULINAS.test(x.name)) || br[0] || null;
}
if ("speechSynthesis" in window) {
  VOZ_LIA = escolherVoz();
  try { speechSynthesis.addEventListener("voiceschanged", () => { VOZ_LIA = escolherVoz(); }); } catch (e) {}
}
function prepararVoz(u) {
  u.lang = "pt-BR"; u.rate = 0.97; u.pitch = 1.0;      // ritmo calmo e tom natural (pitch alto soa robótico)
  const v = VOZ_LIA || escolherVoz();
  if (v) { u.voice = v; u.lang = v.lang; }
  // sem voz feminina instalada: sobe um pouco o tom da voz padrão para não soar masculina
  if (!v || VOZES_MASCULINAS.test(v.name)) u.pitch = 1.12;
}

// voz simples (Lia): fala em pt-BR e ouve uma resposta; devolve null se o navegador não deixar
function falarNavegador(texto) {
  return new Promise((res) => {
    if (!("speechSynthesis" in window)) return res(false);
    let feito = false; const fim = (ok) => { if (!feito) { feito = true; res(ok); } };
    try {
      const u = new SpeechSynthesisUtterance(texto); prepararVoz(u);
      u.onend = () => fim(true); u.onerror = () => fim(false);
      speechSynthesis.cancel(); speechSynthesis.speak(u);
    } catch (e) { fim(false); }
    setTimeout(() => fim(true), 900 + texto.length * 70);
  });
}
// voz neural feminina (gerada no servidor) tocada pelo Web Audio; desbloqueada no primeiro toque
function audioCtx() { if (!G.ac) { const AC = window.AudioContext || window.webkitAudioContext; if (AC) G.ac = new AC(); } return G.ac; }
function desbloquearAudio() {
  const ac = audioCtx(); if (!ac) return;
  try { if (ac.state === "suspended") ac.resume();
        const b = ac.createBuffer(1, 1, 22050), src = ac.createBufferSource(); src.buffer = b; src.connect(ac.destination); src.start(0); } catch (e) {}
}
if (!G.audioLigado) { G.audioLigado = true; ["pointerdown", "touchend", "click", "keydown"].forEach((ev) => document.addEventListener(ev, desbloquearAudio, true)); }
function receberTts(raiz, data) {
  const t = data && data.tts;
  if (t && raiz.__ttsPend && raiz.__ttsPend[t.id]) { const f = raiz.__ttsPend[t.id]; delete raiz.__ttsPend[t.id]; f(t); }
}
async function tocarB64(b64) {
  const ac = audioCtx(); if (!ac) throw new Error("sem audio");
  if (ac.state === "suspended") await ac.resume();
  const bin = atob(b64), buf = new Uint8Array(bin.length);
  for (let i = 0; i < bin.length; i++) buf[i] = bin.charCodeAt(i);
  const audio = await ac.decodeAudioData(buf.buffer);
  return new Promise((res) => {
    const src = ac.createBufferSource(); src.buffer = audio;
    const ganho = ac.createGain(); ganho.gain.value = 0.95; src.connect(ganho); ganho.connect(ac.destination);
    let feito = false; const fim = () => { if (!feito) { feito = true; res(); } };
    src.onended = fim; src.start(0); setTimeout(fim, audio.duration * 1000 + 600);
  });
}
async function falarLia(texto, raiz) {
  if (raiz && raiz.__set && !G.ttsOff) {
    raiz.__ttsPend = raiz.__ttsPend || {};
    const id = "t" + Date.now() + Math.floor(Math.random() * 1000);
    const r = await new Promise((res) => { raiz.__ttsPend[id] = res; setTimeout(() => res(null), 6000); raiz.__set("tts", { id, texto }); });
    if (r && r.b64) { try { await tocarB64(r.b64); return true; } catch (e) {} }
    if (r && r.erro) G.ttsOff = true;        // servidor sem voz neural: usa a do aparelho daqui em diante
  }
  return falarNavegador(texto);
}
function ouvirLia(ms = 7000, aoParcial) {
  return new Promise((res) => {
    const SR = window.SpeechRecognition || window.webkitSpeechRecognition;
    if (!SR) return res(null);
    let final = "", parcial = "", feito = false;
    const r = new SR(); r.lang = "pt-BR"; r.interimResults = true; r.maxAlternatives = 1;
    const fim = () => { if (feito) return; feito = true; try { r.stop(); } catch (e) {} res((final || parcial).trim() || null); };
    r.onresult = (e) => { let t = ""; for (const x of e.results) t += x[0].transcript; parcial = t; aoParcial && aoParcial(t);
      if (e.results[e.results.length - 1].isFinal) final = t; };
    r.onerror = () => fim(); r.onend = () => fim();
    setTimeout(fim, ms);
    try { r.start(); } catch (e) { fim(); }
  });
}
"""

# ------------------------------------------------------------------------------- portão (menus)
HTML_PORTAO = """
<div class="sa-bio">
  <div class="cam"><video playsinline muted></video><div class="anel"></div><div class="icone escondido"></div></div>
  <div class="titulo">Olhe para a câmera</div>
  <div class="sub">Confirmando que é você para <span class="verbo">abrir</span> <b class="tela"></b>…</div>
  <div class="pedido escondido">
    <div class="senha"><input type="password" inputmode="numeric" maxlength="4" placeholder="••••" autocomplete="off">
      <button class="entrar">Entrar</button></div>
    <button class="sec falar-senha" style="margin-top:8px">🎤 Falar a senha</button>
    <div class="ouvindo sub"></div>
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
  raiz.__set = setTriggerValue; receberTts(raiz, data);
  if (raiz.__iniciado) return;
  raiz.__iniciado = true;
  if (data.tema === "escuro") $(".sa-bio").classList.add("escuro");
  carregarDetector();
  $(".tela").textContent = data.rotulo || data.tela;
  if (data.verbo) $(".verbo").textContent = data.verbo;
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
      sub.textContent = r.motivo === "camera" ? "Câmera indisponível ou sem permissão. Diga ou digite sua senha de acesso."
                                              : "Diga ou digite sua senha de acesso para continuar.";
      sub.innerHTML += ` <span style="color:#7A8391">(protótipo: ${data.senha})</span>`;
      pedido.classList.remove("escondido"); campo.value = ""; erro.textContent = "";
      // sem rosto (dirigindo, celular na mochila…): a Lia fala e ouve a senha; o campo continua valendo
      await falarLia("Não consegui identificar seu rosto. Diga a sua senha de acesso.", raiz);
      ouvirSenha();
    }
  }
  let tentativas = 0;
  function conferir(valor, origem) {
    if (digitos(valor) === data.senha) {
      setTriggerValue("liberado", { tela: data.tela, metodo: origem === "voz" ? "senha_voz" : "senha" });
      return true;
    }
    tentativas++;
    erro.textContent = "Senha incorreta. Tente de novo.";
    campo.value = "";
    if (origem === "voz" && tentativas < 2) falarLia("Senha incorreta. Diga de novo, por favor.", raiz).then(ouvirSenha);
    return false;
  }
  async function ouvirSenha() {
    const ouv = $(".ouvindo");
    ouv.textContent = "🎤 Ouvindo a senha…";
    const t = await ouvirLia(7000, () => { ouv.textContent = "🎤 ••••"; });
    ouv.textContent = t ? "" : "Não ouvi. Toque em “Falar a senha” ou digite.";
    if (t) conferir(t, "voz");
  }
  function entrar() { conferir(campo.value, "texto"); campo.focus(); }
  $(".falar-senha").onclick = () => { tentativas = 0; ouvirSenha(); };
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
      <div class="sub">Sem senha: “quando vence a fatura?”. Com rosto: “qual meu saldo?”, “pagar o piscineiro 300 reais”.</div></div>
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
const SINONIMOS = {luz:"enel",energia:"enel",internet:"vivo",fibra:"vivo",condominio:"condominio",academia:"academia",ipva:"ipva"};
const SIM = /\b(ok|okay|okey|oquei|seguir|segue|sigo|siga|confirm\w*|sim|pode|manda|vai|isso)\b/;
const NAO = /\b(nao|cancel\w*|pare|para tudo|desist\w*)\b/;
const TRANSACAO = /\b(pag\w*|pix|manda\w*|mande|transf\w*|envi\w*|deposit\w*|quit\w*)\b/;
const ABRIR = /\b(abr\w*|mostr\w*|ver|veja|entr\w*|acess\w*)\b/;
const ABRIR_FORTE = /\b(abr\w*|entr\w*|acess\w*)\b/;
const TELAS_VOZ = [[/\bextrato\b|movimenta/, "Extrato", "o extrato"], [/\bpix\b/, "Pix", "o Pix"],
  [/\bcartao\b|\bfatura\b|virtual/, "Cartão", "o cartão"], [/\bpagamento|\bcontas?\b|boleto/, "Pagar", "os pagamentos"],
  [/invest/, "Investir", "os investimentos"], [/\bgastos?\b/, "Gastos", "os gastos"], [/inicio|\bapp\b|conta corrente|minha conta/, "Início", "a sua conta"]];

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
  raiz.__data = data; raiz.__set = setTriggerValue; receberTts(raiz, data);
  if (raiz.__iniciado) return;
  raiz.__iniciado = true;
  const $ = (s) => raiz.querySelector(s);
  const D = () => raiz.__data;
  if (data.tema === "escuro") $(".sa-bio").classList.add("escuro");
  if (data.layout === "barra") { $(".sa-bio").classList.add("barra"); $(".mic").innerHTML = "🎙️&nbsp; LIA"; }
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
    return falarLia(texto, raiz);
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

  // rosto por 3 s; sem rosto, a Lia fala e pede a senha (2 tentativas). Devolve {metodo, rosto} ou null.
  async function validar() {
    const d = D();
    ui.cam.className = "cam"; ui.icone.classList.add("escondido");
    const rosto = await verificarRosto($(".op video"), d.segundos * 1000, (s) => status(`Validando seu rosto… ${s}s`));
    if (rosto.ok) {
      ui.cam.className = "cam ok"; ui.icone.textContent = "✅"; ui.icone.classList.remove("escondido");
      status("Rosto confirmado", "ok");
      return { metodo: "rosto", rosto };
    }
    ui.cam.className = "cam falhou"; ui.icone.textContent = "🔑"; ui.icone.classList.remove("escondido");
    status("Rosto não identificado · validação por senha", "alerta");
    await falar("Não consegui identificar seu rosto. Se você estiver dirigindo ou com o celular guardado, tudo bem: diga a sua senha de acesso.");
    for (let tent = 1; tent <= 2; tent++) {
      const r = await resposta({ placeholder: `Senha (protótipo: ${d.senha})`, tipo: "password" });
      ui.voce.textContent = r.origem === "voz" ? "🎤 ••••" : "••••";
      if (NAO.test(norm(r.v))) { await falar("Tudo bem, cancelei."); return null; }
      if (digitos(r.v) === d.senha) { status("Senha confirmada", "ok"); return { metodo: "senha", rosto }; }
      if (tent === 1) await falar("Senha incorreta. Diga de novo, por favor.");
    }
    status("Senha incorreta", "alerta");
    await falar("Senha incorreta de novo. Por segurança, cancelei.");
    return null;
  }

  // consultas: livres só os lembretes (sem valores nem fornecedores); valores pedem rosto ou senha
  function consulta(cmd, d) {
    const n = norm(cmd);
    if (TRANSACAO.test(n) || ABRIR_FORTE.test(n)) return null;
    const querValor = /\b(quanto|valor|valores|total|quais|qual)\b/.test(n);
    if (/\b(saldo|quanto (eu )?tenho|quanto tem)\b/.test(n))
      return { protegido: true, assunto: "Saldo", texto: () => `Seu saldo disponível é de ${valorFalado(D().saldo)}.` };
    if (/\blimite\b/.test(n))
      return { protegido: true, assunto: "Limite do cartão", texto: () => `Você tem ${valorFalado(D().limite_disponivel)} de limite disponível no cartão.` };
    if (/\b(fatura|cartao)\b/.test(n)) {
      if (!d.fatura) return { protegido: false, texto: () => "Você não tem fatura em aberto." };
      if (/\b(quando|vence|vencimento|dia)\b/.test(n) && !/\b(quanto|valor)\b/.test(n))
        return { protegido: false, texto: () => `A fatura do cartão vence dia ${d.fatura.vencimento}.` };
      return { protegido: true, assunto: "Valor da fatura", texto: () => `Sua fatura está em ${valorFalado(D().fatura.valor)} e vence dia ${D().fatura.vencimento}.` };
    }
    if (/\b(contas|boletos?|vence|vencem|vencimentos?|pendentes?)\b|\bconta (a pagar|vencida)/.test(n)) {
      const venc = d.contas.filter((c) => c.status === "vencida").length, abertas = d.contas.length - venc;
      if (!d.contas.length) return { protegido: false, texto: () => "Você não tem contas pendentes." };
      if (querValor)
        return { protegido: true, assunto: "Contas a pagar", texto: () => "Suas contas pendentes: " + D().contas.map((c) => `${c.descricao}, ${valorFalado(c.valor)}, ${c.status === "vencida" ? "vencida" : "vence dia " + c.vencimento}`).join("; ") + "." };
      const partes = [];
      if (abertas) partes.push(`${abertas} ${abertas === 1 ? "conta a vencer" : "contas a vencer"} nos próximos dias`);
      if (venc) partes.push(`${venc} ${venc === 1 ? "já vencida" : "já vencidas"}`);
      return { protegido: false, texto: () => `Lembrete: você tem ${partes.join(" e ")}. Para ver valores, peça que eu confirmo seu rosto.` };
    }
    return null;
  }
  function telaPedida(cmd) {
    const n = norm(cmd);
    if (!ABRIR.test(n)) return null;
    for (const [re, tela, nome] of TELAS_VOZ) if (re.test(n)) return { tela, nome };
    return null;
  }

  async function fluxo() {
    if (rodando) return;
    rodando = true;
    carregarDetector();
    ui.painel.classList.remove("escondido"); ui.op.classList.add("escondido"); ui.voce.textContent = ""; ui.erro.textContent = "";
    if (raiz.querySelector(".barra")) setTimeout(() => { try { ui.painel.scrollIntoView({ behavior: "smooth", block: "nearest" }); } catch (e) {} }, 60);
    status("");
    const d = D();
    try {
      // 1) comando
      await falar(`Oi, ${d.nome}! O que você precisa?`);
      let cmd = (await resposta({ placeholder: "Ou digite: pagar o piscineiro 300 reais" })).v;
      ui.voce.textContent = "🎤 " + cmd;
      if (NAO.test(norm(cmd))) { await falar("Tudo bem, cancelei."); return fimFluxo(); }

      // consulta: lembretes respondem na hora; valores (saldo, limite, fatura, contas) pedem rosto ou senha
      const info = consulta(cmd, d);
      if (info) {
        status("");
        if (info.protegido && !d.logado) {
          ui.op.classList.remove("escondido");
          $(".f-tipo").textContent = "Consulta"; $(".f-para").textContent = info.assunto;
          $(".f-chave").textContent = "—"; $(".f-valor").textContent = "•••••";
          const v = await validar();
          if (!v) return fimFluxo();
        }
        await falar(info.texto());
        raiz.__set("consulta", { comando: cmd, protegido: !!info.protegido });
        return fimFluxo();
      }

      // "abrir o extrato", "ver meu cartão": valida o rosto e abre a tela
      const abrir = telaPedida(cmd);
      if (abrir) {
        ui.op.classList.remove("escondido");
        $(".f-tipo").textContent = "Abrir no app"; $(".f-para").textContent = abrir.nome;
        $(".f-chave").textContent = "—"; $(".f-valor").textContent = "—";
        const v = d.logado ? { metodo: "sessao" } : await validar();
        if (!v) return fimFluxo();
        await falar(`${v.metodo === "sessao" ? "Certo" : v.metodo === "senha" ? "Senha confirmada" : "Rosto confirmado"}. Abrindo ${abrir.nome}.`);
        fimFluxo();
        raiz.__set("abrir", { tela: abrir.tela, metodo: v.metodo });
        return;
      }
      if (!TRANSACAO.test(norm(cmd)) && !destinoDe(cmd, d.contatos, d.contas)) {
        await falar("Sem senha eu te lembro do vencimento da fatura e das contas a vencer. Para saldo, valores, Pix, pagamentos ou abrir o app, eu confirmo seu rosto antes.");
        return fimFluxo();
      }
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

      // 2) rosto por 3 segundos (ao mesmo tempo em que a ficha aparece); sem rosto, senha falada
      const falaDados = `${op.tipo === "conta" ? "Pagamento de " + op.nome : "Pix para " + op.nome.split(" (")[0]}, valor de ${valorFalado(op.valor)}`;
      // logado: conta a pagar segue sem nova validação; Pix sempre confirma o rosto
      const valid = (op.tipo === "conta" && d.logado) ? { metodo: "sessao", rosto: { motivo: "sessao" } } : await validar();
      if (!valid) return fimFluxo();
      const { metodo, rosto } = valid;

      // 3) confirmação com "ok" ou "seguir"
      const aviso = op.novo ? " Atenção: é um destinatário novo." : "";
      await falar(`${metodo === "sessao" ? "" : metodo === "senha" ? "Senha confirmada. " : "Rosto confirmado. "}${falaDados}.${aviso} Diga ok ou seguir para confirmar.`);
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


def portao(tela: str, rotulo: str = "", tema: str = "claro", prefixo: str = "bio", verbo: str = "abrir"):
    """Mostra a verificação de rosto. Devolve {'tela', 'metodo'} quando liberar."""
    chave = f"{prefixo}_{tela}"
    res = _portao(key=chave, data={"tela": tela, "rotulo": rotulo or tela, "tema": tema, "verbo": verbo,
                                   "senha": SENHA_ACESSO, "segundos": SEGUNDOS_ROSTO,
                                   "tts": st.session_state.get(f"_tts_{chave}")},
                  on_liberado_change=lambda: None, on_tts_change=lambda: None)
    if not res.liberado:          # a liberação vale mais que um pedido de fala no mesmo instante
        _ponte_tts(res, chave)
    return res.liberado


def lia_voz(nome: str, contatos: list[dict], contas: list[dict], saldo: float, key: str = "lia_voz",
            tema: str = "claro", chamada: str = "", dica: str = "", fatura: dict | None = None,
            limite_disponivel: float = 0.0, logado: bool = False, layout: str = "cartao"):
    """Botão LIA por voz. Consultas sem senha; transações e abrir telas com rosto (ou senha).
    Devolve o resultado do componente: .executar (operação confirmada), .abrir (tela liberada), .consulta."""
    dados = {
        "tema": tema, "chamada": chamada, "dica": dica, "logado": logado, "layout": layout,
        "nome": nome, "senha": SENHA_ACESSO, "segundos": SEGUNDOS_ROSTO, "saldo": round(float(saldo), 2),
        "contatos": [{"nome": c["nome"], "chave": c["chave"], "banco": c.get("banco", "")} for c in contatos],
        "contas": [{"descricao": c["descricao"], "valor": c["valor"], "vencimento": c["vencimento"].strftime("%d/%m"),
                    "status": c.get("status", "aberta")} for c in contas],
        "fatura": fatura, "limite_disponivel": round(float(limite_disponivel), 2),
    }
    dados["tts"] = st.session_state.get(f"_tts_{key}")
    res = _voz(key=key, data=dados, on_executar_change=lambda: None, on_abrir_change=lambda: None,
               on_consulta_change=lambda: None, on_tts_change=lambda: None)
    if not (res.executar or res.abrir or res.consulta):
        _ponte_tts(res, key)
    return res
