/**
 * Automated test suite for SENTINEL Node.js Mail Service
 */

const http = require('http');

async function makeRequest(options, data) {
  return new Promise((resolve, reject) => {
    const req = http.request(options, (res) => {
      let body = '';
      res.on('data', chunk => body += chunk);
      res.on('end', () => {
        try {
          resolve({ status: res.statusCode, headers: res.headers, body: JSON.parse(body) });
        } catch(e) {
          resolve({ status: res.statusCode, headers: res.headers, body });
        }
      });
    });
    req.on('error', reject);
    if (data) req.write(JSON.stringify(data));
    req.end();
  });
}

async function runTests() {
  console.log('--- Starting Mail Service Unit & Integration Tests ---');
  const app = require('./mailService');
  const server = app.listen(5099, async () => {
    try {
      // 1. Health check
      console.log('Test 1: Health check endpoint');
      const healthRes = await makeRequest({
        hostname: 'localhost',
        port: 5099,
        path: '/health',
        method: 'GET'
      });
      console.assert(healthRes.status === 200, `Health check returned ${healthRes.status}`);
      console.assert(healthRes.body.status === 'ok', 'Status should be ok');
      console.log('✓ Health check passed');

      // 2. Validation check: Missing fields
      console.log('Test 2: Validation on missing fields');
      const invalidRes = await makeRequest({
        hostname: 'localhost',
        port: 5099,
        path: '/api/contact',
        method: 'POST',
        headers: { 'Content-Type': 'application/json' }
      }, { name: 'A' });
      console.assert(invalidRes.status === 400, `Should return 400 on invalid input, got ${invalidRes.status}`);
      console.assert(invalidRes.body.success === false, 'success should be false');
      console.log('✓ Missing fields rejected properly');

      // 3. Validation check: Invalid email
      console.log('Test 3: Validation on invalid email');
      const badEmailRes = await makeRequest({
        hostname: 'localhost',
        port: 5099,
        path: '/api/contact',
        method: 'POST',
        headers: { 'Content-Type': 'application/json' }
      }, {
        name: 'Inspector Vikram',
        email: 'invalid-email-format',
        organization: 'Cyber Cell',
        subject: 'Demo Request',
        message: 'This is a valid test message that exceeds ten characters.'
      });
      console.assert(badEmailRes.status === 400, `Should return 400 on bad email, got ${badEmailRes.status}`);
      console.log('✓ Invalid email rejected properly');

      // 4. Valid Submission
      console.log('Test 4: Valid form submission');
      const validRes = await makeRequest({
        hostname: 'localhost',
        port: 5099,
        path: '/api/contact',
        method: 'POST',
        headers: { 'Content-Type': 'application/json' }
      }, {
        name: 'Inspector Vikram Demo',
        email: 'vikram.demo@sentinel-forensics.org',
        organization: 'Forensic Lab Unit 4',
        subject: 'Platform Evaluation Request',
        phone: '+91 98765 43210',
        message: 'Requesting access to the SENTINEL 3D forensic investigation demo environment.'
      });
      console.assert(validRes.status === 200, `Should return 200 on valid submission, got ${validRes.status}`);
      console.assert(validRes.body.success === true, 'success should be true');
      console.assert(validRes.body.message === 'Message sent successfully.', 'Correct success message');
      console.log('✓ Valid contact request processed successfully');

      // 5. Password Reset Validation Check
      console.log('Test 5: Password reset validation checks');
      const badResetRes = await makeRequest({
        hostname: 'localhost',
        port: 5099,
        path: '/api/mail/password-reset',
        method: 'POST',
        headers: { 'Content-Type': 'application/json' }
      }, { email: 'bad-email', resetUrl: 'invalid-url' });
      console.assert(badResetRes.status === 400, `Should return 400 on invalid reset payload, got ${badResetRes.status}`);
      console.log('✓ Invalid password reset input rejected');

      // 6. Valid Password Reset Submission
      console.log('Test 6: Valid password reset email dispatch');
      const validResetRes = await makeRequest({
        hostname: 'localhost',
        port: 5099,
        path: '/api/mail/password-reset',
        method: 'POST',
        headers: { 'Content-Type': 'application/json' }
      }, {
        email: 'officer.test@sentinel-forensics.org',
        resetUrl: 'http://localhost:3000/reset-password.html?token=test-mock-token-xyz123',
        recipientName: 'Lead Investigator'
      });
      console.assert(validResetRes.status === 200, `Should return 200 on valid reset request, got ${validResetRes.status}`);
      console.assert(validResetRes.body.success === true, 'success should be true');
      console.log('✓ Valid password reset request processed successfully');

      console.log('\n=== ALL MAIL SERVICE TESTS PASSED! ===');
    } catch (e) {
      console.error('Test execution error:', e);
      process.exitCode = 1;
    } finally {
      server.close();
    }
  });
}

runTests();
