/**
 * Lobby: story list and create form.
 */

import * as api from './api.js';
import { showToast } from './app.js';

let onStorySelect = null;

export function init(selectCallback) {
  onStorySelect = selectCallback;

  document.getElementById('create-story-form').addEventListener('submit', handleCreate);
  loadStories();
}

async function loadStories() {
  const container = document.getElementById('story-list');
  try {
    const stories = await api.listStories();
    if (stories.length === 0) {
      container.innerHTML = '<p class="empty-state">No stories yet. Create one!</p>';
      return;
    }
    container.innerHTML = '';
    for (const story of stories) {
      container.appendChild(createStoryCard(story));
    }
  } catch (err) {
    container.innerHTML = `<p class="empty-state">Failed to load stories</p>`;
    showToast(err.message, 'error');
  }
}

function createStoryCard(story) {
  const card = document.createElement('div');
  card.className = 'story-card';

  const info = document.createElement('div');
  info.className = 'story-card-info';

  const title = document.createElement('h3');
  title.textContent = story.title;

  const meta = document.createElement('div');
  meta.className = 'meta';
  const date = new Date(story.created_at).toLocaleDateString();
  meta.textContent = story.genre ? `${story.genre} \u00b7 ${date}` : date;

  info.appendChild(title);
  info.appendChild(meta);

  const deleteBtn = document.createElement('button');
  deleteBtn.className = 'btn btn-danger';
  deleteBtn.textContent = 'Delete';
  deleteBtn.addEventListener('click', async (e) => {
    e.stopPropagation();
    if (!confirm(`Delete "${story.title}"?`)) return;
    try {
      await api.deleteStory(story.id);
      card.remove();
      showToast('Story deleted', 'success');
    } catch (err) {
      showToast(err.message, 'error');
    }
  });

  card.appendChild(info);
  card.appendChild(deleteBtn);

  card.addEventListener('click', () => {
    onStorySelect?.(story);
  });

  return card;
}

async function handleCreate(e) {
  e.preventDefault();

  const titleInput = document.getElementById('story-title');
  const genreInput = document.getElementById('story-genre');
  const openingInput = document.getElementById('story-opening');

  const title = titleInput.value.trim();
  const genre = genreInput.value.trim();
  const opening = openingInput.value.trim();

  if (!title || !opening) return;

  const btn = e.target.querySelector('button[type="submit"]');
  btn.disabled = true;
  btn.textContent = 'Creating...';

  try {
    const story = await api.createStory(title, genre);
    titleInput.value = '';
    genreInput.value = '';
    openingInput.value = '';
    showToast(`Created "${story.title}"`, 'success');

    // Open the story in the writer, passing the opening direction
    onStorySelect?.(story, opening);
  } catch (err) {
    showToast(err.message, 'error');
  } finally {
    btn.disabled = false;
    btn.textContent = 'Create Story';
  }
}

export function refresh() {
  loadStories();
}
