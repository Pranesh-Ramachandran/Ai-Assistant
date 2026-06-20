document.addEventListener('DOMContentLoaded', () => {
  const API = 'http://127.0.0.1:7890';

  const els = {
    apiStatus: document.getElementById('apiStatus'),
    aiStatus: document.getElementById('aiStatus'),
    visionStatus: document.getElementById('visionStatus'),
    messageInput: document.getElementById('messageInput'),
    sendButton: document.getElementById('sendButton'),
    chatMessages: document.getElementById('chatMessages'),
    moduleTabs: document.getElementById('moduleTabs'),
    drawer: document.getElementById('sidebar'),
    drawerBackdrop: document.getElementById('drawerBackdrop'),
    hamburger: document.getElementById('hamburger'),
    drawerClose: document.getElementById('drawerClose'),
    quickChips: document.getElementById('quickChips'),
    clearChatBtn: document.getElementById('clearChatBtn'),
    visionHint: document.getElementById('visionHint'),
    visionOutput: document.getElementById('visionOutput'),
    visPreview: document.getElementById('visPreview'),
    visCanvas: document.getElementById('visCanvas'),
    visBadge: document.getElementById('visBadge'),
    visionCloudToggle: document.getElementById('visionCloudToggle'),
    visStartBtn: document.getElementById('visStartBtn'),
    visCaptureBtn: document.getElementById('visCaptureBtn'),
    visAnalyzeBtn: document.getElementById('visAnalyzeBtn'),
    visStopBtn: document.getElementById('visStopBtn'),
    visScreenBtn: document.getElementById('visScreenBtn'),
    visQrBtn: document.getElementById('visQrBtn'),
    visOcrBtn: document.getElementById('visOcrBtn'),
    bookCity: document.getElementById('bookCity'),
    bookQuery: document.getElementById('bookQuery'),
    bookMovie: document.getElementById('bookMovie'),
    bookTheater: document.getElementById('bookTheater'),
    bookShows: document.getElementById('bookShows'),
    bookSeats: document.getElementById('bookSeats'),
    bookCheckoutBtn: document.getElementById('bookCheckoutBtn'),
    bookRefreshBtn: document.getElementById('bookRefreshBtn'),
    bookingOutput: document.getElementById('bookingOutput'),
    calSummary: document.getElementById('calSummary'),
    calWhen: document.getElementById('calWhen'),
    calDuration: document.getElementById('calDuration'),
    calAddBtn: document.getElementById('calAddBtn'),
    calendarOutput: document.getElementById('calendarOutput'),
    memName: document.getElementById('memName'),
    memCity: document.getElementById('memCity'),
    memPlaceLabel: document.getElementById('memPlaceLabel'),
    memPlaceName: document.getElementById('memPlaceName'),
    memSaveProfileBtn: document.getElementById('memSaveProfileBtn'),
    memSavePlaceBtn: document.getElementById('memSavePlaceBtn'),
    memReloadBtn: document.getElementById('memReloadBtn'),
    memoryOutput: document.getElementById('memoryOutput'),
    webCommand: document.getElementById('webCommand'),
    webRunBtn: document.getElementById('webRunBtn'),
    webConfirmBtn: document.getElementById('webConfirmBtn'),
    webCancelBtn: document.getElementById('webCancelBtn'),
    webOutput: document.getElementById('webOutput'),
    msgContact: document.getElementById('msgContact'),
    msgText: document.getElementById('msgText'),
    msgDraftBtn: document.getElementById('msgDraftBtn'),
    msgConfirmBtn: document.getElementById('msgConfirmBtn'),
    msgCancelBtn: document.getElementById('msgCancelBtn'),
    msgOutput: document.getElementById('msgOutput'),
    homeCommand: document.getElementById('homeCommand'),
    homeRunBtn: document.getElementById('homeRunBtn'),
    homeOutput: document.getElementById('homeOutput'),
    emojiToggleBtn: document.getElementById('emojiToggleBtn'),
    emojiBar: document.getElementById('emojiBar'),
    sysOutput: document.getElementById('sysOutput'),
  };

  const state = {
    activePanel: 'chat',
    visionStream: null,
    visionBusy: false,
    pendingWeb: false,
    pendingMsg: false,
    selectedShowtime: '',
    selectedMovie: '',
    selectedTheater: '',
    selectedMovieTitle: '',
  };

  const PANEL_LOADERS = {
    chat: () => {},
    vision: () => startVisionPreview(),
    booking: () => loadMovies(),
    calendar: () => loadCalendar('today'),
    memory: () => loadMemory(),
    tools: () => loadSystem('all'),
  };

  function setStatusBadge(el, text, tone = 'default') {
    if (!el) return;
    el.textContent = text;
    el.dataset.tone = tone;
  }

  function setVisionBadge(text, tone = 'default') {
    if (!els.visBadge) return;
    els.visBadge.textContent = text;
    els.visBadge.dataset.tone = tone;
  }

  function setPanel(panel) {
    state.activePanel = panel;
    document.querySelectorAll('.module-tab').forEach(btn => {
      btn.classList.toggle('active', btn.dataset.panel === panel);
    });
    document.querySelectorAll('.panel').forEach(section => {
      section.classList.toggle('active', section.id === `panel-${panel}`);
    });

    if (panel !== 'vision') {
      stopVisionPreview();
    }

    const loader = PANEL_LOADERS[panel];
    if (loader) loader();
  }

  function openDrawer() {
    els.drawer.classList.add('open');
    els.drawerBackdrop.classList.add('open');
    els.drawer.setAttribute('aria-hidden', 'false');
  }

  function closeDrawer() {
    els.drawer.classList.remove('open');
    els.drawerBackdrop.classList.remove('open');
    els.drawer.setAttribute('aria-hidden', 'true');
  }

  function appendMessage(role, text) {
    const row = document.createElement('div');
    row.className = `message ${role}`;

    const avatar = document.createElement('div');
    avatar.className = 'avatar';
    avatar.textContent = role === 'user' ? '🧑' : '🤖';

    const bubble = document.createElement('div');
    bubble.className = 'bubble';

    // Emoji reactions row (appears on hover)
    const reactions = document.createElement('div');
    reactions.className = 'bubble-reactions';
    ['👍','❤️','😂','🔥','✨'].forEach(emoji => {
      const btn = document.createElement('button');
      btn.className = 'reaction-btn';
      btn.textContent = emoji;
      btn.title = emoji;
      btn.addEventListener('click', () => {
        btn.classList.toggle('reacted');
        // fun jiggle on the bubble
        bubble.style.animation = 'none';
        requestAnimationFrame(() => {
          bubble.style.animation = '';
          bubble.style.animation = 'bubbleWobbleIn 0.45s cubic-bezier(0.34,1.8,0.64,1)';
        });
        setTimeout(() => { bubble.style.animation = ''; }, 480);
      });
      reactions.appendChild(btn);
    });

    const msgContent = document.createElement('div');
    msgContent.style.display = 'flex';
    msgContent.style.flexDirection = 'column';
    msgContent.style.alignItems = role === 'user' ? 'flex-end' : 'flex-start';
    msgContent.appendChild(bubble);
    msgContent.appendChild(reactions);

    if (role === 'user') {
      row.appendChild(msgContent);
      row.appendChild(avatar);
    } else {
      row.appendChild(avatar);
      row.appendChild(msgContent);
    }
    els.chatMessages.appendChild(row);

    const speed = role === 'user' ? 0 : 11;

    if (speed === 0) {
      bubble.textContent = text;
      els.chatMessages.scrollTop = els.chatMessages.scrollHeight;
      return;
    }

    let i = 0;
    const type = () => {
      bubble.textContent += text.charAt(i);
      i++;
      if (i < text.length) {
        setTimeout(type, speed);
      } else {
        els.chatMessages.scrollTop = els.chatMessages.scrollHeight;
      }
    };
    type();
  }

  function showTypingIndicator() {
    const row = document.createElement('div');
    row.className = 'message ai typing-indicator';
    row.id = '__typing__';

    const avatar = document.createElement('div');
    avatar.className = 'avatar';
    avatar.textContent = '🤖';

    const bubble = document.createElement('div');
    bubble.className = 'bubble';
    [1,2,3].forEach(() => {
      const dot = document.createElement('span');
      dot.className = 'typing-dot';
      bubble.appendChild(dot);
    });

    row.appendChild(avatar);
    row.appendChild(bubble);
    els.chatMessages.appendChild(row);
    els.chatMessages.scrollTop = els.chatMessages.scrollHeight;
    return row;
  }

  function removeTypingIndicator() {
    const el = document.getElementById('__typing__');
    if (el) el.remove();
  }

  async function api(path, body = {}) {
    const res = await fetch(`${API}${path}`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
    });
    return res.json();
  }

  async function refreshStatus() {
    try {
      const data = await api('/api/status', {});
      setStatusBadge(els.apiStatus, 'API: online', 'ok');
      setStatusBadge(els.aiStatus, data.ai_ready ? 'AI: ready' : 'AI: offline', data.ai_ready ? 'ok' : 'warn');
      setStatusBadge(els.visionStatus, data.tts_ready ? 'Vision: live' : 'Vision: ready', 'ok');
    } catch (err) {
      setStatusBadge(els.apiStatus, 'API: offline', 'danger');
      setStatusBadge(els.aiStatus, 'AI: unavailable', 'danger');
      setStatusBadge(els.visionStatus, 'Vision: idle', 'subtle');
      if (state.activePanel === 'chat') {
        appendMessage('ai', 'Server offline. Start jarvis_grid_server.py to unlock live features.');
      }
    }
  }

  function submitChat() {
    const text = els.messageInput.value.trim();
    if (!text) return;
    appendMessage('user', text);
    els.messageInput.value = '';
    // Show typing indicator while waiting
    const typingRow = showTypingIndicator();
    api('/api/chat', { message: text })
      .then(data => {
        removeTypingIndicator();
        appendMessage('ai', data.reply || data.error || 'No response.');
      })
      .catch(() => {
        removeTypingIndicator();
        appendMessage('ai', 'Server offline. 😴');
      });
  }

  let visionTimer = null;
  async function startVisionPreview() {
    if (state.visionStream) return state.visionStream;
    if (!navigator.mediaDevices?.getUserMedia) {
      els.visionHint.textContent = 'Camera not supported in this browser.';
      setVisionBadge('Camera unsupported', 'warn');
      return null;
    }
    if (location.protocol === 'file:') {
      els.visionHint.textContent = 'Open this UI from localhost/HTTPS for camera permissions.';
    }
    try {
      state.visionStream = await navigator.mediaDevices.getUserMedia({
        video: { facingMode: { ideal: 'environment' } },
        audio: false,
      });
      els.visPreview.srcObject = state.visionStream;
      await els.visPreview.play().catch(() => {});
      setVisionBadge('Camera live', 'ok');
      els.visionHint.textContent = 'Preview is live. Capture to stay free, Analyze for cloud vision.';
      return state.visionStream;
    } catch (err) {
      state.visionStream = null;
      setVisionBadge('Camera blocked', 'danger');
      els.visionHint.textContent = `Camera unavailable: ${err.message || err}`;
      return null;
    }
  }

  function stopVisionPreview() {
    if (visionTimer) {
      clearTimeout(visionTimer);
      visionTimer = null;
    }
    if (state.visionStream) {
      state.visionStream.getTracks().forEach(track => track.stop());
      state.visionStream = null;
    }
    if (els.visPreview) {
      els.visPreview.srcObject = null;
    }
    setVisionBadge('Camera off', 'subtle');
  }

  function captureFrame() {
    if (!state.visionStream || !els.visPreview.videoWidth) return null;
    const canvas = els.visCanvas;
    canvas.width = els.visPreview.videoWidth;
    canvas.height = els.visPreview.videoHeight;
    const ctx = canvas.getContext('2d');
    ctx.drawImage(els.visPreview, 0, 0, canvas.width, canvas.height);
    return canvas.toDataURL('image/jpeg', 0.86).split(',')[1];
  }

  async function runVisionFrame(mode) {
    await startVisionPreview();
    if (!state.visionStream) return;
    if (!els.visPreview.videoWidth) {
      await new Promise(resolve => setTimeout(resolve, 300));
    }
    const image_b64 = captureFrame();
    if (!image_b64) {
      els.visionOutput.textContent = 'Camera frame not ready yet.';
      return;
    }
    const cloudAllowed = els.visionCloudToggle.checked;
    const action = mode === 'cloud' && cloudAllowed ? 'analyze' : 'frame';
    const prompt = action === 'analyze'
      ? 'Describe this camera image clearly and briefly.'
      : 'Extract any visible text from this camera image.';
    setVisionBadge(action === 'analyze' ? 'Cloud analyze' : 'Free capture', action === 'analyze' ? 'warn' : 'ok');
    els.visionOutput.textContent = 'Processing snapshot...';
    try {
      const data = await api('/api/vision', {
        action,
        image_b64,
        prompt,
      });
      els.visionOutput.textContent = data.result || data.error || 'No result.';
    } catch (err) {
      els.visionOutput.textContent = `Vision error: ${err.message || err}`;
    }
  }

  async function runScreenVision() {
    els.visionOutput.textContent = 'Reading screen...';
    const data = await api('/api/vision', { action: 'screen' }).catch(() => ({ result: 'Server offline.' }));
    els.visionOutput.textContent = data.result || data.error || '';
  }

  async function runQrVision() {
    els.visionOutput.textContent = 'Scanning QR...';
    const data = await api('/api/vision', { action: 'qr' }).catch(() => ({ result: 'Server offline.' }));
    els.visionOutput.textContent = data.result || data.error || '';
  }

  async function runOcrVision() {
    els.visionOutput.textContent = 'Reading text...';
    const data = await api('/api/vision', { action: 'command', command: 'read screen' }).catch(() => ({ result: 'Server offline.' }));
    els.visionOutput.textContent = data.result || data.error || '';
  }

  function renderShowtimes(showtimes) {
    els.bookShows.innerHTML = '';
    showtimes.forEach(show => {
      const btn = document.createElement('button');
      btn.className = 'showtime';
      btn.type = 'button';
      btn.textContent = `${show.time} · ${show.price || ''}`;
      btn.addEventListener('click', async () => {
        state.selectedShowtime = show.time;
        const summary = await api('/api/booking', {
          action: 'confirm',
          movie: state.selectedMovieTitle,
          theater: els.bookTheater.selectedOptions[0]?.textContent || '',
          showtime: show.time,
          seats: Number(els.bookSeats.value || 1),
        }).catch(() => ({ summary: 'Unable to create booking summary.' }));
        els.bookingOutput.textContent = summary.summary || summary.result || summary.error || '';
      });
      els.bookShows.appendChild(btn);
    });
  }

  async function loadMovies() {
    const query = els.bookQuery.value.trim();
    const city = els.bookCity.value.trim() || 'Chennai';
    els.bookingOutput.textContent = 'Loading movie catalog...';
    try {
      const data = await api('/api/booking', { action: 'list', query, city });
      const movies = data.movies || [];
      els.bookMovie.innerHTML = movies.length
        ? '<option value="">Select movie...</option>'
        : '<option value="">No movies found</option>';
      movies.forEach(movie => {
        const opt = document.createElement('option');
        opt.value = movie.id;
        opt.textContent = movie.title || movie.name || `Movie ${movie.id}`;
        opt.dataset.title = movie.title || movie.name || '';
        els.bookMovie.appendChild(opt);
      });
      els.bookingOutput.textContent = movies.length
        ? `${movies.length} movies ready. Choose one to continue.`
        : 'No movies available right now.';
      state.selectedMovie = '';
      state.selectedTheater = '';
      state.selectedShowtime = '';
      els.bookTheater.innerHTML = '<option value="">Select a movie first</option>';
      els.bookShows.innerHTML = '';
    } catch (err) {
      els.bookingOutput.textContent = `Booking error: ${err.message || err}`;
    }
  }

  async function loadTheaters(movieId) {
    const city = els.bookCity.value.trim() || 'Chennai';
    try {
      const data = await api('/api/booking', { action: 'theaters', movie_id: movieId, city });
      const theaters = data.theaters || [];
      els.bookTheater.innerHTML = theaters.length
        ? '<option value="">Select theater...</option>'
        : '<option value="">No theaters found</option>';
      theaters.forEach(theater => {
        const opt = document.createElement('option');
        opt.value = theater.id;
        opt.textContent = `${theater.name} · ${theater.location || theater.distance || ''}`;
        opt.dataset.name = theater.name || '';
        els.bookTheater.appendChild(opt);
      });
      state.selectedTheater = '';
      state.selectedShowtime = '';
      els.bookShows.innerHTML = '';
      els.bookingOutput.textContent = theaters.length
        ? 'Pick a theater to see showtimes.'
        : 'No theaters available.';
    } catch (err) {
      els.bookingOutput.textContent = `Theater lookup failed: ${err.message || err}`;
    }
  }

  async function loadShowtimes(movieId, theaterId) {
    const city = els.bookCity.value.trim() || 'Chennai';
    try {
      const data = await api('/api/booking', { action: 'showtimes', movie_id: movieId, venue_id: theaterId, city });
      renderShowtimes(data.showtimes || []);
      els.bookingOutput.textContent = (data.showtimes || []).length
        ? 'Choose a showtime to prepare checkout.'
        : 'No showtimes returned.';
    } catch (err) {
      els.bookingOutput.textContent = `Showtime lookup failed: ${err.message || err}`;
    }
  }

  async function openCheckout() {
    if (!state.selectedMovie || !state.selectedTheater || !state.selectedShowtime) {
      els.bookingOutput.textContent = 'Choose a movie, theater, and showtime first.';
      return;
    }
    try {
      const confirm = await api('/api/booking', {
        action: 'confirm',
        movie: state.selectedMovieTitle,
        theater: els.bookTheater.selectedOptions[0]?.textContent || '',
        showtime: state.selectedShowtime,
        seats: Number(els.bookSeats.value || 1),
      });
      els.bookingOutput.textContent = confirm.summary || confirm.result || 'Opening checkout...';
      await api('/api/booking', {
        action: 'checkout',
        movie_id: state.selectedMovie,
        venue_id: state.selectedTheater,
        show_id: state.selectedShowtime,
        seats: Number(els.bookSeats.value || 1),
      });
    } catch (err) {
      els.bookingOutput.textContent = `Checkout failed: ${err.message || err}`;
    }
  }

  async function loadCalendar(action) {
    try {
      const data = await api('/api/calendar', { action, duration: Number(els.calDuration.value || 60), speak: false });
      els.calendarOutput.textContent = data.result || data.error || 'No calendar data.';
    } catch (err) {
      els.calendarOutput.textContent = `Calendar error: ${err.message || err}`;
    }
  }

  async function addCalendarEvent() {
    try {
      const data = await api('/api/calendar', {
        action: 'add',
        summary: els.calSummary.value.trim() || 'Meeting',
        when: els.calWhen.value.trim() || 'tomorrow 10am',
        duration: Number(els.calDuration.value || 60),
        speak: false,
      });
      els.calendarOutput.textContent = data.result || 'Event added.';
    } catch (err) {
      els.calendarOutput.textContent = `Add event failed: ${err.message || err}`;
    }
  }

  async function loadMemory() {
    try {
      const data = await api('/api/memory', { action: 'get' });
      const profile = data.profile || {};
      const places = data.places || {};
      if (profile.name) els.memName.value = profile.name;
      if (profile.city) els.memCity.value = profile.city;
      els.memoryOutput.textContent = [
        data.summary || 'No memory summary available.',
        Object.keys(places).length ? `Saved places: ${Object.keys(places).join(', ')}` : 'No saved places yet.',
      ].join('\n');
    } catch (err) {
      els.memoryOutput.textContent = `Memory error: ${err.message || err}`;
    }
  }

  async function saveProfile() {
    try {
      const data = await api('/api/memory', {
        action: 'set_profile',
        name: els.memName.value.trim(),
        city: els.memCity.value.trim(),
        language: 'en',
      });
      els.memoryOutput.textContent = data.ok ? 'Profile saved.' : 'Could not save profile.';
    } catch (err) {
      els.memoryOutput.textContent = `Profile save failed: ${err.message || err}`;
    }
  }

  async function savePlace() {
    try {
      const data = await api('/api/memory', {
        action: 'save_place',
        label: els.memPlaceLabel.value.trim(),
        name: els.memPlaceName.value.trim(),
      });
      els.memoryOutput.textContent = data.ok ? 'Place saved.' : 'Could not save place.';
      loadMemory();
    } catch (err) {
      els.memoryOutput.textContent = `Place save failed: ${err.message || err}`;
    }
  }

  async function runWeb(command) {
    try {
      const data = await api('/api/web', { action: 'command', command });
      els.webOutput.textContent = data.result || data.error || '';
      state.pendingWeb = !!data.needs_confirm;
      if (state.pendingWeb) {
        els.webOutput.textContent = data.confirm_prompt || data.result || els.webOutput.textContent;
      }
    } catch (err) {
      els.webOutput.textContent = `Web error: ${err.message || err}`;
    }
  }

  async function confirmWeb(action) {
    try {
      const data = await api('/api/web', { action });
      els.webOutput.textContent = data.result || data.error || '';
      state.pendingWeb = !!data.needs_confirm;
    } catch (err) {
      els.webOutput.textContent = `Web error: ${err.message || err}`;
    }
  }

  async function runMessages(command) {
    try {
      const data = await api('/api/callsms', { action: 'command', command });
      els.msgOutput.textContent = data.result || data.error || '';
      state.pendingMsg = !!data.needs_confirm;
      if (state.pendingMsg) {
        els.msgOutput.textContent = data.confirm_prompt || data.result || els.msgOutput.textContent;
      }
    } catch (err) {
      els.msgOutput.textContent = `Messages error: ${err.message || err}`;
    }
  }

  async function confirmMessages(action) {
    try {
      const data = await api('/api/callsms', { action });
      els.msgOutput.textContent = data.result || data.error || '';
      state.pendingMsg = !!data.needs_confirm;
    } catch (err) {
      els.msgOutput.textContent = `Messages error: ${err.message || err}`;
    }
  }

  async function runSmartHome(command) {
    try {
      const data = await api('/api/smarthome', { action: 'control', command });
      els.homeOutput.textContent = data.result || data.error || '';
    } catch (err) {
      els.homeOutput.textContent = `Smart home error: ${err.message || err}`;
    }
  }

  async function runScene(scene) {
    try {
      const data = await api('/api/smarthome', { action: 'scene', scene });
      els.homeOutput.textContent = data.result || data.error || '';
    } catch (err) {
      els.homeOutput.textContent = `Scene error: ${err.message || err}`;
    }
  }

  async function loadSystem(query) {
    try {
      const data = await api('/api/system', { query });
      const payload = data.result || data.error || JSON.stringify(data, null, 2);
      els.sysOutput.textContent = typeof payload === 'string' ? payload : JSON.stringify(payload, null, 2);
    } catch (err) {
      els.sysOutput.textContent = `System error: ${err.message || err}`;
    }
  }

  // Events
  els.sendButton.addEventListener('click', submitChat);
  els.messageInput.addEventListener('keydown', e => {
    if (e.key === 'Enter') submitChat();
  });

  els.quickChips.addEventListener('click', e => {
    const btn = e.target.closest('[data-text]');
    if (!btn) return;
    els.messageInput.value = btn.dataset.text;
    submitChat();
  });

  els.clearChatBtn.addEventListener('click', async () => {
    await api('/api/clear', {}).catch(() => {});
    els.chatMessages.innerHTML = '';
    appendMessage('ai', 'Memory cleared. Ready for the next command. 🧹');
  });

  // Emoji bar toggle
  if (els.emojiToggleBtn && els.emojiBar) {
    els.emojiToggleBtn.addEventListener('click', () => {
      const isOpen = els.emojiBar.classList.toggle('open');
      els.emojiToggleBtn.classList.toggle('active', isOpen);
      // fun spin animation on toggle
      els.emojiToggleBtn.style.animation = 'none';
      requestAnimationFrame(() => {
        els.emojiToggleBtn.style.animation = '';
      });
    });

    els.emojiBar.addEventListener('click', e => {
      const btn = e.target.closest('[data-emoji]');
      if (!btn) return;
      const emoji = btn.dataset.emoji;
      els.messageInput.value += emoji;
      els.messageInput.focus();
      // fun wobble on the button
      btn.style.transform = 'scale(1.6) rotate(15deg)';
      setTimeout(() => { btn.style.transform = ''; }, 200);
    });
  }

  els.hamburger.addEventListener('click', openDrawer);
  els.drawerClose.addEventListener('click', closeDrawer);
  els.drawerBackdrop.addEventListener('click', closeDrawer);

  document.querySelectorAll('[data-panel-target]').forEach(btn => {
    btn.addEventListener('click', () => {
      const panel = btn.dataset.panelTarget;
      if (panel) setPanel(panel);
      closeDrawer();
    });
  });

  els.moduleTabs.addEventListener('click', e => {
    const btn = e.target.closest('[data-panel]');
    if (!btn) return;
    setPanel(btn.dataset.panel);
  });

  els.visStartBtn.addEventListener('click', () => startVisionPreview());
  els.visCaptureBtn.addEventListener('click', () => runVisionFrame('free'));
  els.visAnalyzeBtn.addEventListener('click', () => runVisionFrame('cloud'));
  els.visStopBtn.addEventListener('click', () => {
    stopVisionPreview();
    els.visionOutput.textContent = 'Camera stopped.';
  });
  els.visScreenBtn.addEventListener('click', runScreenVision);
  els.visQrBtn.addEventListener('click', runQrVision);
  els.visOcrBtn.addEventListener('click', runOcrVision);

  els.bookRefreshBtn.addEventListener('click', loadMovies);
  els.bookQuery.addEventListener('keydown', e => {
    if (e.key === 'Enter') loadMovies();
  });
  els.bookMovie.addEventListener('change', async () => {
    const movieId = els.bookMovie.value;
    const opt = els.bookMovie.selectedOptions[0];
    state.selectedMovie = movieId;
    state.selectedMovieTitle = opt?.dataset.title || opt?.textContent || '';
    state.selectedTheater = '';
    state.selectedShowtime = '';
    els.bookShows.innerHTML = '';
    if (movieId) {
      await loadTheaters(movieId);
    }
  });
  els.bookTheater.addEventListener('change', async () => {
    const theaterId = els.bookTheater.value;
    state.selectedTheater = theaterId;
    state.selectedShowtime = '';
    els.bookShows.innerHTML = '';
    if (state.selectedMovie && theaterId) {
      await loadShowtimes(state.selectedMovie, theaterId);
    }
  });
  els.bookCheckoutBtn.addEventListener('click', openCheckout);

  document.querySelectorAll('[data-calendar]').forEach(btn => {
    btn.addEventListener('click', () => loadCalendar(btn.dataset.calendar));
  });
  els.calAddBtn.addEventListener('click', addCalendarEvent);

  els.memSaveProfileBtn.addEventListener('click', saveProfile);
  els.memSavePlaceBtn.addEventListener('click', savePlace);
  els.memReloadBtn.addEventListener('click', loadMemory);

  els.webRunBtn.addEventListener('click', () => runWeb(els.webCommand.value.trim()));
  els.webConfirmBtn.addEventListener('click', () => confirmWeb('confirm'));
  els.webCancelBtn.addEventListener('click', () => confirmWeb('cancel'));
  els.webCommand.addEventListener('keydown', e => {
    if (e.key === 'Enter') runWeb(els.webCommand.value.trim());
  });

  els.msgDraftBtn.addEventListener('click', () => {
    const contact = els.msgContact.value.trim();
    const text = els.msgText.value.trim();
    if (!contact || !text) {
      els.msgOutput.textContent = 'Enter both contact and message.';
      return;
    }
    runMessages(`reply to ${contact} saying ${text}`);
  });
  els.msgConfirmBtn.addEventListener('click', () => confirmMessages('confirm'));
  els.msgCancelBtn.addEventListener('click', () => confirmMessages('cancel'));
  els.msgText.addEventListener('keydown', e => {
    if (e.key === 'Enter') els.msgDraftBtn.click();
  });

  els.homeRunBtn.addEventListener('click', () => runSmartHome(els.homeCommand.value.trim()));
  document.querySelectorAll('[data-scene]').forEach(btn => {
    btn.addEventListener('click', () => runScene(btn.dataset.scene));
  });
  document.querySelectorAll('[data-system]').forEach(btn => {
    btn.addEventListener('click', () => loadSystem(btn.dataset.system));
  });

  window.addEventListener('beforeunload', stopVisionPreview);

  // Initial load
  refreshStatus();
  loadMemory();
  loadMovies();
  loadCalendar('today');
  loadSystem('all');
  setPanel('chat');

  if (location.protocol === 'file:') {
    els.visionHint.textContent = 'Camera needs localhost or HTTPS to ask for permission.';
  }

  setInterval(refreshStatus, 30000);
});
