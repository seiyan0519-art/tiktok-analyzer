import './style.css';

document.querySelector('#app').innerHTML = `
<header><a class="brand" href="/">beauty clip<span>動画から、伝わる理由を。</span></a><span class="badge">美容レビュー動画分析</span></header>
<main><div class="intro"><span class="eyebrow">BEAUTY VIDEO WORKSPACE</span><h1>最初の3秒を、<br>もっとよく見てみよう。</h1><p>美容商品のレビュー動画をアップロード。<br>動画の長さと冒頭のシーンを、ひと目で確認できます。</p></div>
<section class="upload-card" aria-labelledby="upload-title"><div class="step">01 <span>動画を選ぶ</span></div><h2 id="upload-title">レビュー動画をアップロード</h2><label class="dropzone" id="dropzone"><span class="upload-icon" aria-hidden="true">↑</span><strong>ここにMP4動画をドロップ</strong><span>または、クリックしてファイルを選択</span><span class="button">動画を選択する</span><small>MP4形式 · 最大200MB</small><input id="file" type="file" accept="video/mp4,.mp4" aria-label="MP4動画を選択"></label><p class="privacy">⌁ 動画はこのブラウザ内で処理され、サーバーには送信されません。</p><p id="status" role="status" aria-live="polite"></p><p id="error" role="alert" hidden></p></section>
<section id="results" hidden aria-labelledby="results-title"><div class="section-heading"><div><span class="eyebrow">VIDEO OVERVIEW</span><h2 id="results-title">動画のプレビュー</h2></div><span class="ready">✓ 読み込み完了</span></div><div class="overview"><video id="video" controls playsinline preload="auto"></video><div class="details"><span class="eyebrow">YOUR VIDEO</span><h3 id="filename"></h3><dl><div><dt>動画の長さ</dt><dd id="duration"></dd></div><div><dt>ファイルサイズ</dt><dd id="size"></dd></div></dl><p>下の画像で、視聴者が最初に目にするシーンを確認しましょう。</p></div></div><div class="section-heading"><div><h2>冒頭3秒のシーン</h2><p>0秒・1秒・2秒時点の画像を切り出しています。</p></div></div><div id="frames" class="frames"></div></section>
<aside><span>これからの分析に</span><p>商品の見せ方、テロップ、使い心地の伝え方。<br>まずは動画の第一印象をチェックしましょう。</p></aside></main><footer>beauty clip <span>美容レビューの、伝わる瞬間を見つける。</span></footer>`;
const input = document.querySelector('#file');
const video = document.querySelector('#video');
const status = document.querySelector('#status');
const error = document.querySelector('#error');
const results = document.querySelector('#results');
let currentUrl;
let generation = 0;
function waitFor(target, event, action) {
  return new Promise((resolve, reject) => {
    const timer = setTimeout(() => finish(new Error('動画の読み込みがタイムアウトしました。別のMP4をお試しください。')), 20000);
    const success = () => finish();
    const failure = () => finish(new Error('この動画を再生できません。H.264形式のMP4動画をお試しください。'));
    function finish(err) { clearTimeout(timer); target.removeEventListener(event, success); target.removeEventListener('error', failure); err ? reject(err) : resolve(); }
    target.addEventListener(event, success, { once: true }); target.addEventListener('error', failure, { once: true });
    action();
  });
}
async function analyze(file) {
  const run = ++generation;
  error.hidden = true; results.hidden = true; status.textContent = '';
  if (currentUrl) { video.pause(); video.removeAttribute('src'); video.load(); URL.revokeObjectURL(currentUrl); currentUrl = undefined; }
  if (!file) return;
  if (!/\.mp4$/i.test(file.name) || (file.type && file.type !== 'video/mp4')) { error.textContent = 'MP4形式の動画を選択してください。'; error.hidden = false; return; }
  if (!file.size || file.size > 200 * 1024 * 1024) { error.textContent = '0バイトより大きく、200MB以下の動画を選択してください。'; error.hidden = false; return; }
  status.textContent = '動画を読み込み、冒頭の画像を準備しています…';
  const reader = document.createElement('video'); reader.muted = true; reader.playsInline = true; reader.preload = 'auto';
  const url = URL.createObjectURL(file);
  try {
    await waitFor(reader, 'loadeddata', () => { reader.src = url; reader.load(); });
    if (!Number.isFinite(reader.duration) || reader.duration <= 0 || !reader.videoWidth) throw new Error('動画の長さを取得できませんでした。別のMP4をお試しください。');
    const frames = [];
    for (const time of [0, 1, 2].filter(t => t < reader.duration)) {
      if (reader.currentTime !== time) await waitFor(reader, 'seeked', () => { reader.currentTime = time; });
      const canvas = document.createElement('canvas'); canvas.width = Math.min(reader.videoWidth, 720); canvas.height = Math.round(canvas.width * reader.videoHeight / reader.videoWidth);
      canvas.getContext('2d').drawImage(reader, 0, 0, canvas.width, canvas.height);
      const figure = document.createElement('figure'); const img = new Image(); img.src = canvas.toDataURL('image/jpeg', .85); img.alt = `動画の${time}秒時点の画像`;
      const caption = document.createElement('figcaption'); caption.textContent = `0:0${time}`; figure.append(img, caption); frames.push(figure);
    }
    if (run !== generation) { URL.revokeObjectURL(url); return; }
    currentUrl = url; video.src = url;
    document.querySelector('#filename').textContent = file.name;
    document.querySelector('#duration').textContent = `${reader.duration.toFixed(2)} 秒`;
    document.querySelector('#size').textContent = `${(file.size / 1024 / 1024).toFixed(2)} MB`;
    document.querySelector('#frames').replaceChildren(...frames);
    results.hidden = false; status.textContent = reader.duration < 3 ? '3秒未満の動画のため、動画内にある秒数の画像のみ表示しています。' : '';
  } catch (err) { URL.revokeObjectURL(url); if (run === generation) { status.textContent = ''; error.textContent = err.message; error.hidden = false; } }
  finally { reader.removeAttribute('src'); reader.load(); }
}
input.addEventListener('change', () => { const file = input.files[0]; input.value = ''; if (file) analyze(file); });
const zone = document.querySelector('#dropzone');
for (const type of ['dragenter', 'dragover']) zone.addEventListener(type, e => { e.preventDefault(); zone.classList.add('dragging'); });
for (const type of ['dragleave', 'drop']) zone.addEventListener(type, e => { e.preventDefault(); zone.classList.remove('dragging'); });
zone.addEventListener('drop', e => { if (e.dataTransfer.files.length !== 1) { error.textContent = '動画を1つずつ選択してください。'; error.hidden = false; return; } analyze(e.dataTransfer.files[0]); });
