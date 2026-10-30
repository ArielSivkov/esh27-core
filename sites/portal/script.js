// --- HAPTIC FEEDBACK ---
function haptic(ms = 18) {
  if (navigator.vibrate) navigator.vibrate(ms);
}
document.addEventListener('click', (e) => {
  const el = e.target.closest('[data-haptic]');
  if (el) haptic(18);
});

// --- LAZY LOAD BACKGROUND IMAGES ---
const lazyBgEls = document.querySelectorAll('[data-bg]');
const bgObserver = new IntersectionObserver((entries, obs) => {
  entries.forEach(entry => {
    if (!entry.isIntersecting) return;
    const el = entry.target;
    const src = el.getAttribute('data-bg');
    el.style.setProperty('--bg', `url("${src}")`);
    obs.unobserve(el);
  });
}, { rootMargin: "250px 0px" });

lazyBgEls.forEach(el => bgObserver.observe(el));

// --- MULTI STEP FORM ---
const leadForm = document.getElementById('leadForm');
if (leadForm) {
  const step1 = leadForm.querySelector('.step[data-step="1"]');
  const step2 = leadForm.querySelector('.step[data-step="2"]');
  const projectType = document.getElementById('projectType');
  const backBtn = document.getElementById('backStep');
  const success = document.getElementById('leadSuccess');

  leadForm.querySelectorAll('[data-pick]').forEach(btn => {
    btn.addEventListener('click', () => {
      projectType.value = btn.getAttribute('data-pick');
      step1.style.display = 'none';
      step2.style.display = 'block';
      const firstInput = step2.querySelector('input[name="fullName"]');
      if (firstInput) firstInput.focus();
    });
  });

  backBtn?.addEventListener('click', () => {
    step2.style.display = 'none';
    step1.style.display = 'block';
    projectType.value = '';
  });

  leadForm.addEventListener('submit', async (e) => {
    e.preventDefault();
    leadForm.style.display = 'none';
    success.style.display = 'block';
  });
}

// --- PWA REGISTRATION ---
if ('serviceWorker' in navigator) {
  window.addEventListener('load', () => {
    navigator.serviceWorker.register('sw.js').catch(() => {});
  });
}

// --- TRANSLATION DATA (i18n) ---
const i18n = {
  he: {
    code: "HE", dir: "rtl",
    nav_divisions: "חטיבות", nav_partners: "שותפים", nav_contact: "צור קשר", nav_about: "אודות", nav_projects: "פרויקטים",
    hero_tag: "Building Realities // Programming Future",
    hero_title: "Architects of Reality.<br>בונים בטון. חושבים קוד.",
    hero_desc: "עבור היזם שרוצה לישון בשקט, והקבלן שחייב דיוק. esh 27 מספקת ביצוע הנדסי מוקפד המגובה בטכנולוגיה למניעת טעויות וחריגות תקציב.",
    cta_explore: "צפה בפרויקטים", cta_strategy: "בנה את העתיד שלך",
    about_tag: "The Human Factor", about_title: "אנשים, לא רק אלגוריתמים.",
    about_desc: "מאחורי כל שורת קוד וכל יציקת בטון עומד צוות של מהנדסים, מנהלי פרויקטים ואנשי מקצוע שחיים את השטח.",
    div1_label: "Division 01 // THE MIND", div1_title: "Cybernetics & AI", div1_short_desc: "התייעלות עסקית אמיתית. מערכות אוטומציה שמחליפות ניירת וכוח אדם יקר.",
    div2_label: "Division 02 // THE BODY", div2_title: "Advanced Engineering", div2_short_desc: "בנייה בראש שקט. ביצוע 'מפתח ביד' עם התחייבות ללו\"ז, שקיפות ובקרת איכות.",
    partners_title: "שותפים אסטרטגיים",
    contact_title: "דברו איתנו", contact_subtitle: "בואו נדבר תכלס. שלח פרטים ונחזור עם הצעה מסודרת.",
    btn_submit: "שלח פנייה", btn_deploy: "הזמן ייעוץ טכנולוגי", btn_build: "התחל פרויקט", btn_back: "חזרה לראשי",
    sw_header: "Department 01 // The Intelligence Layer", sw_tagline: "\"Efficiency through Code\"",
    sw_s1_title: "Autonomous AI", sw_s1_desc: "חסכון בכוח אדם. סוכני AI לביצוע משימות מכירה, שירות ותפעול שוטף.",
    sw_s2_title: "Blockchain & Fintech", sw_s2_desc: "אבטחה פיננסית. חוזים חכמים ותשתיות מבוזרות.",
    sw_s3_title: "Digital Twins", sw_s3_desc: "שליטה מלאה. דשבורד ניהולי המציג את מצב הנכסים והמערכות בזמן אמת.",
    sw_s4_title: "CTO-as-a-Service", sw_s4_desc: "המחלקה הטכנית שלך. ניהול ספקים ופיקוח על פיתוח ללא צורך בידע טכני.",
    con_header: "Department 02 // The Physical Layer", con_tagline: "\"Peace of Mind Construction\"",
    con_s1_title: "Turnkey Projects", con_s1_desc: "ביצוע מפתח ביד ללא דאגות. אחריות משלב השלד ועד לגמר.",
    con_s2_title: "Client Dashboard", con_s2_desc: "שקיפות מלאה. אפליקציה ללקוח המראה התקדמות, תקציב וצילומים מהשטח.",
    con_s3_title: "Project Management", con_s3_desc: "מפקחים מטעמך. מניעת ליקויי בנייה ובקרת איכות (QA) קפדנית.",
    con_s4_title: "Material Supply", con_s4_desc: "רכש ישיר של חומרי גלם פרימיום ומומחי תשתית במחירים סיטונאיים.",
    dash_budget: "ניצול תקציב", dash_progress: "התקדמות בנייה", dash_materials: "מלאי חומרים"
  },
  en: {
    code: "EN", dir: "ltr",
    nav_divisions: "Divisions", nav_partners: "Partners", nav_contact: "Contact", nav_about: "About", nav_projects: "Projects",
    hero_title: "Architects of Reality.<br>We Build, The System Thinks.",
    hero_desc: "For the executive who wants peace of mind, and the builder demanding precision. esh 27 provides elite engineering execution backed by tech.",
    cta_explore: "View Projects", cta_strategy: "Build Your Future",
    about_title: "People, Not Just Algorithms.", about_desc: "Behind every line of code stands a team of engineers living in the field.",
    div1_title: "Cybernetics & AI", div1_short_desc: "Real business efficiency. Automation replacing paperwork and overhead.",
    div2_title: "Advanced Engineering", div2_short_desc: "Worry-free construction. Turnkey execution with timeline commitment.",
    btn_submit: "Send Request", btn_deploy: "Get Tech Consult", btn_build: "Start Project", btn_back: "Back to Base",
    sw_s1_title: "Autonomous AI", sw_s1_desc: "Cut labor costs. AI agents for sales and ops.",
    sw_s2_title: "Blockchain", sw_s2_desc: "Financial security. Smart contracts and decentralized infra.",
    sw_s3_title: "Digital Twins", sw_s3_desc: "Full Control. Management dashboard showing asset status.",
    sw_s4_title: "CTO-as-a-Service", sw_s4_desc: "Your tech department. Vendor management.",
    con_s1_title: "Turnkey Projects", con_s1_desc: "Worry-free execution from skeleton to finish.",
    con_s2_title: "Client Dashboard", con_s2_desc: "Full transparency. Client app showing progress.",
    con_s3_title: "Project Management", con_s3_desc: "Supervision on your behalf. Strict QA.",
    con_s4_title: "Material Supply", con_s4_desc: "Direct sourcing of premium materials.",
    dash_budget: "BUDGET USED", dash_progress: "CONSTRUCTION", dash_materials: "MATERIALS"
  },
  ru: { code: "RU", dir: "ltr", hero_title: "Архитекторы Реальности", cta_strategy: "Ваше Будущее", btn_deploy: "Консультация", btn_build: "Начать проект" },
  ar: { code: "AR", dir: "rtl", hero_title: "مهندسو الواقع", cta_strategy: "ابنِ مستقبلك", btn_deploy: "استشارة تقنية", btn_build: "ابدأ المشروع" }
};

function setLanguage(lang) {
  const data = i18n[lang] || i18n.he;
  document.documentElement.lang = lang;
  document.documentElement.dir = data.dir;
  const codeEl = document.getElementById('currentLangCode');
  if(codeEl) codeEl.innerText = data.code;

  document.querySelectorAll('[data-i18n]').forEach(el => {
    const key = el.getAttribute('data-i18n');
    if (data[key]) el.innerHTML = data[key];
  });
  
  document.querySelectorAll('[data-i18n-placeholder]').forEach(el => {
    const key = el.getAttribute('data-i18n-placeholder');
    if (data[key]) el.placeholder = data[key];
  });
}

// --- NAVIGATION & THEME ---
function switchView(viewId, anchorId = null) {
  const body = document.body;
  // Apply construction theme for construction dept AND projects
  if(viewId === 'construction' || viewId.startsWith('project-')) {
    body.classList.add('theme-construction');
  } else {
    body.classList.remove('theme-construction');
  }

  document.querySelectorAll('.view').forEach(v => v.classList.remove('active'));
  const target = document.getElementById(viewId);
  if(target) target.classList.add('active');
  
  window.scrollTo({ top: 0, behavior: 'smooth' });
  
  if (anchorId) {
    setTimeout(() => {
      const el = document.getElementById(anchorId);
      if (el) el.scrollIntoView({ behavior: 'smooth' });
    }, 100);
  }
}

// --- MATRIX ANIMATION ---
const canvas = document.getElementById('matrix');
if (canvas) {
  const ctx = canvas.getContext('2d');
  let width, height, columns, drops = [];
  const fontSize = 16, chars = "אבגדהוזחטיכלמנסעפצקרשת01ABCDEF".split("");

  function resize() {
    width = canvas.width = window.innerWidth;
    height = canvas.height = window.innerHeight;
    columns = Math.floor(width / fontSize);
    drops = []; 
    for (let i = 0; i < columns; i++) drops[i] = Math.random() * -100;
  }

  function draw() {
    ctx.fillStyle = 'rgba(5, 7, 9, 0.15)'; ctx.fillRect(0, 0, width, height);
    ctx.font = fontSize + 'px "JetBrains Mono"';
    for (let i = 0; i < drops.length; i++) {
      const x = i * fontSize;
      const y = drops[i] * fontSize;
      ctx.fillStyle = (Math.random() > 0.99) ? '#FFFFFF' : 'rgba(255,255,255,0.1)'; 
      ctx.fillText(chars[Math.floor(Math.random() * chars.length)], x, y);
      if (y > height && Math.random() > 0.99) drops[i] = 0;
      drops[i] += 0.5;
    }
  }

  window.addEventListener('resize', resize);
  resize();
  setInterval(draw, 50);
}

// Initialize
setLanguage('he');