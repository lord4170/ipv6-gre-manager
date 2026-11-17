#!/usr/bin/env python3
import argparse,base64,fcntl,hashlib,ipaddress,json,os,re,secrets,subprocess,sys,time,uuid
from pathlib import Path
ROOT=Path("/etc/gre-manager"); DATA=ROOT/"tunnels"; REG=ROOT/"registry.json"; LOCK=ROOT/".lock"; UNITS=Path("/etc/systemd/system"); BIN="/usr/local/sbin/gre-manager"; POOL=ipaddress.ip_network("10.250.0.0/16")
def cmd(a,ok=True):
 p=subprocess.run(a,text=True,stdout=subprocess.PIPE,stderr=subprocess.PIPE)
 if ok and p.returncode: raise RuntimeError((p.stderr or p.stdout).strip() or "Command failed: "+" ".join(a))
 return p
def root():
 if os.geteuid()!=0: raise RuntimeError("Run as root: sudo gre-manager")
def dirs():
 ROOT.mkdir(parents=True,exist_ok=True,mode=0o700); DATA.mkdir(exist_ok=True,mode=0o700)
 if not REG.exists(): save(REG,{"version":1,"tunnels":[]})
def save(p,x):
 t=p.with_suffix(p.suffix+".tmp"); t.write_text(json.dumps(x,indent=2,sort_keys=True)+"\n"); os.chmod(t,0o600); os.replace(t,p)
def load(p,d=None):
 try:return json.loads(p.read_text())
 except FileNotFoundError:return d
def lock():
 dirs(); f=open(LOCK,"a+"); fcntl.flock(f,fcntl.LOCK_EX); return f
def v6(s):
 try:a=ipaddress.IPv6Address(s)
 except:raise RuntimeError("Invalid IPv6 address.")
 if not a.is_global: raise RuntimeError("A public global IPv6 address is required.")
 return str(a)
def ifname(s):
 if not re.fullmatch(r"[A-Za-z0-9_.-]{1,15}",s): raise RuntimeError("Interface name must be 1-15 characters.")
 return s
def exists(n):return cmd(["ip","link","show","dev",n],False).returncode==0
def globals6():
 p=cmd(["ip","-6","-o","addr","show","scope","global"],False); out=[]
 for l in p.stdout.splitlines():
  m=re.search(r"inet6 ([0-9a-fA-F:]+)/",l)
  if m:
   try:
    x=v6(m.group(1))
    if x not in out:out.append(x)
   except:pass
 return out
def select6(prompt):
 xs=globals6()
 if xs:
  print("Detected global IPv6 addresses:")
  for i,x in enumerate(xs,1):print(f"  {i}. {x}")
  s=input(prompt+" [number or address]: ").strip()
  a=xs[int(s)-1] if s.isdigit() and 1<=int(s)<=len(xs) else v6(s or xs[0])
 else:a=v6(input(prompt+": ").strip())
 if a not in xs:raise RuntimeError("Selected IPv6 is not assigned locally.")
 return a
def networks():
 out=[]
 for args,pat in [(["ip","-o","-4","addr","show"],r"inet (\d+\.\d+\.\d+\.\d+/\d+)"),(["ip","-4","route","show","table","all"],None)]:
  p=cmd(args,False)
  for l in p.stdout.splitlines():
   try:
    if pat:
     m=re.search(pat,l); n=ipaddress.ip_interface(m.group(1)).network if m else None
    else:
     t=l.split()[0]; n=None if t=="default" else ipaddress.ip_network(t,strict=False)
    if n:out.append(n)
   except:pass
 return out
def apply(c):
 n=ifname(c["ifname"])
 if exists(n):raise RuntimeError("Interface "+n+" already exists; refusing to overwrite.")
 cmd(["ip","-6","tunnel","add",n,"mode","ip6gre","local",c["local6"],"remote",c["remote6"],"key",str(c["key"]),"hoplimit","255"])
 try:
  cmd(["ip","link","set","dev",n,"mtu",str(c["mtu"])]);cmd(["ip","addr","add",c["local4"]+"/30","dev",n]);cmd(["ip","link","set","dev",n,"up"])
 except:
  cmd(["ip","link","del","dev",n],False);raise
def down(c):
 if exists(c["ifname"]):cmd(["ip","link","del","dev",c["ifname"]],False)
def unit(tid):
 p=UNITS/("gre-manager@"+tid+".service")
 p.write_text("[Unit]\nDescription=GRE Manager tunnel "+tid+"\nAfter=network-online.target\nWants=network-online.target\n[Service]\nType=oneshot\nRemainAfterExit=yes\nExecStart="+BIN+" --apply "+tid+"\nExecStop="+BIN+" --down "+tid+"\n[Install]\nWantedBy=multi-user.target\n")
 cmd(["systemctl","daemon-reload"])
def start(tid):
 unit(tid);cmd(["systemctl","enable","--now","gre-manager@"+tid+".service"])
def stop(tid):
 cmd(["systemctl","disable","--now","gre-manager@"+tid+".service"],False);cmd(["systemctl","daemon-reload"],False)
def link(c):
 b=json.dumps(c,sort_keys=True,separators=(",",":")).encode(); return "GRE6V2."+base64.urlsafe_b64encode(b).decode().rstrip("=")+"."+hashlib.sha256(b).hexdigest()[:16]
def decode(s):
 q=s.strip().split(".")
 if len(q)!=3 or q[0]!="GRE6V2":raise RuntimeError("Invalid transfer link.")
 try:b=base64.urlsafe_b64decode(q[1]+"="*(-len(q[1])%4))
 except:raise RuntimeError("Cannot decode transfer link.")
 if not secrets.compare_digest(hashlib.sha256(b).hexdigest()[:16],q[2]):raise RuntimeError("Transfer link checksum mismatch.")
 c=json.loads(b)
 for k in ("id","name","hub6","iran6","key","network","hub4","iran4","ifname","mtu","role"):
  if k not in c:raise RuntimeError("Incomplete transfer link.")
 if c["role"]!="iran":raise RuntimeError("Unsupported link role.")
 c["hub6"]=v6(c["hub6"]);c["iran6"]=v6(c["iran6"]);c["ifname"]=ifname(c["ifname"])
 net=ipaddress.ip_network(c["network"],strict=True)
 if net.prefixlen!=30 or ipaddress.ip_address(c["hub4"]) not in net or ipaddress.ip_address(c["iran4"]) not in net:raise RuntimeError("Invalid tunnel subnet.")
 c["key"]=int(c["key"]);c["mtu"]=int(c["mtu"])
 if not 1<=c["key"]<=4294967295 or not 1280<=c["mtu"]<=9000:raise RuntimeError("Invalid GRE key or MTU.")
 return c
def create():
 root(); name=input("Peer name: ").strip()
 if not name or len(name)>64:raise RuntimeError("Peer name must be 1-64 characters.")
 hub=select6("Select Hub public IPv6"); iran=v6(input("Iran public IPv6: ").strip())
 if hub==iran:raise RuntimeError("Hub and Iran IPv6 addresses must differ.")
 mtu=int(input("Tunnel MTU [1400]: ").strip() or "1400")
 if not 1280<=mtu<=9000:raise RuntimeError("MTU must be 1280-9000.")
 f=lock()
 try:
  r=load(REG,{"version":1,"tunnels":[]})
  old=next((x for x in r["tunnels"] if x["iran6"]==iran),None)
  if old:raise RuntimeError("Iran IPv6 already registered under name '"+old["name"]+"'.")
  used=networks(); keys=set()
  for x in r["tunnels"]:
   used.append(ipaddress.ip_network(x["network"]));keys.add(int(x["key"]))
  net=next((n for n in POOL.subnets(new_prefix=30) if not any(n.overlaps(x) for x in used)),None)
  if net is None:raise RuntimeError("No free /30 subnet in 10.250.0.0/16.")
  key=next((k for k in (secrets.randbelow(2147483646)+1 for _ in range(100)) if k not in keys),None)
  if key is None:raise RuntimeError("Could not allocate unique GRE key.")
  hosts=list(net.hosts()); tid=uuid.uuid4().hex[:12]; iface="g6"+secrets.token_hex(5)
  while exists(iface):iface="g6"+secrets.token_hex(5)
  peer={"id":tid,"name":name,"role":"iran","hub6":hub,"iran6":iran,"key":key,"network":str(net),"hub4":str(hosts[0]),"iran4":str(hosts[1]),"ifname":iface,"mtu":mtu,"created":int(time.time())}
  local={"id":tid,"name":name,"role":"hub","ifname":iface,"local6":hub,"remote6":iran,"key":key,"network":str(net),"local4":str(hosts[0]),"peer4":str(hosts[1]),"mtu":mtu}
  save(DATA/(tid+".json"),local)
  try:start(tid)
  except:
   down(local);(DATA/(tid+".json")).unlink(missing_ok=True);raise
  r["tunnels"].append(peer);save(REG,r)
  print("\n[OK] Hub peer created.\nName: "+name+"\nInterface: "+iface+"\nHub IP: "+str(hosts[0])+"\nIran IP: "+str(hosts[1])+"\nGRE key: "+str(key))
  print("\nTransfer link (keep confidential):\n"+link(peer))
 finally:fcntl.flock(f,fcntl.LOCK_UN);f.close()
def import_peer():
 root();c=decode(input("Paste Hub transfer link: "))
 local=select6("Select this server public IPv6")
 if local!=c["iran6"]:raise RuntimeError("Local IPv6 does not match the Iran endpoint in link.")
 name=input("Local tunnel name ["+c["name"]+"]: ").strip() or c["name"]
 iface=ifname(input("Interface name ["+c["ifname"]+"]: ").strip() or c["ifname"])
 if exists(iface):raise RuntimeError("Interface already exists; refusing to overwrite.")
 net=ipaddress.ip_network(c["network"])
 if any(net.overlaps(x) for x in networks()):raise RuntimeError("Tunnel subnet overlaps an existing address or route.")
 tid=c["id"];path=DATA/(tid+".json")
 if path.exists():raise RuntimeError("This tunnel ID is already imported.")
 localc={"id":tid,"name":name,"role":"iran","ifname":iface,"local6":c["iran6"],"remote6":c["hub6"],"key":c["key"],"network":str(net),"local4":c["iran4"],"peer4":c["hub4"],"mtu":c["mtu"]}
 save(path,localc)
 try:start(tid)
 except:down(localc);path.unlink(missing_ok=True);raise
 print("[OK] Imported "+name+"; systemd autostart enabled. Peer IP: "+c["hub4"])
def configs():
 dirs();out=[]
 for p in sorted(DATA.glob("*.json")):
  try:out.append(json.loads(p.read_text()))
  except:print("[WARN] Invalid config "+p.name)
 return out
def listing():
 cs=configs()
 if not cs:print("No local tunnels.");return
 for c in cs:
  s=cmd(["systemctl","is-active","gre-manager@"+c["id"]+".service"],False).stdout.strip()
  print("\n"+c["name"]+" | "+c["role"]+" | "+c["ifname"]+" | "+(s or "unknown")+" | peer "+c["peer4"])
  p=cmd(["ip","-s","link","show","dev",c["ifname"]],False)
  for line in p.stdout.splitlines():
   if "RX:" in line or "TX:" in line or re.match(r"\s+\d+\s+\d+",line):print("  "+line.strip())
def ping():
 cs=configs()
 for i,c in enumerate(cs,1):print(f"{i}. {c['name']} -> {c['peer4']}")
 n=int(input("Select tunnel: "))
 if not 1<=n<=len(cs):raise RuntimeError("Invalid selection.")
 c=cs[n-1];p=cmd(["ping","-I",c["ifname"],"-c","4","-W","2",c["peer4"]],False);print(p.stdout or p.stderr)
 if p.returncode:print("[WARN] Ping failed. Check IPv6 GRE protocol 47 and endpoint reachability.")
def remove():
 cs=configs()
 for i,c in enumerate(cs,1):print(f"{i}. {c['name']} ({c['ifname']}, {c['role']})")
 n=int(input("Select local tunnel to remove: "))
 if not 1<=n<=len(cs):raise RuntimeError("Invalid selection.")
 c=cs[n-1]
 if input("Type DELETE to confirm: ")!="DELETE":print("Cancelled.");return
 stop(c["id"]);down(c);(DATA/(c["id"]+".json")).unlink(missing_ok=True)
 (UNITS/("gre-manager@"+c["id"]+".service")).unlink(missing_ok=True);cmd(["systemctl","daemon-reload"],False)
 if c["role"]=="hub":
  f=lock()
  try:r=load(REG,{"version":1,"tunnels":[]});r["tunnels"]=[x for x in r["tunnels"] if x["id"]!=c["id"]];save(REG,r)
  finally:fcntl.flock(f,fcntl.LOCK_UN);f.close()
 print("[OK] Removed local endpoint only. Remote peer was not changed.")
def registry():
 r=load(REG,{"tunnels":[]})
 if not r["tunnels"]:print("No Hub peers registered.");return
 for x in r["tunnels"]:print(f"{x['name']} | Iran {x['iran6']} | {x['network']} | key {x['key']} | {x['ifname']}")
def main():
 a=argparse.ArgumentParser();a.add_argument("--version",action="store_true");a.add_argument("--apply");a.add_argument("--down");x=a.parse_args()
 if x.version:print("GRE Tunnel Manager 2.0.0");return
 root();dirs()
 if x.apply or x.down:
  c=load(DATA/((x.apply or x.down)+".json"))
  if not c:raise RuntimeError("Tunnel configuration not found.")
  apply(c) if x.apply else down(c);return
 while True:
  print("\nGRE TUNNEL MANAGER v2 - HUB / SPOKE\n1. Create Iran peer on this Hub server\n2. Import Hub link on Iran server\n3. List local tunnels and counters\n4. Ping a tunnel peer\n5. Remove one local tunnel\n6. Show Hub peer registry\n0. Exit")
  q=input("Select option: ").strip()
  try:
   if q=="1":create()
   elif q=="2":import_peer()
   elif q=="3":listing()
   elif q=="4":ping()
   elif q=="5":remove()
   elif q=="6":registry()
   elif q=="0":break
   else:print("[ERROR] Invalid option.")
  except KeyboardInterrupt:print("\n[INFO] Cancelled.")
  except Exception as e:print("[ERROR] "+str(e))
if __name__=="__main__":
 try:main()
 except Exception as e:print("[ERROR] "+str(e),file=sys.stderr);sys.exit(1)
