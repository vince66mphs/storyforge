/**
 * 4-image selection grid modal.
 * Shows a 2x2 grid of candidate images generated via SSE.
 * User clicks one to select it as the entity's reference image.
 */

import * as api from './api.js';
import { showToast } from './app.js';

let overlay, grid, title, regenBtn, closeBtn;
let candidates = [];  // [{index, filename, seed, element}]
let currentEntityId = null;
let generating = false;
let eventSource = null;
let onSelectCallback = null;

export function isOpen() {
  return overlay && !overlay.classList.contains('hidden');
}

export function init() {
  overlay = document.getElementById('image-grid-overlay');
  grid = document.getElementById('image-grid');
  title = document.getElementById('image-grid-title');
  regenBtn = document.getElementById('image-grid-regen');
  closeBtn = document.getElementById('image-grid-close');

  closeBtn.addEventListener('click', close);
  overlay.addEventListener('click', (e) => {
    if (e.target === overlay) close();
  });
  regenBtn.addEventListener('click', () => {
    if (currentEntityId && !generating) startGeneration(currentEntityId);
  });
}

/**
 * Open the grid modal and start generating 4 images.
 * @param {string} entityId
 * @param {string} entityName - displayed as title
 * @param {Function} onSelect - called with updated entity after selection
 */
export function open(entityId, entityName, onSelect) {
  currentEntityId = entityId;
  onSelectCallback = onSelect;
  title.textContent = entityName;
  overlay.classList.remove('hidden');

  startGeneration(entityId);
}

export function close() {
  stopGeneration();
  overlay.classList.add('hidden');
  currentEntityId = null;
  onSelectCallback = null;
  candidates = [];
}

function startGeneration(entityId) {
  stopGeneration();
  candidates = [];
  generating = true;
  regenBtn.disabled = true;
  regenBtn.textContent = 'Generating...';

  // Clear grid and create 4 placeholder slots
  grid.innerHTML = '';
  for (let i = 0; i < 4; i++) {
    const slot = document.createElement('div');
    slot.className = 'image-grid-slot';
    slot.innerHTML = '<div class="image-grid-placeholder"><span class="spinner"></span></div>';
    grid.appendChild(slot);
  }

  const url = api.generateEntityImagesUrl(entityId);

  // Use fetch + ReadableStream for SSE (works with POST if needed, but this is GET-like POST)
  // Actually the endpoint is POST but browser EventSource only supports GET.
  // So we use fetch with a reader instead.
  fetchSSE(url, entityId);
}

async function fetchSSE(url, entityId) {
  try {
    const response = await fetch(url, { method: 'POST' });
    if (!response.ok) {
      const err = await response.json().catch(() => ({ detail: response.statusText }));
      showToast('Image generation failed: ' + (err.detail || `HTTP ${response.status}`), 'error');
      finishGeneration();
      return;
    }

    const reader = response.body.getReader();
    const decoder = new TextDecoder();
    let buffer = '';

    while (true) {
      const { done, value } = await reader.read();
      if (done) break;

      buffer += decoder.decode(value, { stream: true });

      // Parse SSE lines
      const lines = buffer.split('\n');
      buffer = lines.pop(); // keep incomplete line in buffer

      for (const line of lines) {
        if (line.startsWith('data: ')) {
          const jsonStr = line.slice(6);
          try {
            const data = JSON.parse(jsonStr);
            if (data.error) {
              showToast('Image generation failed: ' + data.error, 'error');
              finishGeneration();
              return;
            }
            if (data.done) {
              finishGeneration();
              return;
            }
            handleCandidate(data, entityId);
          } catch (e) {
            // ignore parse errors
          }
        }
      }
    }
    finishGeneration();
  } catch (e) {
    showToast('Image generation failed: ' + e.message, 'error');
    finishGeneration();
  }
}

function handleCandidate(data, entityId) {
  // data: {index, filename, seed}
  const { index, filename, seed } = data;
  candidates.push({ index, filename, seed });

  const slots = grid.querySelectorAll('.image-grid-slot');
  if (index >= slots.length) return;

  const slot = slots[index];
  slot.innerHTML = '';

  const img = document.createElement('img');
  img.src = `/static/images/${filename}`;
  img.alt = `Candidate ${index + 1}`;
  img.className = 'image-grid-img';
  img.addEventListener('click', () => selectImage(entityId, filename, seed));

  slot.appendChild(img);
}

function finishGeneration() {
  generating = false;
  regenBtn.disabled = false;
  regenBtn.textContent = 'Regenerate All';
}

function stopGeneration() {
  if (eventSource) {
    eventSource.close();
    eventSource = null;
  }
  generating = false;
}

async function selectImage(entityId, filename, seed) {
  // Determine which filenames to reject (the ones not selected)
  const rejectFilenames = candidates
    .filter(c => c.filename !== filename)
    .map(c => c.filename);

  // Visual feedback
  const imgs = grid.querySelectorAll('.image-grid-img');
  imgs.forEach(img => {
    if (img.src.includes(filename)) {
      img.classList.add('selected');
    } else {
      img.classList.add('rejected');
    }
  });

  try {
    const updated = await api.selectEntityImage(entityId, filename, seed, rejectFilenames);
    showToast('Image selected', 'success');

    if (onSelectCallback) onSelectCallback(updated);

    // Brief delay so user sees the selection highlight
    setTimeout(() => close(), 400);
  } catch (err) {
    showToast('Failed to select image: ' + err.message, 'error');
    // Remove visual feedback on error
    imgs.forEach(img => {
      img.classList.remove('selected', 'rejected');
    });
  }
}
