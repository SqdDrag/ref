import os
import time

from web.endpoints import check

os.environ["CAPTCHA_SECRET"] = "test-secret"
check._CAPTCHA_SECRET = "test-secret"

captcha = check._build_captcha(1, "token")
assert check._verify_captcha(1, "token", captcha["a"], captcha["b"], captcha["ts"], captcha["nonce"], captcha["sig"], str(captcha["a"] + captcha["b"]))
assert not check._verify_captcha(1, "token", captcha["a"], captcha["b"], captcha["ts"], captcha["nonce"], captcha["sig"], "0")

old_ts = int(time.time()) - 400
assert not check._verify_captcha(1, "token", 2, 2, old_ts, "x", check._sign("1:token:2:2:%s:x" % old_ts), "4")
print("captcha tests ok")
