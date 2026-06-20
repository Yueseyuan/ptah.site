/* ── Cruel & Associates Credit Monitor — App JS ── */

/* Mock user session (replace with real auth API) */
const MOCK_USER = {
  firstName: 'Marcus',
  lastName:  'Johnson',
  email:     'marcus.j@email.com',
  score:     742,
  scoreChange: +18,
  lastUpdated: 'June 13, 2026',
  bureaus: {
    equifax:    736,
    experian:   748,
    transunion: 742,
  },
  factors: [
    { name: 'Payment History',      pct: 97, weight: 35, impact: 'high' },
    { name: 'Credit Utilization',   pct: 22, weight: 30, impact: 'high' },
    { name: 'Credit Age',           pct: 68, weight: 15, impact: 'med'  },
    { name: 'Credit Mix',           pct: 80, weight: 10, impact: 'low'  },
    { name: 'New Credit Inquiries', pct: 90, weight: 10, impact: 'low'  },
  ],
  alerts: [
    { icon: '✅', type: 'good', title: 'Score Increased',         desc: 'Your score went up 18 points this month.',       time: '2 hours ago' },
    { icon: '⚠️', type: 'warn', title: 'Credit Card Utilization', desc: 'Chase Sapphire utilization reached 28%.',         time: 'Yesterday'   },
    { icon: 'ℹ️', type: 'info', title: 'New Account Detected',    desc: 'A new inquiry was added to your Experian report.',time: '3 days ago'  },
    { icon: '✅', type: 'good', title: 'On-Time Payment',         desc: 'Bank of America payment recorded on time.',       time: '5 days ago'  },
  ],
};

/* ── Score color by range ── */
function scoreColor(s) {
  if (s < 580) return '#ef4444';
  if (s < 670) return '#f97316';
  if (s < 740) return '#eab308';
  if (s < 800) return '#22c55e';
  return '#16a34a';
}
function scoreRating(s) {
  if (s < 580) return 'Poor';
  if (s < 670) return 'Fair';
  if (s < 740) return 'Good';
  if (s < 800) return 'Very Good';
  return 'Excellent';
}

/* ── SVG arc gauge ── */
function buildGaugeSVG(score, size = 200) {
  const min = 300, max = 850;
  const pct  = (score - min) / (max - min);
  const angle = -150 + pct * 300; // -150° to +150°
  const cx = size / 2, cy = size / 2, r = size * 0.42;
  const toRad = d => d * Math.PI / 180;
  const arcX = (deg) => cx + r * Math.cos(toRad(deg - 90));
  const arcY = (deg) => cy + r * Math.sin(toRad(deg - 90));

  const startD = -150, endD = 150;
  const segments = [
    { from: -150, to: -90,  color: '#ef4444' },
    { from:  -90, to: -30,  color: '#f97316' },
    { from:  -30, to:  30,  color: '#eab308' },
    { from:   30, to:  90,  color: '#22c55e' },
    { from:   90, to: 150,  color: '#16a34a' },
  ];

  let arcs = segments.map(({ from, to, color }) => {
    const large = (to - from) > 180 ? 1 : 0;
    return `<path d="M ${arcX(from)} ${arcY(from)} A ${r} ${r} 0 ${large} 1 ${arcX(to)} ${arcY(to)}"
      fill="none" stroke="${color}" stroke-width="${size * 0.07}" stroke-linecap="round" opacity="0.25"/>`;
  }).join('');

  // Active arc
  const activeTo = -150 + pct * 300;
  const activeArcLarge = (activeTo - startD) > 180 ? 1 : 0;
  const col = scoreColor(score);
  arcs += `<path d="M ${arcX(startD)} ${arcY(startD)} A ${r} ${r} 0 ${activeArcLarge} 1 ${arcX(activeTo)} ${arcY(activeTo)}"
    fill="none" stroke="${col}" stroke-width="${size * 0.07}" stroke-linecap="round"/>`;

  // Needle
  const nLen = r * 0.72;
  const nAngle = angle - 90;
  const nx = cx + nLen * Math.cos(toRad(nAngle));
  const ny = cy + nLen * Math.sin(toRad(nAngle));
  arcs += `<line x1="${cx}" y1="${cy}" x2="${nx}" y2="${ny}" stroke="${col}" stroke-width="2.5" stroke-linecap="round"/>
           <circle cx="${cx}" cy="${cy}" r="5" fill="${col}"/>`;

  return `<svg viewBox="0 0 ${size} ${size}" xmlns="http://www.w3.org/2000/svg">${arcs}</svg>`;
}

/* ── Factor progress color ── */
function factorColor(pct) {
  if (pct < 40) return '#ef4444';
  if (pct < 65) return '#eab308';
  return '#22c55e';
}

/* ── Bureau bar fill ── */
function bureauFill(score) {
  const pct = Math.round(((score - 300) / 550) * 100);
  return { pct, color: scoreColor(score) };
}

/* ── Toast notification ── */
function showToast(msg, duration = 3000) {
  const t = document.createElement('div');
  t.className = 'toast';
  t.textContent = msg;
  document.body.appendChild(t);
  setTimeout(() => t.remove(), duration);
}

/* ── Simple auth simulation (localStorage) ── */
const Auth = {
  login(email, password) {
    /* TODO: replace with real API call
       fetch('/api/auth/login', { method:'POST', body: JSON.stringify({email,password}) }) */
    if (email && password.length >= 6) {
      localStorage.setItem('ca_session', JSON.stringify({ email, ts: Date.now() }));
      return true;
    }
    return false;
  },
  signup(data) {
    /* TODO: replace with real API call
       fetch('/api/auth/signup', { method:'POST', body: JSON.stringify(data) }) */
    localStorage.setItem('ca_session', JSON.stringify({ email: data.email, ts: Date.now() }));
    return true;
  },
  logout() {
    localStorage.removeItem('ca_session');
    window.location.href = 'index.html';
  },
  isLoggedIn() {
    const s = localStorage.getItem('ca_session');
    if (!s) return false;
    const { ts } = JSON.parse(s);
    return (Date.now() - ts) < 24 * 60 * 60 * 1000; // 24h session
  },
  getSession() {
    const s = localStorage.getItem('ca_session');
    return s ? JSON.parse(s) : null;
  }
};
