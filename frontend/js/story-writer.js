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

export function init(ws) {
  socket = ws;
  scenesContainer = document.getElementById('scenes-container');
  promptInput = document.getElementById('prompt-input');
  continueBtn = document.getElementById('continue-btn');
  branchBtn = document.getElementById('branch-btn');
  generatingIndicator = document.getElementById('generating-indicator');
  contentModeBtn = document.getElementById('content-mode-btn');

  continueBtn.addEventListener('click', handleContinue);
  branchBtn.addEventListener('click', handleBranch);
  contentModeBtn.addEventListener('click', handleToggleContentMode);

  promptInput.addEventListener('keydown', (e) => {
    if (e.key === 'Enter' && (e.ctrlKey || e.metaKey)) {
      e.preventDefault();
      handleContinue();
    }
  });

  // WebSocket handlers
  socket.onToken = handleToken;
  socket.onComplete = handleComplete;
  socket.onError = handleWsError;
}

export async function loadStory(story, openingPrompt = null) {
  currentStory = story;
  currentLeafId = story.current_leaf_id;

  document.getElementById('story-title-display').textContent = story.title;
  updateContentModeDisplay(story.content_mode);
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

  const content = document.createElement('div');
  content.className = 'scene-content';
  content.textContent = node.content;

  scene.appendChild(meta);
  scene.appendChild(content);
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

  if (activeSceneEl) {
    // Remove cursor
    const cursor = activeSceneEl.querySelector('.cursor');
    if (cursor) cursor.remove();

    // Update meta
    const meta = activeSceneEl.querySelector('.scene-meta');
    meta.textContent = `Scene \u00b7 ${new Date(node.created_at).toLocaleTimeString()}`;

    // Store node ID
    activeSceneEl.dataset.nodeId = node.id;
  }

  currentLeafId = node.id;
  activeSceneEl = null;

  // Dispatch event for tree/entity refresh
  document.dispatchEvent(new CustomEvent('scene-complete', { detail: { node } }));
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

function scrollToBottom() {
  scenesContainer.scrollTop = scenesContainer.scrollHeight;
}
