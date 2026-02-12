/**
 * Reusable lightbox modal for viewing full-size images.
 * Supports close via X button, backdrop click, or Escape key.
 */

let overlay, img, caption, closeBtn;

export function isOpen() {
  return overlay && !overlay.classList.contains('hidden');
}

export function init() {
  overlay = document.getElementById('lightbox-overlay');
  img = document.getElementById('lightbox-img');
  caption = document.getElementById('lightbox-caption');
  closeBtn = document.getElementById('lightbox-close');

  closeBtn.addEventListener('click', close);
  overlay.addEventListener('click', (e) => {
    if (e.target === overlay) close();
  });
}

export function open(src, alt) {
  img.src = src;
  caption.textContent = alt || '';
  overlay.classList.remove('hidden');
}

export function close() {
  overlay.classList.add('hidden');
  img.src = '';
}
