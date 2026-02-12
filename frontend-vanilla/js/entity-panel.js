/**
 * Entity panel: detect entities, list them, generate images, manual creation.
 */

import * as api from './api.js';
import { ApiError } from './api.js';
import { showToast } from './app.js';
import { getCurrentStory, getCurrentLeafId } from './story-writer.js';
import { open as openLightbox } from './lightbox.js';
import { open as openImageGrid } from './image-grid.js';
import { open as openEntityDetail } from './entity-detail.js';

let entityList = [];

export function init() {
  document.getElementById('detect-entities-btn').addEventListener('click', handleDetect);
  document.getElementById('add-entity-btn').addEventListener('click', toggleAddForm);
  document.getElementById('add-entity-form').addEventListener('submit', handleAddEntity);
  document.getElementById('add-entity-cancel').addEventListener('click', hideAddForm);

  // Refresh entities when a scene completes
  document.addEventListener('scene-complete', () => {
    const story = getCurrentStory();
    if (story) loadEntities(story.id);
  });

  // Refresh when an entity is added from a warning button
  document.addEventListener('entity-added', () => {
    const story = getCurrentStory();
    if (story) loadEntities(story.id);
  });
}

export async function load(storyId) {
  hideAddForm();
  await loadEntities(storyId);
}

export function clear() {
  entityList = [];
  hideAddForm();
  render();
}

async function loadEntities(storyId) {
  try {
    entityList = await api.listEntities(storyId);
    render();
  } catch (err) {
    showToast('Failed to load entities: ' + err.message, 'error');
  }
}

function toggleAddForm() {
  const form = document.getElementById('add-entity-form');
  form.classList.toggle('hidden');
  if (!form.classList.contains('hidden')) {
    document.getElementById('entity-name-input').focus();
  }
}

function hideAddForm() {
  const form = document.getElementById('add-entity-form');
  form.classList.add('hidden');
  form.reset();
}

async function handleAddEntity(e) {
  e.preventDefault();

  const story = getCurrentStory();
  if (!story) {
    showToast('No active story', 'error');
    return;
  }

  const name = document.getElementById('entity-name-input').value.trim();
  const entityType = document.getElementById('entity-type-select').value;
  const description = document.getElementById('entity-desc-input').value.trim();
  const basePrompt = document.getElementById('entity-prompt-input').value.trim();

  if (!name || !description || !basePrompt) {
    showToast('All fields are required', 'error');
    return;
  }

  const submitBtn = document.getElementById('add-entity-submit');
  submitBtn.disabled = true;
  submitBtn.textContent = 'Adding...';

  try {
    await api.createEntity(story.id, entityType, name, description, basePrompt);
    showToast(`Added ${name}`, 'success');
    hideAddForm();
    await loadEntities(story.id);
  } catch (err) {
    showToast('Failed to add entity: ' + err.message, 'error');
  } finally {
    submitBtn.disabled = false;
    submitBtn.textContent = 'Add';
  }
}

function render() {
  const container = document.getElementById('entity-list');

  if (entityList.length === 0) {
    container.innerHTML = '<p class="empty-state">No entities yet</p>';
    return;
  }

  container.innerHTML = '';

  // Group by type
  const groups = {};
  for (const entity of entityList) {
    const type = entity.entity_type;
    if (!groups[type]) groups[type] = [];
    groups[type].push(entity);
  }

  const typeOrder = ['character', 'location', 'prop'];
  const typeIcons = { character: '\u{1F464}', location: '\u{1F3D4}', prop: '\u{2728}' };

  for (const type of typeOrder) {
    const entities = groups[type];
    if (!entities) continue;

    for (const entity of entities) {
      const item = document.createElement('div');
      item.className = 'entity-item';
      item.style.cursor = 'pointer';

      // Clicking anywhere on the item opens the detail panel
      item.addEventListener('click', () => {
        openEntityDetail(entity, (updated) => {
          const idx = entityList.findIndex(e => e.id === entity.id);
          if (idx >= 0) entityList[idx] = updated;
          render();
        });
      });

      // Thumbnail or placeholder
      if (entity.reference_image_path) {
        const img = document.createElement('img');
        img.className = 'entity-thumb';
        img.src = `/static/images/${entity.reference_image_path}`;
        img.alt = entity.name;
        img.title = 'Click to view full image';
        img.addEventListener('click', (e) => {
          e.stopPropagation();
          openLightbox(`/static/images/${entity.reference_image_path}`, entity.name);
        });
        item.appendChild(img);
      } else {
        const placeholder = document.createElement('div');
        placeholder.className = 'entity-thumb-placeholder';
        placeholder.textContent = typeIcons[type] || '?';
        placeholder.title = 'Click to generate images';
        placeholder.addEventListener('click', (e) => {
          e.stopPropagation();
          openImageGrid(entity.id, entity.name, (updated) => {
            const idx = entityList.findIndex(e => e.id === entity.id);
            if (idx >= 0) entityList[idx] = updated;
            render();
          });
        });
        item.appendChild(placeholder);
      }

      const info = document.createElement('div');
      info.className = 'entity-info';

      const name = document.createElement('div');
      name.className = 'entity-name';
      name.textContent = entity.name;

      const typeBadge = document.createElement('div');
      typeBadge.className = 'entity-type';
      typeBadge.textContent = entity.entity_type;

      info.appendChild(name);
      info.appendChild(typeBadge);
      item.appendChild(info);

      container.appendChild(item);
    }
  }
}

async function handleDetect() {
  const story = getCurrentStory();
  const leafId = getCurrentLeafId();
  if (!story || !leafId) {
    showToast('No active story or scene', 'error');
    return;
  }

  const btn = document.getElementById('detect-entities-btn');
  btn.disabled = true;
  btn.textContent = 'Detecting...';

  try {
    // Get current scene text
    const path = await api.getNodePath(leafId);
    const scenes = path.filter(n => n.node_type !== 'root');
    if (scenes.length === 0) {
      showToast('No scenes to analyze', 'error');
      return;
    }

    // Detect from the latest scene
    const latestScene = scenes[scenes.length - 1];
    const created = await api.detectEntities(story.id, latestScene.content);

    if (created.length === 0) {
      showToast('No new entities detected', 'success');
    } else {
      showToast(`Detected ${created.length} new entit${created.length === 1 ? 'y' : 'ies'}`, 'success');
    }

    await loadEntities(story.id);
  } catch (err) {
    if (err instanceof ApiError && err.errorType === 'model_not_found') {
      showToast('Model not found. Run "ollama pull <model>" on the server.', 'error');
    } else if (err instanceof ApiError && err.isServiceUnavailable) {
      showToast(`Entity detection unavailable — ${err.service || 'Ollama'} is not running`, 'error');
    } else if (err instanceof ApiError && err.isTimeout) {
      showToast('Entity detection timed out. Try again later.', 'error');
    } else {
      showToast('Entity detection failed: ' + err.message, 'error');
    }
  } finally {
    btn.disabled = false;
    btn.textContent = 'Detect Entities';
  }
}

async function generateImage(entity, element) {
  // Add generating state
  element.classList?.add('generating');
  if (element.tagName === 'DIV') element.textContent = '...';

  try {
    const updated = await api.generateEntityImage(entity.id);
    showToast(`Generated image for ${entity.name}`, 'success');

    // Update in our list and re-render
    const idx = entityList.findIndex(e => e.id === entity.id);
    if (idx >= 0) entityList[idx] = updated;
    render();
  } catch (err) {
    if (err instanceof ApiError && err.errorType === 'model_not_found') {
      showToast('Model not found. Run "ollama pull <model>" on the server.', 'error');
    } else if (err instanceof ApiError && err.isServiceUnavailable) {
      showToast(`Image generation unavailable — ${err.service || 'ComfyUI'} is not running`, 'error');
    } else if (err instanceof ApiError && err.isTimeout) {
      showToast('Image generation timed out. Try again later.', 'error');
    } else {
      showToast('Image generation failed: ' + err.message, 'error');
    }
    element.classList?.remove('generating');
  }
}
