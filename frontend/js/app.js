/**
 * StoryForge 2.0 — Frontend entry point.
 * View switching, state management, toast notifications.
 */

import { StorySocket } from './ws.js';
import * as storyList from './story-list.js';
import * as storyWriter from './story-writer.js';
import * as entityPanel from './entity-panel.js';
import * as treeView from './tree-view.js';
import { exportMarkdownUrl } from './api.js';

// ── State ────────────────────────────────────────────────────────────

const socket = new StorySocket();

// ── Toast Notifications ──────────────────────────────────────────────

export function showToast(message, type = 'info') {
  const container = document.getElementById('toast-container');
  const toast = document.createElement('div');
  toast.className = `toast ${type}`;
  toast.textContent = message;
  container.appendChild(toast);
  setTimeout(() => toast.remove(), 4000);
}

// ── View Switching ───────────────────────────────────────────────────

function showView(name) {
  document.querySelectorAll('.view').forEach(v => v.classList.add('hidden'));
  document.getElementById(`${name}-view`).classList.remove('hidden');
}

function openLobby() {
  storyWriter.unload();
  entityPanel.clear();
  treeView.clear();
  storyList.refresh();
  showView('lobby');
}

async function openStory(story, openingPrompt = null) {
  showView('writing');
  await storyWriter.loadStory(story, openingPrompt);
  entityPanel.load(story.id);
  treeView.load(story.id);
}

// ── Init ─────────────────────────────────────────────────────────────

function init() {
  // Initialize modules
  storyList.init((story, opening) => openStory(story, opening));
  storyWriter.init(socket);
  entityPanel.init();
  treeView.init();

  // Header buttons
  document.getElementById('back-btn').addEventListener('click', openLobby);
  document.getElementById('export-btn').addEventListener('click', () => {
    const story = storyWriter.getCurrentStory();
    if (!story) return;
    window.open(exportMarkdownUrl(story.id), '_blank');
  });

  // Start on lobby
  showView('lobby');
}

document.addEventListener('DOMContentLoaded', init);
