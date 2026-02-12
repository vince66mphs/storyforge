/**
 * Narrative tree: display and click-to-navigate.
 */

import * as api from './api.js';
import { showToast } from './app.js';
import { getCurrentLeafId, navigateToNode } from './story-writer.js';

let treeNodes = [];

export function init() {
  // Refresh tree when a scene completes
  document.addEventListener('scene-complete', () => {
    if (currentStoryId) loadTree(currentStoryId);
  });
}

let currentStoryId = null;

export async function load(storyId) {
  currentStoryId = storyId;
  await loadTree(storyId);
}

export function clear() {
  treeNodes = [];
  currentStoryId = null;
  render();
}

async function loadTree(storyId) {
  try {
    treeNodes = await api.getStoryTree(storyId);
    render();
  } catch (err) {
    showToast('Failed to load tree: ' + err.message, 'error');
  }
}

function render() {
  const container = document.getElementById('tree-view');
  const currentLeaf = getCurrentLeafId();

  if (treeNodes.length === 0) {
    container.innerHTML = '<p class="empty-state">No nodes yet</p>';
    return;
  }

  container.innerHTML = '';

  // Build parent->children map
  const childrenMap = {};
  let root = null;
  for (const node of treeNodes) {
    const pid = node.parent_id || '__root__';
    if (!childrenMap[pid]) childrenMap[pid] = [];
    childrenMap[pid].push(node);
    if (!node.parent_id) root = node;
  }

  if (!root) return;

  // Render tree recursively
  renderNode(container, root, childrenMap, currentLeaf, 0);
}

function renderNode(container, node, childrenMap, currentLeaf, depth) {
  const el = document.createElement('div');
  el.className = 'tree-node';
  if (node.id === currentLeaf) el.classList.add('active');

  // Indentation
  const indent = document.createElement('span');
  indent.className = 'tree-indent';
  indent.style.width = `${depth * 16}px`;

  // Label
  const label = document.createElement('span');
  label.className = 'node-label';
  const preview = node.content.replace(/\n/g, ' ').substring(0, 30);
  const suffix = node.content.length > 30 ? '...' : '';
  const typeTag = node.node_type === 'root' ? '[root] ' : '';
  label.textContent = `${typeTag}${preview}${suffix}`;

  el.appendChild(indent);
  el.appendChild(label);

  el.addEventListener('click', async () => {
    await navigateToNode(node.id);
    render();
  });

  container.appendChild(el);

  // Render children
  const children = childrenMap[node.id] || [];
  for (const child of children) {
    renderNode(container, child, childrenMap, currentLeaf, depth + 1);
  }
}
