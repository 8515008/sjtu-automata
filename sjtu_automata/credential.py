from time import sleep
from time import time
from getpass import getpass

import requests
from PIL import Image
from requests.adapters import HTTPAdapter
from requests.exceptions import RequestException
from tenacity import retry, retry_if_exception_type, wait_fixed

from sjtu_automata.autocaptcha import autocaptcha
from sjtu_automata.utils import (re_search, get_timestamp)
from sjtu_automata.utils.exceptions import (RetryRequest, AutomataError)


import json
import time
import threading
import websocket
import requests
from PIL import Image
from io import BytesIO

HOST = "jaccount.sjtu.edu.cn"
WS_URL = None
QR_BASE_URL = None

# JS-equivalent flags
hasSub = False
subFailed = False
# Stop flag for connect_websocket loop
_stop_sub = threading.Event()


def _create_session():
    session = requests.Session()
    session.headers = {'Referer':'https://jaccount.sjtu.edu.cn'}
    session.mount('http://', HTTPAdapter(max_retries=3))
    session.mount('https://', HTTPAdapter(max_retries=3))
    # session.verify = False    # WARNING! Only use it in Debug mode!
    return session


@retry(retry=retry_if_exception_type(RequestException), wait=wait_fixed(3))
def _get_login_page(session, url):
    # return page text
    req = session.get(url)
    # if last login exists, it will go to error page. so ignore it
    if '<div id="login-form" class="login-card">' in req.text:
        return req.text
    else:
        raise RetryRequest  # make it retry


@retry(retry=retry_if_exception_type(RequestException), wait=wait_fixed(3))
def _bypass_captcha(session, url, useocr):
    # return captcha code
    captcha = session.get(url)
    with open('captcha.jpeg', 'wb') as f:
        f.write(captcha.content)

    if useocr:
        code = autocaptcha('captcha.jpeg').strip()
        if not code.isalpha():
            code = '1234'   # cant recongnize, go for next round
    else:
        img = Image.open('captcha.jpeg')
        img.show()
        code = input('Input the code(captcha.jpeg): ')

    return code


@retry(retry=retry_if_exception_type(RequestException), wait=wait_fixed(3))
def _login(session, sid, returl, se, client, username, password, code, uuid):
    # return 0 suc, 1 wrong credential, 2 code error, 3 30s ban
    data = {'sid': sid, 'returl': returl, 'se': se, 'client': client, 'user': username,
            'pass': password, 'captcha': code, 'v': '', 'uuid': uuid}
    req = session.post(
        'https://jaccount.sjtu.edu.cn/jaccount/ulogin', data=data)

    # result
    # be careful return english version website in english OS
    if '请正确填写验证码' in req.text or 'wrong captcha' in req.text:
        return 2
    elif '请正确填写你的用户名和密码' in req.text or 'wrong username or password' in req.text:
        return 16
    elif '30秒后' in req.text:  # 30s ban
        return 3
    elif '<img id="qr-img"' in req.text:
        # Extract UUID from javascript: socketUrl +="/jaccount/sub" + <UUID>
        uuid_ws = re_search(r'socketUrl\s*\+=\s*"/jaccount/sub/?([0-9a-fA-F\-]{36})"', req.text) \
                  or re_search(r'/jaccount/sub/?([0-9a-fA-F\-]{36})', req.text)
        if not uuid_ws:
            raise AutomataError
        connect_websocket(uuid_ws, session)
        return 0
    else:
        raise AutomataError


# 自动重连的 WebSocket 客户端
def connect_websocket(uuid_ws, session: requests.Session = None):
    global WS_URL, QR_BASE_URL, hasSub, _stop_sub
    WS_URL = f"wss://{HOST}/jaccount/sub/{uuid_ws}"
    QR_BASE_URL = f"https://{HOST}/jaccount/qrcode?uuid={uuid_ws}"
    hasSub = True
    _stop_sub.clear()
    # Save for use in on_message LOGIN action
    connect_websocket._session = session
    connect_websocket._uuid = uuid_ws

    headers = []
    if session is not None:
        cookie_str = "; ".join([f"{k}={v}" for k, v in session.cookies.items()])
        if cookie_str:
            headers.append(f"Cookie: {cookie_str}")
        ua = session.headers.get("User-Agent")
        if ua:
            headers.append(f"User-Agent: {ua}")
    headers.append(f"Origin: https://{HOST}")

    while not _stop_sub.is_set():
        try:
            print(f"Connecting to {WS_URL}...")
            ws = websocket.WebSocketApp(
                WS_URL,
                header=headers,
                on_open=lambda w: on_open(w),
                on_message=on_message,
                on_error=on_error,
                on_close=on_close
            )
            ws.run_forever(ping_interval=20, ping_timeout=10)
        except Exception as e:
            if _stop_sub.is_set():
                break
            print("Connection failed:", e)
        if _stop_sub.is_set():
            break
        print("Retrying in 5 seconds...")
        time.sleep(5)
    # Return after stop requested
    return

def on_open(ws):
    global subFailed
    print("WebSocket connected successfully!")
    subFailed = False
    after_sub_success(ws)

def on_error(ws, error):
    print("WebSocket Error:", error)
    after_sub_failed(ws)

def on_close(ws, close_status_code, close_msg):
    global hasSub
    hasSub = False
    print(f"WebSocket closed: {close_status_code}, {close_msg}")
    # JS shows message and resubscribes based on code; here we just log.
    # Reconnect handled by connect_websocket loop.
    # If you need UI messaging, integrate showQr equivalent here.

def after_sub_success(ws):
    # Equivalent to JS afterSubSuccess: send UPDATE_QR_CODE every 60s
    def loop_send():
        global hasSub, subFailed
        while hasSub and not subFailed:
            try:
                ws.send('{ "type": "UPDATE_QR_CODE" }')
                time.sleep(60)
            except Exception:
                try:
                    ws.close()
                except Exception:
                    pass
                break
    threading.Thread(target=loop_send, daemon=True).start()

def after_sub_failed(ws):
    global subFailed
    subFailed = True
    print("Load QR code failed")

def on_message(ws, message):
    print("WS text message:", message)
    try:
        msg = json.loads(message)
    except Exception:
        return
    t = msg.get("type")
    if t == "UPDATE_QR_CODE":
        payload = msg.get("payload", {})
        ts = payload.get("ts")
        sig = payload.get("sig")
        if ts and sig and QR_BASE_URL:
            qr_url = f"{QR_BASE_URL}&ts={ts}&sig={sig}"
            print("QR Code URL:", qr_url)
            try:
                img_data = requests.get(qr_url).content
                img = Image.open(BytesIO(img_data))
                img.save("qrcode.png")
                print("QR code saved as qrcode.png")
                img = Image.open("qrcode.png")
                img.show()
            except Exception as e:
                print("Failed to fetch/show QR:", e)
    elif t == "ERROR_MESSAGE":
        after_sub_failed(ws)
    elif t == "LOGIN":
        # Mirror JS: navigate to expresslogin with UUID, and on success stop WS and return
        uuid_ws = getattr(connect_websocket, "_uuid", None)
        session = getattr(connect_websocket, "_session", None)
        if uuid_ws:
            express_url = f"https://{HOST}/jaccount/expresslogin?uuid={uuid_ws}"
            print(f"LOGIN received. Calling express login: {express_url}")
            try:
                resp = session.get(express_url, allow_redirects=True) if session else requests.get(express_url, allow_redirects=True)
                print(f"Express login status: {resp.status_code}")
                if 200 <= resp.status_code < 400:
                    # Success: close WS and signal loop to stop
                    try:
                        ws.close()
                    finally:
                        global hasSub, _stop_sub
                        hasSub = False
                        _stop_sub.set()
                else:
                    print("Express login did not succeed; continuing WebSocket.")
            except Exception as e:
                print("Express login failed:", e)
        else:
            print("LOGIN received but UUID missing.")

def login(url, useocr=False):
    """Call this function to login.

    Captcha picture will be stored in captcha.jpeg.
    WARNING: From 0.2.0, username and password will not be allowed to pass as params, all done by this function itself.

    Args:
        url: string, direct login url
        useocr=False: bool, True to use ocr to autofill captcha

    Returns:
        requests login session.
    """
    while True:
        #echoinfo("test")
        username = input('Username: ')
        password = getpass('Password(no echo): ')

        while True:
            session = _create_session()
            req = _get_login_page(session, url)
            #captcha_id = re_search(r'img.src = \'captcha\?(.*)\'', req)
            captcha_id = re_search(r'captcha\?uuid=(.*?)&t=', req)
            #echoinfo(captcha_id)
            if not captcha_id:
                echoinfo('Captcha not found! Retrying...')
                sleep(3)
                continue
            #captcha_id += get_timestamp()
            #captcha_url = 'https://jaccount.sjtu.edu.cn/jaccount/captcha?' + captcha_id
            captcha_url = 'https://jaccount.sjtu.edu.cn/jaccount/captcha?uuid=' + captcha_id + '&t=1726120863879'
            #echoinfo(captcha_url)
            
            code = _bypass_captcha(session, captcha_url, useocr)
            #echoinfo(code)

            sid = re_search(r'sid: "(.*?)"', req)
            returl = re_search(r'returl:"(.*?)"', req)
            se = re_search(r'se: "(.*?)"', req)
            client = re_search(r'client: "(.*?)"', req)
            uuid = re_search(r'captcha\?uuid=(.*?)&t=', req)
            if not (sid and returl and se and uuid):
                print('Params not found! Retrying...')
                sleep(3)
                continue

            res = _login(session, sid, returl, se, client,
                         username, password, code, uuid)

            if res == 2:
                if not useocr:
                    print('Wrong captcha! Try again!')
                continue
            elif res == 1:
                print('Wrong username or password! Try again!')
                break
            elif res == 3:
                print('Opps! You are banned for 30s...Waiting...')
                sleep(30)
                continue
            else:
                return session
