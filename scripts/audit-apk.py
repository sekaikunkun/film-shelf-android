from collections import defaultdict
from io import BytesIO
from pathlib import Path
from zipfile import ZipFile,ZIP_STORED
import struct,sys
by=defaultdict(int)
bad=[]
def scan(z, prefix='', backing=None):
 for ent in z.infolist():
    n=ent.filename
    if n.endswith('.so'):
        f=z.open(ent); head=f.read(64)
        if head[:6]!=b'\x7fELF\x02\x01':
            bad.append((prefix+n,'not ELF64LE'))
            continue
        machine=struct.unpack_from('<H',head,18)[0]
        off=struct.unpack_from('<Q',head,32)[0]
        es,cnt=struct.unpack_from('<HH',head,54)
        if not(56<=es<=1024 and 0<cnt<1024):
            bad.append((prefix+n,'unexpected program headers'))
            continue
        f.seek(off)
        align=[seg[7] for seg in [struct.unpack_from('<IIQQQQQQ',f.read(es)) for _ in range(cnt)] if seg[0]==1]
        group='installable' if not prefix and n.startswith('lib/') else 'assets'
        by[group]+=1
        if machine!=183 or not align or min(align)<16384: bad.append((prefix+n,machine,align))
        if group=='installable':
            if ent.compress_type==ZIP_STORED:
                backing.seek(ent.header_offset+26)
                size,extra=struct.unpack('<HH',backing.read(4))
                if (ent.header_offset+30+size+extra)%16384:
                    bad.append((n,'stored APK offset not 16 KiB aligned'))
            else: by['compressed installable']+=1
    if not prefix and n.startswith('assets/chaquopy/') and n.endswith(('.imy','.zip')):
        data=z.read(ent)
        if data.startswith(b'PK\x03\x04'):
            with ZipFile(BytesIO(data)) as inner:
                scan(inner, prefix+n+'!')
p=Path(sys.argv[1])
with ZipFile(p) as z,p.open('rb') as raw:
    scan(z,backing=raw)
print(dict(by))
for x in bad: print(*x)
sys.exit(bool(bad) or not by["installable"] or not by["assets"])
