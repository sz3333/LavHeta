# -*- coding: utf-8 -*-
# meta developer: @LavHeta

from .. import loader, utils
import aiohttp, asyncio, json, re

INDEX_URL = "https://raw.githubusercontent.com/sz3333/LavHeta/main/LavIndexRaw.json"
DELAY = 2

def _norm(s):
    return re.sub(r"\s+"," ",s.strip().lower()) if s else ""

def _safe(s):
    return utils.escape_html(str(s)) if s else ""

class LavHetaSearch(loader.Module):
    """LavHetaSearch — автономный поиск LavHeta Index"""
    strings={"name":"LavHetaSearch"}

    async def client_ready(self,client,db):
        self._cards=[]
        self._keys=[]
        try:
            async with aiohttp.ClientSession() as sess:
                async with sess.get(INDEX_URL,timeout=40) as r:
                    if r.status==200:
                        data=await r.json(loads=json.loads)
                    else:
                        return
        except:
            return

        arr = data.get("modules", data if isinstance(data,list) else [])
        for it in arr:
            if not isinstance(it,dict): continue

            name=str(it.get("name","")).strip()
            repo=str(it.get("repo","")).strip()
            author=repo.split("/",1)[0] if "/" in repo else ""
            install=str(it.get("install","")).strip()
            desc=""
            d=it.get("description")
            if isinstance(d,dict): desc=d.get("ru_doc") or d.get("en_doc") or ""
            elif isinstance(d,str): desc=d

            self._cards.append((name,author,repo,install,desc))
            blob=" ".join([_norm(name),_norm(author),_norm(repo),_norm(desc)])
            self._keys.append((_norm(name),_norm(author),_norm(repo),blob))

    @loader.command()
    async def lheta(self, m):
        q=utils.get_args_raw(m)
        if not q: return await utils.answer(m,"🥸 запрос где? .lheta slapper")

        if not self._cards:
            return await utils.answer(m,"😿 индекс не подгружен (перезапусти юзербот)")

        await utils.answer(m,f"🔎 ищу «<b>{_safe(q)}</b>». мем-пауза {DELAY}s…")
        await asyncio.sleep(DELAY)

        qn=_norm(q)
        scored=[]
        for i,(name,author,repo,install,desc) in enumerate(self._cards):
            n,a,r,b = self._keys[i]
            s=0
            if n==qn: s+=120
            if n.startswith(qn): s+=40
            if qn in n: s+=28
            if a==qn or r==qn: s+=20
            elif qn in a or qn in r: s+=12
            if qn in b: s+=10
            if n: s+=max(0,6-min(6,len(n)/8))
            if s>0: scored.append((i,s))

        if not scored:
            return await utils.answer(m,f"🥲 нулевой результат по <b>{_safe(q)}</b>")

        scored.sort(key=lambda x:x[1],reverse=True)
        scored=scored[:12]

        out=["😼 <b>LavHeta</b> докладывает:\n"]
        for k,(idx,sc) in enumerate(scored,1):
            name,author,repo,install,desc = self._cards[idx]
            t=f"<b>{k}.</b> <code>{_safe(name)}</code> — 👤 <b>{_safe(author)}</b> • 📦 <code>{_safe(repo)}</code>\n"
            if desc:
                d=_safe(desc)
                if len(d)>300:d=d[:300]+"…"
                t+=f"📝 {d}\n"
            t+=f"⚙️ <code>{_safe(install)}</code>"
            out.append(t)

        await utils.answer(m,"\n\n".join(out))
