/**
 * Writing view: scene display, streaming, prompt input.
 */

import * as api from './api.js';
import { showToast } from './app.js';

let socket = null;
let currentStory = null;
let currentLeafId = null;
let isGenerating = false;

// DOM refs
let scenesContainer;
let promptInput;
let continueBtn;
let branchBtn;
let generatingIndicator;
let activeSceneEl = null;

let contentModeBtn;
let autoIllustrateBtn;

export function init(ws) {
  socket = ws;
  scenesContainer = document.getElementById('scenes-container');
  promptInput = document.getElementById('prompt-input');
  continueBtn = document.getElementById('continue-btn');
  branchBtn = document.getElementById('branch-btn');
  generatingIndicator = document.getElementById('generating-indicator');
  contentModeBtn = document.getElementById('content-mode-btn');
  autoIllustrateBtn = document.getElementById('auto-illustrate-btn');

  continueBtn.addEventListener('click', handleContinue);
  branchBtn.addEventListener('click', handleBranch);
  contentModeBtn.addEventListener('click', handleToggleContentMode);
  if (autoIllustrateBtn) {
    autoIllustrateBtn.addEventListener('click', handleToggleAutoIllustrate);
  }

  promptInput.addEventListener('keydown', (e) => {
    if (e.key === 'Enter' && (e.ctrlKey || e.metaKey)) {
      e.preventDefault();
      handleContinue();
    }
  });

  // WebSocket handlers
  socket.onToken = handleToken;
  socket.onPhase = handlePhase;
  socket.onComplete = handleComplete;
  socket.onIllustration = handleIllustration;
  socket.onError = handleWsError;
}

export async function loadStory(story, openingPrompt = null) {
  currentStory = story;
  currentLeafId = story.current_leaf_id;

  document.getElementById('story-title-display').textContent = story.title;
  updateContentModeDisplay(story.content_mode);
  updateAutoIllustrateDisplay(story.auto_illustrate);
  scenesContainer.innerHTML = '';

  // Connect WebSocket (await so send() works immediately after)
  await socket.connect();

  // Load existing scenes
  if (currentLeafId) {
    try {
      const path = await api.getNodePath(currentLeafId);
      for (const node of path) {
        if (node.node_type === 'root') continue;
        appendScene(node);
      }
      scrollToBottom();
    } catch (err) {
      showToast('Failed to load scenes: ' + err.message, 'error');
    }
  }

  // Auto-generate opening if provided
  if (openingPrompt) {
    promptInput.value = '';
    startGeneration();
    socket.generate(currentStory.id, openingPrompt);
  }

  setInputEnabled(true);
}

export function unload() {
  // Clean up active generation if in progress
  if (activeSceneEl) {
    const cursor = activeSceneEl.querySelector('.cursor');
    if (cursor) cursor.remove();
    // Remove empty partial scenes
    const content = activeSceneEl.querySelector('.scene-content');
    if (content && !content.textContent.trim()) {
      activeSceneEl.remove();
    }
  }
  if (isGenerating) {
    generatingIndicator.classList.add('hidden');
  }
  socket.disconnect();
  currentStory = null;
  currentLeafId = null;
  isGenerating = false;
  activeSceneEl = null;
}

export function getCurrentStory() {
  return currentStory;
}

export function getCurrentLeafId() {
  return currentLeafId;
}

export async function navigateToNode(nodeId) {
  // Reload scenes from root to this node
  currentLeafId = nodeId;
  await reloadPath(nodeId);
}

// ── Internal ─────────────────────────────────────────────────────────

async function reloadPath(nodeId) {
  try {
    const path = await api.getNodePath(nodeId);
    scenesContainer.innerHTML = '';
    for (const node of path) {
      if (node.node_type === 'root') continue;
      appendScene(node);
    }
    scrollToBottom();

    // Update story's current_leaf
    currentLeafId = nodeId;
  } catch (err) {
    showToast('Failed to load path: ' + err.message, 'error');
  }
}

function appendScene(node) {
  const scene = document.createElement('div');
  scene.className = 'scene';
  scene.dataset.nodeId = node.id;

  const meta = document.createElement('div');
  meta.className = 'scene-meta';
  meta.textContent = `Scene \u00b7 ${new Date(node.created_at).toLocaleTimeString()}`;

  // Illustration (shown above content if available)
  const illustrationDiv = document.createElement('div');
  illustrationDiv.className = 'scene-illustration';
  if (node.illustration_path) {
    const img = document.createElement('img');
    img.src = `/static/images/${node.illustration_path}`;
    img.alt = 'Scene illustration';
    img.loading = 'lazy';
    illustrationDiv.appendChild(img);
  }

  const content = document.createElement('div');
  content.className = 'scene-content';
  content.textContent = node.content;

  // Scene actions (illustrate button, visible on hover)
  const actions = document.createElement('div');
  actions.className = 'scene-actions';
  const illustrateBtn = document.createElement('button');
  illustrateBtn.className = 'btn btn-ghost btn-small scene-illustrate-btn';
  illustrateBtn.textContent = node.illustration_path ? 'Re-illustrate' : 'Illustrate';
  illustrateBtn.addEventListener('click', () => handleIllustrate(node.id, scene));
  actions.appendChild(illustrateBtn);

  scene.appendChild(meta);
  scene.appendChild(illustrationDiv);
  scene.appendChild(content);
  scene.appendChild(actions);

  // Show beat if present (loaded from API)
  if (node.beat) {
    const details = document.createElement('details');
    details.className = 'scene-beat';
    const summary = document.createElement('summary');
    summary.textContent = 'Scene Beat';
    details.appendChild(summary);

    const beatContent = document.createElement('div');
    beatContent.className = 'scene-beat-content';
    const beat = node.beat;
    let html = '';
    if (beat.setting) html += `<div><strong>Setting:</strong> ${escapeHtml(beat.setting)}</div>`;
    if (beat.characters_present?.length) html += `<div><strong>Characters:</strong> ${beat.characters_present.map(escapeHtml).join(', ')}</div>`;
    if (beat.key_events?.length) html += `<div><strong>Events:</strong><ul>${beat.key_events.map(e => `<li>${escapeHtml(e)}</li>`).join('')}</ul></div>`;
    if (beat.emotional_tone) html += `<div><strong>Tone:</strong> ${escapeHtml(beat.emotional_tone)}</div>`;
    if (beat.continuity_notes) html += `<div><strong>Continuity:</strong> ${escapeHtml(beat.continuity_notes)}</div>`;
    beatContent.innerHTML = html;
    details.appendChild(beatContent);
    scene.appendChild(details);
  }

  scenesContainer.appendChild(scene);

  return scene;
}

function startGeneration() {
  isGenerating = true;
  setInputEnabled(false);
  generatingIndicator.classList.remove('hidden');

  // Create a new scene div with cursor
  const scene = document.createElement('div');
  scene.className = 'scene';

  const meta = document.createElement('div');
  meta.className = 'scene-meta';
  meta.textContent = 'Scene \u00b7 generating...';

  const content = document.createElement('div');
  content.className = 'scene-content';

  const cursor = document.createElement('span');
  cursor.className = 'cursor';
  content.appendChild(cursor);

  scene.appendChild(meta);
  scene.appendChild(content);
  scenesContainer.appendChild(scene);

  activeSceneEl = scene;
  scrollToBottom();
}

function handlePhase(phase) {
  if (!generatingIndicator) return;
  const label = generatingIndicator.querySelector('.generating-label');
  if (label) {
    if (phase === 'planning') {
      label.textContent = 'Planning scene...';
    } else if (phase === 'writing') {
      label.textContent = 'Writing...';
    }
  }
}

function handleToken(text) {
  if (!activeSceneEl) return;
  const content = activeSceneEl.querySelector('.scene-content');
  const cursor = content.querySelector('.cursor');
  // Insert text before cursor
  if (cursor) {
    content.insertBefore(document.createTextNode(text), cursor);
  } else {
    content.appendChild(document.createTextNode(text));
  }
  scrollToBottom();
}

function handleComplete(node) {
  isGenerating = false;
  setInputEnabled(true);
  generatingIndicator.classList.add('hidden');

  // Reset generating label for next time
  const label = generatingIndicator.querySelector('.generating-label');
  if (label) label.textContent = 'Generating...';

  if (activeSceneEl) {
    // Remove cursor
    const cursor = activeSceneEl.querySelector('.cursor');
    if (cursor) cursor.remove();

    // Update meta
    const meta = activeSceneEl.querySelector('.scene-meta');
    meta.textContent = `Scene \u00b7 ${new Date(node.created_at).toLocaleTimeString()}`;

    // Store node ID
    activeSceneEl.dataset.nodeId = node.id;

    // Show beat as expandable details if present
    if (node.beat) {
      const details = document.createElement('details');
      details.className = 'scene-beat';
      const summary = document.createElement('summary');
      summary.textContent = 'Scene Beat';
      details.appendChild(summary);

      const beatContent = document.createElement('div');
      beatContent.className = 'scene-beat-content';
      const beat = node.beat;
      let html = '';
      if (beat.setting) html += `<div><strong>Setting:</strong> ${escapeHtml(beat.setting)}</div>`;
      if (beat.characters_present?.length) html += `<div><strong>Characters:</strong> ${beat.characters_present.map(escapeHtml).join(', ')}</div>`;
      if (beat.key_events?.length) html += `<div><strong>Events:</strong><ul>${beat.key_events.map(e => `<li>${escapeHtml(e)}</li>`).join('')}</ul></div>`;
      if (beat.emotional_tone) html += `<div><strong>Tone:</strong> ${escapeHtml(beat.emotional_tone)}</div>`;
      if (beat.continuity_notes) html += `<div><strong>Continuity:</strong> ${escapeHtml(beat.continuity_notes)}</div>`;
      beatContent.innerHTML = html;
      details.appendChild(beatContent);
      activeSceneEl.appendChild(details);
    }
  }

  // Show continuity warnings as toasts
  if (node.continuity_warnings?.length) {
    for (const warning of node.continuity_warnings) {
      showToast(`Continuity: ${warning}`, 'error');
    }
  }

  currentLeafId = node.id;
  activeSceneEl = null;

  // Dispatch event for tree/entity refresh
  document.dispatchEvent(new CustomEvent('scene-complete', { detail: { node } }));
}

function escapeHtml(text) {
  const div = document.createElement('div');
  div.textContent = text;
  return div.innerHTML;
}

function handleWsError(message, errorType, service) {
  isGenerating = false;
  setInputEnabled(true);
  generatingIndicator.classList.add('hidden');

  if (activeSceneEl) {
    const cursor = activeSceneEl.querySelector('.cursor');
    if (cursor) cursor.remove();
    // If the scene is empty, remove it
    const content = activeSceneEl.querySelector('.scene-content');
    if (!content.textContent.trim()) {
      activeSceneEl.remove();
    }
  }
  activeSceneEl = null;

  // Show user-friendly messages based on error type
  let displayMsg = message;
  if (errorType === 'service_unavailable') {
    displayMsg = `${service || 'Service'} is not available. Please check that it's running and try again.`;
  } else if (errorType === 'service_timeout') {
    displayMsg = `${service || 'Service'} took too long to respond. Try again or use a shorter prompt.`;
  } else if (errorType === 'generation_error') {
    displayMsg = `Generation failed (${service || 'unknown'}). Please try again.`;
  }

  showToast(displayMsg, 'error');
}

function handleContinue() {
  if (isGenerating || !currentStory) return;
  const prompt = promptInput.value.trim();
  if (!prompt) {
    showToast('Enter a direction for the next scene', 'error');
    return;
  }

  promptInput.value = '';
  startGeneration();
  socket.generate(currentStory.id, prompt, currentLeafId);
}

function handleBranch() {
  if (isGenerating || !currentStory || !currentLeafId) return;
  const prompt = promptInput.value.trim();
  if (!prompt) {
    showToast('Enter an alternative direction for branching', 'error');
    return;
  }

  promptInput.value = '';
  startGeneration();
  socket.branch(currentStory.id, currentLeafId, prompt);
}

function setInputEnabled(enabled) {
  promptInput.disabled = !enabled;
  continueBtn.disabled = !enabled;
  branchBtn.disabled = !enabled;
}

function updateContentModeDisplay(mode) {
  if (!contentModeBtn) return;
  const isSafe = mode === 'safe';
  contentModeBtn.textContent = isSafe ? 'Safe' : 'Unrestricted';
  contentModeBtn.classList.toggle('mode-safe', isSafe);
  contentModeBtn.classList.toggle('mode-unrestricted', !isSafe);
}

async function handleToggleContentMode() {
  if (!currentStory || isGenerating) return;
  const newMode = currentStory.content_mode === 'safe' ? 'unrestricted' : 'safe';
  try {
    const updated = await api.updateStory(currentStory.id, { content_mode: newMode });
    currentStory.content_mode = updated.content_mode;
    updateContentModeDisplay(updated.content_mode);
    showToast(`Content mode: ${updated.content_mode}`, 'success');
  } catch (err) {
    showToast('Failed to update content mode: ' + err.message, 'error');
  }
}

async function handleIllustrate(nodeId, sceneEl) {
  const btn = sceneEl.querySelector('.scene-illustrate-btn');
  if (btn) {
    btn.disabled = true;
    btn.textContent = 'Illustrating...';
  }
  try {
    const updated = await api.illustrateNode(nodeId);
    if (updated.illustration_path) {
      const illustrationDiv = sceneEl.querySelector('.scene-illustration');
      illustrationDiv.innerHTML = '';
      const img = document.createElement('img');
      img.src = `/static/images/${updated.illustration_path}`;
      img.alt = 'Scene illustration';
      illustrationDiv.appendChild(img);
      if (btn) btn.textContent = 'Re-illustrate';
      showToast('Illustration generated', 'success');
    }
  } catch (err) {
    showToast('Illustration failed: ' + err.message, 'error');
  } finally {
    if (btn) btn.disabled = false;
  }
}

function handleIllustration(nodeId, path) {
  // Handle auto-illustrate WebSocket notification
  const sceneEl = scenesContainer.querySelector(`.scene[data-node-id="${nodeId}"]`);
  if (!sceneEl) return;
  const illustrationDiv = sceneEl.querySelector('.scene-illustration');
  if (!illustrationDiv) return;
  illustrationDiv.innerHTML = '';
  const img = document.createElement('img');
  img.src = path;
  img.alt = 'Scene illustration';
  illustrationDiv.appendChild(img);
  const btn = sceneEl.querySelector('.scene-illustrate-btn');
  if (btn) btn.textContent = 'Re-illustrate';
}

function updateAutoIllustrateDisplay(enabled) {
  if (!autoIllustrateBtn) return;
  autoIllustrateBtn.textContent = enabled ? 'Auto-Illust: On' : 'Auto-Illust: Off';
  autoIllustrateBtn.classList.toggle('active', !!enabled);
}

async function handleToggleAutoIllustrate() {
  if (!currentStory || isGenerating) return;
  const newVal = !currentStory.auto_illustrate;
  try {
    const updated = await api.updateStory(currentStory.id, { auto_illustrate: newVal });
    currentStory.auto_illustrate = updated.auto_illustrate;
    updateAutoIllustrateDisplay(updated.auto_illustrate);
    showToast(`Auto-illustrate: ${updated.auto_illustrate ? 'on' : 'off'}`, 'success');
  } catch (err) {
    showToast('Failed to toggle auto-illustrate: ' + err.message, 'error');
  }
}

function scrollToBottom() {
  scenesContainer.scrollTop = scenesContainer.scrollHeight;
}
