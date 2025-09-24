function openVideoModal(filename) {
  fetch(`/video_popup/${filename}`)
    .then(res => res.text())
    .then(html => {
      const modal = document.getElementById('videoModal');
      modal.innerHTML = html;
      modal.style.display = 'block';

      const player = modal.querySelector('#popupPlayer');
      player.src = `/static/videos/${filename}`;

      currentVideo = filename;
      loadComments(filename);
      loadReactions(filename);
    });
}


function react(type) {
  fetch('/react', {
    method: 'POST',
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify({ video: currentVideo, type })
  }).then(() => loadReactions(currentVideo));
}

function loadReactions(filename) {
  fetch(`/reactions/${filename}`)
    .then(res => res.json())
    .then(data => {
      const stats = Object.entries(data)
        .map(([key, val]) => `${key}: ${val}`).join(' • ');
      document.getElementById('reactionStats').textContent = stats;
    });
}

function submitComment() {
  const text = document.getElementById('popupCommentInput').value;
  fetch('/comment_video', {
    method: 'POST',
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify({ video: currentVideo, comment: text })
  }).then(() => loadComments(currentVideo));
}

function loadComments(filename) {
  fetch(`/comments_video/${filename}`)
    .then(res => res.json())
    .then(comments => {
      const list = document.getElementById('popupCommentList');
      list.innerHTML = '';
      comments.forEach(c => {
        const li = document.createElement('li');
        li.textContent = c;
        list.appendChild(li);
      });
    });
}
