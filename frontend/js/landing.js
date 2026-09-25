/**
 * SENTINEL Landing Page Interactive Controller
 * Handles Navigation, Risk Simulator, AI Copilot Mockup, Nodemailer Contact System,
 * and IntersectionObserver Animations.
 */

(function () {
  'use strict';

  // 1. Navigation & Authentication State
  function setupNavigation() {
    const nav = document.querySelector('.landing-nav');
    const authBtn = document.getElementById('navAuthBtn');
    const heroStartBtn = document.getElementById('heroStartBtn');
    const mobileToggle = document.getElementById('mobileMenuToggle');
    const navLinks = document.getElementById('navLinks');

    // Sticky navbar on scroll
    window.addEventListener('scroll', () => {
      if (window.scrollY > 30) {
        nav?.classList.add('scrolled');
      } else {
        nav?.classList.remove('scrolled');
      }
    }, { passive: true });

    // Check auth status
    const token = localStorage.getItem('token');
    if (token) {
      if (authBtn) {
        authBtn.innerHTML = '<i class="fa-solid fa-gauge-high"></i> Dashboard';
        authBtn.href = 'dashboard.html';
      }
      if (heroStartBtn) {
        heroStartBtn.href = 'analyze.html';
      }
    } else {
      if (authBtn) {
        authBtn.innerHTML = '<i class="fa-solid fa-right-to-bracket"></i> Login';
        authBtn.href = 'login.html';
      }
      if (heroStartBtn) {
        heroStartBtn.href = 'login.html';
      }
    }

    // Mobile Hamburger
    if (mobileToggle && navLinks) {
      mobileToggle.addEventListener('click', () => {
        navLinks.classList.toggle('mobile-open');
        const icon = mobileToggle.querySelector('i');
        if (icon) {
          icon.className = navLinks.classList.contains('mobile-open') ? 'fa-solid fa-xmark' : 'fa-solid fa-bars';
        }
      });

      // Close mobile menu on link click
      navLinks.querySelectorAll('a').forEach(link => {
        link.addEventListener('click', () => {
          navLinks.classList.remove('mobile-open');
          const icon = mobileToggle.querySelector('i');
          if (icon) icon.className = 'fa-solid fa-bars';
        });
      });
    }
  }

  // 2. Interactive Risk Simulator
  const riskCaseData = {
    'case-1': {
      score: 84,
      status: 'HIGH SUSPICION',
      color: 'var(--danger)',
      glow: 'rgba(255, 77, 77, 0.4)',
      breakdown: [
        { title: 'Typography: Font Baseline Jitter', impact: '+25 Risk', type: 'danger' },
        { title: 'QR Payload vs OCR Name Mismatch', impact: '+30 Risk', type: 'danger' },
        { title: 'ELA: Photo Frame Compression Variance', impact: '+20 Risk', type: 'warning' },
        { title: 'Layout: Header Indentation Offset', impact: '+9 Risk', type: 'warning' }
      ]
    },
    'case-2': {
      score: 18,
      status: 'LOW RISK',
      color: 'var(--green)',
      glow: 'rgba(85, 224, 126, 0.4)',
      breakdown: [
        { title: 'Image Resolution & Sharpness', impact: 'Consistent (Pass)', type: 'normal' },
        { title: 'OCR & QR Payload Integrity', impact: 'Verified Match', type: 'normal' },
        { title: 'Typography Uniformity', impact: 'Standard Weights', type: 'normal' },
        { title: 'ELA Compression Surface', impact: 'Uniform Noise', type: 'normal' }
      ]
    },
    'case-3': {
      score: 68,
      status: 'SUSPICIOUS',
      color: 'var(--orange)',
      glow: 'rgba(255, 157, 80, 0.4)',
      breakdown: [
        { title: 'ELA: Spliced Photo Clone Anomaly', impact: '+35 Risk', type: 'danger' },
        { title: 'Heavy Laplacian Blur (Score 42.1)', impact: '+20 Risk', type: 'warning' },
        { title: 'Layout Alignment Drift', impact: '+13 Risk', type: 'warning' }
      ]
    }
  };

  function setupRiskSimulator() {
    const chipBtns = document.querySelectorAll('.case-chip-btn');
    const scoreEl = document.getElementById('riskDialScore');
    const statusEl = document.getElementById('riskDialStatus');
    const listEl = document.getElementById('riskBreakdownList');

    if (!scoreEl || !statusEl || !listEl) return;

    chipBtns.forEach(btn => {
      btn.addEventListener('click', () => {
        chipBtns.forEach(b => b.classList.remove('active'));
        btn.classList.add('active');

        const caseId = btn.getAttribute('data-case');
        const data = riskCaseData[caseId];
        if (!data) return;

        scoreEl.innerText = data.score;
        scoreEl.style.color = data.color;
        scoreEl.style.textShadow = `0 0 25px ${data.glow}`;

        statusEl.innerText = data.status;
        statusEl.style.color = data.color;

        listEl.innerHTML = data.breakdown.map(item => `
          <div class="risk-breakdown-row ${item.type}">
            <span class="risk-row-title">${item.title}</span>
            <span class="risk-row-impact" style="color: ${item.type === 'danger' ? 'var(--danger)' : item.type === 'warning' ? 'var(--orange)' : 'var(--green)'};">${item.impact}</span>
          </div>
        `).join('');
      });
    });
  }

  // 3. Interactive AI Copilot Mockup
  function setupCopilotMockup() {
    const chatBody = document.getElementById('copilotChatBody');
    const chips = document.querySelectorAll('.quick-action-chip');
    if (!chatBody) return;

    const mockResponses = {
      'explain': {
        user: 'Explain the contributing risk score of 84/100.',
        ai: 'The composite score of 84/100 is driven by two high-severity anomalies: 1) The QR code payload text does not correspond to the extracted OCR name field (+30 risk). 2) Font baseline jitter (+25 risk) suggests digital string substitution over a scanned background.'
      },
      'compare': {
        user: 'Compare this document with similar historical cases.',
        ai: 'Correlating with repository cluster #SYNTH-CLUSTER-09: Identical font misalignment and photo frame edge artifacts were detected in Case #2026-088. This strongly indicates a shared automated synthetic generator template.'
      },
      'extract': {
        user: 'Extract all demographic and forensic markers.',
        ai: 'Extracted Demographics:\n- Name: AARAV DEMO (OCR Conf: 96%)\n- DOB: 01/01/2000 (OCR Conf: 98%)\n- Specimen ID: SENTINEL-DEMO-001\n- QR Content: SENTINEL-DEMO-QR\n- Face Aspect Ratio: 1.25 [Standard]'
      },
      'summary': {
        user: 'Generate an executive investigative summary.',
        ai: 'EXECUTIVE SUMMARY: Specimen SENTINEL-DEMO-001 exhibits clear visual hallmarks of an Aadhaar look-alike. Digital forensic inspection confirms typography and cryptographic payload inconsistencies. Recommended Action: Escalate for secondary manual inspection; do not accept as primary credential.'
      }
    };

    chips.forEach(chip => {
      chip.addEventListener('click', () => {
        const action = chip.getAttribute('data-action');
        const convo = mockResponses[action];
        if (!convo) return;

        // Append user bubble
        const userDiv = document.createElement('div');
        userDiv.className = 'chat-bubble chat-bubble-user';
        userDiv.innerHTML = `<strong>Investigator:</strong> ${convo.user}`;
        chatBody.appendChild(userDiv);

        // Append AI bubble with slight typing delay
        setTimeout(() => {
          const aiDiv = document.createElement('div');
          aiDiv.className = 'chat-bubble chat-bubble-ai';
          aiDiv.innerHTML = `<strong>SENTINEL Copilot:</strong> ${convo.ai.replace(/\n/g, '<br>')}`;
          chatBody.appendChild(aiDiv);
          chatBody.scrollTop = chatBody.scrollHeight;
        }, 350);

        chatBody.scrollTop = chatBody.scrollHeight;
      });
    });
  }

  // 4. Nodemailer Contact & Demo Request System
  function setupContactForm() {
    const form = document.getElementById('contactForm');
    const submitBtn = document.getElementById('contactSubmitBtn');
    if (!form || !submitBtn) return;

    form.addEventListener('submit', async (e) => {
      e.preventDefault();

      const name = document.getElementById('contactName')?.value.trim();
      const email = document.getElementById('contactEmail')?.value.trim();
      const organization = document.getElementById('contactOrg')?.value.trim();
      const subject = document.getElementById('contactSubject')?.value.trim();
      const phone = document.getElementById('contactPhone')?.value.trim();
      const message = document.getElementById('contactMessage')?.value.trim();

      // Client-side validations
      if (!name || name.length < 2) {
        showToast('warning', 'Validation Warning', 'Please enter your full name.');
        return;
      }

      const emailRegex = /^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$/;
      if (!email || !emailRegex.test(email)) {
        showToast('warning', 'Validation Warning', 'Please enter a valid email address.');
        return;
      }

      if (!organization || organization.length < 2) {
        showToast('warning', 'Validation Warning', 'Please enter your organization or agency.');
        return;
      }

      if (!subject || subject.length < 2) {
        showToast('warning', 'Validation Warning', 'Please provide a subject for your request.');
        return;
      }

      if (!message || message.length < 10) {
        showToast('warning', 'Validation Warning', 'Please provide a detailed message (minimum 10 characters).');
        return;
      }

      // Set Loading State
      const originalBtnHtml = submitBtn.innerHTML;
      submitBtn.disabled = true;
      submitBtn.innerHTML = '<i class="fa-solid fa-circle-notch fa-spin"></i> Transmitting Request...';

      const payload = { name, email, organization, subject, phone, message };

      // Helper function to send request with dual-endpoint fallback (port 5001 Node mail service or port 8000 FastAPI bridge)
      async function dispatchContactRequest() {
        // Try direct Node mail service first
        try {
          const res1 = await fetch('http://localhost:5001/api/contact', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload)
          });
          if (res1.ok) return await res1.json();
          if (res1.status === 429) {
            const data = await res1.json();
            throw new Error(data.error || 'Rate limit exceeded. Please wait a few minutes.');
          }
        } catch (err1) {
          // If 429 rate-limit, do not retry
          if (err1.message.includes('Rate limit')) throw err1;
          console.warn('[Contact] Node mail service on 5001 unreachable, attempting FastAPI bridge on 8000...', err1);
        }

        // Fallback to FastAPI endpoint
        const res2 = await fetch('http://localhost:8000/api/contact', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(payload)
        });

        if (!res2.ok) {
          const errorData = await res2.json().catch(() => ({}));
          throw new Error(errorData.detail || errorData.error || 'Unable to send message. Please try again.');
        }

        return await res2.json();
      }

      try {
        const result = await dispatchContactRequest();
        showToast('success', 'Message Sent Successfully', result.message || 'Your inquiry has been received by the SENTINEL team.');
        form.reset();
      } catch (err) {
        console.error('[Contact Error]', err);
        showToast('error', 'Transmission Failed', err.message || 'Unable to send message. Please try again.');
      } finally {
        submitBtn.disabled = false;
        submitBtn.innerHTML = originalBtnHtml;
      }
    });
  }

  // Toast Helper utilizing existing window.Toast
  function showToast(type, title, message) {
    if (window.Toast && typeof window.Toast[type] === 'function') {
      window.Toast[type](title, message);
    } else {
      // Fallback
      alert(`${title}: ${message}`);
    }
  }

  // 5. Scroll Reveal with IntersectionObserver
  function setupScrollReveals() {
    const observer = new IntersectionObserver((entries) => {
      entries.forEach(entry => {
        if (entry.isIntersecting) {
          entry.target.classList.add('revealed');
          observer.unobserve(entry.target);
        }
      });
    }, { threshold: 0.15 });

    document.querySelectorAll('.landing-section, .workflow-card, .pillar-card-detailed, .problem-card-compare').forEach(el => {
      observer.observe(el);
    });
  }

  // DOM Loaded
  document.addEventListener('DOMContentLoaded', () => {
    setupNavigation();
    setupRiskSimulator();
    setupCopilotMockup();
    setupContactForm();
    setupScrollReveals();
  });

})();
