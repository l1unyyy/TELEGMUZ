/*
 * TELEGMUZZ Mini App — базовая версия.
 *
 * Сейчас интерфейс работает в демо-режиме: поиск по примерам,
 * избранное сохраняется в браузере/Telegram WebView.
 *
 * Чтобы подключить настоящую выдачу, укажи API_BASE_URL и реализуй
 * GET /api/search?q=... на сервере бота. Формат ответа:
 * { "tracks": [{ "id":"...", "title":"...", "artist":"...",
 *   "cover":"https://...", "duration":"3:21", "audio_url":"https://..." }] }
 */
const API_BASE_URL = ""; // Например: "https://api.example.com"

const tg = window.Telegram?.WebApp;
if (tg) {
  tg.ready();
  tg.expand();
  try { tg.setHeaderColor("#101010"); tg.setBackgroundColor("#101010"); } catch (_) {}
}

const demoTracks = [
  { id: "demo-1", title: "Ночной город", artist: "TELEGMUZZ selection", duration: "3:24" },
  { id: "demo-2", title: "На повторе", artist: "Daily Mix", duration: "2:58" },
  { id: "demo-3", title: "После полуночи", artist: "Late Night", duration: "4:06" },
  { id: "demo-4", title: "Тёплый воздух", artist: "Chill Radio", duration: "3:41" }
];

let tracks = [...demoTracks];
let currentTrack = null;
let isPlaying = false;
let favorites = loadFavorites();

const $ = (id) => document.getElementById(id);
const trackList = $("trackList");
const favoritesList = $("favoritesList");

function loadFavorites() {
  try { return JSON.parse(localStorage.getItem("telegmuzz_favorites") || "[]"); }
  catch (_) { return []; }
}
function saveFavorites() {
  localStorage.setItem("telegmuzz_favorites", JSON.stringify(favorites));
}
function escapeHtml(value = "") {
  return String(value).replace(/[&<>"']/g, c => ({
    "&":"&amp;", "<":"&lt;", ">":"&gt;", '"':"&quot;", "'":"&#39;"
  }[c]));
}
function renderTrack(track, isFavoriteList = false) {
  const favorite = favorites.some(item => item.id === track.id);
  const cover = track.cover
    ? `<img src="${escapeHtml(track.cover)}" alt="" onerror="this.remove()">`
    : "♫";
  return `<article class="track">
    <div class="cover">${cover}</div>
    <div class="track-info">
      <strong>${escapeHtml(track.title || "Без названия")}</strong>
      <span>${escapeHtml(track.artist || "Неизвестный исполнитель")}${track.duration ? " · " + escapeHtml(track.duration) : ""}</span>
    </div>
    <div class="track-actions">
      <button class="icon-button ${favorite ? "favorite" : ""}" data-fav="${escapeHtml(track.id)}" aria-label="В избранное">${favorite ? "♥" : "♡"}</button>
      <button class="icon-button play" data-play="${escapeHtml(track.id)}" aria-label="Выбрать трек">▶</button>
    </div>
  </article>`;
}
function render() {
  trackList.innerHTML = tracks.map(track => renderTrack(track)).join("");
  const saved = favorites;
  favoritesList.innerHTML = saved.map(track => renderTrack(track, true)).join("");
  $("favoritesCount").textContent = `${saved.length} треков`;
  $("favoritesEmpty").classList.toggle("hidden", saved.length > 0);
  $("emptyState").classList.toggle("hidden", tracks.length > 0);
}
function toggleFavorite(id) {
  const track = [...tracks, ...favorites].find(item => item.id === id);
  if (!track) return;
  favorites = favorites.some(item => item.id === id)
    ? favorites.filter(item => item.id !== id)
    : [...favorites, track];
  saveFavorites();
  render();
}
function selectTrack(id) {
  currentTrack = [...tracks, ...favorites].find(item => item.id === id);
  if (!currentTrack) return;
  $("playerTitle").textContent = currentTrack.title || "Без названия";
  $("playerArtist").textContent = currentTrack.artist || "Неизвестный исполнитель";
  $("playerArt").textContent = "♫";
  isPlaying = true;
  $("playButton").textContent = "Ⅱ";
  // Реальное воспроизведение подключается через audio_url после настройки API.
  if (currentTrack.audio_url) {
    if (!window.audioPlayer) window.audioPlayer = new Audio();
    window.audioPlayer.src = currentTrack.audio_url;
    window.audioPlayer.play().catch(() => {
      $("playerArtist").textContent = "Не удалось начать воспроизведение";
      isPlaying = false; $("playButton").textContent = "▶";
    });
  } else {
    $("playerArtist").textContent = "Выбран демо-трек — подключи API для аудио";
  }
}
async function searchTracks(query) {
  const clean = query.trim();
  $("resultsTitle").textContent = clean ? `Результаты: ${clean}` : "Популярное";
  $("statusLine").textContent = "Ищу…";
  if (!clean) {
    tracks = [...demoTracks];
    $("statusLine").textContent = "Демо-режим: подключи API бота, чтобы искать настоящие треки.";
    $("resultCount").textContent = "Подборка";
    render(); return;
  }
  if (API_BASE_URL) {
    try {
      const response = await fetch(`${API_BASE_URL}/api/search?q=${encodeURIComponent(clean)}`);
      if (!response.ok) throw new Error(`HTTP ${response.status}`);
      const data = await response.json();
      tracks = Array.isArray(data.tracks) ? data.tracks : [];
      $("statusLine").textContent = "Результаты с сервера";
      $("resultCount").textContent = `${tracks.length} треков`;
      render(); return;
    } catch (error) {
      $("statusLine").textContent = "Не удалось связаться с сервером. Проверь API и адрес.";
      tracks = [];
      $("resultCount").textContent = "Ошибка";
      render(); return;
    }
  }
  tracks = demoTracks.filter(track =>
    `${track.title} ${track.artist}`.toLowerCase().includes(clean.toLowerCase())
  );
  $("statusLine").textContent = "Пока включён демо-режим. Для настоящего поиска подключи API бота.";
  $("resultCount").textContent = `${tracks.length} найдено`;
  render();
}

$("searchForm").addEventListener("submit", event => {
  event.preventDefault();
  searchTracks($("searchInput").value);
});
document.addEventListener("click", event => {
  const favoriteButton = event.target.closest("[data-fav]");
  const play = event.target.closest("[data-play]");
  if (favoriteButton) toggleFavorite(favoriteButton.dataset.fav);
  if (play) selectTrack(play.dataset.play);
});
$("playButton").addEventListener("click", () => {
  if (!currentTrack) return;
  if (window.audioPlayer && currentTrack.audio_url) {
    if (isPlaying) window.audioPlayer.pause();
    else window.audioPlayer.play().catch(() => {});
  }
  isPlaying = !isPlaying;
  $("playButton").textContent = isPlaying ? "Ⅱ" : "▶";
});
document.querySelectorAll(".nav-item").forEach(button => {
  button.addEventListener("click", () => {
    document.querySelectorAll(".nav-item").forEach(item => item.classList.remove("active"));
    button.classList.add("active");
    const target = button.dataset.target;
    if (target === "favoritesList") $("favoritesList").scrollIntoView({ behavior: "smooth", block: "center" });
    else $("resultsSection").scrollIntoView({ behavior: "smooth", block: "start" });
  });
});
$("profileButton").addEventListener("click", () => {
  const user = tg?.initDataUnsafe?.user;
  if (user) alert(`Привет, ${user.first_name || "музыкант"}!`);
  else alert("TELEGMUZZ");
});

render();
