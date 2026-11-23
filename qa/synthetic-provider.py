"""Deterministic same-source episode scan acceptance fixture; localhost only."""
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlsplit, parse_qs
import argparse, json, re, time
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
CROSS_SITE = {"key":"qa-cross","name":"Cross-source Fixture","type":1,"api":BASE+"/cross","searchable":1}
CROSS_DETAIL = dict(DETAIL, vod_id="cross-id", vod_play_from="Trailer-first fixture",
    vod_play_url=f"Trailer${BASE}/trailer.mp4#EP01${BASE}/cross01.mp4")
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
        elif p=="/cross.json": payload={"sites":[SITE,CROSS_SITE]}
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
        elif p=="/fake09.mp4": self.send_bytes(b"<html>not video</html>","text/html"); return
        elif p in ("/current09.mp4","/verified09.mp4","/manual09","/slow09.mp4","/trailer.mp4","/cross01.mp4"):
            if p=="/slow09.mp4": time.sleep(12)
            self.send_bytes(MEDIA,"video/mp4",True); return
        else: self.send_error(404); return
        self.send_bytes(json.dumps(payload,ensure_ascii=False).encode(),"application/json")
if __name__=="__main__":
    ThreadingHTTPServer(("127.0.0.1",PORT),Handler).serve_forever()
