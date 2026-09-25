/**
 * SENTINEL Brand System Helper
 * Standardizes official SENTINEL branding across all views and viewports.
 * Variants:
 *  - FULL: [S mark] SENTINEL
 *  - COMPACT: [S mark]
 *  - WORDMARK: SENTINEL
 */

(function () {
  'use strict';

  const SentinelBrand = {
    assets: {
      markDark: 'assets/sentinel-mark.png',
      markLight: 'assets/sentinel-mark-light.png',
      logoDark: 'assets/sentinel-logo.png',
      logoLight: 'assets/sentinel-logo-light.png',
      horizDark: 'assets/sentinel-logo-horizontal.png',
      horizLight: 'assets/sentinel-logo-horizontal-light.png',
      favicon: 'assets/favicon.ico'
    },

    getCurrentTheme() {
      return document.documentElement.getAttribute('data-theme') || localStorage.getItem('sentinel_theme') || 'dark';
    },

    /**
     * Update all brand images on the page according to active theme
     */
    updateTheme(theme) {
      const isLight = theme === 'light';

      // Update dynamic mark images
      document.querySelectorAll('[data-brand-variant="mark"], .sentinel-dynamic-mark').forEach(img => {
        img.src = isLight ? this.assets.markLight : this.assets.markDark;
      });

      // Update dynamic full stacked logo images
      document.querySelectorAll('[data-brand-variant="logo"], .sentinel-dynamic-logo').forEach(img => {
        img.src = isLight ? this.assets.logoLight : this.assets.logoDark;
      });

      // Update dynamic horizontal logo images
      document.querySelectorAll('[data-brand-variant="horizontal"], .sentinel-dynamic-horizontal').forEach(img => {
        img.src = isLight ? this.assets.horizLight : this.assets.horizDark;
      });

      // As an extra safeguard for any dual-image tags, enforce inline display styles
      document.querySelectorAll('.sentinel-logo-dark').forEach(el => {
        el.style.display = isLight ? 'none' : 'block';
      });
      document.querySelectorAll('.sentinel-logo-light').forEach(el => {
        el.style.display = isLight ? 'block' : 'none';
      });
    },

    /**
     * Generate HTML for Compact S Mark
     */
    getCompactMark(options = {}) {
      const size = options.size || 32;
      const extraClass = options.className || '';
      const isLight = this.getCurrentTheme() === 'light';
      const src = isLight ? this.assets.markLight : this.assets.markDark;
      return `
        <div class="sentinel-brand-mark ${extraClass}" style="width:${size}px; height:${size}px;" aria-label="SENTINEL">
          <img src="${src}" alt="SENTINEL" class="sentinel-mark-img sentinel-dynamic-mark" data-brand-variant="mark" style="width:100%; height:100%; object-fit:contain;" />
        </div>
      `;
    },

    /**
     * Generate HTML for Full Logo ([S mark] SENTINEL)
     */
    getFullLogo(options = {}) {
      const height = options.height || 36;
      const extraClass = options.className || '';
      const href = options.href !== undefined ? options.href : 'index.html';
      const tag = href ? 'a' : 'div';
      const hrefAttr = href ? `href="${href}"` : '';
      const isLight = this.getCurrentTheme() === 'light';
      const src = isLight ? this.assets.horizLight : this.assets.horizDark;

      return `
        <${tag} ${hrefAttr} class="sentinel-brand-logo full ${extraClass}" aria-label="SENTINEL AI-Powered Document Forensics">
          <img src="${src}" alt="SENTINEL" class="sentinel-logo-img sentinel-dynamic-horizontal" data-brand-variant="horizontal" style="height:${height}px; width:auto; object-fit:contain;" />
        </${tag}>
      `;
    },

    /**
     * Generate HTML for Wordmark only
     */
    getWordmark(options = {}) {
      const extraClass = options.className || '';
      return `<span class="sentinel-brand-wordmark ${extraClass}">SENTINEL</span>`;
    },

    /**
     * Generate HTML for Minimal Loading State
     */
    createLoader(statusText = 'INITIALIZING FORENSIC ENGINE...') {
      const isLight = this.getCurrentTheme() === 'light';
      const src = isLight ? this.assets.markLight : this.assets.markDark;
      return `
        <div class="sentinel-loader" role="status" aria-live="polite">
          <div class="sentinel-loader-mark">
            <img src="${src}" alt="SENTINEL" data-brand-variant="mark" class="sentinel-dynamic-mark" style="width:100%; height:100%; object-fit:contain;" />
          </div>
          <div class="sentinel-loader-word">SENTINEL</div>
          <div class="sentinel-loader-sub">${statusText}</div>
        </div>
      `;
    },

    /**
     * Ensure favicon tags are present in <head>
     */
    ensureFavicon() {
      if (!document.querySelector('link[rel*="icon"]')) {
        const head = document.head;
        const icon1 = document.createElement('link');
        icon1.rel = 'icon';
        icon1.type = 'image/png';
        icon1.sizes = '32x32';
        icon1.href = this.assets.markDark;

        const icon2 = document.createElement('link');
        icon2.rel = 'shortcut icon';
        icon2.href = this.assets.favicon;

        head.appendChild(icon1);
        head.appendChild(icon2);
      }
    },

    /**
     * Mount into DOM placeholders
     */
    mountAll() {
      this.ensureFavicon();
      const currentTheme = this.getCurrentTheme();

      // Standardize Sidebar Brand
      document.querySelectorAll('.sidebar-brand').forEach(el => {
        if (!el.querySelector('.sentinel-dynamic-mark')) {
          const isLight = currentTheme === 'light';
          const src = isLight ? this.assets.markLight : this.assets.markDark;
          el.innerHTML = `
            <div class="sentinel-brand-mark" style="width:28px; height:28px; flex-shrink:0;">
              <img src="${src}" alt="SENTINEL" class="sentinel-mark-img sentinel-dynamic-mark" data-brand-variant="mark" style="width:100%; height:100%; object-fit:contain;" />
            </div>
            <span class="brand-text">SENTINEL</span>
          `;
        }
      });

      // Mount any explicit data-sentinel-brand containers
      document.querySelectorAll('[data-sentinel-brand]').forEach(el => {
        const variant = el.getAttribute('data-sentinel-brand');
        const height = parseInt(el.getAttribute('data-brand-height') || '36', 10);
        if (variant === 'full') {
          el.innerHTML = this.getFullLogo({ height });
        } else if (variant === 'compact') {
          el.innerHTML = this.getCompactMark({ size: height });
        } else if (variant === 'wordmark') {
          el.innerHTML = this.getWordmark();
        }
      });

      this.updateTheme(currentTheme);
    },

    init() {
      this.mountAll();

      // Listen for global theme changes
      window.addEventListener('sentinel-theme-change', (e) => {
        this.updateTheme(e.detail.theme);
      });
    }
  };

  window.SentinelBrand = SentinelBrand;

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', () => SentinelBrand.init());
  } else {
    SentinelBrand.init();
  }
})();
