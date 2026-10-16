// NPTEL Mock Test App - Client Logic & State Management

let currentUser = null;
let currentExamData = null;
let currentQuestionIndex = 0;
let userAnswers = {};
let examTimerInterval = null;
let remainingSeconds = 0;
let bookmarkedQuestions = [];

// Initialize App
document.addEventListener('DOMContentLoaded', () => {
  checkExistingSession();
  loadLeaderboard();
  loadBookmarks();
});

// Auth Tab Switcher
function switchAuthTab(tab) {
  const loginForm = document.getElementById('login-form');
  const signupForm = document.getElementById('signup-form');
  const tabLoginBtn = document.getElementById('tab-login-btn');
  const tabSignupBtn = document.getElementById('tab-signup-btn');

  if (tab === 'login') {
    loginForm.classList.remove('hidden');
    signupForm.classList.add('hidden');
    tabLoginBtn.classList.add('active');
    tabSignupBtn.classList.remove('active');
  } else {
    loginForm.classList.add('hidden');
    signupForm.classList.remove('hidden');
    tabLoginBtn.classList.remove('active');
    tabSignupBtn.classList.add('active');
  }
}

function togglePasswordVisibility(fieldId) {
  const input = document.getElementById(fieldId);
  if (input.type === 'password') {
    input.type = 'text';
  } else {
    input.type = 'password';
  }
}

// Session Check
function checkExistingSession() {
  const savedUser = localStorage.getItem('nptel_user');
  if (savedUser) {
    try {
      currentUser = JSON.parse(savedUser);
      showDashboard(currentUser);
    } catch (e) {
      localStorage.removeItem('nptel_user');
    }
  }
}

// Login Handler
async function handleLogin(event) {
  if (event) event.preventDefault();
  const email = document.getElementById('login-email').value;

  try {
    const res = await fetch('/api/auth/login', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ email })
    });
    const data = await res.json();
    if (data.success) {
      currentUser = data.user;
      localStorage.setItem('nptel_user', JSON.stringify(currentUser));
      showDashboard(currentUser);
    }
  } catch (err) {
    console.error('Login error:', err);
  }
}

function handleDemoLogin() {
  document.getElementById('login-email').value = 'alex.nptel@student.ac.in';
  handleLogin(null);
}

// Signup Handler
async function handleSignup(event) {
  event.preventDefault();
  const name = document.getElementById('signup-name').value;
  const email = document.getElementById('signup-email').value;
  const course = document.getElementById('signup-course').value;

  try {
    const res = await fetch('/api/auth/signup', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ name, email, course })
    });
    const data = await res.json();
    if (data.success) {
      currentUser = data.user;
      localStorage.setItem('nptel_user', JSON.stringify(currentUser));
      showDashboard(currentUser);
    }
  } catch (err) {
    console.error('Signup error:', err);
  }
}

// Logout Handler
function handleLogout() {
  currentUser = null;
  localStorage.removeItem('nptel_user');
  document.getElementById('dashboard-view').classList.add('hidden');
  document.getElementById('auth-view').classList.remove('hidden');
}

// Dashboard Transition
function showDashboard(user) {
  document.getElementById('auth-view').classList.add('hidden');
  document.getElementById('dashboard-view').classList.remove('hidden');

  // Update profile details
  document.getElementById('user-name').innerText = user.name;
  document.getElementById('hero-user-name').innerText = user.name.split(' ')[0];
  document.getElementById('user-avatar').src = user.avatar || 'https://images.unsplash.com/photo-1534528741775-53994a69daeb?w=150&auto=format&fit=crop&q=80';
  document.getElementById('user-rank').innerHTML = `<i class="fa-solid fa-trophy"></i> Rank #${user.rank || 4}`;
  document.getElementById('user-xp').innerText = (user.xp || 3450).toLocaleString();
  document.getElementById('user-streak').innerText = user.streak || 5;

  showTab('home');
}

// Tab Switcher inside Dashboard
function showTab(tabId) {
  // Update sidebar buttons
  document.querySelectorAll('.nav-item').forEach(btn => {
    if (btn.getAttribute('data-tab') === tabId) {
      btn.classList.add('active');
    } else {
      btn.classList.remove('active');
    }
  });

  // Update tab pages
  document.querySelectorAll('.tab-page').forEach(page => {
    if (page.id === `tab-${tabId}`) {
      page.classList.add('active');
    } else {
      page.classList.remove('active');
    }
  });

  if (tabId === 'leaderboard') loadLeaderboard();
  if (tabId === 'bookmarks') renderBookmarksTab();
}

function toggleSidebar() {
  const sidebar = document.getElementById('sidebar');
  sidebar.classList.toggle('hidden');
}

// Quick Start Test shortcut
function quickStartTest(subject, difficulty, count) {
  document.getElementById('gen-subject').value = subject;
  const countInput = document.getElementById('gen-count');
  if (countInput) {
    countInput.value = count;
    document.getElementById('q-count-val').innerText = count;
  }
  showTab('generate');
  generateAndStartExam(subject, difficulty, count, 20);
}

// Generate Form Submit
function handleGenerateTest(event) {
  event.preventDefault();
  const subject = document.getElementById('gen-subject').value;
  const difficulty = document.querySelector('input[name="difficulty"]:checked').value;
  const count = parseInt(document.getElementById('gen-count').value, 10);
  const timerMins = parseInt(document.getElementById('gen-timer').value, 10);

  generateAndStartExam(subject, difficulty, count, timerMins);
}

// Core Exam Generation API Call
async function generateAndStartExam(subject, difficulty, count, timerMins) {
  const loadingModal = document.getElementById('ai-loading-modal');
  loadingModal.classList.remove('hidden');
  document.getElementById('loader-status').innerText = 'Querying Claude 3.5 AI & Supabase Cache...';

  try {
    const res = await fetch('/api/tests/generate', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ subject, difficulty, count })
    });
    const data = await res.json();
    loadingModal.classList.add('hidden');

    if (data.questions && data.questions.length > 0) {
      startExamEngine(data, timerMins);
    } else {
      alert('Could not generate questions for selected options.');
    }
  } catch (err) {
    loadingModal.classList.add('hidden');
    console.error('Generation error:', err);
    alert('Server connection error. Please try again.');
  }
}

// Exam Engine Launcher
function startExamEngine(examData, timerMins) {
  currentExamData = examData;
  currentQuestionIndex = 0;
  userAnswers = {};

  document.getElementById('exam-subject-title').innerText = examData.subject;
  document.getElementById('exam-diff-title').innerText = examData.difficulty;

  // Set Timer
  remainingSeconds = (timerMins || 20) * 60;
  startTimer();

  // Render question & palette
  renderCurrentQuestion();
  renderPaletteGrid();

  document.getElementById('exam-modal').classList.remove('hidden');
}

// Timer Logic
function startTimer() {
  clearInterval(examTimerInterval);
  updateTimerDisplay();

  examTimerInterval = setInterval(() => {
    remainingSeconds--;
    if (remainingSeconds <= 0) {
      clearInterval(examTimerInterval);
      alert('Time is up! Auto-submitting your test...');
      submitExam();
    } else {
      updateTimerDisplay();
    }
  }, 1000);
}

function updateTimerDisplay() {
  const mins = Math.floor(remainingSeconds / 60);
  const secs = remainingSeconds % 60;
  const timerStr = `${mins.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`;
  document.getElementById('exam-timer-display').innerText = timerStr;
}

// Question Renderer
function renderCurrentQuestion() {
  const questions = currentExamData.questions;
  const q = questions[currentQuestionIndex];

  document.getElementById('question-number-lbl').innerText = `Question ${currentQuestionIndex + 1} of ${questions.length}`;
  document.getElementById('question-week-lbl').innerText = q.nptel_week || 'NPTEL Core';
  document.getElementById('question-text').innerText = q.question;

  // Options
  const container = document.getElementById('options-container');
  container.innerHTML = '';

  const selectedOpt = userAnswers[currentQuestionIndex];

  q.options.forEach((optText, idx) => {
    const isSelected = (selectedOpt === idx);
    const optEl = document.createElement('div');
    optEl.className = `option-item ${isSelected ? 'selected' : ''}`;
    optEl.onclick = () => selectOption(idx);

    optEl.innerHTML = `
      <div class="opt-radio">
        ${isSelected ? '<i class="fa-solid fa-check text-dark" style="font-size: 0.65rem;"></i>' : ''}
      </div>
      <span class="opt-text"><strong>${String.fromCharCode(65 + idx)}.</strong> ${optText}</span>
    `;
    container.appendChild(optEl);
  });

  // Progress fill
  const progressPercent = ((currentQuestionIndex + 1) / questions.length) * 100;
  document.getElementById('exam-progress-fill').style.width = `${progressPercent}%`;

  // Buttons state
  document.getElementById('prev-q-btn').disabled = (currentQuestionIndex === 0);
  const nextBtn = document.getElementById('next-q-btn');
  const submitBtn = document.getElementById('submit-exam-btn');

  if (currentQuestionIndex === questions.length - 1) {
    nextBtn.classList.add('hidden');
    submitBtn.classList.remove('hidden');
  } else {
    nextBtn.classList.remove('hidden');
    submitBtn.classList.add('hidden');
  }

  // Answered count
  const answeredCount = Object.keys(userAnswers).length;
  document.getElementById('answered-count-lbl').innerText = `${answeredCount} of ${questions.length} Answered`;

  // Bookmark state
  const isBookmarked = bookmarkedQuestions.some(b => b.question === q.question);
  const bookmarkBtn = document.getElementById('bookmark-btn');
  if (isBookmarked) {
    bookmarkBtn.classList.add('active');
    bookmarkBtn.innerHTML = '<i class="fa-solid fa-bookmark"></i> Saved';
  } else {
    bookmarkBtn.classList.remove('active');
    bookmarkBtn.innerHTML = '<i class="fa-regular fa-bookmark"></i> Save';
  }
}

function selectOption(optionIndex) {
  userAnswers[currentQuestionIndex] = optionIndex;
  renderCurrentQuestion();
  renderPaletteGrid();
}

function navigateQuestion(delta) {
  const newIdx = currentQuestionIndex + delta;
  if (newIdx >= 0 && newIdx < currentExamData.questions.length) {
    currentQuestionIndex = newIdx;
    renderCurrentQuestion();
    renderPaletteGrid();
  }
}

// Palette Grid Renderer
function renderPaletteGrid() {
  const grid = document.getElementById('palette-grid');
  grid.innerHTML = '';

  currentExamData.questions.forEach((q, idx) => {
    const isAnswered = (userAnswers[idx] !== undefined);
    const isCurrent = (idx === currentQuestionIndex);
    const isBookmarked = bookmarkedQuestions.some(b => b.question === q.question);

    const btn = document.createElement('button');
    let classes = 'pal-btn';
    if (isAnswered) classes += ' answered';
    if (isCurrent) classes += ' current';
    if (isBookmarked) classes += ' bookmarked';

    btn.className = classes;
    btn.innerText = idx + 1;
    btn.onclick = () => {
      currentQuestionIndex = idx;
      renderCurrentQuestion();
      renderPaletteGrid();
    };
    grid.appendChild(btn);
  });
}

// Bookmark Toggle
async function toggleCurrentBookmark() {
  const q = currentExamData.questions[currentQuestionIndex];
  try {
    const res = await fetch('/api/bookmarks', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ question: q })
    });
    const data = await res.json();
    loadBookmarks();
    renderCurrentQuestion();
    renderPaletteGrid();
  } catch (err) {
    console.error('Bookmark error:', err);
  }
}

// Exit Exam Confirmation
function confirmExitExam() {
  if (confirm('Are you sure you want to exit? Your exam progress will be discarded.')) {
    clearInterval(examTimerInterval);
    document.getElementById('exam-modal').classList.add('hidden');
  }
}

// Submit Exam API Call
async function submitExam() {
  clearInterval(examTimerInterval);

  try {
    const res = await fetch('/api/tests/submit', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        answers: userAnswers,
        questions: currentExamData.questions
      })
    });

    const results = await res.json();
    document.getElementById('exam-modal').classList.add('hidden');
    renderResultsModal(results);
  } catch (err) {
    console.error('Submission error:', err);
    alert('Error submitting test. Please try again.');
  }
}

// Results Renderer
function renderResultsModal(results) {
  document.getElementById('results-score-percent').innerText = `${results.score_percentage}%`;
  document.getElementById('results-grade').innerText = results.performance_grade;
  document.getElementById('results-correct').innerText = `${results.correct_count} / ${results.total_questions}`;
  document.getElementById('results-xp').innerText = `+${results.xp_earned} XP`;
  document.getElementById('results-ai-analysis').innerText = results.ai_analysis;

  const list = document.getElementById('results-breakdown-list');
  list.innerHTML = '';

  results.results.forEach((item, idx) => {
    const card = document.createElement('div');
    card.className = `breakdown-card ${item.is_correct ? 'correct-q' : 'incorrect-q'}`;

    const userAnsText = item.user_answer !== undefined && item.user_answer !== null ? item.options[item.user_answer] : 'Not Answered';
    const correctAnsText = item.options[item.correct_answer];

    card.innerHTML = `
      <div class="bq-header">
        <span class="bq-text">Q${idx + 1}. ${item.question}</span>
        <span class="${item.is_correct ? 'text-green' : 'text-orange'} font-bold">
          <i class="fa-solid ${item.is_correct ? 'fa-circle-check' : 'fa-circle-xmark'}"></i>
          ${item.is_correct ? 'Correct' : 'Incorrect'}
        </span>
      </div>
      <div style="font-size: 0.88rem; color: #d1d5db;">
        <div><strong>Your Answer:</strong> ${userAnsText}</div>
        <div><strong>Correct Answer:</strong> ${correctAnsText}</div>
      </div>
      <div class="explanation-box">
        <strong><i class="fa-solid fa-robot"></i> Claude AI Explanation:</strong> ${item.explanation}
      </div>
    `;
    list.appendChild(card);
  });

  document.getElementById('results-modal').classList.remove('hidden');

  // Update profile XP locally
  if (currentUser) {
    currentUser.xp = (currentUser.xp || 3450) + results.xp_earned;
    currentUser.tests_taken = (currentUser.tests_taken || 14) + 1;
    document.getElementById('user-xp').innerText = currentUser.xp.toLocaleString();
    localStorage.setItem('nptel_user', JSON.stringify(currentUser));
  }
}

function closeResultsModal() {
  document.getElementById('results-modal').classList.add('hidden');
}

// Fetch Leaderboard Data
async function loadLeaderboard() {
  try {
    const res = await fetch('/api/leaderboard');
    const data = await res.json();
    const listContainer = document.getElementById('leaderboard-list');

    if (listContainer && data.leaderboard) {
      listContainer.innerHTML = '';
      data.leaderboard.forEach(item => {
        const isUser = item.name.includes('(You)');
        const row = document.createElement('div');
        row.className = `leader-row-item ${isUser ? 'highlight-user' : ''}`;
        row.innerHTML = `
          <span><strong>#${item.rank}</strong></span>
          <span><strong>${item.name}</strong></span>
          <span style="color: #9ca3af;">${item.institution}</span>
          <span class="text-cyan font-bold">${item.score}</span>
          <span class="text-gold font-bold">${item.xp} XP</span>
        `;
        listContainer.appendChild(row);
      });
    }
  } catch (err) {
    console.error('Leaderboard error:', err);
  }
}

// Fetch Bookmarks
async function loadBookmarks() {
  try {
    const res = await fetch('/api/bookmarks');
    const data = await res.json();
    bookmarkedQuestions = data.bookmarks || [];
  } catch (err) {
    console.error('Bookmarks error:', err);
  }
}

function renderBookmarksTab() {
  const container = document.getElementById('bookmarks-container');
  container.innerHTML = '';

  if (bookmarkedQuestions.length === 0) {
    container.innerHTML = `
      <div class="empty-state">
        <i class="fa-regular fa-bookmark"></i>
        <p>No questions saved yet. Click the bookmark icon during any mock test to review tricky questions here.</p>
      </div>
    `;
    return;
  }

  bookmarkedQuestions.forEach((q, idx) => {
    const card = document.createElement('div');
    card.className = 'breakdown-card correct-q';
    card.innerHTML = `
      <div class="bq-header">
        <span class="bq-text">Q${idx + 1}. ${q.question}</span>
        <span class="text-cyan font-bold">${q.nptel_week || 'Saved MCQ'}</span>
      </div>
      <div class="explanation-box">
        <strong><i class="fa-solid fa-robot"></i> Claude AI Explanation:</strong> ${q.explanation}
      </div>
    `;
    container.appendChild(card);
  });
}
