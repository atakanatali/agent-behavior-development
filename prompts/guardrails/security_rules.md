# Security Rules & Constraints

Mandatory security standards that apply to all code, all domains, all features.

## Authentication & Authorization

### Authentication Requirements
- **Every protected endpoint** must verify user identity
- **No reliance on client-side checks** for security decisions
- **Token/session validation required** on every request to protected resources
- **Invalid tokens must be rejected** (don't try to repair them)

### Authorization Requirements
- **Every operation affecting data** must check if user has permission
- **Role-based or attribute-based** access control consistently applied
- **Deny by default**: User can only do what's explicitly allowed
- **Principle of least privilege**: Users get minimum permissions needed

### Session Management
- **Secure session tokens**: Long, random, cryptographically generated
- **HTTPOnly cookies**: If using cookies, set HTTPOnly flag
- **Secure flag**: If using HTTPS (required in production), set Secure flag
- **SameSite attribute**: Prevent CSRF attacks
- **Session expiration**: Set reasonable timeout (typically 24 hours for web, shorter for APIs)
- **Logout clears session**: Invalidate token/session on logout

### Password Requirements
- **Minimum length**: 8 characters
- **Complexity optional**: But if required, document clearly
- **Hashing required**: bcrypt, Argon2, or PBKDF2 (never plaintext or simple MD5/SHA1)
- **Never transmit plaintext**: Use HTTPS always
- **Never log passwords**: Not even for debugging

## Input Validation

### Mandatory Validation
- **Every input** from users, APIs, files must be validated
- **Whitelist approach**: Accept known good, reject everything else
- **Type checking**: Verify type is expected
- **Length limits**: Check string lengths
- **Format validation**: Email format, phone format, etc.
- **Range checking**: Numbers within expected range

### Validation Examples

```typescript
// Bad: No validation
function createUser(email) {
  db.users.insert({ email });
}

// Good: Validation on input
function createUser(email: string) {
  // Type checking (TypeScript)
  // Length validation
  if (email.length > 255) throw new ValidationError('Email too long');

  // Format validation
  if (!email.includes('@') || !email.includes('.')) {
    throw new ValidationError('Invalid email format');
  }

  // Safe to use
  db.users.insert({ email: email.toLowerCase() });
}
```

### Validation Locations
- **API boundary**: Validate all incoming requests
- **Database layer**: Secondary validation (belt-and-suspenders)
- **Business logic**: Validate state/relationships
- **Never trust**: User input, API responses, file contents

## SQL Injection Prevention

### Mandatory: Parameterized Queries
```typescript
// Bad: Vulnerable to SQL injection
const query = `SELECT * FROM users WHERE email = '${email}'`;
db.execute(query);

// Good: Parameterized query
const query = 'SELECT * FROM users WHERE email = ?';
db.execute(query, [email]);

// Also good: ORM with bound parameters
const user = await User.findOne({ where: { email } });
```

### Never String Concatenate
- Don't build SQL strings with concatenation
- Use ORM parameterization or prepared statements
- Test with injection attempts: `' OR 1=1 --`

## XSS (Cross-Site Scripting) Prevention

### Web Applications
- **Never use dangerouslySetInnerHTML** unless absolutely necessary
- **Escape HTML output**: `<div>{userInput}</div>` is safe in React
- **Content Security Policy**: Set CSP headers
- **No inline scripts**: No onclick handlers with user data

### Prevention Examples
```typescript
// Bad: XSS vulnerability
function displayComment(comment) {
  div.innerHTML = comment; // User script executes!
}

// Good: React auto-escapes
function displayComment(comment) {
  return <div>{comment}</div>; // Safe, HTML escaped
}

// Bad: Manual HTML construction
function buildHTML(userInput) {
  return `<p>${userInput}</p>`; // Vulnerable!
}

// Good: Escaped
function buildHTML(userInput) {
  const div = document.createElement('div');
  div.textContent = userInput; // Escaped
  return div;
}
```

## CSRF (Cross-Site Request Forgery) Prevention

### Web Applications
- **CSRF tokens required** for state-changing operations (POST, PUT, DELETE)
- **Token in request body or header** (not URL parameter)
- **Validate token matches session**
- **SameSite cookies** as backup

### Implementation
```typescript
// Frontend: Include token in form
<form action="/api/users" method="POST">
  <input type="hidden" name="_token" value="csrf_token_here">
  <!-- form fields -->
</form>

// Backend: Validate token
app.post('/api/users', (req, res) => {
  if (req.body._token !== req.session.csrfToken) {
    return res.status(403).send('Invalid token');
  }
  // Process request
});
```

## Secrets Management

### Mandatory Rules
- **No hardcoded secrets** (API keys, database passwords, etc.)
- **Use environment variables** in development
- **Use secrets manager** in production (AWS Secrets Manager, HashiCorp Vault, etc.)
- **Rotate secrets regularly** (yearly minimum, monthly recommended)
- **Never commit secrets** to version control (even in branches)

### Secrets Include
- Database passwords
- API keys for third-party services
- JWT signing keys
- Encryption keys
- OAuth client secrets
- Any authentication credentials

### Example
```typescript
// Bad: Hardcoded secret
const dbPassword = 'abc123hardcoded';
const db = connect(dbPassword);

// Good: Environment variable
const dbPassword = process.env.DB_PASSWORD;
if (!dbPassword) throw new Error('DB_PASSWORD not set');
const db = connect(dbPassword);

// Production: Secrets manager
const secretsManager = new AWS.SecretsManager();
const secret = await secretsManager.getSecretValue({ SecretId: 'db-password' });
const dbPassword = secret.SecretString;
```

## Encryption

### Data at Rest
- **Sensitive data encrypted** when stored
- **Database-level encryption**: Encryption key separate from DB
- **Field-level encryption**: For highly sensitive fields
- **Key management**: Separate from data (different system, rotating keys)

### Data in Transit
- **HTTPS required**: All traffic over secure connection
- **Enforce HTTPS**: Redirect HTTP to HTTPS
- **HSTS header**: Prevent downgrade attacks
- **TLS 1.2 or higher**: No old SSL/TLS versions

### Encryption Examples
```typescript
// Bad: Plaintext password storage
db.users.insert({ password: 'usersPassword' });

// Good: Hashed password
const hashedPassword = await bcrypt.hash(password, 10);
db.users.insert({ password: hashedPassword });

// Bad: Plaintext data transmission
fetch('http://api.example.com/data'); // HTTPS required!

// Good: HTTPS
fetch('https://api.example.com/data');
```

## OWASP Top 10 Coverage

### 1. Broken Access Control
- Verify authorization on every operation
- User can only access own data
- Admin endpoints properly secured
- Test with unauthorized users

### 2. Cryptographic Failures
- Data encrypted at rest
- Data encrypted in transit (HTTPS)
- Sensitive data not logged
- Encryption keys properly managed

### 3. Injection
- SQL injection prevention (parameterized queries)
- Command injection prevention (don't use eval, exec)
- Template injection prevention (sanitize templates)
- Validate all input

### 4. Insecure Design
- Security by design (not afterthought)
- Threat modeling completed
- Security requirements in specs
- Architecture reviewed for security

### 5. Security Misconfiguration
- No default credentials
- Framework/library security headers enabled
- Debug mode disabled in production
- Security updates applied

### 6. Vulnerable Components
- Dependencies scanned for vulnerabilities
- Regular updates applied
- Known vulnerabilities tracked
- Software composition analysis (SCA) tools used

### 7. Authentication Failures
- Strong password requirements
- Account lockout after failed attempts
- Session timeout implemented
- MFA supported (optional)

### 8. Software & Data Integrity Failures
- Dependencies from trusted sources
- Code integrity verified (signing, checksums)
- Secure deployment pipeline
- Change management process

### 9. Security Logging & Monitoring
- Security events logged (login, failures, changes)
- Logs protected from tampering
- Alerts configured for suspicious activity
- Monitoring/alerting on security events

### 10. SSRF (Server-Side Request Forgery)
- Validate URLs before making requests
- Whitelist allowed domains
- Don't allow localhost/internal IPs
- Block cloud metadata endpoints

## Secure Coding Practices

### Error Messages
- **Never leak internals**: Don't tell attackers if email exists or why
- **Generic messages**: "Invalid credentials" instead of "Email not found"
- **Log details**: Internal error details logged with context, not exposed to user

### Rate Limiting
- **Brute force protection**: Limit login attempts (5 per 15 minutes typical)
- **API rate limiting**: Prevent abuse (requests per second limits)
- **Implement exponential backoff**: Increase delay after failures
- **Lock accounts**: Temporary lockout after too many failures

### Account Enumeration Prevention
- **Same error for invalid email vs. invalid password**: Don't reveal which email exists
- **Same response time**: Prevent timing attacks (password checking time varies)
- **No public user lists**: Don't expose list of valid users

### File Upload Security
- **Whitelist file types**: Only allow expected types (PDF, images, etc.)
- **Scan for malware**: Use antivirus scanning before storing
- **Store outside webroot**: Don't allow direct execution
- **Rename files**: Don't preserve original names
- **Limit file size**: Prevent DoS via huge uploads

### Dependency Security
- **Lock versions**: Use exact versions, not wildcards
- **Audit dependencies**: Regularly check for vulnerabilities
- **Update regularly**: Monthly minimum for security patches
- **Supply chain security**: Use packages from trusted sources

## Compliance Considerations

### Data Protection (GDPR, etc.)
- **Consent**: User must consent to data collection
- **Retention**: Don't store data longer than needed
- **Right to deletion**: Ability to delete user data
- **Data portability**: Export data in standard format

### PII Handling
- **Minimize collection**: Only collect needed data
- **Minimize retention**: Delete when no longer needed
- **Access controls**: Limit who can access PII
- **Data minimization**: Don't expose PII unnecessarily

## Security Testing

### Required Testing
- **Penetration testing**: Professional security assessment
- **OWASP scanning**: Automated scanning for known vulnerabilities
- **Dependency scanning**: Check for vulnerable dependencies
- **Code review**: Security-focused peer review
- **Threat modeling**: Identify attack vectors

### Test Data
- **Sanitize test data**: Remove real PII from test databases
- **Never use production data** in non-production environments
- **Anonymize test data**: Can't be re-identified as real users

## Incident Response

### Security Breach Response
- **Immediate**: Isolate affected systems
- **Investigation**: Determine what was compromised
- **Notification**: Notify affected users
- **Remediation**: Fix vulnerabilities
- **Post-mortem**: Learn and improve

### Reporting Security Issues
- **Responsible disclosure**: Contact security team privately
- **Bug bounty**: Consider bug bounty program
- **Don't patch publicly** before users can update

---

These security rules are mandatory. No exceptions. All code must pass security review before production. Security is everyone's responsibility.
