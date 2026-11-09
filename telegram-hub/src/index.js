// telegram-hub — stage 1: Telegram bot → Google Drive ingest (one folder: D&A)
// Cloudflare Worker (ES module). No secrets in code: all come from `env` (wrangler secret).

const TG_API = 'https://api.telegram.org';
const DRIVE_UPLOAD = 'https://www.googleapis.com/upload/drive/v3/files';
const TOKEN_URL = 'https://oauth2.googleapis.com/token';
export const MAX_BYTES = 20 * 1024 * 1024; // Bot API cloud getFile download limit

// ---------- helpers ----------
const ok = () => new Response('ok', { status: 200 });

function csvSet(v) {
  return new Set(String(v || '').split(',').map((s) => s.trim()).filter(Boolean));
}

export function isAllowed(env, chatId, fromId) {
  const chats = csvSet(env.ALLOWED_CHAT_IDS);
  const users = csvSet(env.ALLOWED_USER_IDS);
  return chats.has(String(chatId)) && users.has(String(fromId));
}

export function datePrefix(unixSeconds, tz = 'Asia/Jerusalem') {
  const d = new Date((unixSeconds ?? Date.now() / 1000) * 1000);
  // en-CA gives YYYY-MM-DD
  return new Intl.DateTimeFormat('en-CA', { timeZone: tz, year: 'numeric', month: '2-digit', day: '2-digit' }).format(d);
}

export function sanitizeName(name) {
  // keep original name + extension; strip only path separators / control chars
  return String(name).replace(/[\/\\\u0000-\u001f]/g, '_').trim() || 'file';
}

// Pick the file object from a message. Returns {file_id, file_size, name, mime} or null.
export function extractFile(msg) {
  if (!msg) return null;
  if (msg.document) {
    const d = msg.document;
    return { file_id: d.file_id, file_size: d.file_size, name: d.file_name || `document_${d.file_unique_id}`, mime: d.mime_type };
  }
  if (Array.isArray(msg.photo) && msg.photo.length) {
    const p = msg.photo[msg.photo.length - 1]; // largest size
    return { file_id: p.file_id, file_size: p.file_size, name: `photo_${p.file_unique_id}.jpg`, mime: 'image/jpeg' };
  }
  for (const [key, ext] of [['video', 'mp4'], ['audio', 'mp3'], ['voice', 'ogg'], ['video_note', 'mp4'], ['animation', 'mp4']]) {
    const f = msg[key];
    if (f) return { file_id: f.file_id, file_size: f.file_size, name: f.file_name || `${key}_${f.file_unique_id}.${ext}`, mime: f.mime_type };
  }
  return null;
}

// ---------- Telegram ----------
async function tg(env, method, body) {
  const r = await fetch(`${TG_API}/bot${env.TELEGRAM_BOT_TOKEN}/${method}`, {
    method: 'POST',
    headers: { 'content-type': 'application/json' },
    body: JSON.stringify(body),
  });
  const j = await r.json().catch(() => ({}));
  if (!j.ok) throw new Error(`telegram ${method} failed: ${j.description || r.status}`);
  return j.result;
}

function reply(env, msg, text) {
  return tg(env, 'sendMessage', {
    chat_id: msg.chat.id,
    text,
    reply_to_message_id: msg.message_id,
    disable_notification: true, // silent
    disable_web_page_preview: true,
  });
}

async function downloadTelegramFile(env, fileId) {
  const info = await tg(env, 'getFile', { file_id: fileId });
  if (info.file_size && info.file_size > MAX_BYTES) throw Object.assign(new Error('too big'), { tooBig: true });
  const r = await fetch(`${TG_API}/file/bot${env.TELEGRAM_BOT_TOKEN}/${info.file_path}`);
  if (!r.ok) throw new Error(`telegram download failed: ${r.status}`);
  return new Uint8Array(await r.arrayBuffer());
}

// ---------- Google auth ----------
function b64url(bytes) {
  let s = '';
  const arr = bytes instanceof Uint8Array ? bytes : new TextEncoder().encode(bytes);
  for (let i = 0; i < arr.length; i++) s += String.fromCharCode(arr[i]);
  return btoa(s).replace(/\+/g, '-').replace(/\//g, '_').replace(/=+$/, '');
}

function pemToDer(pem) {
  const b64 = pem.replace(/-----[^-]+-----/g, '').replace(/\s+/g, '');
  const bin = atob(b64);
  const out = new Uint8Array(bin.length);
  for (let i = 0; i < bin.length; i++) out[i] = bin.charCodeAt(i);
  return out.buffer;
}

async function serviceAccountToken(sa) {
  const now = Math.floor(Date.now() / 1000);
  const header = b64url(JSON.stringify({ alg: 'RS256', typ: 'JWT' }));
  const claim = b64url(JSON.stringify({
    iss: sa.client_email, scope: 'https://www.googleapis.com/auth/drive.file',
    aud: TOKEN_URL, iat: now, exp: now + 3600,
  }));
  const key = await crypto.subtle.importKey('pkcs8', pemToDer(sa.private_key),
    { name: 'RSASSA-PKCS1-v1_5', hash: 'SHA-256' }, false, ['sign']);
  const sig = new Uint8Array(await crypto.subtle.sign('RSASSA-PKCS1-v1_5', key, new TextEncoder().encode(`${header}.${claim}`)));
  const jwt = `${header}.${claim}.${b64url(sig)}`;
  return tokenRequest({ grant_type: 'urn:ietf:params:oauth:grant-type:jwt-bearer', assertion: jwt });
}

async function tokenRequest(params) {
  const r = await fetch(TOKEN_URL, {
    method: 'POST',
    headers: { 'content-type': 'application/x-www-form-urlencoded' },
    body: new URLSearchParams(params).toString(),
  });
  const j = await r.json().catch(() => ({}));
  if (!j.access_token) throw new Error(`google token failed: ${j.error || r.status}`);
  return j.access_token;
}

export async function googleAccessToken(env) {
  if (env.GOOGLE_REFRESH_TOKEN) {
    return tokenRequest({
      grant_type: 'refresh_token',
      refresh_token: env.GOOGLE_REFRESH_TOKEN,
      client_id: env.GOOGLE_CLIENT_ID,
      client_secret: env.GOOGLE_CLIENT_SECRET,
    });
  }
  if (env.GOOGLE_SERVICE_ACCOUNT_JSON) return serviceAccountToken(JSON.parse(env.GOOGLE_SERVICE_ACCOUNT_JSON));
  throw new Error('no Google credentials configured');
}

// ---------- Drive ----------
export async function uploadToDrive(env, { name, mime, bytes }) {
  const token = await googleAccessToken(env);
  const boundary = 'tghub' + crypto.randomUUID().replace(/-/g, '');
  const meta = JSON.stringify({ name, parents: [env.DRIVE_FOLDER_ID] });
  const enc = new TextEncoder();
  const head = enc.encode(`--${boundary}\r\nContent-Type: application/json; charset=UTF-8\r\n\r\n${meta}\r\n--${boundary}\r\nContent-Type: ${mime || 'application/octet-stream'}\r\n\r\n`);
  const tail = enc.encode(`\r\n--${boundary}--`);
  const body = new Uint8Array(head.length + bytes.length + tail.length);
  body.set(head, 0); body.set(bytes, head.length); body.set(tail, head.length + bytes.length);

  const r = await fetch(`${DRIVE_UPLOAD}?uploadType=multipart&supportsAllDrives=true&fields=id,webViewLink`, {
    method: 'POST',
    headers: { authorization: `Bearer ${token}`, 'content-type': `multipart/related; boundary=${boundary}` },
    body,
  });
  const j = await r.json().catch(() => ({}));
  if (!r.ok || !j.id) throw new Error(`drive upload failed: ${j.error?.message || r.status}`);
  return j.webViewLink || `https://drive.google.com/file/d/${j.id}/view`;
}

// ---------- handlers ----------
async function saveFile(env, msg, source) {
  const f = extractFile(source);
  if (!f) return reply(env, msg, 'לא נמצא קובץ בהודעה. שלחו קובץ, או השיבו /save על הודעה עם קובץ.');
  if (f.file_size && f.file_size > MAX_BYTES) {
    return reply(env, msg, '⚠️ הקובץ גדול מ-20MB (מגבלת הבוט). העלו אותו ישירות לדרייב.');
  }
  try {
    const bytes = await downloadTelegramFile(env, f.file_id);
    const name = `${datePrefix(source.date)}_${sanitizeName(f.name)}`;
    const link = await uploadToDrive(env, { name, mime: f.mime, bytes });
    return reply(env, msg, `📂 ${link}`);
  } catch (e) {
    if (e.tooBig) return reply(env, msg, '⚠️ הקובץ גדול מ-20MB (מגבלת הבוט). העלו אותו ישירות לדרייב.');
    console.error(e.message); // never log tokens
    return reply(env, msg, '❌ השמירה נכשלה. נסו שוב או בדקו /status.');
  }
}

export async function handleUpdate(env, update) {
  const msg = update.message || update.channel_post;
  if (!msg || !msg.chat) return;
  if (!isAllowed(env, msg.chat.id, msg.from?.id)) return; // silently ignore strangers

  const text = (msg.text || msg.caption || '').trim();
  const cmd = text.startsWith('/') ? text.split(/\s+/)[0].split('@')[0].toLowerCase() : null;

  if (cmd === '/status') {
    let drive = 'לא הוגדר';
    try { await googleAccessToken(env); drive = 'מחובר ✅'; } catch { drive = 'שגיאת התחברות ❌'; }
    return reply(env, msg, `🤖 פעיל\nתיקייה: D&A\nDrive: ${drive}\nמגבלה: 20MB לקובץ`);
  }
  if (cmd === '/save') return saveFile(env, msg, msg.reply_to_message || msg);
  if (extractFile(msg)) return saveFile(env, msg, msg);
  // anything else: ignore (only /save and /status are supported)
}

export default {
  async fetch(request, env) {
    if (request.method !== 'POST') return new Response('not found', { status: 404 });
    if (!env.WEBHOOK_SECRET || request.headers.get('x-telegram-bot-api-secret-token') !== env.WEBHOOK_SECRET) {
      return new Response('forbidden', { status: 403 });
    }
    let update;
    try { update = await request.json(); } catch { return ok(); }
    try { await handleUpdate(env, update); } catch (e) { console.error(e.message); }
    return ok(); // always 200 so Telegram doesn't retry-loop
  },
};
