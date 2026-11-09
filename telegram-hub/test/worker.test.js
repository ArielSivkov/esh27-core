import { test, beforeEach } from 'node:test';
import assert from 'node:assert/strict';
import { generateKeyPairSync } from 'node:crypto';
import worker, { datePrefix, extractFile, isAllowed, MAX_BYTES } from '../src/index.js';

const BASE_ENV = {
  TELEGRAM_BOT_TOKEN: 'TEST:TOKEN',
  WEBHOOK_SECRET: 'hook-secret',
  ALLOWED_CHAT_IDS: '-100123, 42',
  ALLOWED_USER_IDS: '42,7',
  DRIVE_FOLDER_ID: '1dO-WzLeE3Zfe-kGFU5p0x6IbArftm1yL',
  GOOGLE_CLIENT_ID: 'cid', GOOGLE_CLIENT_SECRET: 'csec', GOOGLE_REFRESH_TOKEN: 'rtok',
};

let calls, sent, driveBodies, opts;
const json = (o, status = 200) => new Response(JSON.stringify(o), { status, headers: { 'content-type': 'application/json' } });

beforeEach(() => {
  calls = []; sent = []; driveBodies = []; opts = { fileSize: 1234, tokenFail: false };
  globalThis.fetch = async (url, init = {}) => {
    url = String(url); calls.push(url);
    if (url.includes('/sendMessage')) { sent.push(JSON.parse(init.body)); return json({ ok: true, result: {} }); }
    if (url.includes('/getFile')) return json({ ok: true, result: { file_path: 'documents/x.pdf', file_size: opts.fileSize } });
    if (url.includes('/file/bot')) return new Response(new Uint8Array([37, 80, 68, 70]));
    if (url.startsWith('https://oauth2.googleapis.com/token')) {
      return opts.tokenFail ? json({ error: 'invalid_grant' }, 400) : json({ access_token: 'gtok' });
    }
    if (url.startsWith('https://www.googleapis.com/upload/drive/v3/files')) {
      driveBodies.push({ headers: init.headers, body: new TextDecoder().decode(init.body) });
      return json({ id: 'FILEID', webViewLink: 'https://drive.google.com/file/d/FILEID/view' });
    }
    throw new Error('unexpected fetch ' + url);
  };
});

const req = (update, secret = 'hook-secret') => new Request('https://w.example/', {
  method: 'POST', headers: { 'x-telegram-bot-api-secret-token': secret, 'content-type': 'application/json' },
  body: JSON.stringify(update),
});
const msg = (extra) => ({ update_id: 1, message: { message_id: 10, date: 1762646400, chat: { id: -100123 }, from: { id: 42 }, ...extra } });

test('rejects wrong webhook secret', async () => {
  const r = await worker.fetch(req(msg({ text: '/status' }), 'nope'), BASE_ENV);
  assert.equal(r.status, 403); assert.equal(calls.length, 0);
});

test('ignores non-whitelisted chat or user silently', async () => {
  await worker.fetch(req({ message: { message_id: 1, chat: { id: 999 }, from: { id: 42 }, text: '/status' } }), BASE_ENV);
  await worker.fetch(req({ message: { message_id: 1, chat: { id: -100123 }, from: { id: 999 }, text: '/status' } }), BASE_ENV);
  assert.equal(calls.length, 0);
  assert.equal(isAllowed(BASE_ENV, -100123, 7), true);
});

test('document → Drive with date prefix + original name, silent 📂 reply', async () => {
  const r = await worker.fetch(req(msg({ document: { file_id: 'F1', file_unique_id: 'U1', file_name: 'דוח רבעוני.xlsx', mime_type: 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet', file_size: 1234 } })), BASE_ENV);
  assert.equal(r.status, 200);
  assert.equal(driveBodies.length, 1);
  const meta = JSON.parse(driveBodies[0].body.split('\r\n\r\n')[1].split('\r\n')[0]);
  assert.equal(meta.name, '2025-11-09_דוח רבעוני.xlsx');
  assert.deepEqual(meta.parents, ['1dO-WzLeE3Zfe-kGFU5p0x6IbArftm1yL']);
  assert.equal(driveBodies[0].headers.authorization, 'Bearer gtok');
  assert.ok(calls.some((u) => u.includes('supportsAllDrives=true')));
  assert.equal(sent.length, 1);
  assert.equal(sent[0].text, '📂 https://drive.google.com/file/d/FILEID/view');
  assert.equal(sent[0].disable_notification, true);
  assert.equal(sent[0].reply_to_message_id, 10);
});

test('/save as reply saves the replied-to file', async () => {
  await worker.fetch(req(msg({ text: '/save@MyBot', reply_to_message: { message_id: 5, date: 1762646400, chat: { id: -100123 }, document: { file_id: 'F2', file_unique_id: 'U2', file_name: 'a.pdf', file_size: 10 } } })), BASE_ENV);
  assert.equal(driveBodies.length, 1);
  assert.match(driveBodies[0].body, /"name":"2025-11-09_a\.pdf"/);
  assert.match(sent[0].text, /^📂 /);
});

test('/save with no file explains', async () => {
  await worker.fetch(req(msg({ text: '/save' })), BASE_ENV);
  assert.equal(driveBodies.length, 0); assert.match(sent[0].text, /לא נמצא קובץ/);
});

test('rejects >20MB by declared size without downloading', async () => {
  await worker.fetch(req(msg({ document: { file_id: 'F3', file_unique_id: 'U3', file_name: 'big.mp4', file_size: MAX_BYTES + 1 } })), BASE_ENV);
  assert.equal(calls.filter((u) => u.includes('getFile')).length, 0);
  assert.match(sent[0].text, /20MB/);
});

test('rejects >20MB reported by getFile', async () => {
  opts.fileSize = MAX_BYTES + 5;
  await worker.fetch(req(msg({ document: { file_id: 'F4', file_unique_id: 'U4', file_name: 'x.zip' } })), BASE_ENV);
  assert.equal(driveBodies.length, 0); assert.match(sent[0].text, /20MB/);
});

test('/status reports Drive state', async () => {
  await worker.fetch(req(msg({ text: '/status' })), BASE_ENV);
  assert.match(sent[0].text, /מחובר ✅/);
  opts.tokenFail = true; sent = [];
  await worker.fetch(req(msg({ text: '/status' })), BASE_ENV);
  assert.match(sent[0].text, /❌/);
});

test('Drive failure → error reply, still 200', async () => {
  opts.tokenFail = true;
  const r = await worker.fetch(req(msg({ document: { file_id: 'F5', file_unique_id: 'U5', file_name: 'a.pdf', file_size: 10 } })), BASE_ENV);
  assert.equal(r.status, 200); assert.match(sent[0].text, /נכשלה/);
});

test('plain text ignored', async () => {
  await worker.fetch(req(msg({ text: 'שלום' })), BASE_ENV);
  assert.equal(calls.length, 0);
});

test('service account JWT path', async () => {
  const { privateKey } = generateKeyPairSync('rsa', { modulusLength: 2048 });
  const env = { ...BASE_ENV, GOOGLE_REFRESH_TOKEN: '', GOOGLE_SERVICE_ACCOUNT_JSON: JSON.stringify({ client_email: 'sa@x.iam.gserviceaccount.com', private_key: privateKey.export({ type: 'pkcs8', format: 'pem' }) }) };
  await worker.fetch(req(msg({ document: { file_id: 'F6', file_unique_id: 'U6', file_name: 'a.pdf', file_size: 10 } })), env);
  assert.equal(driveBodies.length, 1);
});

test('helpers: photo naming, date prefix in Jerusalem tz', () => {
  assert.equal(extractFile({ photo: [{ file_id: 's', file_unique_id: 'a' }, { file_id: 'L', file_unique_id: 'b', file_size: 5 }] }).name, 'photo_b.jpg');
  assert.equal(datePrefix(Date.UTC(2026, 10, 8, 22, 30) / 1000), '2026-11-09'); // 00:30 IL
});
