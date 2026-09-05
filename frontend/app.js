// Comment Triage Bot Frontend Application Logic

let allComments = [];
let activeCategory = 'all';
let currentVideoMeta = null;

// User settings stored in localStorage
let userSettings = {
  creatorStyle: 'friendly_concise',
  pastReplies: '',
  ytApiKey: '',
  llmApiKey: ''
};

// Initialize on page load
document.addEventListener('DOMContentLoaded', () => {
  loadSavedSettings();
  lucide.createIcons();
  
  // Auto-trigger analysis for the default demo so user lands on an active, populated dashboard
  setTimeout(() => {
    handleAnalyze();
  }, 300);
});

function loadSavedSettings() {
  const saved = localStorage.getItem('triage_bot_settings');
  if (saved) {
    try {
      userSettings = { ...userSettings, ...JSON.parse(saved) };
      // Update modal inputs
      const radio = document.querySelector(`input[name="creatorStyleRadio"][value="${userSettings.creatorStyle}"]`);
      if (radio) radio.checked = true;
      document.getElementById('pastRepliesInput').value = userSettings.pastReplies || '';
      document.getElementById('ytApiKeyInput').value = userSettings.ytApiKey || '';
      document.getElementById('llmApiKeyInput').value = userSettings.llmApiKey || '';
    } catch (e) {
      console.error('Failed to parse saved settings', e);
    }
  }
}

function saveSettings() {
  const selectedRadio = document.querySelector('input[name="creatorStyleRadio"]:checked');
  if (selectedRadio) {
    userSettings.creatorStyle = selectedRadio.value;
  }
  userSettings.pastReplies = document.getElementById('pastRepliesInput').value.trim();
  userSettings.ytApiKey = document.getElementById('ytApiKeyInput').value.trim();
  userSettings.llmApiKey = document.getElementById('llmApiKeyInput').value.trim();

  localStorage.setItem('triage_bot_settings', JSON.stringify(userSettings));
  closeSettingsModal();
  showToast('Settings & Creator Persona saved!');
}

function openSettingsModal() {
  document.getElementById('settingsModal').classList.remove('hidden');
  lucide.createIcons();
}

function closeSettingsModal() {
  document.getElementById('settingsModal').classList.add('hidden');
}

function toggleExportMenu() {
  const menu = document.getElementById('exportMenu');
  menu.classList.toggle('hidden');
}

document.addEventListener('click', (e) => {
  const btn = document.getElementById('btnExportToggle');
  const menu = document.getElementById('exportMenu');
  if (btn && menu && !btn.contains(e.target) && !menu.contains(e.target)) {
    menu.classList.add('hidden');
  }
});

function loadSampleVideo(id) {
  document.getElementById('videoUrlInput').value = id;
  handleAnalyze();
}

async function handleAnalyze(e) {
  if (e) e.preventDefault();

  const videoInput = document.getElementById('videoUrlInput').value.trim();
  if (!videoInput) return;

  const analyzeBtn = document.getElementById('analyzeBtn');
  const statusIndicator = document.getElementById('statusIndicator');
  const statusText = document.getElementById('statusText');
  const statusPercent = document.getElementById('statusPercent');
  const progressBar = document.getElementById('progressBar');

  // UI state: analyzing
  if (analyzeBtn) analyzeBtn.disabled = true;
  if (statusIndicator) statusIndicator.classList.remove('hidden');

  // Multi-step progress animation
  const steps = [
    { percent: 25, text: 'Layer 1: Ingesting comment threads from YouTube Data API v3...' },
    { percent: 55, text: 'Layer 2: Batch classifying comments with structured LLM...' },
    { percent: 80, text: 'Priority Engine: Scoring engagement leverage & recency...' },
    { percent: 95, text: 'Layer 3: Drafting authentic replies in creator voice...' }
  ];

  let currentStep = 0;
  if (statusText) statusText.innerHTML = `<span>${steps[0].text}</span>`;
  if (progressBar) progressBar.style.width = `${steps[0].percent}%`;
  if (statusPercent) statusPercent.innerText = `${steps[0].percent}%`;

  const interval = setInterval(() => {
    currentStep++;
    if (currentStep < steps.length) {
      if (statusText) statusText.innerHTML = `<span>${steps[currentStep].text}</span>`;
      if (progressBar) progressBar.style.width = `${steps[currentStep].percent}%`;
      if (statusPercent) statusPercent.innerText = `${steps[currentStep].percent}%`;
    }
  }, 400);

  try {
    const pastRepliesArray = userSettings.pastReplies
      ? userSettings.pastReplies.split('\n').map(s => s.trim()).filter(Boolean)
      : [];

    const payload = {
      video_url_or_id: videoInput,
      api_key_youtube: userSettings.ytApiKey || null,
      api_key_llm: userSettings.llmApiKey || null,
      creator_style: userSettings.creatorStyle || 'friendly_concise',
      past_replies: pastRepliesArray,
      max_comments: 50
    };

    const response = await fetch('/api/analyze', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload)
    });

    clearInterval(interval);

    if (!response.ok) {
      const err = await response.json();
      throw new Error(err.detail || 'Analysis request failed');
    }

    const data = await response.json();
    if (progressBar) progressBar.style.width = '100%';
    if (statusPercent) statusPercent.innerText = '100%';
    if (statusText) statusText.innerHTML = '<span class="text-emerald-400">✓ Triage Complete!</span>';

    setTimeout(() => {
      if (statusIndicator) statusIndicator.classList.add('hidden');
      if (analyzeBtn) analyzeBtn.disabled = false;
    }, 600);

    // Save and render
    currentVideoMeta = data.metadata;
    allComments = data.comments;

    const fallbackBanner = document.getElementById('fallbackBanner');
    if (data.is_fallback) {
      document.getElementById('fallbackBannerText').innerText = data.fallback_reason || "To fetch live comments from your real YouTube video, enter your YouTube API key in Settings.";
      fallbackBanner.classList.remove('hidden');
    } else {
      fallbackBanner.classList.add('hidden');
    }

    updateVideoMetadataCard(data.metadata);
    updateMetrics(data.stats);
    updateTabCounts(data.comments);
    renderFilteredComments();

    showToast(`Successfully triaged ${data.comments.length} comments!`);

  } catch (error) {
    clearInterval(interval);
    console.error('Analyze error:', error);
    statusIndicator.classList.add('hidden');
    analyzeBtn.disabled = false;
    alert(`Error: ${error.message}`);
  }
}

function updateVideoMetadataCard(meta) {
  if (!meta) return;
  const card = document.getElementById('videoMetaCard');
  card.classList.remove('hidden');

  document.getElementById('videoThumb').src = meta.thumbnail_url || 'https://images.unsplash.com/photo-1618005182384-a83a8bd57fbe?w=600';
  document.getElementById('videoTitle').innerText = meta.title;
  document.getElementById('videoChannel').innerText = `by ${meta.channel_title}`;
  document.getElementById('metaViews').innerText = Number(meta.view_count || 0).toLocaleString();
  document.getElementById('metaLikes').innerText = Number(meta.like_count || 0).toLocaleString();
  document.getElementById('metaComments').innerText = Number(meta.comment_count || 0).toLocaleString();
}

function updateMetrics(stats) {
  if (!stats) return;
  document.getElementById('metricTotal').innerText = stats.total_comments;
  document.getElementById('metricNeedsReply').innerText = stats.needs_reply;
  document.getElementById('metricQuestions').innerText = stats.questions;
  document.getElementById('metricSponsors').innerText = stats.sponsor_pitches;
  document.getElementById('metricSpam').innerText = stats.spam_and_toxic;
  document.getElementById('metricTimeSaved').innerText = `${stats.est_minutes_saved}m`;
}

function updateTabCounts(comments) {
  const counts = {
    all: comments.length,
    needs_reply: 0,
    question: 0,
    sponsor_pitch: 0,
    positive: 0,
    negative: 0,
    spam_toxic: 0
  };

  comments.forEach(c => {
    if (c.needs_reply) counts.needs_reply++;
    if (c.category === 'question') counts.question++;
    if (c.category === 'sponsor_pitch') counts.sponsor_pitch++;
    if (c.category === 'positive') counts.positive++;
    if (c.category === 'negative') counts.negative++;
    if (c.category === 'spam' || c.category === 'toxic') counts.spam_toxic++;
  });

  for (const [key, count] of Object.entries(counts)) {
    const el = document.getElementById(`count-${key}`);
    if (el) el.innerText = count;
  }
}

function setCategoryFilter(category) {
  activeCategory = category;

  // Update tab UI
  document.querySelectorAll('.cat-tab').forEach(tab => {
    if (tab.getAttribute('data-cat') === category) {
      tab.classList.add('active');
      tab.classList.remove('bg-slate-900', 'text-slate-300');
    } else {
      tab.classList.remove('active');
      tab.classList.add('bg-slate-900', 'text-slate-300');
    }
  });

  renderFilteredComments();
}

function renderFilteredComments() {
  const container = document.getElementById('commentsFeed');
  const searchTerm = (document.getElementById('commentSearch').value || '').toLowerCase().trim();
  const sortBy = document.getElementById('sortBy').value;

  let filtered = allComments.filter(c => {
    // Category match
    if (activeCategory === 'needs_reply') {
      if (!c.needs_reply) return false;
    } else if (activeCategory === 'spam_toxic') {
      if (c.category !== 'spam' && c.category !== 'toxic') return false;
    } else if (activeCategory !== 'all') {
      if (c.category !== activeCategory) return false;
    }

    // Search filter
    if (searchTerm) {
      const matchAuthor = (c.author || '').toLowerCase().includes(searchTerm);
      const matchText = (c.text || '').toLowerCase().includes(searchTerm);
      if (!matchAuthor && !matchText) return false;
    }

    return true;
  });

  // Sorting
  if (sortBy === 'priority') {
    filtered.sort((a, b) => (b.priority_score || 0) - (a.priority_score || 0));
  } else if (sortBy === 'likes') {
    filtered.sort((a, b) => (b.like_count || 0) - (a.like_count || 0));
  } else if (sortBy === 'newest') {
    filtered.sort((a, b) => new Date(b.published_at) - new Date(a.published_at));
  }

  if (filtered.length === 0) {
    container.innerHTML = `
      <div class="py-12 text-center text-slate-500 border border-dashed border-slate-800 rounded-xl">
        <i data-lucide="filter-x" class="w-8 h-8 mx-auto text-slate-600 mb-2"></i>
        <p class="text-sm font-medium text-slate-400">No comments match the selected filter</p>
      </div>
    `;
    lucide.createIcons();
    return;
  }

  container.innerHTML = filtered.map(c => renderCommentCard(c)).join('');
  lucide.createIcons();
}

function renderCommentCard(c) {
  const categoryLabels = {
    question: 'Question',
    sponsor_pitch: 'Sponsor Pitch',
    positive: 'Positive',
    negative: 'Feedback',
    spam: 'Spam Link',
    toxic: 'Toxic Abuse'
  };

  const catLabel = categoryLabels[c.category] || c.category;
  const isActionable = c.needs_reply;
  const confidencePercent = Math.round((c.confidence || 0.9) * 100);

  const priorityClass = c.priority_label === 'High' ? 'priority-high' : (c.priority_label === 'Medium' ? 'priority-medium' : 'priority-low');

  const formattedTime = formatTimestamp(c.published_at);

  return `
    <div id="comment-card-${c.id}" class="rounded-xl bg-slate-900/80 border ${c.is_approved ? 'border-emerald-500/50 bg-emerald-950/10' : 'border-slate-800'} p-4 space-y-3 transition hover:border-slate-700">
      <!-- Card Top: Badges, Priority, Actions -->
      <div class="flex flex-wrap items-center justify-between gap-2">
        <div class="flex items-center space-x-2">
          <!-- Category Badge -->
          <span class="px-2.5 py-0.5 rounded-full text-xs font-semibold badge-${c.category}">
            ${catLabel}
          </span>

          <!-- Priority Score -->
          <span class="px-2.5 py-0.5 rounded-full text-xs font-medium ${priorityClass}">
            ${c.priority_label} Priority (${c.priority_score})
          </span>

          <!-- Confidence & Reasoning -->
          <span class="text-[11px] text-slate-400 flex items-center space-x-1" title="${c.reasoning}">
            <i data-lucide="brain-circuit" class="w-3.5 h-3.5 text-purple-400"></i>
            <span>${confidencePercent}% AI match</span>
          </span>
        </div>

        <div class="flex items-center space-x-2">
          ${c.is_approved ? `
            <span class="inline-flex items-center space-x-1 px-2 py-0.5 rounded bg-emerald-500/20 text-emerald-300 text-xs font-medium border border-emerald-500/40">
              <i data-lucide="check" class="w-3 h-3"></i>
              <span>Approved</span>
            </span>
          ` : ''}
          <span class="text-[11px] text-slate-500 font-mono">${formattedTime}</span>
        </div>
      </div>

      <!-- Comment Author & Body -->
      <div class="flex items-start space-x-3">
        <img src="${c.author_profile_image || `https://api.dicebear.com/7.x/bottts/svg?seed=${c.author}`}" alt="${c.author}" class="w-8 h-8 rounded-full bg-slate-800 border border-slate-700 mt-0.5 flex-shrink-0">
        <div class="flex-1 min-w-0">
          <div class="flex items-center space-x-2">
            <span class="text-xs font-semibold text-slate-200 truncate">${c.author}</span>
            <span class="inline-flex items-center space-x-1 text-[11px] text-slate-400 bg-slate-800/60 px-1.5 py-0.5 rounded">
              <i data-lucide="thumbs-up" class="w-3 h-3 text-slate-400"></i>
              <span>${c.like_count}</span>
            </span>
          </div>
          <p class="text-xs text-slate-300 mt-1 leading-relaxed break-words">${escapeHtml(c.text)}</p>
          <p class="text-[11px] text-slate-500 mt-1 italic">${c.reasoning}</p>
        </div>
      </div>

      <!-- Layer 3: Draft Reply Section (for Actionable comments) -->
      ${isActionable && c.draft_reply ? `
        <div class="mt-3 pt-3 border-t border-slate-800/80 bg-slate-950/40 -mx-4 -mb-4 p-4 rounded-b-xl space-y-2">
          <div class="flex items-center justify-between text-xs">
            <div class="flex items-center space-x-1.5 text-purple-300 font-medium">
              <i data-lucide="message-square-plus" class="w-3.5 h-3.5 text-purple-400"></i>
              <span>Draft Reply (In Creator Voice):</span>
            </div>
            <span class="text-[11px] text-slate-500 font-mono">Style-matched</span>
          </div>

          <!-- Editable draft response area -->
          <textarea
            id="draft-text-${c.id}"
            class="w-full p-2.5 bg-slate-900 border border-purple-500/30 rounded-lg text-xs text-slate-100 placeholder-slate-500 focus:outline-none focus:border-purple-500 focus:ring-1 focus:ring-purple-500 leading-relaxed font-sans"
            rows="2"
          >${escapeHtml(c.draft_reply)}</textarea>

          <!-- Reply action toolbar -->
          <div class="flex items-center justify-between pt-1">
            <button
              onclick="regenerateDraft('${c.id}', '${escapeAttr(c.text)}', '${escapeAttr(c.author)}', '${c.category}')"
              class="inline-flex items-center space-x-1 text-[11px] text-slate-400 hover:text-purple-300 transition"
              id="regen-btn-${c.id}"
            >
              <i data-lucide="refresh-cw" class="w-3 h-3"></i>
              <span>Regenerate Draft</span>
            </button>

            <div class="flex items-center space-x-2">
              <button
                onclick="copyReply('${c.id}')"
                id="copy-btn-${c.id}"
                class="inline-flex items-center space-x-1.5 px-3 py-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-200 text-xs font-medium border border-slate-700 transition"
              >
                <i data-lucide="copy" class="w-3.5 h-3.5"></i>
                <span id="copy-label-${c.id}">Copy Reply</span>
              </button>

              <button
                onclick="approveReply('${c.id}')"
                class="inline-flex items-center space-x-1.5 px-3 py-1.5 rounded-lg bg-purple-600 hover:bg-purple-500 text-white text-xs font-medium transition shadow-sm"
              >
                <i data-lucide="check" class="w-3.5 h-3.5"></i>
                <span>Approve</span>
              </button>
            </div>
          </div>
        </div>
      ` : ''}
    </div>
  `;
}

function copyReply(commentId) {
  const textarea = document.getElementById(`draft-text-${commentId}`);
  if (!textarea) return;

  const textToCopy = textarea.value;
  navigator.clipboard.writeText(textToCopy).then(() => {
    const btnLabel = document.getElementById(`copy-label-${commentId}`);
    const copyBtn = document.getElementById(`copy-btn-${commentId}`);
    if (btnLabel && copyBtn) {
      btnLabel.innerText = 'Copied! ✓';
      copyBtn.classList.add('bg-emerald-600/30', 'border-emerald-500/50', 'text-emerald-200');

      setTimeout(() => {
        btnLabel.innerText = 'Copy Reply';
        copyBtn.classList.remove('bg-emerald-600/30', 'border-emerald-500/50', 'text-emerald-200');
      }, 2000);
    }
    showToast('Reply copied to clipboard!');
  }).catch(err => {
    console.error('Failed to copy', err);
    showToast('Failed to copy reply.');
  });
}

async function approveReply(commentId) {
  const textarea = document.getElementById(`draft-text-${commentId}`);
  const replyText = textarea ? textarea.value : '';

  try {
    const res = await fetch('/api/approve', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ comment_id: commentId, draft_reply: replyText })
    });

    if (res.ok) {
      // Mark as approved in local dataset
      const c = allComments.find(x => x.id === commentId);
      if (c) {
        c.is_approved = true;
        c.draft_reply = replyText;
      }
      renderFilteredComments();
      showToast('Comment reply marked as approved!');
    }
  } catch (e) {
    console.error('Approve failed', e);
  }
}

async function regenerateDraft(commentId, commentText, author, category) {
  const btn = document.getElementById(`regen-btn-${commentId}`);
  if (btn) btn.classList.add('opacity-50', 'pointer-events-none');

  try {
    const res = await fetch('/api/draft', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        comment_id: commentId,
        comment_text: commentText,
        author: author,
        category: category,
        creator_style: userSettings.creatorStyle || 'friendly_concise',
        api_key_llm: userSettings.llmApiKey || null
      })
    });

    if (res.ok) {
      const data = await res.json();
      const textarea = document.getElementById(`draft-text-${commentId}`);
      if (textarea) textarea.value = data.draft_reply;
      
      const c = allComments.find(x => x.id === commentId);
      if (c) c.draft_reply = data.draft_reply;

      showToast('Draft reply regenerated!');
    }
  } catch (e) {
    console.error('Regenerate error:', e);
  } finally {
    if (btn) btn.classList.remove('opacity-50', 'pointer-events-none');
  }
}

function showToast(message) {
  const toast = document.getElementById('toast');
  const msg = document.getElementById('toastMessage');
  msg.innerText = message;
  toast.classList.remove('hidden');

  setTimeout(() => {
    toast.classList.add('hidden');
  }, 2500);
}

function formatTimestamp(isoString) {
  if (!isoString) return '';
  try {
    const date = new Date(isoString);
    const now = new Date();
    const diffHours = Math.round((now - date) / (1000 * 60 * 60));
    if (diffHours < 1) return 'Just now';
    if (diffHours === 1) return '1 hour ago';
    if (diffHours < 24) return `${diffHours} hours ago`;
    const diffDays = Math.round(diffHours / 24);
    return `${diffDays} days ago`;
  } catch (e) {
    return '';
  }
}

function escapeHtml(str) {
  if (!str) return '';
  return str.replace(/&/g, '&amp;')
            .replace(/</g, '&lt;')
            .replace(/>/g, '&gt;')
            .replace(/"/g, '&quot;')
            .replace(/'/g, '&#039;');
}

function escapeAttr(str) {
  if (!str) return '';
  return str.replace(/'/g, "\\'").replace(/"/g, '&quot;');
}
