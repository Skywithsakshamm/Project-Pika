/**
 * Selvie Personal AI Assistant - Frontend Controller
 * Handles Voice Interaction, Audio Waveforms, WebSocket IPC, Panels & Settings.
 */

// Application State
const State = {
  IDLE: 'IDLE',
  LISTENING: 'LISTENING',
  THINKING: 'THINKING',
  SPEAKING: 'SPEAKING',
  ERROR: 'ERROR'
};

let currentState = State.IDLE;
let ws = null;
let speechRecognizer = null;
let isMuted = false;
let pendingConfirmationTicket = null;

// DOM Elements
const micBtn = document.getElementById('micBtn');
const stateText = document.getElementById('stateText');
const stateBadge = document.getElementById('stateBadge');
const statusDot = document.getElementById('statusDot');
const glowRing = document.getElementById('glowRing');
const dialogueText = document.getElementById('dialogueText');
const actionPill = document.getElementById('actionPill');
const actionPillText = document.getElementById('actionPillText');
const ttsAudioPlayer = document.getElementById('ttsAudioPlayer');
const canvas = document.getElementById('waveformCanvas');
const ctx = canvas.getContext('2d');

const panelDrawer = document.getElementById('panelDrawer');
const drawerToggleBtn = document.getElementById('drawerToggleBtn');
const closeDrawerBtn = document.getElementById('closeDrawerBtn');
const muteBtn = document.getElementById('muteBtn');
const minimizeBtn = document.getElementById('minimizeBtn');
const closeBtn = document.getElementById('closeBtn');

// Modals & Panels
const confirmModal = document.getElementById('confirmModal');
const confirmModalText = document.getElementById('confirmModalText');
const confirmApproveBtn = document.getElementById('confirmApproveBtn');
const confirmCancelBtn = document.getElementById('confirmCancelBtn');

// ----------------------------------------------------
// 1. STATE & UI CONTROLLER
// ----------------------------------------------------

function setState(newState, message = null) {
  currentState = newState;

  // Clear previous state classes
  micBtn.classList.remove('listening', 'speaking');
  glowRing.style.background = '';

  switch (newState) {
    case State.IDLE:
      stateText.textContent = 'Ready';
      statusDot.style.background = '#10b981';
      stateBadge.style.borderColor = 'rgba(139, 92, 246, 0.35)';
      glowRing.style.background = 'radial-gradient(circle, rgba(139, 92, 246, 0.35) 0%, transparent 70%)';
      break;

    case State.LISTENING:
      stateText.textContent = 'Listening...';
      statusDot.style.background = '#06b6d4';
      stateBadge.style.borderColor = '#06b6d4';
      micBtn.classList.add('listening');
      glowRing.style.background = 'radial-gradient(circle, rgba(6, 182, 212, 0.6) 0%, transparent 70%)';
      if (message) dialogueText.textContent = message;
      break;

    case State.THINKING:
      stateText.textContent = 'Thinking...';
      statusDot.style.background = '#f59e0b';
      stateBadge.style.borderColor = '#f59e0b';
      glowRing.style.background = 'radial-gradient(circle, rgba(245, 158, 11, 0.5) 0%, transparent 70%)';
      break;

    case State.SPEAKING:
      stateText.textContent = 'Speaking...';
      statusDot.style.background = '#ec4899';
      stateBadge.style.borderColor = '#ec4899';
      micBtn.classList.add('speaking');
      glowRing.style.background = 'radial-gradient(circle, rgba(236, 72, 153, 0.6) 0%, transparent 70%)';
      if (message) dialogueText.textContent = message;
      break;

    case State.ERROR:
      stateText.textContent = 'Error';
      statusDot.style.background = '#f43f5e';
      stateBadge.style.borderColor = '#f43f5e';
      if (message) dialogueText.textContent = message;
      break;
  }
}

function showActionPill(text) {
  actionPillText.textContent = text;
  actionPill.style.display = 'flex';
  setTimeout(() => {
    actionPill.style.display = 'none';
  }, 4500);
}

// ----------------------------------------------------
// 2. AUDIO WAVEFORM VISUALIZER
// ----------------------------------------------------

let animationFrameId;
let wavePhase = 0;

function drawWaveform() {
  ctx.clearRect(0, 0, canvas.width, canvas.height);
  const width = canvas.width;
  const height = canvas.height;
  const centerY = height / 2;
  const bars = 36;
  const barWidth = 4;
  const gap = (width - bars * barWidth) / (bars - 1);

  wavePhase += 0.05;

  for (let i = 0; i < bars; i++) {
    let barHeight = 4;

    if (currentState === State.LISTENING) {
      // Dynamic reactive listening waves
      barHeight = 6 + Math.sin(wavePhase * 2.5 + i * 0.4) * 16 + Math.cos(i * 0.3) * 8;
    } else if (currentState === State.SPEAKING) {
      // Harmonic voice speech waves
      barHeight = 10 + Math.abs(Math.sin(wavePhase * 3.5 + i * 0.35)) * 26 + Math.sin(i * 0.8) * 6;
    } else if (currentState === State.THINKING) {
      // Traveling thought ripple
      barHeight = 6 + Math.sin(wavePhase * 4 + i * 0.5) * 12;
    } else {
      // Subtle idle breathing
      barHeight = 3 + Math.sin(wavePhase + i * 0.2) * 3;
    }

    barHeight = Math.max(3, Math.min(height - 4, barHeight));
    const x = i * (barWidth + gap);
    const y = centerY - barHeight / 2;

    // Gradient styling
    const grad = ctx.createLinearGradient(0, y, 0, y + barHeight);
    if (currentState === State.LISTENING) {
      grad.addColorStop(0, '#06b6d4');
      grad.addColorStop(1, '#3b82f6');
    } else if (currentState === State.SPEAKING) {
      grad.addColorStop(0, '#f43f5e');
      grad.addColorStop(1, '#8b5cf6');
    } else {
      grad.addColorStop(0, '#8b5cf6');
      grad.addColorStop(1, '#6366f1');
    }

    ctx.fillStyle = grad;
    ctx.beginPath();
    ctx.roundRect(x, y, barWidth, barHeight, 2);
    ctx.fill();
  }

  animationFrameId = requestAnimationFrame(drawWaveform);
}

// ----------------------------------------------------
// 3. SPEECH SYNTHESIS & PLAYBACK
// ----------------------------------------------------

async function speakAudioBase64(base64Data, textFallback) {
  if (isMuted) return;

  if (base64Data && base64Data.startsWith('data:audio')) {
    try {
      ttsAudioPlayer.src = base64Data;
      setState(State.SPEAKING);
      await ttsAudioPlayer.play();
      ttsAudioPlayer.onended = () => {
        setState(State.IDLE);
      };
      return;
    } catch (e) {
      console.warn('Audio playback failed, falling back to Web Speech API:', e);
    }
  }

  // Browser Web Speech fallback
  if ('speechSynthesis' in window && textFallback) {
    window.speechSynthesis.cancel();
    const utterance = new SpeechSynthesisUtterance(textFallback);
    const voices = window.speechSynthesis.getVoices();
    const inVoice = voices.find(v => v.lang.includes('IN') || v.name.includes('India') || v.name.includes('Neerja'));
    if (inVoice) utterance.voice = inVoice;
    utterance.rate = 1.0;
    utterance.pitch = 1.05;

    utterance.onstart = () => setState(State.SPEAKING);
    utterance.onend = () => setState(State.IDLE);
    utterance.onerror = () => setState(State.IDLE);

    window.speechSynthesis.speak(utterance);
  } else {
    setState(State.IDLE);
  }
}

// ----------------------------------------------------
// 4. SPEECH RECOGNITION (STT)
// ----------------------------------------------------

function initSpeechRecognition() {
  const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
  if (!SpeechRecognition) {
    console.warn('Web Speech API not supported in this browser environment.');
    return;
  }

  speechRecognizer = new SpeechRecognition();
  speechRecognizer.continuous = false;
  speechRecognizer.interimResults = true;
  speechRecognizer.lang = 'en-IN'; // Indian English / Hinglish

  speechRecognizer.onstart = () => {
    setState(State.LISTENING, "I'm listening...");
  };

  speechRecognizer.onresult = (event) => {
    let transcript = '';
    for (let i = event.resultIndex; i < event.results.length; ++i) {
      transcript += event.results[i][0].transcript;
    }
    dialogueText.textContent = `"${transcript}"`;

    if (event.results[0].isFinal) {
      handleFinalUserInput(transcript);
    }
  };

  speechRecognizer.onerror = (event) => {
    console.error('Speech recognition error:', event.error);
    if (event.error !== 'no-speech') {
      setState(State.ERROR, "I couldn't hear that clearly. Try speaking again.");
      setTimeout(() => setState(State.IDLE), 3000);
    } else {
      setState(State.IDLE);
    }
  };

  speechRecognizer.onend = () => {
    if (currentState === State.LISTENING) {
      setState(State.IDLE);
    }
  };
}

function toggleListening() {
  if (currentState === State.LISTENING) {
    if (speechRecognizer) speechRecognizer.stop();
    setState(State.IDLE);
  } else {
    if (ttsAudioPlayer) ttsAudioPlayer.pause();
    if (window.speechSynthesis) window.speechSynthesis.cancel();

    if (speechRecognizer) {
      try {
        speechRecognizer.start();
      } catch (e) {
        speechRecognizer.stop();
        setTimeout(() => speechRecognizer.start(), 100);
      }
    } else {
      // Fallback: prompt for text input if mic permission or API unavailable
      const promptText = prompt("Speak to Selvie (or type your command):", "");
      if (promptText) {
        handleFinalUserInput(promptText);
      }
    }
  }
}

// Expose globally for Python desktop wrapper (Ctrl+Space trigger)
window.selvieToggleListening = toggleListening;

// ----------------------------------------------------
// 5. MESSAGE PIPELINE & BACKEND IPC
// ----------------------------------------------------

async function handleFinalUserInput(text) {
  const clean = text.trim();
  if (!clean) return;

  setState(State.THINKING, "Let me think...");

  // Send via WebSocket if connected, otherwise fallback to HTTP POST /api/chat
  if (ws && ws.readyState === WebSocket.OPEN) {
    ws.send(jsonStr({ type: 'user_message', text: clean }));
  } else {
    try {
      const res = await fetch('/api/chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ message: clean })
      });
      const data = await res.json();
      handleAssistantResponse(data);
    } catch (e) {
      console.error('API Error:', e);
      setState(State.ERROR, "Couldn't reach Selvie's brain. Is the backend running?");
    }
  }
}

function handleAssistantResponse(data) {
  const reply = data.reply || "Done!";
  dialogueText.textContent = reply;

  // Check if tools were executed
  if (data.tools_executed && data.tools_executed.length > 0) {
    const summary = data.tools_executed.map(t => t.tool.replace('_', ' ')).join(', ');
    showActionPill(`Executed: ${summary}`);
    refreshAllPanels();
  }

  // Check if action requires confirmation
  if (data.pending_confirmation) {
    pendingConfirmationTicket = data.pending_confirmation.ticket_id;
    confirmModalText.textContent = data.pending_confirmation.confirmation_prompt;
    confirmModal.style.display = 'flex';
  }

  // Speak response
  speakAudioBase64(data.audio_base64, reply);
}

function connectWebSocket() {
  const loc = window.location;
  const wsUrl = (loc.protocol === 'https:' ? 'wss://' : 'ws://') + loc.host + '/ws';
  ws = new WebSocket(wsUrl);

  ws.onopen = () => {
    console.log('[Selvie WS] Connected to backend');
  };

  ws.onmessage = (event) => {
    try {
      const msg = JSON.parse(event.data);
      if (msg.type === 'assistant_response') {
        handleAssistantResponse(msg);
      } else if (msg.type === 'reminder_triggered') {
        // Voice alert + Pill
        showActionPill(`⏰ Reminder: ${msg.reminder.message}`);
        dialogueText.textContent = msg.announcement;
        speakAudioBase64(msg.audio_base64, msg.announcement);
        refreshReminders();
      } else if (msg.type === 'state_change') {
        setState(msg.state);
      }
    } catch (e) {
      console.error('[Selvie WS] Parse error:', e);
    }
  };

  ws.onclose = () => {
    console.log('[Selvie WS] Reconnecting in 3s...');
    setTimeout(connectWebSocket, 3000);
  };
}

function jsonStr(obj) {
  return JSON.stringify(obj);
}

// ----------------------------------------------------
// 6. INITIAL STARTUP GREETING
// ----------------------------------------------------

async function loadInitialGreeting() {
  try {
    const res = await fetch('/api/greeting');
    const data = await res.json();
    dialogueText.textContent = data.reply;
    // Play warm voice
    if (data.audio_base64) {
      speakAudioBase64(data.audio_base64, data.reply);
    }
  } catch (e) {
    console.warn('Initial greeting fetch failed:', e);
  }
}

// ----------------------------------------------------
// 7. PANELS & DATA MANAGEMENT
// ----------------------------------------------------

async function refreshTasks() {
  try {
    const res = await fetch('/api/tasks');
    const tasks = await res.json();
    const container = document.getElementById('taskListContainer');
    document.getElementById('taskCountBadge').textContent = `${tasks.length} tasks`;

    container.innerHTML = tasks.map(t => `
      <div class="task-card ${t.status === 'Completed' ? 'completed' : ''}" data-id="${t.id}">
        <div class="task-left">
          <button class="task-check" onclick="completeTask(${t.id})">
            ${t.status === 'Completed' ? '✓' : ''}
          </button>
          <div>
            <div class="task-title">${t.title}</div>
            <div style="font-size: 10.5px; color: var(--text-muted);">
              ${t.duration_minutes ? t.duration_minutes + 'm • ' : ''}${t.due_time || 'Today'}
            </div>
          </div>
        </div>
        <div style="display:flex; align-items:center; gap:8px;">
          <span class="task-prio-badge prio-${t.priority.toLowerCase()}">${t.priority}</span>
          <button class="icon-btn" onclick="deleteTask(${t.id})" title="Delete" style="width:24px; height:24px;">×</button>
        </div>
      </div>
    `).join('') || '<p style="color:var(--text-muted); font-size:12px; text-align:center;">No tasks yet. Say "Add study probability" to create one!</p>';
  } catch (e) {
    console.error('Failed to load tasks:', e);
  }
}

async function completeTask(id) {
  await fetch(`/api/tasks/${id}/complete`, { method: 'POST' });
  refreshTasks();
  refreshSchedule();
}

async function deleteTask(id) {
  await fetch(`/api/tasks/${id}`, { method: 'DELETE' });
  refreshTasks();
  refreshSchedule();
}

async function refreshSchedule() {
  try {
    const res = await fetch('/api/schedule');
    const data = await res.json();
    const container = document.getElementById('scheduleTimeline');
    const stressBox = document.getElementById('stressAlertBox');
    const stressText = document.getElementById('stressAlertText');

    if (data.notes) {
      stressText.textContent = data.notes;
      stressBox.style.display = 'flex';
    } else {
      stressBox.style.display = 'none';
    }

    container.innerHTML = data.blocks.map(b => `
      <div class="timeline-block ${b.type === 'break' ? 'break' : ''}">
        <div class="time-slot">${b.start_time} - ${b.end_time}</div>
        <div class="slot-info">
          <div class="slot-title">${b.title}</div>
          <div style="font-size: 10.5px; color: var(--text-muted); text-transform: capitalize;">${b.type} block</div>
        </div>
      </div>
    `).join('') || '<p style="color:var(--text-muted); font-size:12px;">No schedule generated yet. Ask Selvie: "Plan my day".</p>';
  } catch (e) {
    console.error('Failed to load schedule:', e);
  }
}

async function refreshReminders() {
  try {
    const res = await fetch('/api/reminders');
    const reminders = await res.json();
    const container = document.getElementById('remindersContainer');

    container.innerHTML = reminders.map(r => `
      <div class="task-card">
        <div class="task-left">
          <span>⏰</span>
          <div>
            <div class="task-title">${r.message}</div>
            <div style="font-size: 10.5px; color: var(--accent-cyan);">${new Date(r.trigger_time).toLocaleTimeString([], {hour: '2-digit', minute:'2-digit'})}</div>
          </div>
        </div>
        <button class="icon-btn" onclick="deleteReminder(${r.id})" style="width:24px; height:24px;">×</button>
      </div>
    `).join('') || '<p style="color:var(--text-muted); font-size:12px; text-align:center;">No active reminders. Say "Remind me at 7 PM to call teammate".</p>';
  } catch (e) {
    console.error('Failed to load reminders:', e);
  }
}

async function deleteReminder(id) {
  await fetch(`/api/reminders/${id}`, { method: 'DELETE' });
  refreshReminders();
}

async function refreshApps() {
  try {
    const res = await fetch('/api/apps');
    const apps = await res.json();
    const grid = document.getElementById('appsGrid');

    const iconMap = {
      'YouTube': '▶️',
      'Spotify': '🎧',
      'WhatsApp': '💬',
      'Chrome': '🌐',
      'VS Code': '💻',
      'Notion': '📝',
      'Discord': '🎮',
      'File Explorer': '📁',
      'Windows Settings': '⚙️',
      'GitHub': '🐙',
      'ChatGPT': '🤖',
      'Gmail': '✉️',
      'Google Drive': '📂'
    };

    grid.innerHTML = apps.map(a => `
      <div class="app-tile" onclick="launchApp('${a.name}')">
        <span style="font-size:20px;">${iconMap[a.name] || '🚀'}</span>
        <span>${a.name}</span>
      </div>
    `).join('');
  } catch (e) {
    console.error('Failed to load apps:', e);
  }
}

async function launchApp(name) {
  showActionPill(`Opening ${name}...`);
  await fetch(`/api/apps/launch/${encodeURIComponent(name)}`, { method: 'POST' });
}

async function refreshMemory() {
  try {
    const res = await fetch('/api/memories');
    const memories = await res.json();
    const container = document.getElementById('memoryListContainer');

    container.innerHTML = memories.map(m => `
      <div class="task-card">
        <div>
          <div style="font-size: 11px; color: var(--accent-purple); font-weight:600; text-transform:uppercase;">${m.key}</div>
          <div style="font-size: 12.5px; color: var(--text-primary); margin-top:2px;">${m.content}</div>
        </div>
        <button class="icon-btn" onclick="forgetMemory('${m.key}')" style="width:24px; height:24px;">×</button>
      </div>
    `).join('') || '<p style="color:var(--text-muted); font-size:12px;">No memories yet. Selvie learns as you talk!</p>';
  } catch (e) {
    console.error('Failed to load memory:', e);
  }
}

async function forgetMemory(key) {
  await fetch(`/api/memories/${encodeURIComponent(key)}`, { method: 'DELETE' });
  refreshMemory();
}

async function loadSettings() {
  try {
    const res = await fetch('/api/settings');
    const s = await res.json();
    document.getElementById('settingUserName').value = s.user_name || 'Saksham';
    document.getElementById('settingVoice').value = s.tts_voice || 'en-IN-NeerjaExpressiveNeural';
    document.getElementById('settingLLM').value = s.llm_provider || 'ollama';
    document.getElementById('settingAutoStart').checked = s.auto_start_windows;
    document.getElementById('settingQuietMode').checked = s.quiet_mode;
  } catch (e) {
    console.error('Failed to load settings:', e);
  }
}

async function saveSettings() {
  const payload = {
    user_name: document.getElementById('settingUserName').value,
    tts_voice: document.getElementById('settingVoice').value,
    llm_provider: document.getElementById('settingLLM').value,
    auto_start: document.getElementById('settingAutoStart').checked,
    quiet_mode: document.getElementById('settingQuietMode').checked
  };

  await fetch('/api/settings', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload)
  });

  showActionPill("Settings saved!");
}

function refreshAllPanels() {
  refreshTasks();
  refreshSchedule();
  refreshReminders();
  refreshApps();
  refreshMemory();
}

// ----------------------------------------------------
// 8. EVENT LISTENERS
// ----------------------------------------------------

micBtn.addEventListener('click', () => {
  toggleListening();
});

// Quick Chips Click
document.querySelectorAll('.chip').forEach(chip => {
  chip.addEventListener('click', () => {
    const cmd = chip.getAttribute('data-cmd');
    handleFinalUserInput(cmd);
  });
});

// Panel Drawer Toggle
drawerToggleBtn.addEventListener('click', () => {
  panelDrawer.classList.toggle('open');
  if (panelDrawer.classList.contains('open')) {
    refreshAllPanels();
  }
});

closeDrawerBtn.addEventListener('click', () => {
  panelDrawer.classList.remove('open');
});

// Drawer Tabs
document.querySelectorAll('.tab-btn').forEach(btn => {
  btn.addEventListener('click', () => {
    document.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
    document.querySelectorAll('.tab-pane').forEach(p => p.classList.remove('active'));
    btn.classList.add('active');
    const target = btn.getAttribute('data-tab');
    document.getElementById(target).classList.add('active');
  });
});

// Add Task
document.getElementById('addTaskBtn').addEventListener('click', async () => {
  const title = document.getElementById('newTaskInput').value.trim();
  const priority = document.getElementById('newTaskPriority').value;
  if (!title) return;

  await fetch('/api/tasks', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ title, priority, due_date: 'today' })
  });

  document.getElementById('newTaskInput').value = '';
  refreshTasks();
  refreshSchedule();
});

// Add Reminder
document.getElementById('addReminderBtn').addEventListener('click', async () => {
  const message = document.getElementById('newReminderText').value.trim();
  const time = document.getElementById('newReminderTime').value.trim();
  if (!message || !time) return;

  await fetch('/api/reminders', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ message, datetime: time })
  });

  document.getElementById('newReminderText').value = '';
  document.getElementById('newReminderTime').value = '';
  refreshReminders();
});

// Regenerate Schedule
document.getElementById('regenerateScheduleBtn').addEventListener('click', async () => {
  await fetch('/api/schedule/generate', { method: 'POST' });
  refreshSchedule();
});

// Settings & Clear Memory
document.getElementById('saveSettingsBtn').addEventListener('click', saveSettings);
document.getElementById('clearMemoryBtn').addEventListener('click', async () => {
  if (confirm("Clear all stored memories?")) {
    await fetch('/api/memories/all', { method: 'DELETE' });
    refreshMemory();
  }
});

// Confirmation Modal
confirmApproveBtn.addEventListener('click', async () => {
  if (pendingConfirmationTicket) {
    confirmModal.style.display = 'none';
    if (ws && ws.readyState === WebSocket.OPEN) {
      ws.send(jsonStr({ type: 'confirm_action', ticket_id: pendingConfirmationTicket, approved: true }));
    } else {
      const res = await fetch('/api/confirm', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ ticket_id: pendingConfirmationTicket, approved: true })
      });
      const d = await res.json();
      handleAssistantResponse(d);
    }
    pendingConfirmationTicket = null;
  }
});

confirmCancelBtn.addEventListener('click', async () => {
  if (pendingConfirmationTicket) {
    confirmModal.style.display = 'none';
    if (ws && ws.readyState === WebSocket.OPEN) {
      ws.send(jsonStr({ type: 'confirm_action', ticket_id: pendingConfirmationTicket, approved: false }));
    } else {
      await fetch('/api/confirm', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ ticket_id: pendingConfirmationTicket, approved: false })
      });
    }
    pendingConfirmationTicket = null;
  }
});

// Window Controls (PySide6 / WebEngine integration)
minimizeBtn.addEventListener('click', () => {
  if (window.pywebview && window.pywebview.api) {
    window.pywebview.api.minimize();
  } else {
    // In browser or QWebEngine, close drawer or minimize
    panelDrawer.classList.remove('open');
  }
});

closeBtn.addEventListener('click', () => {
  if (window.pywebview && window.pywebview.api) {
    window.pywebview.api.close();
  } else {
    panelDrawer.classList.remove('open');
  }
});

// Mute Audio Toggle
muteBtn.addEventListener('click', () => {
  isMuted = !isMuted;
  if (isMuted) {
    ttsAudioPlayer.pause();
    if (window.speechSynthesis) window.speechSynthesis.cancel();
    muteBtn.style.color = 'var(--accent-rose)';
  } else {
    muteBtn.style.color = 'var(--text-secondary)';
  }
});

// Keyboard shortcut (Ctrl + Space within window)
window.addEventListener('keydown', (e) => {
  if (e.ctrlKey && e.code === 'Space') {
    e.preventDefault();
    toggleListening();
  }
});

// ----------------------------------------------------
// 9. INIT
// ----------------------------------------------------

window.addEventListener('DOMContentLoaded', () => {
  drawWaveform();
  initSpeechRecognition();
  connectWebSocket();
  loadInitialGreeting();
  refreshAllPanels();
  loadSettings();
});
