/**
 * REST API client for StoryForge backend.
 */

const BASE = '';

class ApiError extends Error {
  constructor(status, detail, errorType = null, service = null) {
    super(detail);
    this.status = status;
    this.errorType = errorType;
    this.service = service;
  }

  get isServiceUnavailable() {
    return this.errorType === 'service_unavailable' || this.status === 503;
  }

  get isTimeout() {
    return this.errorType === 'service_timeout' || this.status === 504;
  }
}

export { ApiError };

async function request(method, path, body = null) {
  const opts = {
    method,
    headers: {},
  };
  if (body !== null) {
    opts.headers['Content-Type'] = 'application/json';
    opts.body = JSON.stringify(body);
  }

  let res;
  try {
    res = await fetch(`${BASE}${path}`, opts);
  } catch (e) {
    throw new ApiError(0, 'Network error — server may be down', 'network_error');
  }

  if (res.status === 204) return null;
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    throw new ApiError(
      res.status,
      err.detail || `HTTP ${res.status}`,
      err.error_type || null,
      err.service || null,
    );
  }
  return res.json();
}

// ── Stories ──────────────────────────────────────────────────────────

export function listStories() {
  return request('GET', '/api/stories');
}

export function getStory(id) {
  return request('GET', `/api/stories/${id}`);
}

export function createStory(title, genre, contentMode = 'unrestricted') {
  return request('POST', '/api/stories', { title, genre: genre || null, content_mode: contentMode });
}

export function updateStory(id, updates) {
  return request('PATCH', `/api/stories/${id}`, updates);
}

export function deleteStory(id) {
  return request('DELETE', `/api/stories/${id}`);
}

export function getStoryTree(storyId) {
  return request('GET', `/api/stories/${storyId}/tree`);
}

// ── Nodes ────────────────────────────────────────────────────────────

export function generateScene(storyId, userPrompt) {
  return request('POST', `/api/stories/${storyId}/nodes`, { user_prompt: userPrompt });
}

export function getNode(nodeId) {
  return request('GET', `/api/nodes/${nodeId}`);
}

export function getNodePath(nodeId) {
  return request('GET', `/api/nodes/${nodeId}/path`);
}

export function createBranch(nodeId, userPrompt) {
  return request('POST', `/api/nodes/${nodeId}/branch`, { user_prompt: userPrompt });
}

export function illustrateNode(nodeId) {
  return request('POST', `/api/nodes/${nodeId}/illustrate`);
}

// ── Entities ─────────────────────────────────────────────────────────

export function listEntities(storyId) {
  return request('GET', `/api/stories/${storyId}/entities`);
}

export function createEntity(storyId, entityType, name, description, basePrompt) {
  return request('POST', `/api/stories/${storyId}/entities`, {
    entity_type: entityType,
    name,
    description,
    base_prompt: basePrompt,
  });
}

export function detectEntities(storyId, text) {
  return request('POST', `/api/stories/${storyId}/entities/detect`, { text });
}

export function generateEntityImage(entityId) {
  return request('POST', `/api/entities/${entityId}/image`);
}

export function selectEntityImage(entityId, filename, seed, rejectFilenames) {
  return request('POST', `/api/entities/${entityId}/images/select`, {
    filename,
    seed,
    reject_filenames: rejectFilenames,
  });
}

export function generateEntityImagesUrl(entityId) {
  return `/api/entities/${entityId}/images/generate`;
}

export function describeEntityFromImage(entityId) {
  return request('POST', `/api/entities/${entityId}/describe`);
}

export function getEntity(entityId) {
  return request('GET', `/api/entities/${entityId}`);
}

export function updateEntity(entityId, updates) {
  return request('PATCH', `/api/entities/${entityId}`, updates);
}

export async function uploadEntityImage(entityId, file) {
  const formData = new FormData();
  formData.append('file', file);

  let res;
  try {
    res = await fetch(`${BASE}/api/entities/${entityId}/image/upload`, {
      method: 'POST',
      body: formData,
    });
  } catch (e) {
    throw new ApiError(0, 'Network error — server may be down', 'network_error');
  }

  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    throw new ApiError(res.status, err.detail || `HTTP ${res.status}`);
  }
  return res.json();
}

// ── Export ────────────────────────────────────────────────────────────

export function exportMarkdownUrl(storyId) {
  return `/api/stories/${storyId}/export/markdown`;
}
