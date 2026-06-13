// Simple static-credential gate for the public (cloudflared) frontend.
// Credentials come from env (GATE_USER / GATE_PASS), set in .env.
// Session = signed cookie: "<user>.<hmac_sha256(user, GATE_SECRET)>".
import crypto from 'crypto';

function secret() {
    return process.env.GATE_SECRET || 'insecure-default-change-me';
}

function sign(user) {
    return crypto.createHmac('sha256', secret()).update(user).digest('hex');
}

function token(user) {
    return user + '.' + sign(user);
}

function authed(r) {
    var cookie = r.headersIn['Cookie'] || '';
    var m = cookie.match(/(?:^|;\s*)gate_session=([^;]+)/);
    if (!m) return false;
    var raw = decodeURIComponent(m[1]);
    var dot = raw.lastIndexOf('.');
    if (dot < 1) return false;
    var user = raw.substring(0, dot);
    var sig = raw.substring(dot + 1);
    return user === (process.env.GATE_USER || '') && sig === sign(user);
}

function parseForm(body) {
    var out = {};
    (body || '').split('&').forEach(function (pair) {
        var i = pair.indexOf('=');
        if (i < 0) return;
        var k = decodeURIComponent(pair.substring(0, i).replace(/\+/g, ' '));
        var v = decodeURIComponent(pair.substring(i + 1).replace(/\+/g, ' '));
        out[k] = v;
    });
    return out;
}

function page(error) {
    var err = error
        ? '<p class="err">' + error + '</p>'
        : '';
    return '<!doctype html><html lang="en"><head><meta charset="utf-8">' +
        '<meta name="viewport" content="width=device-width,initial-scale=1">' +
        '<title>Sign in</title><style>' +
        '*{box-sizing:border-box}body{margin:0;min-height:100vh;display:flex;' +
        'align-items:center;justify-content:center;font-family:system-ui,sans-serif;' +
        'background:#0f172a;color:#e2e8f0}' +
        '.card{background:#1e293b;padding:2.5rem;border-radius:14px;width:320px;' +
        'box-shadow:0 10px 40px rgba(0,0,0,.4)}' +
        'h1{margin:0 0 1.5rem;font-size:1.35rem;text-align:center}' +
        'label{display:block;font-size:.8rem;margin:0 0 .35rem;color:#94a3b8}' +
        'input{width:100%;padding:.65rem .75rem;margin-bottom:1rem;border-radius:8px;' +
        'border:1px solid #334155;background:#0f172a;color:#e2e8f0;font-size:.95rem}' +
        'input:focus{outline:none;border-color:#6366f1}' +
        'button{width:100%;padding:.7rem;border:0;border-radius:8px;background:#6366f1;' +
        'color:#fff;font-size:.95rem;font-weight:600;cursor:pointer}' +
        'button:hover{background:#4f46e5}' +
        '.err{background:#7f1d1d;color:#fecaca;padding:.55rem .75rem;border-radius:8px;' +
        'font-size:.85rem;margin:0 0 1rem;text-align:center}' +
        '</style></head><body><form class="card" method="POST" action="/login">' +
        '<h1>🔒 Restricted</h1>' + err +
        '<label>Username</label><input name="username" autocomplete="username" autofocus>' +
        '<label>Password</label><input name="password" type="password" autocomplete="current-password">' +
        '<button type="submit">Sign in</button></form></body></html>';
}

function setCookie(r, value, maxAge) {
    // Secure only over HTTPS (the cloudflared tunnel). Plain http://localhost
    // would silently drop a Secure cookie and loop back to /login.
    var https = (r.headersIn['X-Forwarded-Proto'] || '') === 'https';
    r.headersOut['Set-Cookie'] =
        'gate_session=' + value + '; Path=/; HttpOnly; SameSite=Lax; Max-Age=' + maxAge +
        (https ? '; Secure' : '');
}

// Return a 200 HTML page that immediately navigates (meta refresh + JS).
// njs r.return() treats the body arg as the Location header for 3xx codes,
// so a real redirect can't carry a body; a 200 redirect-page works in every
// client, including webviews that don't auto-follow a 302/303 after a POST.
function redirect(r, location) {
    r.headersOut['Content-Type'] = 'text/html; charset=utf-8';
    r.return(200,
        '<!doctype html><meta charset="utf-8">' +
        '<meta http-equiv="refresh" content="0; url=' + location + '">' +
        '<script>location.replace(' + JSON.stringify(location) + ')</script>' +
        '<p>Redirecting to <a href="' + location + '">' + location + '</a>…</p>');
}

// auth_request target: 204 if logged in, 401 otherwise.
function check(r) {
    r.return(authed(r) ? 204 : 401);
}

function login(r) {
    if (r.method === 'GET') {
        if (authed(r)) {
            redirect(r, '/');
            return;
        }
        r.headersOut['Content-Type'] = 'text/html; charset=utf-8';
        r.return(200, page(''));
        return;
    }
    if (r.method === 'POST') {
        var params = parseForm(r.requestText);
        if (params.username === (process.env.GATE_USER || '') &&
            params.password === (process.env.GATE_PASS || '') &&
            process.env.GATE_USER) {
            setCookie(r, encodeURIComponent(token(params.username)), 86400);
            redirect(r, '/');
            return;
        }
        r.headersOut['Content-Type'] = 'text/html; charset=utf-8';
        r.return(401, page('Invalid username or password'));
        return;
    }
    r.return(405);
}

function logout(r) {
    setCookie(r, 'deleted', 0);
    redirect(r, '/login');
}

export default { check, login, logout };
