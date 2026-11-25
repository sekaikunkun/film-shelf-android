"""Deterministic same-source episode scan acceptance fixture; localhost only."""
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlsplit, parse_qs
from threading import Lock
import argparse, hashlib, json, re, time
parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("video", type=Path, help="locally generated H.264 MP4; do not use private media")
parser.add_argument("--port", type=int, default=18656)
args = parser.parse_args()
PORT = args.port
BASE = f"http://127.0.0.1:{PORT}"
MEDIA = args.video.read_bytes()
ROUTES = [
    ("Start", [("Episode01", "/must-not-fetch.mp4"), ("Episode09", "/current09.mp4")]),
    ("Verified", [("第９集", "/verified09.mp4"), ("第1集", "/must-not-fetch.mp4")]),
    ("Unverified", [("09", "/fake09.mp4")]),
    ("Manual", [("EP.09", "/manual09")]),
    ("Unmatched", [("Episode01", "/must-not-fetch.mp4")]),
    ("Ambiguous", [("09", "/must-not-fetch.mp4?a"), ("第九集", "/must-not-fetch.mp4?b"), ("E09", "/must-not-fetch.mp4?c")]),
    ("Slow", [("09", "/slow09.mp4")]),
]
SITE = {"key":"qa-local","name":"Acceptance Fixture","type":1,"api":BASE+"/api","searchable":1}
DETAIL = {"vod_id":"same-id","vod_name":"Same-episode acceptance","type_id":1,"type_name":"QA",
          "vod_remarks":"QA","vod_play_from":"$$$".join(n for n,_ in ROUTES),
          "vod_play_url":"$$$".join("#".join(f"{label}${BASE}{path}" for label,path in lines) for _,lines in ROUTES)}
AUTH = {"key":"qa-auth","name":"QR Fixture","type":4,"api":BASE+"/auth","searchable":1}
AUTH_DETAIL = dict(DETAIL, vod_id="same-auth", vod_name="QR acceptance",
    vod_play_from="Auth first$$$Auth alternative$$$Genuine timeout",
    vod_play_url="Episode09$challenge$$$09$success$$$Episode09$negated")
# The playback observer's fixture gives different files different paths, even
# when the lab reuses the same local port and the player's disk cache persists.
OBSERVER_MEDIA = "/observer/" + hashlib.sha256(MEDIA).hexdigest() + "/media.mp4"
OBSERVER_SITE = dict(SITE, key="qa-observer", name="Playback Lab", api=BASE+"/observer")
OBSERVER_AUTH = dict(AUTH, key="qa-observer-auth", name="QR Lab", api=BASE+"/observer-auth")
OBSERVER_DETAIL = dict(DETAIL, vod_id="observer-playback", vod_name="Observer Lab TITLE_CANARY",
                       vod_play_from="Lab", vod_play_url=f"EP01${BASE}{OBSERVER_MEDIA}")
OBSERVER_AUTH_DETAIL = dict(AUTH_DETAIL, vod_id="observer-auth", vod_name="QR Lab TITLE_CANARY",
                            vod_play_from="Waiting", vod_play_url="EP01$wait")

AUTO_NAMESPACE = "/auto/" + hashlib.sha256(MEDIA).hexdigest()[:16]
AUTO_SITE = dict(SITE, key="qa-auto", name="Auto Recovery Lab", api=BASE+"/auto-api")
AUTO_DETAIL = dict(DETAIL, vod_id="auto-restart", vod_name="Automatic Episode09",
    vod_play_from="Removed first$$$Wrong episode$$$Removed second$$$Episode09 backup",
    vod_play_url=(f"EP09${BASE}{AUTO_NAMESPACE}/removed-1.mp4$$$"
                  f"EP01${BASE}{AUTO_NAMESPACE}/never-episode01.mp4$$$"
                  f"第9集${BASE}{AUTO_NAMESPACE}/removed-2.mp4$$$"
                  f"Episode01${BASE}{AUTO_NAMESPACE}/never-episode01.mp4#E09${BASE}{AUTO_NAMESPACE}/playing09.mp4"))

RECOVERY_SITE = dict(SITE, key="qa-recovery", name="Recovery Lab", api=BASE+"/recovery")
RECOVERY_DETAIL = dict(DETAIL, vod_id="recovery-episode09", vod_name="Recovery Episode09",
    vod_play_from="Stalled$$$Wrong episode$$$Verified",
    vod_play_url=(f"EP09${BASE}/recovery-stall09.mp4$$$"
                  f"EP01${BASE}/recovery-never01.mp4$$$"
                  f"E09${BASE}/recovery-verified09.mp4"))

PROGRESS_SITE = dict(SITE, key="qa-progress", name="Progress Lab", api=BASE+"/progress-api")
PROGRESS_DETAIL = dict(DETAIL, vod_id="progress-episode09", vod_name="Progress Episode09",
    vod_play_from="Current$$$Slow disc$$$Login disc$$$Forbidden disc$$$Verified disc",
    vod_play_url=(f"EP09${BASE}/progress-current09.mp4$$$"
                  f"EP09${BASE}/progress-slow09.mp4$$$"
                  f"EP09${BASE}/progress-login09.mp4$$$"
                  f"EP09${BASE}/progress-forbidden09.mp4$$$"
                  f"EP09${BASE}/progress-verified09.mp4"))

PROGRESS_CROSS_AUTH = dict(SITE, key="qa-progress-cross-auth", name="Login source",
                          api=BASE+"/progress-cross-auth")
PROGRESS_CROSS_DIRECT = dict(SITE, key="qa-progress-cross-direct", name="Direct source",
                            api=BASE+"/progress-cross-direct")
PROGRESS_CROSS_DETAIL = dict(PROGRESS_DETAIL, vod_id="progress-cross-episode01",
                            vod_play_from="Pilot", vod_play_url=f"EP01${BASE}/progress-cross01.mp4")

OVAL_STYLE = {"type":"oval", "ratio":1}
OVAL_SITE = dict(SITE, key="qa-oval", name="Oval Card Lab", api=BASE+"/oval-api", style=OVAL_STYLE)
OVAL_DETAIL = dict(PROGRESS_DETAIL, vod_id="oval-card-episode09", vod_name="Oval Episode09",
                   style=OVAL_STYLE, vod_play_from="Current",
                   vod_play_url=f"EP09${BASE}/progress-current09.mp4")

CROSS_SITE = {"key":"qa-cross","name":"Cross-source Fixture","type":1,"api":BASE+"/cross","searchable":1}
CROSS_DETAIL = dict(DETAIL, vod_id="cross-id", vod_play_from="Trailer-first fixture",
    vod_play_url=f"Trailer${BASE}/trailer.mp4#EP01${BASE}/cross01.mp4")
WRONG_DETAIL = dict(CROSS_DETAIL, vod_id="not-requested",
    vod_play_url=f"EP01${BASE}/wrong-title.mp4")
WRONG_SAME_ROUTE = dict(CROSS_DETAIL, vod_id="not-requested")
CROSS_CASES = ("ordered", "wrong-only", "duplicate", "changes")
IDENTITY_SITES = [dict(CROSS_SITE, key="qa-cross-"+case, name="Identity "+case,
    api=BASE+"/identity/"+case) for case in CROSS_CASES]
DETAIL_CALLS = {}
DETAIL_LOCK = Lock()

def detail_rows(case, is_detail):
    if not is_detail:
        # Keep the changing provider's detail counter for the scan and switch requests.
        if case == "changes":
            return [dict(CROSS_DETAIL, vod_pic=BASE+"/qa-cover.png")]
        return [CROSS_DETAIL]
    if case == "ordered":
        return [WRONG_DETAIL, CROSS_DETAIL]
    if case == "wrong-only":
        return [WRONG_DETAIL]
    if case == "duplicate":
        return [CROSS_DETAIL, CROSS_DETAIL]
    with DETAIL_LOCK:
        DETAIL_CALLS[case] = DETAIL_CALLS.get(case, 0) + 1
        return [CROSS_DETAIL] if DETAIL_CALLS[case] == 1 else [WRONG_SAME_ROUTE]

class Handler(BaseHTTPRequestHandler):
    challenges = 0
    def send_bytes(self,data,media_type,ranges=False):
        length=len(data)
        first,last=0,length-1
        raw=self.headers.get("Range") if ranges else None
        if raw:
            m=re.fullmatch(r"bytes=(\d+)-(\d*)", raw)
            if not m: self.send_error(416); return
            first=int(m[1]); last=min(last,int(m[2])) if m[2] else last
            if first>last: self.send_error(416); return
        self.send_response(206 if raw else 200)
        self.send_header("Content-Type",media_type)
        if raw: self.send_header("Content-Range",f"bytes {first}-{last}/{length}")
        if ranges: self.send_header("Accept-Ranges","bytes")
        self.send_header("Content-Length",str(last-first+1)); self.end_headers()
        try: self.wfile.write(data[first:last+1])
        except (BrokenPipeError, ConnectionResetError): pass
    def do_GET(self):
        req=urlsplit(self.path); p=req.path; q=parse_qs(req.query)
        if p=="/config.json": payload={"sites":[SITE,AUTH]}
        elif p=="/auto.json": payload={"sites":[AUTO_SITE]}
        elif p=="/auto-api":
            payload={"class":[{"type_id":1,"type_name":"QA"}],"list":[AUTO_DETAIL],"page":1,"pagecount":1,"total":1}
        elif p==AUTO_NAMESPACE+"/removed-1.mp4": self.send_error(404); return
        elif p==AUTO_NAMESPACE+"/removed-2.mp4": self.send_error(410); return
        elif p in (AUTO_NAMESPACE+"/playing09.mp4", AUTO_NAMESPACE+"/never-episode01.mp4"):
            self.send_bytes(MEDIA,"video/mp4",True); return
        elif p=="/recovery.json": payload={"sites":[RECOVERY_SITE]}
        elif p=="/recovery":
            payload={"class":[{"type_id":1,"type_name":"QA"}],"list":[RECOVERY_DETAIL],"page":1,"pagecount":1,"total":1}
        elif p=="/recovery-stall09.mp4":
            print("recovery-stall09 requested", flush=True)
            time.sleep(24)
            self.send_bytes(MEDIA,"video/mp4",True); return
        elif p in ("/recovery-verified09.mp4", "/recovery-never01.mp4"):
            self.send_bytes(MEDIA,"video/mp4",True); return
        elif p=="/progress.json": payload={"sites":[PROGRESS_SITE]}
        elif p=="/progress-cross.json": payload={"sites":[PROGRESS_SITE, PROGRESS_CROSS_AUTH, PROGRESS_CROSS_DIRECT]}
        elif p in ("/progress-cross-auth", "/progress-cross-direct"):
            if q.get("ids"):
                time.sleep(2)
                if p.endswith("auth"):
                    self.send_response(401)
                    self.send_header("WWW-Authenticate", 'Basic realm="Synthetic QA"')
                    self.send_header("Content-Length", "0")
                    self.end_headers(); return
            payload={"class":[{"type_id":1,"type_name":"QA"}],"list":[PROGRESS_CROSS_DETAIL],"page":1,"pagecount":1,"total":1}
        elif p=="/progress-cross01.mp4":
            self.send_bytes(MEDIA,"video/mp4",True); return
        elif p=="/oval.json": payload={"sites":[OVAL_SITE]}
        elif p=="/oval-api":
            payload={"class":[{"type_id":1,"type_name":"QA"}],"list":[OVAL_DETAIL],"page":1,"pagecount":1,"total":1}
        elif p=="/progress-api":
            payload={"class":[{"type_id":1,"type_name":"QA"}],"list":[PROGRESS_DETAIL],"page":1,"pagecount":1,"total":1}
        elif p=="/progress-slow09.mp4":
            print("progress slow candidate requested", flush=True)
            time.sleep(8)
            self.send_bytes(MEDIA,"video/mp4",True); return
        elif p=="/progress-login09.mp4":
            self.send_response(401)
            self.send_header("WWW-Authenticate", 'Basic realm="Synthetic QA"')
            self.send_header("Content-Length", "0")
            self.end_headers(); return
        elif p=="/progress-forbidden09.mp4":
            time.sleep(2)
            self.send_error(403); return
        elif p in ("/progress-current09.mp4", "/progress-verified09.mp4"):
            self.send_bytes(MEDIA,"video/mp4",True); return
        elif p=="/observer.json": payload={"sites":[OBSERVER_SITE, OBSERVER_AUTH]}
        elif p=="/observer": payload={"class":[{"type_id":1,"type_name":"QA"}],"list":[OBSERVER_DETAIL],"page":1,"pagecount":1,"total":1}
        elif p=="/observer-auth":
            if q.get("play") == ["wait"]:
                payload={"msg":"QR code expired", "url":""}
            else:
                payload={"class":[{"type_id":1,"type_name":"QA"}],"list":[OBSERVER_AUTH_DETAIL],"page":1,"pagecount":1,"total":1}
        elif p==OBSERVER_MEDIA:
            self.send_bytes(MEDIA,"video/mp4",True); return
        elif p=="/cross.json": payload={"sites":[SITE,CROSS_SITE]}
        elif p=="/cross-identity.json": payload={"sites":[SITE,*IDENTITY_SITES]}
        elif p.startswith("/identity/") and p.split("/")[-1] in CROSS_CASES:
            rows=detail_rows(p.split("/")[-1], q.get("ids") == ["cross-id"])
            payload={"class":[{"type_id":1,"type_name":"QA"}],"list":rows,"page":1,"pagecount":1,"total":len(rows)}
        elif p=="/cross": payload={"class":[{"type_id":1,"type_name":"QA"}],"list":[CROSS_DETAIL],"page":1,"pagecount":1,"total":1}
        elif p=="/qr.json": payload={"sites":[AUTH]}
        elif p=="/auth":
            play=q.get("play", [""])[0]
            if play=="challenge":
                Handler.challenges += 1
                payload={"msg":"QR code expired","url":""} if Handler.challenges==1 else {"parse":0,"url":BASE+"/verified09.mp4"}
            elif play=="success":
                payload={"parse":0,"url":BASE+"/verified09.mp4"}
            elif play=="negated":
                payload={"msg":"不需扫码，网络连接超时","url":""}
            else:
                payload={"class":[{"type_id":1,"type_name":"QA"}],"list":[AUTH_DETAIL],"page":1,"pagecount":1,"total":1}
        elif p=="/api": payload={"class":[{"type_id":1,"type_name":"QA"}],"list":[DETAIL],"page":1,"pagecount":1,"total":1}
        elif p=="/qa-cover.png": self.send_error(404); return
        elif p=="/fake09.mp4": self.send_bytes(b"<html>not video</html>","text/html"); return
        elif p in ("/current09.mp4","/verified09.mp4","/manual09","/slow09.mp4","/trailer.mp4","/cross01.mp4","/wrong-title.mp4"):
            if p=="/slow09.mp4": time.sleep(12)
            self.send_bytes(MEDIA,"video/mp4",True); return
        else: self.send_error(404); return
        self.send_bytes(json.dumps(payload,ensure_ascii=False).encode(),"application/json")
if __name__=="__main__":
    ThreadingHTTPServer(("127.0.0.1",PORT),Handler).serve_forever()
