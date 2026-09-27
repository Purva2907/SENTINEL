/**
 * SENTINEL Centralized Sidebar Navigation System
 * 
 * Provides a single centralized navigation configuration for the sidebar.
 * Ensures identical labels, icons, and routes across all pages.
 * Controls visual active states dynamically based on the current route/pathname
 * without altering navigation labels.
 */

(function () {
  'use strict';

  const SYNTHETIC_LAB_ROUTE = 'lab.html';
  const COMPARE_ROUTE = 'compare.html';

  const NAV_ITEMS = [
    {
      label: 'Dashboard',
      icon: 'fa-solid fa-chart-line',
      href: 'dashboard.html',
      aliases: ['dashboard.html', 'dashboard', 'index.html']
    },
    {
      label: 'New Analysis',
      icon: 'fa-solid fa-microscope',
      href: 'analyze.html',
      aliases: ['analyze.html', 'analyze', 'results.html', 'results']
    },
    {
      label: 'Cases',
      icon: 'fa-solid fa-folder-open',
      href: 'cases.html',
      aliases: ['cases.html', 'cases', 'case-detail.html', 'case-detail']
    },
    {
      label: 'Synthetic Lab',
      icon: 'fa-solid fa-flask-vial',
      href: SYNTHETIC_LAB_ROUTE,
      aliases: [SYNTHETIC_LAB_ROUTE, 'lab']
    },
    {
      label: 'Compare',
      icon: 'fa-solid fa-code-compare',
      href: COMPARE_ROUTE,
      aliases: [COMPARE_ROUTE, 'compare']
    },
    {
      label: 'Reports',
      icon: 'fa-solid fa-file-pdf',
      href: 'reports.html',
      aliases: ['reports.html', 'reports']
    },
    {
      label: 'Analytics',
      icon: 'fa-solid fa-chart-pie',
      href: 'analytics.html',
      aliases: ['analytics.html', 'analytics']
    },
    {
      label: 'Profile',
      icon: 'fa-solid fa-user-shield',
      href: 'profile.html',
      aliases: ['profile.html', 'profile']
    },
    {
      label: 'Settings',
      icon: 'fa-solid fa-gear',
      href: 'settings.html',
      aliases: ['settings.html', 'settings']
    }
  ];

  const SentinelNav = {
    NAV_ITEMS,
    SYNTHETIC_LAB_ROUTE,
    COMPARE_ROUTE,

    /**
     * Determine normalized current page/route filename from window.location.pathname
     */
    getCurrentRoute() {
      const pathname = window.location.pathname || '';
      const cleanPath = pathname.split('?')[0].split('#')[0];
      const segments = cleanPath.split('/').filter(Boolean);
      const filename = segments.length > 0 ? segments[segments.length - 1].toLowerCase() : '';
      return filename;
    },

    /**
     * Check if a given nav item matches the current page route
     */
    isItemActive(item, currentRoute) {
      if (!currentRoute) {
        return item.href.toLowerCase() === 'dashboard.html';
      }
      if (item.href.toLowerCase() === currentRoute) return true;
      if (item.aliases && item.aliases.map(a => a.toLowerCase()).includes(currentRoute)) return true;
      return false;
    },

    /**
     * Synchronize and standardize sidebar navigation elements.
     * Enforces exact centralized labels and icons.
     * Ensures active state is strictly visual (CSS class .active) and NEVER changes label text.
     */
    syncSidebar(sidebarEl) {
      if (!sidebarEl) return;

      const currentRoute = this.getCurrentRoute();
      const navLinks = sidebarEl.querySelectorAll('a.nav-item');

      navLinks.forEach(link => {
        const rawHref = (link.getAttribute('href') || '').trim();
        if (rawHref === '#' || rawHref.startsWith('javascript:')) return;

        const baseHref = rawHref.split('/').pop().split('?')[0].split('#')[0].toLowerCase();

        // Match against centralized navigation configuration
        const config = NAV_ITEMS.find(item => {
          return item.href.toLowerCase() === baseHref ||
            (item.aliases && item.aliases.map(a => a.toLowerCase()).includes(baseHref));
        });

        if (config) {
          // Guarantee consistent icon and exact label (e.g. Compare is ALWAYS "Compare", never "Document Compare")
          link.innerHTML = `<i class="${config.icon}"></i> ${config.label}`;

          // Visual active state only: toggle class 'active'
          const active = this.isItemActive(config, currentRoute);
          if (active) {
            link.classList.add('active');
          } else {
            link.classList.remove('active');
          }
        }
      });
    },

    init() {
      const sidebars = document.querySelectorAll('.sidebar');
      sidebars.forEach(sb => this.syncSidebar(sb));
    }
  };

  window.SentinelNav = SentinelNav;

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', () => SentinelNav.init());
  } else {
    SentinelNav.init();
  }
})();
