/**
 * SENTINEL Forensics - Secure Mail & Demo Request Service
 * Node.js + Express + Nodemailer microservice
 */

const express = require('express');
const cors = require('cors');
const nodemailer = require('nodemailer');
const path = require('path');
const dotenv = require('dotenv');

// Load environment variables from workspace root .env if available, then fallback to local
const rootEnvPath = path.resolve(__dirname, '../../.env');
dotenv.config({ path: rootEnvPath });
dotenv.config(); // fallback to local .env if present

const app = express();
const PORT = process.env.MAIL_SERVICE_PORT || process.env.PORT || 5001;

// Middlewares
app.use(express.json({ limit: '100kb' }));
app.use(express.urlencoded({ extended: true, limit: '100kb' }));

// CORS configuration
const allowedOrigins = [
  'http://localhost:3000',
  'http://127.0.0.1:3000',
  'http://localhost:8000',
  'http://127.0.0.1:8000',
  'http://localhost:5001',
  'http://127.0.0.1:5001'
];

app.use(cors({
  origin: (origin, callback) => {
    // Allow requests with no origin (like mobile apps, curl, server-to-server) or localhost
    if (!origin || allowedOrigins.includes(origin) || origin.startsWith('http://localhost') || origin.startsWith('http://127.0.0.1')) {
      return callback(null, true);
    }
    return callback(new Error('Blocked by CORS'));
  },
  methods: ['GET', 'POST', 'OPTIONS'],
  credentials: true
}));

// In-Memory Rate Limiting
const rateLimitMap = new Map();
const RATE_LIMIT_WINDOW_MS = 15 * 60 * 1000; // 15 minutes
const MAX_REQUESTS_PER_WINDOW = 5;

function rateLimiter(req, res, next) {
  const ip = req.headers['x-forwarded-for'] || req.socket.remoteAddress || '127.0.0.1';
  const now = Date.now();

  const record = rateLimitMap.get(ip) || { count: 0, resetTime: now + RATE_LIMIT_WINDOW_MS };

  if (now > record.resetTime) {
    record.count = 1;
    record.resetTime = now + RATE_LIMIT_WINDOW_MS;
  } else {
    record.count += 1;
  }

  rateLimitMap.set(ip, record);

  if (record.count > MAX_REQUESTS_PER_WINDOW) {
    const retryAfterSec = Math.ceil((record.resetTime - now) / 1000);
    res.setHeader('Retry-After', retryAfterSec);
    return res.status(429).json({
      success: false,
      error: 'Rate limit exceeded. Please wait a few minutes before submitting again.'
    });
  }

  next();
}

// Input Sanitization & Validation Helpers
function sanitizeString(str) {
  if (typeof str !== 'string') return '';
  return str
    .replace(/<[^>]*>?/gm, '') // Strip HTML tags
    .replace(/[\r\n]+/g, ' ')  // Prevent header injection in single-line fields
    .trim();
}

function sanitizeMultiLine(str) {
  if (typeof str !== 'string') return '';
  return str
    .replace(/<[^>]*>?/gm, '') // Strip HTML tags
    .trim();
}

function isValidEmail(email) {
  if (!email || typeof email !== 'string') return false;
  // RFC 5322 compliant regex for common practical emails
  const emailRegex = /^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$/;
  return emailRegex.test(email.trim());
}

// Transporter Cache / Initialization
let transporterPromise = null;

async function getTransporter() {
  if (transporterPromise) return transporterPromise;

  transporterPromise = (async () => {
    const host = process.env.SMTP_HOST;
    const port = parseInt(process.env.SMTP_PORT || '587', 10);
    const user = process.env.SMTP_USER;
    const pass = process.env.SMTP_PASS;

    // If real credentials are provided
    if (host && user && pass) {
      console.log(`[MailService] Configuring SMTP transporter for ${host}:${port}`);
      return nodemailer.createTransport({
        host,
        port,
        secure: port === 465,
        auth: { user, pass },
        tls: { rejectUnauthorized: false }
      });
    }

    // In development or when SMTP is not configured, create test/ethereal or simulated fallback
    console.log('[MailService] SMTP credentials not provided or empty. Initializing Ethereal/simulated dev transport...');
    try {
      const testAccount = await nodemailer.createTestAccount();
      console.log('[MailService] Created Ethereal test account:', testAccount.user);
      return nodemailer.createTransport({
        host: 'smtp.ethereal.email',
        port: 587,
        secure: false,
        auth: {
          user: testAccount.user,
          pass: testAccount.pass
        }
      });
    } catch (err) {
      console.warn('[MailService] Could not connect to Ethereal, using mock transporter for safe offline development:', err.message);
      return {
        sendMail: async (mailOptions) => {
          console.log('[MailService MOCK SEND] To:', mailOptions.to, '| Subject:', mailOptions.subject);
          return { messageId: `mock-${Date.now()}` };
        }
      };
    }
  })();

  return transporterPromise;
}

// Health Check Endpoint
app.get('/health', (req, res) => {
  res.json({
    status: 'ok',
    service: 'SENTINEL Mail Service',
    smtpConfigured: Boolean(process.env.SMTP_HOST && process.env.SMTP_USER && process.env.SMTP_PASS),
    contactEmail: process.env.CONTACT_EMAIL || 'investigations@sentinel-forensics.org',
    timestamp: new Date().toISOString()
  });
});

app.get('/api/contact/health', (req, res) => {
  res.json({ status: 'ok', service: 'SENTINEL Mail Service' });
});

// Contact / Demo Request Endpoint
app.post('/api/contact', rateLimiter, async (req, res) => {
  try {
    let { name, email, organization, subject, message, phone } = req.body || {};

    // Sanitize
    name = sanitizeString(name);
    email = sanitizeString(email);
    organization = sanitizeString(organization);
    subject = sanitizeString(subject);
    phone = phone ? sanitizeString(phone) : '';
    message = sanitizeMultiLine(message);

    // Validate
    if (!name || name.length < 2 || name.length > 100) {
      return res.status(400).json({ success: false, error: 'A valid name (2-100 characters) is required.' });
    }

    if (!isValidEmail(email) || email.length > 120) {
      return res.status(400).json({ success: false, error: 'A valid email address is required.' });
    }

    if (!organization || organization.length < 2 || organization.length > 120) {
      return res.status(400).json({ success: false, error: 'Organization name (2-120 characters) is required.' });
    }

    if (!subject || subject.length < 2 || subject.length > 150) {
      return res.status(400).json({ success: false, error: 'Subject (2-150 characters) is required.' });
    }

    if (!message || message.length < 10 || message.length > 3000) {
      return res.status(400).json({ success: false, error: 'Message must be between 10 and 3000 characters.' });
    }

    const timestamp = new Date().toISOString();
    const contactEmail = process.env.CONTACT_EMAIL || 'investigations@sentinel-forensics.org';
    const senderFrom = process.env.SMTP_USER || '"SENTINEL Forensics" <no-reply@sentinel-forensics.org>';

    const transporter = await getTransporter();

    // 1. Send Admin Notification Email
    const adminMailOptions = {
      from: senderFrom,
      to: contactEmail,
      replyTo: email,
      subject: `[SENTINEL] New Demo / Contact Request: ${subject}`,
      text: `SENTINEL CONTACT REQUEST\n\nName: ${name}\nEmail: ${email}\nOrganization: ${organization}\nPhone: ${phone || 'Not provided'}\nSubject: ${subject}\n\nMessage:\n${message}\n\nSubmitted: ${new Date().toUTCString()}\nTimestamp: ${timestamp}`,
      html: `
        <!DOCTYPE html>
        <html>
        <head>
          <style>
            body { font-family: 'Helvetica Neue', Arial, sans-serif; background-color: #0b0f19; color: #e2e8f0; margin: 0; padding: 20px; }
            .container { max-width: 600px; margin: 0 auto; background: #111827; border: 1px solid #1f2937; border-radius: 8px; overflow: hidden; }
            .header { background: #030712; padding: 20px 24px; border-bottom: 2px solid #1DCED8; }
            .header h1 { margin: 0; font-size: 20px; color: #1DCED8; letter-spacing: 1px; }
            .header p { margin: 5px 0 0; color: #94a3b8; font-size: 12px; }
            .content { padding: 24px; }
            .field-group { margin-bottom: 16px; border-bottom: 1px solid #1f2937; padding-bottom: 12px; }
            .label { font-size: 11px; text-transform: uppercase; color: #FF9D50; letter-spacing: 0.5px; margin-bottom: 4px; }
            .value { font-size: 15px; color: #f8fafc; font-weight: 500; }
            .message-box { background: #030712; border-left: 3px solid #1DCED8; padding: 15px; border-radius: 4px; font-size: 14px; line-height: 1.6; white-space: pre-wrap; color: #cbd5e1; }
            .footer { padding: 16px 24px; background: #030712; font-size: 12px; color: #64748b; text-align: center; border-top: 1px solid #1f2937; }
          </style>
        </head>
        <body>
          <div class="container">
            <div class="header">
              <h1>🛡️ SENTINEL FORENSICS</h1>
              <p>INCOMING INVESTIGATION / DEMO REQUEST</p>
            </div>
            <div class="content">
              <div class="field-group">
                <div class="label">Requester Name</div>
                <div class="value">${name}</div>
              </div>
              <div class="field-group">
                <div class="label">Requester Email</div>
                <div class="value"><a href="mailto:${email}" style="color: #1DCED8; text-decoration: none;">${email}</a></div>
              </div>
              <div class="field-group">
                <div class="label">Organization / Agency</div>
                <div class="value">${organization}</div>
              </div>
              ${phone ? `
              <div class="field-group">
                <div class="label">Contact Phone</div>
                <div class="value">${phone}</div>
              </div>` : ''}
              <div class="field-group">
                <div class="label">Inquiry Subject</div>
                <div class="value">${subject}</div>
              </div>
              <div class="field-group" style="border-bottom: none;">
                <div class="label">Detailed Message</div>
                <div class="message-box">${message}</div>
              </div>
            </div>
            <div class="footer">
              Submitted on ${new Date().toUTCString()} &bull; ISO: ${timestamp}<br>
              SENTINEL AI-Powered Document Forensics Platform
            </div>
          </div>
        </body>
        </html>
      `
    };

    const adminResult = await transporter.sendMail(adminMailOptions);
    if (adminResult && adminResult.messageId) {
      console.log(`[MailService] Sent contact notification to ${contactEmail}, ID: ${adminResult.messageId}`);
      if (nodemailer.getTestMessageUrl && adminResult) {
        const previewUrl = nodemailer.getTestMessageUrl(adminResult);
        if (previewUrl) console.log(`[MailService] Ethereal Preview URL: ${previewUrl}`);
      }
    }

    // 2. Send Optional Confirmation Email to Requester
    try {
      const confirmMailOptions = {
        from: senderFrom,
        to: email,
        subject: `SENTINEL — Request Received`,
        text: `Hello ${name},\n\nYour request regarding "${subject}" has been received by the SENTINEL team.\n\nSummary of your request:\n- Organization: ${organization}\n- Subject: ${subject}\n- Received: ${new Date().toUTCString()}\n\nOur team investigates each inquiry methodically. Thank you for your interest in SENTINEL.\n\nRegards,\nSENTINEL Forensics Team\nAI-Powered Document Forensics\nhttps://sentinel-forensics.org`,
        html: `
          <!DOCTYPE html>
          <html>
          <head>
            <style>
              body { font-family: 'Helvetica Neue', Arial, sans-serif; background-color: #0b0f19; color: #e2e8f0; margin: 0; padding: 20px; }
              .container { max-width: 600px; margin: 0 auto; background: #111827; border: 1px solid #1f2937; border-radius: 8px; overflow: hidden; }
              .header { background: #030712; padding: 20px 24px; border-bottom: 2px solid #1DCED8; }
              .header h1 { margin: 0; font-size: 20px; color: #1DCED8; letter-spacing: 1px; }
              .content { padding: 24px; line-height: 1.6; font-size: 14px; color: #cbd5e1; }
              .notice { background: rgba(29, 206, 216, 0.08); border-left: 3px solid #1DCED8; padding: 12px 16px; margin: 16px 0; border-radius: 4px; }
              .footer { padding: 16px 24px; background: #030712; font-size: 12px; color: #64748b; text-align: center; border-top: 1px solid #1f2937; }
            </style>
          </head>
          <body>
            <div class="container">
              <div class="header">
                <h1>🛡️ SENTINEL FORENSICS</h1>
              </div>
              <div class="content">
                <p>Hello <strong>${name}</strong>,</p>
                <div class="notice">
                  Your request has been received by the SENTINEL team.
                </div>
                <p>We have logged your inquiry regarding <em>"${subject}"</em> under organization <strong>${organization}</strong>.</p>
                <p>SENTINEL is an AI-powered document forensics screening engine purpose-built for synthetic identity detection, tamper localization, and explainable risk analysis.</p>
                <p style="margin-top: 24px;">Sincerely,<br><strong>SENTINEL Forensics Operations</strong><br><em>Trust the Evidence.</em></p>
              </div>
              <div class="footer">
                &copy; 2026 SENTINEL Forensics &bull; Problem Statement CX0203
              </div>
            </div>
          </body>
          </html>
        `
      };
      await transporter.sendMail(confirmMailOptions);
    } catch (confErr) {
      console.warn('[MailService] Requester confirmation email could not be sent (non-fatal):', confErr.message);
    }

    return res.json({
      success: true,
      message: 'Message sent successfully.'
    });

  } catch (err) {
    // Log error internally without exposing credentials to client
    console.error('[MailService Error]', err.message);
    return res.status(500).json({
      success: false,
      error: 'Unable to send message. Please try again.'
    });
  }
});

// Start Server if run directly
if (require.main === module) {
  app.listen(PORT, () => {
    console.log(`===============================================`);
    console.log(`🛡️  SENTINEL Mail Service running on port ${PORT}`);
    console.log(`📡 Endpoints:`);
    console.log(`   - GET  http://localhost:${PORT}/health`);
    console.log(`   - POST http://localhost:${PORT}/api/contact`);
    console.log(`===============================================`);
  });
}

module.exports = app;
