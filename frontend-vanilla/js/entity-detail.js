/**
 * Entity detail panel — expanded view for editing entity properties.
 * Shows description, base_prompt (editable), reference image,
 * and actions: generate image (4-image grid), describe from image (vision).
 */

import * as api from './api.js';
import { ApiError } from './api.js';
import { showToast } from './app.js';
import { open as openLightbox } from './lightbox.js';
import { open as openImageGrid } from './image-grid.js';

let overlay, panel;
let currentEntity = null;
let onUpdateCallback = null;

export function isOpen() {
  return overlay && !overlay.classList.contains('hidden');
}

export function init() {
  overlay = document.getElementById('entity-detail-overlay');
  panel = document.getElementById('entity-detail-panel');

  overlay.addEventListener('click', (e) => {
    if (e.target === overlay) close();
  });
}

/**
 * Open the detail panel for an entity.
 * @param {object} entity - The entity data
 * @param {Function} onUpdate - Called with updated entity when changes are saved
 */
export function open(entity, onUpdate) {
  currentEntity = entity;
  onUpdateCallback = onUpdate;
  render();
  overlay.classList.remove('hidden');
}

export function close() {
  overlay.classList.add('hidden');
  currentEntity = null;
  onUpdateCallback = null;
}

function render() {
  const e = currentEntity;
  const typeIcons = { character: '\u{1F464}', location: '\u{1F3D4}', prop: '\u{2728}' };
  const icon = typeIcons[e.entity_type] || '?';

  panel.innerHTML = `
    <div class="detail-header">
      <div>
        <h3>${icon} ${escapeHtml(e.name)}</h3>
        <span class="entity-type">${e.entity_type}</span>
      </div>
      <button class="lightbox-close" id="detail-close">&times;</button>
    </div>

    <div class="detail-image-section">
      ${e.reference_image_path
        ? `<img src="/static/images/${e.reference_image_path}" alt="${escapeHtml(e.name)}" class="detail-image" id="detail-img">`
        : '<div class="detail-image-empty">No reference image</div>'
      }
      <div class="detail-image-actions">
        <button class="btn btn-small btn-secondary" id="detail-gen-image">Generate Image</button>
        <button class="btn btn-small btn-ghost" id="detail-upload-image">Upload Image</button>
        <input type="file" id="detail-upload-input" accept=".png,.jpg,.jpeg,.webp" class="hidden">
        ${e.reference_image_path
          ? '<button class="btn btn-small btn-ghost" id="detail-describe">Describe from Image</button>'
          : ''
        }
      </div>
    </div>

    <div class="detail-fields">
      <div class="form-group">
        <label for="detail-description">Description</label>
        <textarea id="detail-description" rows="3">${escapeHtml(e.description)}</textarea>
      </div>
      <div class="form-group">
        <label for="detail-base-prompt">Image Prompt</label>
        <textarea id="detail-base-prompt" rows="3">${escapeHtml(e.base_prompt)}</textarea>
      </div>
      <div class="detail-save-row">
        <button class="btn btn-primary btn-small" id="detail-save">Save Changes</button>
        <span class="detail-version">v${e.version}</span>
      </div>
    </div>
  `;

  // Wire up events
  panel.querySelector('#detail-close').addEventListener('click', close);

  const img = panel.querySelector('#detail-img');
  if (img) {
    img.style.cursor = 'pointer';
    img.addEventListener('click', () => {
      openLightbox(`/static/images/${e.reference_image_path}`, e.name);
    });
  }

  panel.querySelector('#detail-gen-image').addEventListener('click', () => {
    openImageGrid(e.id, e.name, (updated) => {
      currentEntity = updated;
      notifyUpdate(updated);
      render();
    });
  });

  const uploadBtn = panel.querySelector('#detail-upload-image');
  const uploadInput = panel.querySelector('#detail-upload-input');
  uploadBtn.addEventListener('click', () => uploadInput.click());
  uploadInput.addEventListener('change', () => {
    if (uploadInput.files.length > 0) handleUpload(uploadInput.files[0]);
  });

  const describeBtn = panel.querySelector('#detail-describe');
  if (describeBtn) {
    describeBtn.addEventListener('click', handleDescribe);
  }

  panel.querySelector('#detail-save').addEventListener('click', handleSave);
}

async function handleSave() {
  const desc = panel.querySelector('#detail-description').value.trim();
  const prompt = panel.querySelector('#detail-base-prompt').value.trim();
  const saveBtn = panel.querySelector('#detail-save');

  if (!desc || !prompt) {
    showToast('Description and image prompt are required', 'error');
    return;
  }

  saveBtn.disabled = true;
  saveBtn.textContent = 'Saving...';

  try {
    const updated = await api.updateEntity(currentEntity.id, {
      description: desc,
      base_prompt: prompt,
    });
    currentEntity = updated;
    showToast('Entity updated', 'success');
    notifyUpdate(updated);
    render();
  } catch (err) {
    showToast('Failed to update: ' + err.message, 'error');
  } finally {
    saveBtn.disabled = false;
    saveBtn.textContent = 'Save Changes';
  }
}

async function handleUpload(file) {
  const btn = panel.querySelector('#detail-upload-image');
  btn.disabled = true;
  btn.textContent = 'Uploading...';

  try {
    const updated = await api.uploadEntityImage(currentEntity.id, file);
    currentEntity = updated;
    showToast('Image uploaded', 'success');
    notifyUpdate(updated);
    render();
  } catch (err) {
    showToast('Upload failed: ' + err.message, 'error');
  } finally {
    btn.disabled = false;
    btn.textContent = 'Upload Image';
  }
}

async function handleDescribe() {
  const btn = panel.querySelector('#detail-describe');
  btn.disabled = true;
  btn.textContent = 'Analyzing...';

  try {
    const updated = await api.describeEntityFromImage(currentEntity.id);
    currentEntity = updated;
    showToast('Description generated from image', 'success');
    notifyUpdate(updated);
    render();
  } catch (err) {
    if (err instanceof ApiError && err.errorType === 'model_not_found') {
      showToast('Vision model not found. Run "ollama pull gemma2:9b"', 'error');
    } else if (err instanceof ApiError && err.isServiceUnavailable) {
      showToast('Ollama is not available', 'error');
    } else {
      showToast('Description generation failed: ' + err.message, 'error');
    }
  } finally {
    btn.disabled = false;
    btn.textContent = 'Describe from Image';
  }
}

function notifyUpdate(updated) {
  if (onUpdateCallback) onUpdateCallback(updated);
}

function escapeHtml(str) {
  const div = document.createElement('div');
  div.textContent = str;
  return div.innerHTML;
}
