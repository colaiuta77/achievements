// 독서 업적 API 응답을 안전한 DOM 카드로 렌더링하고 상태 필터를 처리합니다.
(function () {
  'use strict';

  const root = document.getElementById('achievements-page');
  if (!root) return;

  const rarityLabels = {
    common: '일반',
    rare: '희귀',
    epic: '영웅',
    legendary: '전설',
  };
  const state = {
    filter: 'all',
    data: null,
    requestId: 0,
  };
  const elements = {
    filters: [...root.querySelectorAll('.achievements-filter')],
    refresh: root.querySelector('#achievements-refresh'),
    state: root.querySelector('#achievements-state'),
    categories: root.querySelector('#achievements-categories'),
    userCopy: root.querySelector('#achievements-user-copy'),
    overallCount: root.querySelector('#achievements-overall-count'),
    overallPercent: root.querySelector('#achievements-overall-percent'),
    countAll: root.querySelector('#achievement-count-all'),
    countUnlocked: root.querySelector('#achievement-count-unlocked'),
    countProgress: root.querySelector('#achievement-count-progress'),
    countLocked: root.querySelector('#achievement-count-locked'),
    booksCompleted: root.querySelector('#metric-books-completed'),
    fixedPages: root.querySelector('#metric-fixed-pages'),
    currentStreak: root.querySelector('#metric-current-streak'),
    audioCompleted: root.querySelector('#metric-audio-completed'),
    nextAchievement: root.querySelector('#metric-next-achievement'),
  };

  function number(value) {
    const parsed = Number(value);
    return Number.isFinite(parsed) ? parsed : 0;
  }

  function setText(element, value) {
    if (element) element.textContent = String(value);
  }

  function showState(message, iconClass) {
    elements.categories.replaceChildren();
    elements.state.replaceChildren();
    const icon = document.createElement('i');
    icon.className = iconClass;
    icon.setAttribute('aria-hidden', 'true');
    elements.state.append(icon, document.createTextNode(` ${message}`));
    elements.state.hidden = false;
  }

  function formatNumber(value) {
    return Math.max(0, number(value)).toLocaleString('ko-KR');
  }

  function formatDate(value) {
    const text = String(value || '').trim();
    if (!text) return '';
    const datePart = text.slice(0, 10).split('-');
    if (datePart.length !== 3) return text.slice(0, 10);
    return `${number(datePart[0])}년 ${number(datePart[1])}월 ${number(datePart[2])}일`;
  }

  function formatProgressValue(item) {
    const current = formatNumber(item.current);
    const target = formatNumber(item.target);
    if (item.unit === '페이지') return `${current} / ${target}페이지`;
    if (item.unit === '일') return `${current} / ${target}일`;
    if (item.unit === '장르') return `${current} / ${target}개 장르`;
    if (item.unit === '태그') return `${current} / ${target}개 태그`;
    return `${current} / ${target}권`;
  }

  function createProgressTrack(percent, className) {
    const track = document.createElement('div');
    track.className = className;
    track.setAttribute('role', 'progressbar');
    track.setAttribute('aria-valuemin', '0');
    track.setAttribute('aria-valuemax', '100');
    track.setAttribute('aria-valuenow', String(number(percent)));
    const fill = document.createElement('span');
    fill.className = className === 'achievement-progress-track' ? 'achievement-progress-fill' : '';
    fill.style.width = `${Math.max(0, Math.min(100, number(percent)))}%`;
    track.appendChild(fill);
    return track;
  }

  function createAchievementCard(item) {
    const card = document.createElement('article');
    card.className = `achievement-card rarity-${item.rarity} status-${item.status}`;
    card.dataset.status = item.status;

    const top = document.createElement('div');
    top.className = 'achievement-card-top';
    const iconBox = document.createElement('div');
    iconBox.className = 'achievement-icon';
    const icon = document.createElement('i');
    icon.className = item.icon;
    icon.setAttribute('aria-hidden', 'true');
    iconBox.appendChild(icon);

    const copy = document.createElement('div');
    copy.className = 'achievement-copy';
    const titleRow = document.createElement('div');
    titleRow.className = 'achievement-title-row';
    const title = document.createElement('h3');
    title.textContent = item.title;
    title.title = item.title;
    const rarity = document.createElement('span');
    rarity.className = 'achievement-rarity';
    rarity.textContent = rarityLabels[item.rarity] || '일반';
    titleRow.append(title, rarity);
    const description = document.createElement('p');
    description.className = 'achievement-description';
    description.textContent = item.description;
    copy.append(titleRow, description);
    top.append(iconBox, copy);
    card.appendChild(top);

    if (item.unlocked) {
      const check = document.createElement('i');
      check.className = 'fa-solid fa-circle-check achievement-check';
      check.setAttribute('aria-label', '달성 완료');
      card.appendChild(check);
    }

    const bottom = document.createElement('div');
    bottom.className = 'achievement-card-bottom';
    if (item.unlocked) {
      const date = document.createElement('span');
      date.className = 'achievement-unlocked-date';
      date.textContent = `${formatDate(item.unlocked_at)} 달성`;
      bottom.appendChild(date);
    } else {
      const meta = document.createElement('div');
      meta.className = 'achievement-progress-meta';
      const value = document.createElement('strong');
      value.textContent = formatProgressValue(item);
      const remaining = document.createElement('span');
      remaining.textContent = item.status === 'locked'
        ? '아직 시작 전'
        : `${formatNumber(item.remaining)} 남음`;
      meta.append(value, remaining);
      bottom.append(meta, createProgressTrack(item.progress_percent, 'achievement-progress-track'));
    }
    card.appendChild(bottom);
    return card;
  }

  function createCategorySection(category, items) {
    const section = document.createElement('section');
    section.className = 'achievement-category';
    section.dataset.category = category.key;
    const header = document.createElement('header');
    header.className = 'achievement-category-header';
    const marker = document.createElement('span');
    marker.className = 'achievement-category-marker';
    marker.setAttribute('aria-hidden', 'true');
    const icon = document.createElement('i');
    icon.className = category.icon;
    icon.setAttribute('aria-hidden', 'true');
    const title = document.createElement('h2');
    title.textContent = category.title;
    const progress = document.createElement('div');
    progress.className = 'achievement-category-progress';
    const progressTrack = createProgressTrack(category.progress_percent, 'achievement-category-track');
    const progressCopy = document.createElement('span');
    progressCopy.textContent = `${category.unlocked} / ${category.total}`;
    progress.append(progressTrack, progressCopy);
    header.append(marker, icon, title, progress);

    const grid = document.createElement('div');
    grid.className = 'achievement-grid';
    items.forEach((item) => grid.appendChild(createAchievementCard(item)));
    section.append(header, grid);
    return section;
  }

  function filteredAchievements() {
    const achievements = state.data?.achievements || [];
    if (state.filter === 'all') return achievements;
    return achievements.filter((item) => item.status === state.filter);
  }

  function render() {
    if (!state.data) return;
    const visibleItems = filteredAchievements();
    elements.categories.replaceChildren();

    state.data.categories.forEach((category) => {
      const categoryItems = visibleItems.filter((item) => item.category === category.key);
      if (categoryItems.length) {
        elements.categories.appendChild(createCategorySection(category, categoryItems));
      }
    });

    if (!visibleItems.length) {
      const empty = document.createElement('div');
      empty.className = 'achievement-empty';
      empty.textContent = '이 상태에 해당하는 업적이 없습니다.';
      elements.categories.appendChild(empty);
    }
    elements.state.hidden = true;
  }

  function updateSummary(data) {
    const summary = data.summary || {};
    const metrics = data.metrics || {};
    setText(elements.userCopy, `${data.user?.username || '사용자'}님의 독서 여정을 기록하고 있습니다.`);
    setText(elements.overallCount, `${formatNumber(summary.unlocked)} / ${formatNumber(summary.total)}`);
    setText(elements.overallPercent, `${formatNumber(summary.progress_percent)}% 달성`);
    setText(elements.countAll, formatNumber(summary.total));
    setText(elements.countUnlocked, formatNumber(summary.unlocked));
    setText(elements.countProgress, formatNumber(summary.in_progress));
    setText(elements.countLocked, formatNumber(summary.locked));
    setText(elements.booksCompleted, `${formatNumber(metrics.books_completed)}권`);
    setText(elements.fixedPages, `${formatNumber(metrics.fixed_pages_read)}페이지`);
    setText(elements.currentStreak, `${formatNumber(metrics.current_streak)}일`);
    setText(elements.audioCompleted, `${formatNumber(metrics.audiobooks_completed)}권`);
    setText(
      elements.nextAchievement,
      data.next_achievement
        ? `${data.next_achievement.title} · ${formatNumber(data.next_achievement.remaining)} 남음`
        : '모든 업적 달성',
    );
  }

  async function loadAchievements() {
    const requestId = ++state.requestId;
    elements.refresh.disabled = true;
    showState('업적을 계산하는 중입니다.', 'fa-solid fa-circle-notch fa-spin');
    try {
      const response = await fetch('/api/media/dashboard/widgets/achievements/data?type=general&limit=100', {
        credentials: 'same-origin',
        headers: { Accept: 'application/json' },
      });
      const data = await response.json();
      if (requestId !== state.requestId) return;
      if (!response.ok || !data.success) {
        throw new Error(data.error || '업적 데이터를 불러오지 못했습니다.');
      }
      state.data = data;
      updateSummary(data);
      render();
    } catch (error) {
      if (requestId !== state.requestId) return;
      showState(error.message || '업적 데이터를 불러오지 못했습니다.', 'fa-solid fa-triangle-exclamation');
    } finally {
      if (requestId === state.requestId) elements.refresh.disabled = false;
    }
  }

  elements.filters.forEach((button) => {
    button.addEventListener('click', () => {
      state.filter = button.dataset.filter || 'all';
      elements.filters.forEach((item) => {
        const active = item === button;
        item.classList.toggle('is-active', active);
        item.setAttribute('aria-pressed', String(active));
      });
      render();
    });
  });
  elements.refresh.addEventListener('click', loadAchievements);
  loadAchievements();
})();
