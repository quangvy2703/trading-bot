"""Nhieu tai khoan: user ngoai dua khoa API, he thong chay MOT BOT RIENG cho ho.

Moi user da duyet la mot tien trinh con chay CHINH app nay (uvicorn app.main:app)
voi kho rieng <USERS_DIR>/u<id>.db va khoa API rieng. Logic giao dich giu nguyen
tung dong, va khong co trang thai nao (RUN_LOCK, cache tai khoan, lech dong ho,
dung an toan) dung chung giua hai tai khoan: dat lenh nham sang tai khoan khac la
loi KHONG THE xay ra, chu khong phai loi hiem.

Tien trinh chinh (admin):
  - so dang ky (bang users trong kho admin); khoa API ma hoa bang APP_SECRET
  - dang nhap (cookie ky HMAC); user chi thay Dieu khien / Tong quan / Nhat ky
    cua CHINH ho — moi /api/... cua user duoc chuyen tiep toi tien trinh cua ho
    theo danh sach cho phep, khong co duong nao cham toi kho admin
  - giu song cac tien trinh con, khoi dong lai khi chet

Tien trinh con: chi nghe 127.0.0.1, doi header X-Worker-Token; doc kho nen va
cau hinh cua admin (MARKET_DB / SETTINGS_DB), chay luot ngay muon hon admin
3 phut de nen vua dong da co san trong kho admin.
"""
from __future__ import annotations

import base64
import hashlib
import io
import hmac
import os
import re
import secrets
import subprocess
import sys
import threading
import time
from pathlib import Path
from urllib.parse import quote

import httpx
from fastapi import APIRouter, Body, HTTPException, Request
from fastapi.responses import FileResponse, JSONResponse, RedirectResponse, Response

from . import db
from .binance import Trader
from .config import CFG

ROOT = Path(__file__).parent.parent
LOGIN_PAGE = Path(__file__).parent / "static" / "login.html"
CONFIRM = "TÔI ĐỒNG Ý CHẠY THẬT"         # trung main.CONFIRM — worker /api/arm doi cau nay
COOKIE = "sess"
SESSION_S = 14 * 86_400
PRE = "mfa"                 # cookie buoc 2: mat khau da dung, chua nhap ma TOTP
PRE_S = 300
NAME_OK = re.compile(r"^[a-z0-9][a-z0-9_.-]{2,31}$")
STATUS = ("pending", "active", "disabled")
MAX_PENDING = 50

SCHEMA = """
CREATE TABLE IF NOT EXISTS users(
  id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT UNIQUE, pw TEXT,
  api_key TEXT, api_secret TEXT, key_fp TEXT UNIQUE, key_hint TEXT,
  status TEXT, start_equity REAL, created INTEGER, approved INTEGER, note TEXT,
  mfa TEXT);
"""


def auth_on() -> bool:
    """Dang nhap bat khi co ADMIN_PASSWORD (va day khong phai bot cua user)."""
    return bool(CFG.admin_password) and not CFG.worker_token


def users_on() -> bool:
    """Dang ky user can them APP_SECRET de ma hoa khoa API."""
    return auth_on() and bool(CFG.app_secret)


def init() -> None:
    if not auth_on():
        return
    with db.tx() as cx:
        cx.executescript(SCHEMA)
        if "mfa" not in [r[1] for r in cx.execute("PRAGMA table_info(users)")]:
            cx.execute("ALTER TABLE users ADD COLUMN mfa TEXT")
    if os.environ.get("ADMIN_MFA_RESET", "") in ("1", "true", "yes"):
        # admin mat may xac thuc: dat bien nay, khoi dong lai, gan lai roi BO bien
        db.kv_set("admin_mfa", None)
        db.log("warn", "ADMIN_MFA_RESET: đã xoá MFA của admin — lần đăng nhập tới phải gắn lại")
    Path(CFG.users_dir).mkdir(parents=True, exist_ok=True)


# ---------------------------------------------------------------- ma hoa
# Khong co thu vien ma hoa trong anh: dung HMAC-SHA256 lam PRF o che do dem
# (CTR) + HMAC tren ban ma (encrypt-then-MAC). Khoa lay tu APP_SECRET, khong
# nam trong kho — ban sao live.db khong lo khoa API cua user.
def _k(label: str) -> bytes:
    # chua co APP_SECRET (chi admin, chua co user) thi khoa lay tu ADMIN_PASSWORD
    k = CFG.app_secret or f"pw|{CFG.admin_password}"
    return hmac.new(k.encode(), label.encode(), hashlib.sha256).digest()


def _stream(nonce: bytes, n: int) -> bytes:
    k, out, i = _k("enc"), b"", 0
    while len(out) < n:
        out += hmac.new(k, nonce + i.to_bytes(4, "big"), hashlib.sha256).digest()
        i += 1
    return out[:n]


def seal(s: str) -> str:
    nonce, b = os.urandom(16), s.encode()
    ct = bytes(x ^ y for x, y in zip(b, _stream(nonce, len(b))))
    tag = hmac.new(_k("mac"), nonce + ct, hashlib.sha256).digest()[:16]
    return base64.urlsafe_b64encode(nonce + ct + tag).decode()


def unseal(t: str) -> str:
    raw = base64.urlsafe_b64decode(t.encode())
    nonce, ct, tag = raw[:16], raw[16:-16], raw[-16:]
    if not hmac.compare_digest(tag, hmac.new(_k("mac"), nonce + ct, hashlib.sha256).digest()[:16]):
        raise RuntimeError("khoá API trong sổ không giải mã được — APP_SECRET đã đổi?")
    return bytes(x ^ y for x, y in zip(ct, _stream(nonce, len(ct)))).decode()


def _pw_hash(pw: str, salt: bytes | None = None) -> str:
    salt = salt or os.urandom(16)
    h = hashlib.pbkdf2_hmac("sha256", pw.encode(), salt, 200_000)
    return f"pbkdf2${salt.hex()}${h.hex()}"


def _pw_ok(pw: str, stored: str) -> bool:
    try:
        _, salt, _h = stored.split("$")
        return hmac.compare_digest(_pw_hash(pw, bytes.fromhex(salt)), stored)
    except Exception:
        return False


# ---------------------------------------------------------------- so user
def _rows(sql: str, *a) -> list:
    cx = db.connect()
    try:
        return [dict(r) for r in cx.execute(sql, a)]
    finally:
        cx.close()


def get(uid: int) -> dict | None:
    r = _rows("SELECT * FROM users WHERE id=?", uid)
    return r[0] if r else None


def keys_of(u: dict) -> tuple[str, str]:
    return unseal(u["api_key"]), unseal(u["api_secret"])


def _fp(key: str) -> str:
    return hashlib.sha256(key.strip().encode()).hexdigest()


def _check_keys(key: str, secret: str) -> float:
    """Kiem khoa tren san TRUOC khi nhan: doc duoc tai khoan, co quyen giao dich,
    che do MOT CHIEU. Tra so du vi (USDT) lam von ban dau."""
    t = None
    try:
        t = Trader(key, secret)
        a = t.account()
        if a.get("canTrade") is False:
            raise ValueError("khoá API chưa bật quyền giao dịch Futures")
        if t.dual_side():
            raise ValueError("tài khoản đang ở chế độ HAI CHIỀU (Hedge) — đổi ở Binance Futures → "
                             "Preferences → Position Mode → One-way rồi đăng ký lại")
        return float(a.get("totalWalletBalance", 0) or 0)
    except ValueError:
        raise
    except Exception as e:
        why = str(e)
        if "-2015" in why or "-2014" in why or "401" in why[:4]:
            ip = re.search(r"request ip: ([0-9a-fA-F.:]+)", why)
            raise ValueError("Binance từ chối khoá API — kiểm tra key/secret, quyền Futures và danh sách IP"
                             + (f" (IP máy chủ: {ip.group(1)})" if ip else ""))
        raise ValueError(f"không đọc được tài khoản: {why[:200]}")
    finally:
        if t is not None:
            t.close()


_REG: list = []             # moc goi dang ky — trang cong khai, moi lan goi Binance


def register(name: str, pw: str, key: str, secret: str) -> dict:
    name, key, secret = (name or "").strip().lower(), (key or "").strip(), (secret or "").strip()
    if not users_on():
        raise ValueError("hệ thống chưa mở đăng ký (thiếu APP_SECRET)")
    # Khoa sai lien tuc ton trong so IP cua MAY CHU tren Binance (ca bot chinh).
    now = time.time()
    _REG[:] = [x for x in _REG if now - x < 600]
    if len(_REG) >= 10:
        raise ValueError("quá nhiều lượt đăng ký — thử lại sau 10 phút")
    _REG.append(now)
    if not NAME_OK.match(name) or name == "admin":
        raise ValueError("tên đăng nhập 3–32 ký tự: chữ thường, số, . _ -")
    if len(pw or "") < 8:
        raise ValueError("mật khẩu tối thiểu 8 ký tự")
    if len(key) < 16 or len(secret) < 16:
        raise ValueError("thiếu API key / secret")
    fp = _fp(key)
    if CFG.api_key and fp == _fp(CFG.api_key):
        # hai bot tren mot tai khoan se dong / mo chong lenh cua nhau
        raise ValueError("khoá này là tài khoản của bot chính")
    if _rows("SELECT 1 FROM users WHERE name=?", name):
        raise ValueError("tên đăng nhập đã có người dùng")
    if _rows("SELECT 1 FROM users WHERE key_fp=?", fp):
        raise ValueError("khoá API này đã được đăng ký")
    if _rows("SELECT COUNT(*) AS n FROM users WHERE status='pending'")[0]["n"] >= MAX_PENDING:
        raise ValueError("đang có quá nhiều đăng ký chờ duyệt — thử lại sau")
    wallet = _check_keys(key, secret)
    with db.tx() as cx:
        uid = cx.execute(
            "INSERT INTO users(name,pw,api_key,api_secret,key_fp,key_hint,status,start_equity,created)"
            " VALUES(?,?,?,?,?,?,?,?,?)",
            (name, _pw_hash(pw), seal(key), seal(secret), fp, f"{key[:4]}…{key[-4:]}",
             "pending", wallet, int(time.time() * 1000))).lastrowid
    db.log("warn", f"user mới đăng ký: {name} (#{uid}) · số dư {wallet:,.2f} USDT · chờ duyệt")
    return {"id": uid, "name": name, "status": "pending"}


def _set(uid: int, **kw) -> None:
    with db.tx() as cx:
        cx.execute(f"UPDATE users SET {', '.join(k + '=?' for k in kw)} WHERE id=?", (*kw.values(), uid))


# ---------------------------------------------------------------- MFA (TOTP)
# RFC 6238: SHA1, 6 so, buoc 30 giay — Google Authenticator, Authy, 1Password...
# Bat buoc voi moi tai khoan khi bat dang nhap (MFA=0 de tat). Bi mat TOTP luu
# ma hoa (seal): cua admin o kv «admin_mfa», cua user o cot users.mfa.
def mfa_on() -> bool:
    return auth_on() and os.environ.get("MFA", "1") not in ("0", "false", "no")


def _totp(secret: str, step: int) -> str:
    k = base64.b32decode(secret + "=" * (-len(secret) % 8))
    h = hmac.new(k, step.to_bytes(8, "big"), hashlib.sha1).digest()
    o = h[-1] & 15
    return f"{(int.from_bytes(h[o:o + 4], 'big') & 0x7FFFFFFF) % 1_000_000:06d}"


_USED: dict = {}            # uid -> buoc 30 giay da dung gan nhat — mot ma khong dung lai duoc


def _totp_ok(uid: int, secret: str, code: str) -> bool:
    code = re.sub(r"\s", "", code or "")
    if not re.fullmatch(r"\d{6}", code):
        return False
    now = int(time.time()) // 30
    for st in (now - 1, now, now + 1):        # lech dong ho dien thoai +-30 giay
        if st > _USED.get(uid, -1) and hmac.compare_digest(_totp(secret, st), code):
            _USED[uid] = st
            return True
    return False


def mfa_secret(uid: int) -> str | None:
    v = db.kv_get("admin_mfa") if uid == 0 else (get(uid) or {}).get("mfa")
    if not v:
        return None
    try:
        return unseal(v)
    except RuntimeError:
        # khoa doi (APP_SECRET / ADMIN_PASSWORD): KHONG coi nhu chua gan — do la
        # ha cap im lang. Admin dat lai (user) hoac ADMIN_MFA_RESET=1 (admin).
        raise ValueError("không giải mã được MFA của tài khoản này — "
                         + ("khởi động lại với ADMIN_MFA_RESET=1" if uid == 0 else "liên hệ admin để đặt lại"))


def _mfa_save(uid: int, secret: str | None) -> None:
    v = seal(secret) if secret else None
    if uid == 0:
        db.kv_set("admin_mfa", v)
    else:
        _set(uid, mfa=v)
    _USED.pop(uid, None)


def _qr_svg(uri: str) -> str | None:
    try:
        import segno
    except ImportError:
        return None                        # thieu thu vien: trang hien khoa de go tay
    b = io.BytesIO()
    segno.make(uri, error="m").save(b, kind="svg", scale=5, border=2, xmldecl=False,
                                    svgns=True, dark="#2A2340")
    return b.getvalue().decode()


_SETUP: dict = {}           # uid -> (bi mat dang gan, het han) — chi luu khi nhap dung ma


def mfa_setup(uid: int, name: str) -> dict:
    sec, exp = _SETUP.get(uid, (None, 0))
    if not sec or exp < time.time():
        sec = base64.b32encode(os.urandom(20)).decode().rstrip("=")
    _SETUP[uid] = (sec, time.time() + PRE_S)
    uri = (f"otpauth://totp/{quote('Quản lý chạy thật')}:{quote(name)}?secret={sec}"
           f"&issuer={quote('Quản lý chạy thật')}&digits=6&period=30")
    return {"mfa": "setup", "secret": sec, "uri": uri, "qr": _qr_svg(uri)}


# ---------------------------------------------------------------- phien
def _sess_key(kind: str = "sess2") -> bytes:
    # Doi ADMIN_PASSWORD hay APP_SECRET la moi phien cu het hieu luc. «sess2»:
    # phien cap truoc khi co MFA cung het.
    return hashlib.sha256(f"{kind}|{CFG.app_secret}|{CFG.admin_password}".encode()).digest()


def _token(uid: int, kind: str = "sess2", age: int = SESSION_S) -> str:
    p = f"{uid}.{int(time.time()) + age}"
    return p + "." + hmac.new(_sess_key(kind), p.encode(), hashlib.sha256).hexdigest()[:32]


def _uid_of(t: str, kind: str = "sess2") -> int | None:
    try:
        uid, exp, sig = (t or "").split(".")
        ok = hmac.compare_digest(sig, hmac.new(_sess_key(kind), f"{uid}.{exp}".encode(),
                                               hashlib.sha256).hexdigest()[:32])
        return int(uid) if ok and int(exp) >= time.time() else None
    except ValueError:
        return None


def session(request: Request) -> dict | None:
    """{"role": "admin"} | {"role": "user", **dong users} | None."""
    uid = _uid_of(request.cookies.get(COOKIE))
    if uid is None:
        return None
    if int(uid) == 0:
        return {"role": "admin", "id": 0, "name": "admin"}
    u = get(int(uid))
    return {"role": "user", **u} if u else None


def me(request: Request) -> dict | None:
    """Thong tin nhung vao trang (khong co khoa / mat khau)."""
    if not auth_on():
        return None
    s = session(request)
    if not s:
        return None
    out = {"role": s["role"], "id": s["id"], "name": s["name"], "users": users_on()}
    if s["role"] == "user":
        out["status"] = s["status"]
    elif (v := request.query_params.get("u")) and v.isdigit() and (u := get(int(v))):
        out["viewing"] = {"id": u["id"], "name": u["name"], "status": u["status"]}
    return out


_FAILS: dict = {}           # ten -> [moc that bai] — chan do mat khau


def login(name: str, pw: str) -> tuple[int, dict]:
    name = (name or "").strip().lower()
    now = time.time()
    f = [x for x in _FAILS.get(name, []) if now - x < 900]
    if len(f) >= 10:
        raise ValueError("sai quá nhiều lần — đợi 15 phút")
    if name == "admin":
        ok, uid, info = hmac.compare_digest((pw or "").encode(), CFG.admin_password.encode()), 0, {"role": "admin"}
    else:
        u = _rows("SELECT * FROM users WHERE name=?", name)
        ok = bool(u) and _pw_ok(pw or "", u[0]["pw"])
        uid, info = (u[0]["id"], {"role": "user", "status": u[0]["status"]}) if u else (-1, {})
    if not ok:
        _FAILS[name] = f + [now]
        time.sleep(0.6)
        raise ValueError("sai tên đăng nhập hoặc mật khẩu")
    _FAILS.pop(name, None)
    return uid, {**info, "name": name}


def mfa_check(uid: int, code: str, setup: bool) -> None:
    """Buoc 2. Sai ma tinh chung han muc 10 lan / 15 phut voi mat khau."""
    key = f"#{uid}"
    now = time.time()
    f = [x for x in _FAILS.get(key, []) if now - x < 900]
    if len(f) >= 10:
        raise ValueError("sai quá nhiều lần — đợi 15 phút")
    if setup:
        if mfa_secret(uid):
            raise ValueError("tài khoản đã gắn MFA")
        sec, exp = _SETUP.get(uid, (None, 0))
        if not sec or exp < now:
            raise ValueError("hết hạn gắn MFA — đăng nhập lại")
    else:
        sec = mfa_secret(uid)
        if not sec:
            raise ValueError("tài khoản chưa gắn MFA — đăng nhập lại")
    if not _totp_ok(uid, sec, code):
        _FAILS[key] = f + [now]
        time.sleep(0.6)
        raise ValueError("mã xác thực không đúng (hoặc đã dùng) — kiểm giờ trên điện thoại")
    _FAILS.pop(key, None)
    if setup:
        _mfa_save(uid, sec)
        _SETUP.pop(uid, None)
        db.log("warn", f"gắn MFA cho {'admin' if uid == 0 else f'user #{uid}'}")


# ---------------------------------------------------------------- tien trinh con
_PROCS: dict = {}           # uid -> {"p": Popen, "port", "token", "since", "fails", "next"}
_PL = threading.RLock()
_STRIP = ("ADMIN_PASSWORD", "APP_SECRET", "NEWS_API_KEY", "NEWS_API_SECRET", "TUNNEL_TOKEN",
          "WORKER_TOKEN", "MARKET_DB", "SETTINGS_DB")


def _port(uid: int) -> int:
    return CFG.worker_port0 + uid


def db_file(uid: int) -> Path:
    return Path(CFG.users_dir) / f"u{uid}.db"


def _run_at(delay_min: int = 3) -> str:
    """Luot ngay cua bot user: muon hon admin vai phut — admin tai nen truoc."""
    hh, _, mm = CFG.run_at_utc.partition(":")
    t = (int(hh) * 60 + int(mm or 0) + delay_min) % 1440
    return f"{t // 60:02d}:{t % 60:02d}"


def _pdeathsig() -> None:
    """Tien trinh chinh chet (ke ca bi kill -9) thi bot con chet theo: khong de
    lai bot mo coi giu cong ma tien trinh moi khong noi duoc."""
    try:
        import ctypes
        ctypes.CDLL("libc.so.6").prctl(1, 15)      # PR_SET_PDEATHSIG, SIGTERM
    except Exception:
        pass


def _alive(uid: int) -> dict | None:
    w = _PROCS.get(uid)
    return w if w and w["p"].poll() is None else None


def start(uid: int) -> None:
    with _PL:
        if _alive(uid):
            return
        u = get(uid)
        if not u or u["status"] != "active":
            return
        key, secret = keys_of(u)
        token = secrets.token_urlsafe(24)
        env = {k: v for k, v in os.environ.items() if k not in _STRIP}
        env.update(DB_PATH=str(db_file(uid)), BINANCE_API_KEY=key, BINANCE_API_SECRET=secret,
                   START_EQUITY_USD=f"{float(u['start_equity'] or 0):.2f}",
                   WORKER_TOKEN=token, MARKET_DB=CFG.db_path, SETTINGS_DB=CFG.db_path,
                   RUN_AT_UTC=_run_at(),
                   # so giay / tin chi chay o bot chinh — chung khong dat lenh, chay lai la thua
                   NEWS_PAPER="0", VSA_PAPER="0", CRASH_PAPER="0", C13_PAPER="0")
        Path(CFG.users_dir).mkdir(parents=True, exist_ok=True)
        lp = Path(CFG.users_dir) / f"u{uid}.log"
        if lp.exists() and lp.stat().st_size > 5_000_000:
            lp.replace(lp.with_suffix(".log.1"))
        p = subprocess.Popen(
            [sys.executable, "-m", "uvicorn", "app.main:app", "--host", "127.0.0.1",
             "--port", str(_port(uid)), "--log-level", "warning"],
            env=env, cwd=str(ROOT), stdout=open(lp, "ab"), stderr=subprocess.STDOUT,
            preexec_fn=_pdeathsig if sys.platform.startswith("linux") else None)
        prev = _PROCS.get(uid) or {}
        _PROCS[uid] = {"p": p, "port": _port(uid), "token": token, "since": time.time(),
                       "fails": prev.get("fails", 0), "next": 0.0}
        db.log("info", f"khởi động bot của {u['name']} (#{uid}) · cổng {_port(uid)} · pid {p.pid}")


def stop(uid: int) -> None:
    with _PL:
        w = _PROCS.pop(uid, None)
    if not w or w["p"].poll() is not None:
        return
    w["p"].terminate()
    try:
        w["p"].wait(15)
    except subprocess.TimeoutExpired:
        w["p"].kill()


def stop_all() -> None:
    for uid in list(_PROCS):
        stop(uid)


def _supervise() -> None:
    """Moi 20 giay: bot cua user dang hoat dong ma chet thi dung lai (gian cach
    tang dan toi 5 phut — bot chet ngay khi khoi dong thi khong quay vong)."""
    while True:
        try:
            for u in _rows("SELECT id, name FROM users WHERE status='active'"):
                w = _PROCS.get(u["id"])
                if _alive(u["id"]):
                    if w and time.time() - w["since"] > 600:
                        w["fails"] = 0
                    continue
                if w and time.time() < w["next"]:
                    continue
                if w:
                    w["fails"] += 1
                    w["next"] = time.time() + min(300, 10 * 2 ** w["fails"])
                    db.log("error", f"bot của {u['name']} (#{u['id']}) đã dừng (mã {w['p'].poll()}) — "
                                    f"khởi động lại · xem {CFG.users_dir}/u{u['id']}.log")
                start(u["id"])
        except Exception as e:
            db.log("error", f"giám sát bot user lỗi: {e}")
        time.sleep(20)


def start_all() -> None:
    if not users_on():
        return
    for u in _rows("SELECT id FROM users WHERE status='active'"):
        try:
            start(u["id"])
        except Exception as e:
            db.log("error", f"khởi động bot user #{u['id']} lỗi: {e}")
    threading.Thread(target=_supervise, daemon=True, name="users").start()


def _wait_up(uid: int, secs: float = 45) -> dict:
    t_end = time.time() + secs
    while time.time() < t_end:
        w = _alive(uid)
        if not w:
            break
        try:
            if httpx.get(f"http://127.0.0.1:{w['port']}/healthz", timeout=2).status_code == 200:
                return w
        except httpx.HTTPError:
            pass
        time.sleep(0.5)
    raise RuntimeError("bot của user không khởi động được — xem nhật ký u<id>.log")


def call(uid: int, method: str, path: str, body: dict | None = None, timeout: float = 30) -> dict:
    """Goi API cua bot user tu tien trinh chinh (dong bo)."""
    w = _alive(uid)
    if not w:
        raise RuntimeError("bot của tài khoản này đang không chạy")
    r = httpx.request(method, f"http://127.0.0.1:{w['port']}{path}", json=body, timeout=timeout,
                      headers={"X-Worker-Token": w["token"]})
    j = r.json() if r.content else {}
    if r.status_code >= 400:
        raise RuntimeError(j.get("detail") or j.get("error") or r.text[:200])
    return j


_AC: dict = {"c": None}


async def proxy(request: Request, uid: int, path: str) -> Response:
    w = _alive(uid)
    if not w:
        return JSONResponse({"error": "bot của tài khoản này đang không chạy"}, status_code=503)
    if _AC["c"] is None:
        _AC["c"] = httpx.AsyncClient(timeout=httpx.Timeout(120, connect=3))
    try:
        r = await _AC["c"].request(
            request.method, f"http://127.0.0.1:{w['port']}{path}", params=request.query_params,
            content=await request.body(),
            headers={"X-Worker-Token": w["token"],
                     "Content-Type": request.headers.get("content-type", "application/json")})
    except httpx.HTTPError as e:
        return JSONResponse({"error": f"bot của tài khoản không trả lời: {e}"}, status_code=502)
    return Response(r.content, status_code=r.status_code,
                    media_type=r.headers.get("content-type", "application/json"))


# ---------------------------------------------------------------- chan quyen
PUBLIC = {"/healthz", "/login", "/api/auth/me", "/api/auth/login", "/api/auth/register",
          "/api/auth/logout", "/api/auth/mfa"}
# User chi doc duoc so cua CHINH ho (Dieu khien / Tong quan / Nhat ky) va tu dung khan.
USER_GET = {"/api/state", "/api/overview", "/api/vsbt", "/api/account", "/api/exits", "/api/equity",
            "/api/candidates"}
USER_POST = {"/api/flatten"}
VIEW = re.compile(r"^/u/(\d+)(/api/[a-z0-9/_-]+)$")


async def gate(request: Request, call_next):
    path = request.url.path
    if CFG.worker_token:
        # bot cua user: chi tien trinh chinh (biet token) duoc goi
        tok = request.headers.get("x-worker-token", "")
        if path == "/healthz" or hmac.compare_digest(tok.encode(), CFG.worker_token.encode()):
            return await call_next(request)
        return JSONResponse({"error": "forbidden"}, status_code=403)
    if not auth_on():
        return await call_next(request)               # che do cu: mot tai khoan, khong dang nhap
    # Chong CSRF: moi yeu cau ghi phai la JSON (form cua trang khac khong gui duoc
    # application/json ma khong qua CORS) va cookie SameSite=Lax.
    if request.method not in ("GET", "HEAD") and \
            "application/json" not in request.headers.get("content-type", ""):
        return JSONResponse({"error": "yêu cầu phải là JSON"}, status_code=415)
    if path in PUBLIC:
        return await call_next(request)
    s = session(request)
    api = path.startswith("/api/") or path.startswith("/u/")
    if s is None:
        return (JSONResponse({"error": "chưa đăng nhập"}, status_code=401) if api
                else RedirectResponse("/login"))
    if s["role"] == "admin":
        m = VIEW.match(path)
        if m:
            return await proxy(request, int(m[1]), m[2])
        return await call_next(request)
    if s["status"] != "active":
        return (JSONResponse({"error": "tài khoản chưa được duyệt"}, status_code=403) if api
                else RedirectResponse("/login"))
    if path == "/":
        return await call_next(request)
    if (request.method == "GET" and path in USER_GET) or (request.method == "POST" and path in USER_POST):
        return await proxy(request, s["id"], path)
    return JSONResponse({"error": "không có quyền"}, status_code=403)


# ---------------------------------------------------------------- API
router = APIRouter()


def _cookie(resp: Response, request: Request, value: str, age: int, name: str = COOKIE) -> None:
    resp.set_cookie(name, value, max_age=age, httponly=True, samesite="lax", path="/",
                    secure=request.headers.get("x-forwarded-proto") == "https"
                    or request.url.scheme == "https")


@router.get("/login")
def login_page():
    return FileResponse(LOGIN_PAGE, media_type="text/html")


@router.get("/api/auth/me")
def auth_me(request: Request):
    return {"auth": auth_on(), "users": users_on(), "mfa": mfa_on(), "me": me(request)}


def _signed_in(request: Request, uid: int, name: str) -> JSONResponse:
    """Mat khau dung: khong bat MFA thi cap phien luon; bat thi chi cap cookie
    buoc 2 (5 phut) — doi ma TOTP (hoac gan MFA lan dau) moi co phien."""
    if not mfa_on():
        resp = JSONResponse({"ok": True})
        _cookie(resp, request, _token(uid), SESSION_S)
        return resp
    try:
        has = bool(mfa_secret(uid))
    except ValueError as e:
        raise HTTPException(400, str(e))
    resp = JSONResponse({"ok": True, **({"mfa": "code"} if has else mfa_setup(uid, name))})
    _cookie(resp, request, _token(uid, "pre", PRE_S), PRE_S, PRE)
    _cookie(resp, request, "", 0)
    return resp


@router.post("/api/auth/login")
def auth_login(request: Request, body: dict = Body(...)):
    if not auth_on():
        raise HTTPException(400, "chưa bật đăng nhập (thiếu ADMIN_PASSWORD)")
    try:
        uid, info = login(body.get("name"), body.get("password"))
    except ValueError as e:
        raise HTTPException(400, str(e))
    return _signed_in(request, uid, info["name"])


@router.post("/api/auth/mfa")
def auth_mfa(request: Request, body: dict = Body(...)):
    uid = _uid_of(request.cookies.get(PRE), "pre")
    if uid is None:
        raise HTTPException(401, "hết phiên xác thực — đăng nhập lại")
    try:
        mfa_check(uid, str(body.get("code") or ""), bool(body.get("setup")))
    except ValueError as e:
        raise HTTPException(400, str(e))
    resp = JSONResponse({"ok": True})
    _cookie(resp, request, _token(uid), SESSION_S)
    _cookie(resp, request, "", 0, PRE)
    return resp


@router.post("/api/auth/logout")
def auth_logout(request: Request):
    resp = JSONResponse({"ok": True})
    _cookie(resp, request, "", 0)
    _cookie(resp, request, "", 0, PRE)
    return resp


@router.post("/api/auth/register")
def auth_register(request: Request, body: dict = Body(...)):
    try:
        u = register(body.get("name"), body.get("password"), body.get("api_key"), body.get("api_secret"))
    except ValueError as e:
        raise HTTPException(400, str(e))
    return _signed_in(request, u["id"], u["name"])


def _admin(request: Request) -> None:
    if not users_on():
        raise HTTPException(400, "chưa bật nhiều tài khoản (cần ADMIN_PASSWORD và APP_SECRET)")
    s = session(request)
    if not s or s["role"] != "admin":
        raise HTTPException(403, "chỉ admin")


def _need(uid: int) -> dict:
    u = get(uid)
    if not u:
        raise HTTPException(404, "không có tài khoản này")
    return u


def _summary(uid: int) -> dict | None:
    try:
        return call(uid, "GET", "/api/summary", timeout=5)
    except Exception as e:
        return {"err": str(e)[:200]}


@router.get("/api/users")
def users_list(request: Request):
    _admin(request)
    rows = _rows("SELECT id, name, key_hint, status, start_equity, created, approved, note, "
                 "mfa IS NOT NULL AS mfa FROM users ORDER BY id")
    out = [None] * len(rows)

    def one(i, u):
        w = _alive(u["id"])
        out[i] = {**u, "running": bool(w), "port": _port(u["id"]),
                  "pid": w["p"].pid if w else None,
                  "summary": _summary(u["id"]) if w else None}
    th = [threading.Thread(target=one, args=(i, u)) for i, u in enumerate(rows)]
    for t in th:
        t.start()
    for t in th:
        t.join()
    return {"rows": out, "run_at": _run_at()}


@router.post("/api/users/{uid}/approve")
def users_approve(uid: int, request: Request, body: dict = Body(default={})):
    """Duyet = von ban dau lay theo so du hien tai, khoi dong bot, bat chay that."""
    _admin(request)
    u = _need(uid)
    if u["status"] != "pending":
        raise HTTPException(400, "tài khoản không ở trạng thái chờ duyệt")
    try:
        wallet = _check_keys(*keys_of(u))
    except ValueError as e:
        raise HTTPException(400, str(e))
    _set(uid, status="active", start_equity=wallet, approved=int(time.time() * 1000))
    db.log("warn", f"duyệt user {u['name']} (#{uid}) · vốn ban đầu {wallet:,.2f} USDT")
    return _arm_after_start(uid, u["name"], bool(body.get("arm", True)))


def _arm_after_start(uid: int, name: str, arm: bool) -> dict:
    try:
        start(uid)
        _wait_up(uid)
    except Exception as e:
        raise HTTPException(500, f"đã duyệt nhưng bot chưa chạy: {e}")
    if not arm:
        return {"ok": True, "armed": False}
    try:
        # lan dau bot dang chep kho nen tu kho admin (giu khoa ghi) — cho lau
        call(uid, "POST", "/api/arm", {"on": True, "confirm": CONFIRM}, timeout=240)
    except Exception as e:
        db.log("error", f"bot của {name} chạy SỔ GIẤY — bật chạy thật lỗi: {e}")
        return {"ok": True, "armed": False, "why": str(e)}
    return {"ok": True, "armed": True}


@router.post("/api/users/{uid}/arm")
def users_arm(uid: int, request: Request, body: dict = Body(...)):
    _admin(request)
    u = _need(uid)
    on = bool(body.get("on"))
    try:
        r = call(uid, "POST", "/api/arm", {"on": on, "confirm": CONFIRM if on else ""})
    except RuntimeError as e:
        raise HTTPException(400, str(e))
    db.log("warn", f"công tắc chạy thật của {u['name']} (#{uid}): {'BẬT' if on else 'TẮT'}")
    return r


@router.post("/api/users/{uid}/disable")
def users_disable(uid: int, request: Request):
    """Khoa: tat cong tac roi dung bot. Vi the dang mo VAN NAM TREN SAN (kem dung
    an toan) — muon dong het thi «Dừng khẩn» truoc."""
    _admin(request)
    u = _need(uid)
    try:
        call(uid, "POST", "/api/arm", {"on": False})
    except Exception:
        pass
    stop(uid)
    _set(uid, status="disabled")
    db.log("warn", f"khoá user {u['name']} (#{uid}) · bot đã dừng")
    return {"ok": True}


@router.post("/api/users/{uid}/enable")
def users_enable(uid: int, request: Request):
    """Mo lai: chay tiep so cu (von ban dau giu nguyen); cong tac chay that van TAT."""
    _admin(request)
    u = _need(uid)
    if u["status"] != "disabled":
        raise HTTPException(400, "chỉ mở lại được tài khoản đã khoá")
    _set(uid, status="active")
    db.log("warn", f"mở lại user {u['name']} (#{uid})")
    return _arm_after_start(uid, u["name"], False)


@router.post("/api/users/{uid}/mfa-reset")
def users_mfa_reset(uid: int, request: Request):
    """User mat dien thoai: xoa MFA, lan dang nhap toi (dung mat khau) gan lai."""
    _admin(request)
    u = _need(uid)
    _mfa_save(uid, None)
    db.log("warn", f"đặt lại MFA của {u['name']} (#{uid})")
    return {"ok": True}


@router.post("/api/users/{uid}/delete")
def users_delete(uid: int, request: Request):
    _admin(request)
    u = _need(uid)
    if u["status"] == "active":
        raise HTTPException(400, "khoá tài khoản trước khi xoá")
    stop(uid)
    with db.tx() as cx:
        cx.execute("DELETE FROM users WHERE id=?", (uid,))
    f = db_file(uid)
    for x in (f, Path(str(f) + "-wal"), Path(str(f) + "-shm")):
        if x.exists():
            # giu lai so (doi ten) — xoa user khong xoa lich su giao dich
            x.replace(x.with_name(x.name + f".deleted-{int(time.time())}"))
    db.log("warn", f"xoá user {u['name']} (#{uid})")
    return {"ok": True}


def worker_summary() -> dict:
    """Tom tat cho bang «Người dùng» — chay TRONG bot cua user (main.py /api/summary)."""
    from . import executor, runner
    ready, why = executor.live_ready()
    m = runner.mode()
    op = _rows("SELECT COUNT(*) AS n, COALESCE(SUM(notional), 0) AS g FROM positions "
               "WHERE open=1 AND mode=?", m)[0]
    snap = _rows("SELECT ts, wallet, upnl FROM acct_snap ORDER BY ts DESC LIMIT 1")
    return {"mode": m, "armed": executor.live_armed(), "ready": ready, "why": why,
            "last_run": db.kv_get("last_run"), "n_open": op["n"], "gross": op["g"],
            "wallet": snap[0]["wallet"] if snap else None,
            "equity": (snap[0]["wallet"] + snap[0]["upnl"]) if snap else None,
            "snap_ts": snap[0]["ts"] if snap else None,
            "start_equity": CFG.start_equity, "run_at": CFG.run_at_utc,
            "seeded": bool(db.kv_get("seeded"))}
