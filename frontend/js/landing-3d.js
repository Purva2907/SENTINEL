/**
 * SENTINEL 3D Forensic Synthetic Identity Document Experience
 * Built with Three.js r128
 * Fully interactive, responsive, and performance-optimized.
 */

(function () {
  'use strict';

  let scene, camera, renderer;
  let cardGroup, scanLine, laserGlowMesh;
  let platformGroup, particlesMesh, connectorLinesGroup;
  let container, hero3dContainer;
  let animationFrameId = null;
  let isTabActive = true;
  let prefersReducedMotion = false;
  let resizeObserver = null;
  let debugHud = null;
  let clock = null;

  // Autonomous cinematic rotation parameters (Requirements 1, 2, 3, 10)
  const ROTATION_SPEED_Y = 0.12; // radians/second (smooth, continuous, forensic)
  const NEUTRAL_ROTATION_Y = -0.28;
  const NEUTRAL_ROTATION_X = 0.10;

  let currentRotationY = NEUTRAL_ROTATION_Y;
  let currentRotationX = NEUTRAL_ROTATION_X;
  let scrollOffset = 0;

  // Check WebGL availability
  function isWebGLAvailable() {
    try {
      const canvas = document.createElement('canvas');
      return !!(window.WebGLRenderingContext && (canvas.getContext('webgl') || canvas.getContext('experimental-webgl')));
    } catch (e) {
      return false;
    }
  }

  // Draw High-Resolution Synthetic Identity Document Canvas Texture (Front)
  function createFrontCardTexture() {
    const canvas = document.createElement('canvas');
    canvas.width = 1024;
    canvas.height = 650;
    const ctx = canvas.getContext('2d');

    // Background gradient - Clean cyber laboratory card
    const grad = ctx.createLinearGradient(0, 0, 1024, 650);
    grad.addColorStop(0, '#f9fafb');
    grad.addColorStop(0.5, '#eef2f6');
    grad.addColorStop(1, '#e2e8f0');
    ctx.fillStyle = grad;
    ctx.fillRect(0, 0, 1024, 650);

    // Subtle guilloche / security micro-lines pattern
    ctx.strokeStyle = 'rgba(29, 206, 216, 0.12)';
    ctx.lineWidth = 1;
    for (let i = 0; i < 1024; i += 24) {
      ctx.beginPath();
      ctx.moveTo(i, 0);
      ctx.bezierCurveTo(i + 150, 200, i - 150, 450, i, 650);
      ctx.stroke();
    }

    // Top Header Banner
    ctx.fillStyle = '#dc2626';
    ctx.font = 'bold 22px "Inter", sans-serif';
    ctx.textAlign = 'center';
    ctx.fillText('SYNTHETIC DEMO DOCUMENT', 512, 42);

    ctx.fillStyle = '#475569';
    ctx.font = '600 14px "Inter", sans-serif';
    ctx.fillText('(For Research & Forensic Demonstration Only — NOT A GOVERNMENT DOCUMENT)', 512, 66);

    // Left Emblem / Demo Crest
    ctx.save();
    ctx.translate(90, 115);
    ctx.fillStyle = '#0f172a';
    ctx.beginPath();
    ctx.arc(0, 0, 32, 0, Math.PI * 2);
    ctx.fill();
    ctx.strokeStyle = '#1DCED8';
    ctx.lineWidth = 2;
    ctx.stroke();

    ctx.fillStyle = '#ffffff';
    ctx.font = 'bold 11px "Inter", sans-serif';
    ctx.textAlign = 'center';
    ctx.fillText('DEMO', 0, -4);
    ctx.fillText('ONLY', 0, 12);
    ctx.restore();

    // Right Header Logo: Official SENTINEL Brand
    ctx.save();
    ctx.translate(910, 95);
    ctx.fillStyle = '#0a1128';
    ctx.beginPath();
    ctx.moveTo(0, -22);
    ctx.lineTo(18, -11);
    ctx.lineTo(18, 11);
    ctx.lineTo(0, 22);
    ctx.lineTo(-18, 11);
    ctx.lineTo(-18, -11);
    ctx.closePath();
    ctx.fill();
    ctx.strokeStyle = '#1DCED8';
    ctx.lineWidth = 1.5;
    ctx.stroke();

    // Geometric S ribbon
    ctx.fillStyle = '#1DCED8';
    ctx.beginPath();
    ctx.moveTo(0, -16);
    ctx.lineTo(12, -9);
    ctx.lineTo(12, -2);
    ctx.lineTo(-3, -2);
    ctx.lineTo(-3, 3);
    ctx.lineTo(12, 9);
    ctx.lineTo(0, 16);
    ctx.lineTo(-12, 9);
    ctx.lineTo(-12, 2);
    ctx.lineTo(3, 2);
    ctx.lineTo(3, -3);
    ctx.lineTo(-12, -9);
    ctx.closePath();
    ctx.fill();

    ctx.fillStyle = '#0f172a';
    ctx.font = '800 14px "Outfit", sans-serif';
    ctx.textAlign = 'center';
    ctx.fillText('SENTINEL', 0, 40);
    ctx.restore();


    // Photo Box (Left Side)
    const photoX = 60, photoY = 175, photoW = 200, photoH = 250;
    ctx.fillStyle = '#cbd5e1';
    ctx.fillRect(photoX, photoY, photoW, photoH);
    ctx.strokeStyle = '#94a3b8';
    ctx.lineWidth = 2;
    ctx.strokeRect(photoX, photoY, photoW, photoH);

    // Stylized Silhouette Avatar
    ctx.fillStyle = '#475569';
    ctx.beginPath();
    ctx.arc(photoX + photoW / 2, photoY + 90, 48, 0, Math.PI * 2); // Head
    ctx.fill();
    ctx.beginPath();
    ctx.ellipse(photoX + photoW / 2, photoY + 220, 80, 70, 0, 0, Math.PI, true); // Shoulders
    ctx.fill();

    // Forensic Photo Watermark / Scan Grid Overlay
    ctx.strokeStyle = 'rgba(29, 206, 216, 0.4)';
    ctx.lineWidth = 1;
    ctx.strokeRect(photoX + 10, photoY + 10, photoW - 20, photoH - 20);
    ctx.fillStyle = 'rgba(29, 206, 216, 0.8)';
    ctx.font = 'bold 11px monospace';
    ctx.textAlign = 'left';
    ctx.fillText('FACE ID: VERIFIED', photoX + 14, photoY + 28);
    ctx.fillText('SYNTHETIC SPECIMEN', photoX + 14, photoY + photoH - 14);

    // Demographic Info Fields (Middle)
    ctx.textAlign = 'left';
    let fieldY = 200;

    // Field 1: Name
    ctx.fillStyle = '#64748b';
    ctx.font = '500 16px "Inter", sans-serif';
    ctx.fillText('नाम / Name', 290, fieldY);
    ctx.fillStyle = '#0f172a';
    ctx.font = 'bold 22px "Inter", sans-serif';
    ctx.fillText('AARAV DEMO', 290, fieldY + 26);

    // Field 2: DOB
    fieldY += 70;
    ctx.fillStyle = '#64748b';
    ctx.font = '500 16px "Inter", sans-serif';
    ctx.fillText('जन्म तिथि / DOB', 290, fieldY);
    ctx.fillStyle = '#0f172a';
    ctx.font = 'bold 20px "Inter", sans-serif';
    ctx.fillText('01/01/2000', 290, fieldY + 26);

    // Field 3: Gender
    fieldY += 70;
    ctx.fillStyle = '#64748b';
    ctx.font = '500 16px "Inter", sans-serif';
    ctx.fillText('लिंग / Gender', 290, fieldY);
    ctx.fillStyle = '#0f172a';
    ctx.font = 'bold 20px "Inter", sans-serif';
    ctx.fillText('पुरुष / MALE', 290, fieldY + 26);

    // QR Code Area (Right Side)
    const qrX = 740, qrY = 175, qrSize = 220;
    ctx.fillStyle = '#ffffff';
    ctx.fillRect(qrX, qrY, qrSize, qrSize);
    ctx.strokeStyle = '#0f172a';
    ctx.lineWidth = 2;
    ctx.strokeRect(qrX, qrY, qrSize, qrSize);

    // Stylized Simulated QR Matrix
    ctx.fillStyle = '#0f172a';
    const cellSize = 11;
    // Corner finders
    function drawFinder(fx, fy) {
      ctx.fillRect(fx, fy, 7 * cellSize, 7 * cellSize);
      ctx.fillStyle = '#ffffff';
      ctx.fillRect(fx + cellSize, fy + cellSize, 5 * cellSize, 5 * cellSize);
      ctx.fillStyle = '#0f172a';
      ctx.fillRect(fx + 2 * cellSize, fy + 2 * cellSize, 3 * cellSize, 3 * cellSize);
    }
    drawFinder(qrX + 10, qrY + 10);
    drawFinder(qrX + qrSize - 10 - 7 * cellSize, qrY + 10);
    drawFinder(qrX + 10, qrY + qrSize - 10 - 7 * cellSize);

    // Pseudo data dots
    ctx.fillStyle = '#0f172a';
    for (let r = 0; r < 18; r++) {
      for (let c = 0; c < 18; c++) {
        // Skip corner finder zones
        if ((r < 7 && c < 7) || (r < 7 && c > 10) || (r > 10 && c < 7)) continue;
        if ((r * 7 + c * 13) % 3 === 0) {
          ctx.fillRect(qrX + 15 + c * cellSize, qrY + 15 + r * cellSize, cellSize - 2, cellSize - 2);
        }
      }
    }

    // QR Label
    ctx.fillStyle = '#475569';
    ctx.font = 'bold 12px monospace';
    ctx.textAlign = 'center';
    ctx.fillText('QR: SENTINEL-DEMO-QR', qrX + qrSize / 2, qrY + qrSize + 22);

    // Document ID Banner
    ctx.fillStyle = '#0f172a';
    ctx.font = 'bold 30px "Outfit", monospace';
    ctx.textAlign = 'center';
    ctx.fillText('SENTINEL-DEMO-001', 490, 485);

    // Diagonal SYNTHETIC DEMO Watermark Stamp across lower right
    ctx.save();
    ctx.translate(760, 490);
    ctx.rotate(-0.16);
    ctx.strokeStyle = 'rgba(239, 68, 68, 0.85)';
    ctx.lineWidth = 3;
    ctx.strokeRect(-130, -22, 260, 44);
    ctx.fillStyle = 'rgba(239, 68, 68, 0.85)';
    ctx.font = 'bold 22px "Outfit", sans-serif';
    ctx.textAlign = 'center';
    ctx.fillText('SYNTHETIC DEMO', 0, 8);
    ctx.restore();

    // Tricolor Micro-Security Strip at Bottom
    const stripY = 560;
    // Saffron strip
    ctx.fillStyle = '#FF9933';
    ctx.fillRect(50, stripY, 924, 7);
    // White strip with micro-text
    ctx.fillStyle = '#ffffff';
    ctx.fillRect(50, stripY + 7, 924, 18);
    ctx.fillStyle = '#138808';
    ctx.fillRect(50, stripY + 25, 924, 7);

    // Microtext in middle strip
    ctx.fillStyle = '#0f172a';
    ctx.font = 'bold 12px monospace';
    ctx.textAlign = 'center';
    ctx.fillText('SENTINEL  •  AI-POWERED FORENSICS  •  TRUST THE EVIDENCE  •  DEMO SPECIMEN', 512, stripY + 20);

    // Card border
    ctx.strokeStyle = '#1DCED8';
    ctx.lineWidth = 4;
    ctx.strokeRect(6, 6, 1012, 638);

    const texture = new THREE.CanvasTexture(canvas);
    texture.minFilter = THREE.LinearFilter;
    texture.magFilter = THREE.LinearFilter;
    return texture;
  }

  // Draw Card Back Texture
  function createBackCardTexture() {
    const canvas = document.createElement('canvas');
    canvas.width = 1024;
    canvas.height = 650;
    const ctx = canvas.getContext('2d');

    // Dark sleek reverse side
    const grad = ctx.createLinearGradient(0, 0, 1024, 650);
    grad.addColorStop(0, '#0a1020');
    grad.addColorStop(1, '#050813');
    ctx.fillStyle = grad;
    ctx.fillRect(0, 0, 1024, 650);

    // Grid lines
    ctx.strokeStyle = 'rgba(29, 206, 216, 0.08)';
    ctx.lineWidth = 1;
    for (let x = 0; x < 1024; x += 40) {
      ctx.beginPath();
      ctx.moveTo(x, 0);
      ctx.lineTo(x, 650);
      ctx.stroke();
    }

    // Top Header
    ctx.fillStyle = '#1DCED8';
    ctx.font = 'bold 20px "Outfit", sans-serif';
    ctx.textAlign = 'left';
    ctx.fillText('SENTINEL FORENSIC AUDIT TRAIL', 60, 60);

    ctx.fillStyle = '#64748b';
    ctx.font = '14px monospace';
    ctx.fillText('SPECIMEN ID: SYN-DEMO-2026-001 | CLASSIFICATION: SYNTHETIC EVALUATION', 60, 88);

    // Fictional address block
    ctx.fillStyle = '#94a3b8';
    ctx.font = '14px "Inter", sans-serif';
    ctx.fillText('पता / Address:', 60, 140);
    ctx.fillStyle = '#f8fafc';
    ctx.font = '500 16px "Inter", sans-serif';
    ctx.fillText('SENTINEL RESEARCH LAB, SECTOR 04, CYBER DEFENSE ENCLAVE,', 60, 170);
    ctx.fillText('NEW DELHI - 110001, INDIA (DEMO PURPOSE ONLY)', 60, 196);

    // Cryptographic Hash & Chain of Custody Box
    ctx.fillStyle = 'rgba(29, 206, 216, 0.05)';
    ctx.fillRect(60, 240, 904, 160);
    ctx.strokeStyle = 'rgba(29, 206, 216, 0.3)';
    ctx.strokeRect(60, 240, 904, 160);

    ctx.fillStyle = '#FF9D50';
    ctx.font = 'bold 13px monospace';
    ctx.fillText('CRYPTOGRAPHIC CHAIN OF CUSTODY ANCHOR', 80, 270);

    ctx.fillStyle = '#94a3b8';
    ctx.font = '12px monospace';
    ctx.fillText('SHA-256 HASH: e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855', 80, 305);
    ctx.fillText('TIMESTAMP: 2026-09-25T18:00:00Z | PIPELINE VERSION: 2.1.0-STABLE', 80, 335);
    ctx.fillText('VERIFICATION STATUS: REPEATABLE SYNTHETIC SAMPLE [NOT A LEGAL ID]', 80, 365);

    // Barcode at bottom
    ctx.fillStyle = '#ffffff';
    ctx.fillRect(60, 440, 904, 80);
    ctx.fillStyle = '#0f172a';
    for (let bx = 90; bx < 930; bx += 8) {
      const barW = (bx % 16 === 0) ? 5 : (bx % 24 === 0) ? 6 : 2;
      ctx.fillRect(bx, 450, barW, 60);
    }

    // Disclaimer
    ctx.fillStyle = '#e2e8f0';
    ctx.font = '12px "Inter", sans-serif';
    ctx.textAlign = 'center';
    ctx.fillText('THIS IS A FICTIONAL DEMO SPECIMEN. DO NOT USE FOR AUTHENTIC IDENTIFICATION.', 512, 590);

    ctx.strokeStyle = '#FF9D50';
    ctx.lineWidth = 3;
    ctx.strokeRect(6, 6, 1012, 638);

    const texture = new THREE.CanvasTexture(canvas);
    texture.minFilter = THREE.LinearFilter;
    texture.magFilter = THREE.LinearFilter;
    return texture;
  }

  // Setup WebGL Fallback if needed
  function setupFallback() {
    container = document.getElementById('canvas-container');
    if (!container) return;
    container.innerHTML = `
      <div class="webgl-fallback" style="text-align: center; padding: 40px;">
        <div style="width: 340px; max-width: 90%; background: rgba(12, 19, 36, 0.95); border: 2px solid #1DCED8; border-radius: 12px; padding: 24px; box-shadow: 0 0 30px rgba(29, 206, 216, 0.3); margin: 0 auto;">
          <div style="background: rgba(239, 68, 68, 0.2); color: #ff8080; border: 1px dashed rgba(239, 68, 68, 0.4); padding: 4px; font-family: monospace; font-size: 0.72rem; border-radius: 4px; margin-bottom: 12px;">
            SYNTHETIC DEMO DOCUMENT
          </div>
          <div style="display: flex; gap: 14px; align-items: center; margin-bottom: 14px;">
            <div style="width: 60px; height: 75px; background: #334155; border: 1px solid #1DCED8; border-radius: 4px; display: flex; align-items: center; justify-content: center; color: #1DCED8;">
              <i class="fa-solid fa-user-shield" style="font-size: 1.8rem;"></i>
            </div>
            <div style="text-align: left;">
              <div style="font-size: 0.7rem; color: #94a3b8;">नाम / Name</div>
              <div style="font-weight: 700; color: #fff; font-size: 1.1rem;">AARAV DEMO</div>
              <div style="font-size: 0.7rem; color: #94a3b8; margin-top: 4px;">SENTINEL-DEMO-001</div>
            </div>
          </div>
          <div style="font-family: monospace; font-size: 0.75rem; color: #FF9D50; border-top: 1px solid rgba(255,255,255,0.1); padding-top: 10px;">
            <i class="fa-solid fa-triangle-exclamation"></i> NOT A GOVERNMENT DOCUMENT
          </div>
        </div>
      </div>
    `;
  }

  // Draw Dynamic Mini Heatmap on the ELA preview canvas
  function initMiniHeatmap() {
    const el = document.getElementById('ela-heatmap-canvas');
    if (!el) return;
    const ctx = el.getContext('2d');
    const w = el.width = 130;
    const h = el.height = 38;

    // Draw localized thermal heatmap representing ELA compression differences
    const imgData = ctx.createImageData(w, h);
    for (let x = 0; x < w; x++) {
      for (let y = 0; y < h; y++) {
        const idx = (y * w + x) * 4;
        // Distances from anomaly hot-spot
        const dist = Math.sqrt((x - 70) * (x - 70) + (y - 18) * (y - 18));
        const heat = Math.max(0, 1 - dist / 35);
        
        // Color gradient from dark blue -> cyan -> yellow -> red
        if (heat > 0.6) {
          imgData.data[idx] = 255;       // R
          imgData.data[idx + 1] = Math.floor((1 - heat) * 255); // G
          imgData.data[idx + 2] = 50;    // B
        } else if (heat > 0.25) {
          imgData.data[idx] = 255;       // R
          imgData.data[idx + 1] = 165;   // G
          imgData.data[idx + 2] = 0;     // B
        } else {
          imgData.data[idx] = 20;        // R
          imgData.data[idx + 1] = Math.floor(heat * 180) + 30; // G
          imgData.data[idx + 2] = 160;   // B
        }
        imgData.data[idx + 3] = 230;     // A
      }
    }
    ctx.putImageData(imgData, 0, 0);
  }

  // Cleanup Three.js scene and listeners idempotently (Requirement 14)
  function cleanupThreeScene() {
    if (animationFrameId) {
      cancelAnimationFrame(animationFrameId);
      animationFrameId = null;
    }

    window.removeEventListener('resize', onWindowResize);
    window.removeEventListener('scroll', onScroll);
    document.removeEventListener('visibilitychange', onVisibilityChange);

    if (resizeObserver) {
      resizeObserver.disconnect();
      resizeObserver = null;
    }

    if (debugHud && debugHud.parentNode) {
      debugHud.parentNode.removeChild(debugHud);
      debugHud = null;
    }

    if (scene) {
      scene.traverse((obj) => {
        if (obj.geometry) obj.geometry.dispose();
        if (obj.material) {
          if (Array.isArray(obj.material)) {
            obj.material.forEach((mat) => {
              if (mat.map) mat.map.dispose();
              mat.dispose();
            });
          } else {
            if (obj.material.map) obj.material.map.dispose();
            obj.material.dispose();
          }
        }
      });
    }

    if (renderer) {
      if (renderer.domElement && renderer.domElement.parentNode) {
        renderer.domElement.parentNode.removeChild(renderer.domElement);
      }
      renderer.dispose();
      renderer.forceContextLoss();
      renderer = null;
    }

    if (container) {
      container.innerHTML = '';
    }

    scene = null;
    camera = null;
    cardGroup = null;
    platformGroup = null;
    particlesMesh = null;
    scanLine = null;
    laserGlowMesh = null;
    connectorLinesGroup = null;
  }

  // Diagnostic Debug HUD (Requirement 17)
  function initDebugHUD() {
    const params = new URLSearchParams(window.location.search);
    if (!params.has('debug3d') || params.get('debug3d') === 'false') return null;

    const existing = document.getElementById('sentinel-3d-debug-hud');
    if (existing) existing.remove();

    const hud = document.createElement('div');
    hud.id = 'sentinel-3d-debug-hud';
    hud.style.cssText = `
      position: fixed;
      bottom: 24px;
      left: 24px;
      background: rgba(10, 16, 32, 0.94);
      border: 1px solid #1DCED8;
      box-shadow: 0 0 25px rgba(29, 206, 216, 0.35);
      color: #e2e8f0;
      font-family: 'JetBrains Mono', monospace, Consolas, sans-serif;
      font-size: 11px;
      line-height: 1.55;
      padding: 12px 18px;
      border-radius: 8px;
      z-index: 99999;
      pointer-events: none;
      backdrop-filter: blur(10px);
      min-width: 220px;
    `;
    document.body.appendChild(hud);
    return hud;
  }

  // Initialize Three.js Scene
  function initThreeScene() {
    // Idempotent cleanup before initialization
    cleanupThreeScene();

    hero3dContainer = document.getElementById('hero-3d-container') || document.querySelector('.hero-3d-container');
    container = document.getElementById('canvas-container');
    if (!container) return;
    if (!hero3dContainer) hero3dContainer = container;

    const width = hero3dContainer.clientWidth || container.clientWidth || 600;
    const height = hero3dContainer.clientHeight || container.clientHeight || 550;

    // Scene
    scene = new THREE.Scene();

    // Camera
    camera = new THREE.PerspectiveCamera(40, width / height, 0.1, 1000);
    camera.position.set(0, 0.4, 7.8);

    // Renderer (Requirement 10: DPR capped at 2)
    renderer = new THREE.WebGLRenderer({
      alpha: true,
      antialias: true,
      powerPreference: 'high-performance'
    });
    renderer.setSize(width, height, false);
    renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, 2));
    renderer.toneMapping = THREE.ACESFilmicToneMapping;
    renderer.toneMappingExposure = 1.1;
    container.appendChild(renderer.domElement);

    // Lights
    const ambientLight = new THREE.AmbientLight(0xffffff, 0.7);
    scene.add(ambientLight);

    const cyanPointLight = new THREE.PointLight(0x1DCED8, 2.5, 20);
    cyanPointLight.position.set(3, 2, 4);
    scene.add(cyanPointLight);

    const orangePointLight = new THREE.PointLight(0xFF9D50, 1.8, 15);
    orangePointLight.position.set(-3, -1, 3);
    scene.add(orangePointLight);

    const bottomGlow = new THREE.PointLight(0x1DCED8, 3.0, 10);
    bottomGlow.position.set(0, -2.2, 0);
    scene.add(bottomGlow);

    // -------------------------------------------------------------------------
    // 3D FLOATING SYNTHETIC CARD MESH
    // -------------------------------------------------------------------------
    cardGroup = new THREE.Group();

    const cardWidth = 4.3;
    const cardHeight = 2.72;
    const cardDepth = 0.06;

    const frontTexture = createFrontCardTexture();
    const backTexture = createBackCardTexture();

    // Materials for 6 faces of BoxGeometry:
    // [right, left, top, bottom, front (+z), back (-z)]
    const edgeMaterial = new THREE.MeshStandardMaterial({
      color: 0x1DCED8,
      metalness: 0.85,
      roughness: 0.2,
      emissive: 0x0a3340,
      emissiveIntensity: 0.6
    });

    const frontMaterial = new THREE.MeshStandardMaterial({
      map: frontTexture,
      roughness: 0.35,
      metalness: 0.15
    });

    const backMaterial = new THREE.MeshStandardMaterial({
      map: backTexture,
      roughness: 0.4,
      metalness: 0.2
    });

    const cardMaterials = [
      edgeMaterial,  // right
      edgeMaterial,  // left
      edgeMaterial,  // top
      edgeMaterial,  // bottom
      frontMaterial, // front (+z)
      backMaterial   // back (-z)
    ];

    const cardGeometry = new THREE.BoxGeometry(cardWidth, cardHeight, cardDepth);
    const cardMesh = new THREE.Mesh(cardGeometry, cardMaterials);
    cardGroup.add(cardMesh);

    // Holographic Cyan Rim Outline
    const edgesGeo = new THREE.EdgesGeometry(cardGeometry);
    const edgesMat = new THREE.LineBasicMaterial({
      color: 0x1DCED8,
      transparent: true,
      opacity: 0.75,
      linewidth: 2
    });
    const edgeLines = new THREE.LineSegments(edgesGeo, edgesMat);
    cardGroup.add(edgeLines);

    // -------------------------------------------------------------------------
    // VERTICAL FORENSIC SCAN LASER LINE
    // -------------------------------------------------------------------------
    const scanLineGeo = new THREE.PlaneGeometry(cardWidth + 0.15, 0.04);
    const scanLineMat = new THREE.MeshBasicMaterial({
      color: 0x00f0ff,
      transparent: true,
      opacity: 0.95,
      side: THREE.DoubleSide
    });
    scanLine = new THREE.Mesh(scanLineGeo, scanLineMat);
    scanLine.position.z = cardDepth / 2 + 0.015;
    cardGroup.add(scanLine);

    // Laser Glow Halo Strip
    const laserGlowGeo = new THREE.PlaneGeometry(cardWidth + 0.25, 0.22);
    const laserGlowMat = new THREE.MeshBasicMaterial({
      color: 0x1DCED8,
      transparent: true,
      opacity: 0.3,
      side: THREE.DoubleSide
    });
    laserGlowMesh = new THREE.Mesh(laserGlowGeo, laserGlowMat);
    laserGlowMesh.position.z = cardDepth / 2 + 0.012;
    cardGroup.add(laserGlowMesh);

    // -------------------------------------------------------------------------
    // FORENSIC SCAN ANCHOR NODES ON CARD
    // -------------------------------------------------------------------------
    const nodeCoords = [
      { x: -1.2, y: 0.3, label: 'OCR_NODE', color: 0x55E07E },
      { x: 1.3, y: 0.2, label: 'QR_NODE', color: 0xFF9D50 },
      { x: -0.2, y: -0.7, label: 'TYPO_NODE', color: 0x1DCED8 },
      { x: 0.9, y: -0.6, label: 'LAYOUT_NODE', color: 0xFF9D50 }
    ];

    connectorLinesGroup = new THREE.Group();

    nodeCoords.forEach((coord, i) => {
      // Inner circle
      const dotGeo = new THREE.CircleGeometry(0.045, 16);
      const dotMat = new THREE.MeshBasicMaterial({ color: coord.color, side: THREE.DoubleSide });
      const dot = new THREE.Mesh(dotGeo, dotMat);
      dot.position.set(coord.x, coord.y, cardDepth / 2 + 0.02);
      cardGroup.add(dot);

      // Pulsing Ring
      const ringGeo = new THREE.RingGeometry(0.065, 0.085, 32);
      const ringMat = new THREE.MeshBasicMaterial({ color: coord.color, transparent: true, opacity: 0.75, side: THREE.DoubleSide });
      const ring = new THREE.Mesh(ringGeo, ringMat);
      ring.position.set(coord.x, coord.y, cardDepth / 2 + 0.02);
      ring.userData = { pulseOffset: i * 1.5 };
      cardGroup.add(ring);
    });

    // Set initial card pose
    cardGroup.position.set(0, 0.3, 0);
    cardGroup.rotation.x = currentRotationX;
    cardGroup.rotation.y = currentRotationY;
    scene.add(cardGroup);

    // -------------------------------------------------------------------------
    // FUTURISTIC CIRCULAR SCANNING PLATFORM
    // -------------------------------------------------------------------------
    platformGroup = new THREE.Group();
    platformGroup.position.set(0, -2.1, 0);

    // Tier 1: Base Outer Steel Ring
    const baseGeo = new THREE.CylinderGeometry(2.8, 3.1, 0.22, 48);
    const baseMat = new THREE.MeshStandardMaterial({
      color: 0x0a1020,
      metalness: 0.9,
      roughness: 0.3
    });
    const baseMesh = new THREE.Mesh(baseGeo, baseMat);
    platformGroup.add(baseMesh);

    // Tier 2: Glowing Neon Accent Ring
    const neonRingGeo = new THREE.TorusGeometry(2.75, 0.04, 16, 64);
    const neonRingMat = new THREE.MeshBasicMaterial({ color: 0x1DCED8 });
    const neonRing = new THREE.Mesh(neonRingGeo, neonRingMat);
    neonRing.rotation.x = Math.PI / 2;
    neonRing.position.y = 0.12;
    platformGroup.add(neonRing);

    // Tier 3: Inner Elevated Disc
    const innerDiscGeo = new THREE.CylinderGeometry(2.1, 2.3, 0.18, 48);
    const innerDiscMat = new THREE.MeshStandardMaterial({
      color: 0x050813,
      metalness: 0.8,
      roughness: 0.4
    });
    const innerDisc = new THREE.Mesh(innerDiscGeo, innerDiscMat);
    innerDisc.position.y = 0.15;
    platformGroup.add(innerDisc);

    // Concentric Radar Rings & Segments
    const radarRingGeo = new THREE.RingGeometry(1.4, 1.44, 48);
    const radarRingMat = new THREE.MeshBasicMaterial({ color: 0x1DCED8, transparent: true, opacity: 0.6, side: THREE.DoubleSide });
    const radarRing = new THREE.Mesh(radarRingGeo, radarRingMat);
    radarRing.rotation.x = -Math.PI / 2;
    radarRing.position.y = 0.25;
    platformGroup.add(radarRing);

    const radarInnerRingGeo = new THREE.RingGeometry(0.8, 0.83, 36);
    const radarInnerRing = new THREE.Mesh(radarInnerRingGeo, radarRingMat);
    radarInnerRing.rotation.x = -Math.PI / 2;
    radarInnerRing.position.y = 0.255;
    platformGroup.add(radarInnerRing);

    // Holographic Vertical Projection Light Beam Cylinder
    const beamGeo = new THREE.CylinderGeometry(1.8, 1.2, 2.5, 32, 1, true);
    const beamMat = new THREE.MeshBasicMaterial({
      color: 0x1DCED8,
      transparent: true,
      opacity: 0.08,
      side: THREE.DoubleSide
    });
    const beamMesh = new THREE.Mesh(beamGeo, beamMat);
    beamMesh.position.y = 1.3;
    platformGroup.add(beamMesh);

    scene.add(platformGroup);

    // -------------------------------------------------------------------------
    // 3D PARTICLES
    // -------------------------------------------------------------------------
    const particleCount = window.innerWidth < 768 ? 80 : 180;
    const particlesGeo = new THREE.BufferGeometry();
    const particlePositions = new Float32Array(particleCount * 3);

    for (let i = 0; i < particleCount * 3; i += 3) {
      particlePositions[i] = (Math.random() - 0.5) * 12;
      particlePositions[i + 1] = (Math.random() - 0.5) * 8;
      particlePositions[i + 2] = (Math.random() - 0.5) * 8;
    }

    particlesGeo.setAttribute('position', new THREE.BufferAttribute(particlePositions, 3));
    const particlesMat = new THREE.PointsMaterial({
      size: 0.045,
      color: 0x1DCED8,
      transparent: true,
      opacity: 0.4
    });
    particlesMesh = new THREE.Points(particlesGeo, particlesMat);
    scene.add(particlesMesh);

    // -------------------------------------------------------------------------
    // EVENT LISTENERS & POINTER INTERACTION (Requirements 2, 3, 8, 9, 11)
    // -------------------------------------------------------------------------
    // Check reduced motion preference
    const mediaQuery = window.matchMedia('(prefers-reduced-motion: reduce)');
    prefersReducedMotion = mediaQuery.matches;
    mediaQuery.addEventListener('change', (e) => {
      prefersReducedMotion = e.matches;
    });

    // Clock for delta-time based autonomous animation (Requirement 10)
    clock = new THREE.Clock();

    // Scroll parallax tracking
    window.addEventListener('scroll', onScroll, { passive: true });

    // Resize handling with ResizeObserver (Requirement 9)
    if (window.ResizeObserver) {
      resizeObserver = new ResizeObserver((entries) => {
        for (const entry of entries) {
          const { width, height } = entry.contentRect;
          if (width > 0 && height > 0) {
            updateDimensions(width, height);
          }
        }
      });
      resizeObserver.observe(hero3dContainer);
    }
    window.addEventListener('resize', onWindowResize);

    // Tab visibility handling (Requirement 11)
    document.addEventListener('visibilitychange', onVisibilityChange);

    // Diagnostic HUD (Requirement 17)
    debugHud = initDebugHUD();

    // Start animation loop
    animate();

    // Expose lifecycle for hot-reloading / testing (Requirement 14)
    window.__SENTINEL_3D__ = {
      dispose: cleanupThreeScene,
      init: initThreeScene
    };
  }



  function onScroll() {
    scrollOffset = window.scrollY || window.pageYOffset || 0;
  }

  function updateDimensions(width, height) {
    if (!camera || !renderer) return;
    if (width <= 0 || height <= 0) return;
    camera.aspect = width / height;
    camera.updateProjectionMatrix();
    renderer.setSize(width, height, false);
  }

  function onWindowResize() {
    if (!hero3dContainer) return;
    const w = hero3dContainer.clientWidth || (container ? container.clientWidth : 600);
    const h = hero3dContainer.clientHeight || (container ? container.clientHeight : 550);
    updateDimensions(w, h);
  }

  function onVisibilityChange() {
    isTabActive = !document.hidden;
    if (isTabActive) {
      if (clock) clock.getDelta(); // flush delta so no giant leap after backgrounding
      if (!animationFrameId) {
        animate();
      }
    } else {
      if (animationFrameId) {
        cancelAnimationFrame(animationFrameId);
        animationFrameId = null;
      }
    }
  }

  // Animation Loop (Requirements 2, 3, 4, 6, 9, 10: Autonomous Cinematic Rotation)
  let fpsHistory = 60;
  function animate() {
    if (!isTabActive) {
      animationFrameId = null;
      return;
    }

    animationFrameId = requestAnimationFrame(animate);

    if (!clock) clock = new THREE.Clock();
    const delta = Math.min(clock.getDelta(), 0.1);
    const elapsedTime = clock.getElapsedTime();

    // Rolling FPS approximation
    const instantFps = delta > 0 ? 1 / delta : 60;
    fpsHistory = Math.round(fpsHistory * 0.9 + instantFps * 0.1);

    // 1. Autonomous Cinematic Document Motion
    if (!prefersReducedMotion && cardGroup) {
      // Slow continuous Y-axis rotation (0.12 rad/sec)
      currentRotationY += ROTATION_SPEED_Y * delta;
      if (currentRotationY > Math.PI * 2) {
        currentRotationY -= Math.PI * 2;
      }
      cardGroup.rotation.y = currentRotationY;

      // Subtle breathing / tilt motion on X-axis (Requirement 3)
      const subtleTiltX = Math.sin(elapsedTime * 0.6) * 0.035;
      cardGroup.rotation.x = NEUTRAL_ROTATION_X + subtleTiltX;

      // Floating altitude oscillation
      cardGroup.position.y = 0.3 + Math.sin(elapsedTime * 1.1) * 0.05;

      // Ambient counter-rotation of scanner platform (Requirement 6)
      if (platformGroup) {
        platformGroup.rotation.y += 0.06 * delta;
      }

      // Ambient particle drift
      if (particlesMesh) {
        particlesMesh.rotation.y += 0.02 * delta;
      }

      // Pulse anchor node rings
      cardGroup.children.forEach((child) => {
        if (child.userData && typeof child.userData.pulseOffset === 'number' && child.material) {
          child.material.opacity = 0.45 + Math.sin(elapsedTime * 2.2 + child.userData.pulseOffset) * 0.35;
        }
      });

    } else if (cardGroup) {
      // Reduced motion: stable, static, perfectly readable presentation (Requirement 9)
      cardGroup.rotation.y = NEUTRAL_ROTATION_Y;
      cardGroup.rotation.x = NEUTRAL_ROTATION_X;
      cardGroup.position.y = 0.3;

      if (platformGroup) {
        platformGroup.rotation.y = 0;
      }
    }

    // 2. Vertical Forensic Scan Laser Animation
    if (!prefersReducedMotion) {
      const scanProgress = (Math.sin(elapsedTime * 1.8) + 1) / 2; // 0 to 1
      const scanMinY = -1.25;
      const scanMaxY = 1.25;
      const currentScanY = scanMinY + scanProgress * (scanMaxY - scanMinY);

      if (scanLine && laserGlowMesh) {
        scanLine.position.y = currentScanY;
        laserGlowMesh.position.y = currentScanY;
        laserGlowMesh.material.opacity = 0.3 + Math.sin(elapsedTime * 2.4) * 0.08;
      }
    } else if (scanLine && laserGlowMesh) {
      scanLine.position.y = 0;
      laserGlowMesh.position.y = 0;
      laserGlowMesh.material.opacity = 0.2;
    }

    // 3. Scroll camera parallax
    if (camera && scrollOffset < 800) {
      camera.position.y = 0.4 - scrollOffset * 0.0012;
    }

    if (renderer && scene && camera) {
      renderer.render(scene, camera);
    }

    // 4. Autonomous Diagnostic Debug HUD (Requirement 13)
    if (debugHud) {
      const cW = hero3dContainer ? hero3dContainer.clientWidth : 0;
      const cH = hero3dContainer ? hero3dContainer.clientHeight : 0;
      const rW = renderer && renderer.domElement ? renderer.domElement.width : 0;
      const rH = renderer && renderer.domElement ? renderer.domElement.height : 0;

      debugHud.innerHTML = `
        <div style="color:#1DCED8; font-weight:bold; font-size:12px; margin-bottom:6px; letter-spacing:1px; border-bottom:1px solid rgba(29,206,216,0.3); padding-bottom:4px;">SENTINEL 3D DIAGNOSTICS</div>
        <div>3D STATUS: <span style="color:#55E07E; font-weight:bold;">READY</span></div>
        <div>WEBGL: <span style="color:#55E07E; font-weight:bold;">YES</span></div>
        <div>ANIMATION: <span style="color:${isTabActive ? '#55E07E' : '#FF9D50'}; font-weight:bold;">${isTabActive ? 'ACTIVE' : 'PAUSED'}</span></div>
        <div>MODE: <span style="color:#1DCED8; font-weight:bold;">AUTONOMOUS</span></div>
        <div>ROTATION: <span style="color:#1DCED8;">${prefersReducedMotion ? 'STATIC (0.00 RAD/S)' : (ROTATION_SPEED_Y.toFixed(2) + ' RAD/S')}</span></div>
        <div>MOTION: <span style="color:${prefersReducedMotion ? '#FF9D50' : '#55E07E'}; font-weight:bold;">${prefersReducedMotion ? 'REDUCED' : 'NORMAL'}</span></div>
        <div>FPS: <span style="color:#55E07E; font-weight:bold;">${fpsHistory}</span></div>
        <div>CANVAS: ${rW} × ${rH}</div>
        <div>CONTAINER: ${cW} × ${cH}</div>
      `;
    }
  }

  // DOM Ready Entrypoint
  document.addEventListener('DOMContentLoaded', () => {
    initMiniHeatmap();

    if (isWebGLAvailable()) {
      try {
        initThreeScene();
      } catch (err) {
        console.error('[SENTINEL 3D] WebGL initialization error:', err);
        setupFallback();
      }
    } else {
      console.warn('[SENTINEL 3D] WebGL not supported, showing fallback visualization.');
      setupFallback();
    }
  });

})();
