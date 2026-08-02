import os, sqlite3, threading, hashlib, re, json
from datetime import datetime, timezone
from urllib.parse import urlparse
import feedparser, requests
from flask import Flask, render_template, request, jsonify, redirect, url_for, g
from dotenv import load_dotenv
from apscheduler.schedulers.background import BackgroundScheduler

load_dotenv()
BASE = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.getenv("DATABASE_PATH", os.path.join(BASE, "data", "signal.db"))
os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
REFRESH_MINUTES = int(os.getenv("REFRESH_MINUTES", "10"))

DEFAULT_FEEDS = [
    ("Reuters World", "https://feeds.reuters.com/reuters/worldNews"),
    ("Reuters Business", "https://feeds.reuters.com/reuters/businessNews"),
    ("TechCrunch", "https://techcrunch.com/feed/"),
    ("MIT Technology Review", "https://www.technologyreview.com/feed/"),
    ("ScienceDaily", "https://www.sciencedaily.com/rss/all.xml"),
    ("WHO News", "https://www.who.int/rss-feeds/news-english.xml"),
    ("Nigeria Health Watch", "https://nigeriahealthwatch.com/feed/"),
    ("TechCabal", "https://techcabal.com/feed/"),
]

TOPICS = [
    ("Nigeria","🇳🇬","Government, economy, society, business and current events."),
    ("Technology","⌘","AI, software, startups, products and technology policy."),
    ("Pharmacy & Healthcare","＋","Medicine, pharmacy, healthcare systems, regulation and research."),
    ("Science","◌","Research, discoveries, evidence and scientific developments."),
    ("Business","◈","Companies, markets, investment and economic developments."),
]

def now_iso(): return datetime.now(timezone.utc).isoformat()

def connect():
    c = sqlite3.connect(DB_PATH, check_same_thread=False)
    c.row_factory = sqlite3.Row
    return c

def init_db():
    c=connect()
    c.executescript("""
    CREATE TABLE IF NOT EXISTS articles(
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      fingerprint TEXT UNIQUE,
      source TEXT NOT NULL,
      title TEXT NOT NULL,
      summary TEXT DEFAULT '',
      url TEXT NOT NULL,
      published_at TEXT,
      topic TEXT DEFAULT 'World',
      image_url TEXT DEFAULT '',
      fetched_at TEXT NOT NULL
    );
    CREATE TABLE IF NOT EXISTS follows(
      topic TEXT PRIMARY KEY,
      created_at TEXT NOT NULL
    );
    CREATE TABLE IF NOT EXISTS saved(
      article_id INTEGER PRIMARY KEY,
      created_at TEXT NOT NULL,
      FOREIGN KEY(article_id) REFERENCES articles(id) ON DELETE CASCADE
    );
    CREATE INDEX IF NOT EXISTS idx_articles_pub ON articles(published_at DESC);
    CREATE INDEX IF NOT EXISTS idx_articles_topic ON articles(topic);
    """)
    c.commit(); c.close()

def infer_topic(title, summary="", source=""):
    s=(title+" "+summary+" "+source).lower()
    if any(x in s for x in ["pharma","pharmacy","drug","medicine","health","hospital","who ","fda","nafdac"]): return "Pharmacy & Healthcare"
    if any(x in s for x in ["ai ","artificial intelligence","software","startup","technology","tech","chip","semiconductor","robot"]): return "Technology"
    if any(x in s for x in ["science","research","study","scientist","space","climate"]): return "Science"
    if any(x in s for x in ["business","market","company","finance","bank","investment","economy"]): return "Business"
    if any(x in s for x in ["nigeria","abuja","lagos","naira","africa"]): return "Nigeria"
    return "World"

def fingerprint(source,title,url):
    return hashlib.sha256((source+"|"+title+"|"+url).encode()).hexdigest()

def ingest():
    c=connect()
    count=0
    for source, feed_url in DEFAULT_FEEDS:
        try:
            d=feedparser.parse(feed_url)
            for e in d.entries[:80]:
                title=(e.get("title") or "").strip()
                url=(e.get("link") or "").strip()
                if not title or not url: continue
                summary=re.sub("<[^>]+>"," ",e.get("summary","")).strip()
                published=e.get("published") or e.get("updated") or now_iso()
                fp=fingerprint(source,title,url)
                image=""
                if e.get("media_content"): image=e.media_content[0].get("url","")
                try:
                    c.execute("""INSERT OR IGNORE INTO articles
                    (fingerprint,source,title,summary,url,published_at,topic,image_url,fetched_at)
                    VALUES(?,?,?,?,?,?,?,?,?)""",
                    (fp,source,title,summary[:4000],url,published,infer_topic(title,summary,source),image,now_iso()))
                    count += c.rowcount
                except Exception: pass
        except Exception:
            continue
    c.commit(); c.close()
    return count

def query_articles(q="", topic="", limit=40, offset=0):
    c=connect()
    sql="SELECT * FROM articles WHERE 1=1"
    args=[]
    if q:
        sql+=" AND (title LIKE ? OR summary LIKE ? OR source LIKE ?)"
        like="%"+q+"%"; args += [like,like,like]
    if topic:
        sql+=" AND topic=?"; args.append(topic)
    sql+=" ORDER BY CASE WHEN published_at IS NULL THEN 1 ELSE 0 END, published_at DESC LIMIT ? OFFSET ?"
    args += [limit,offset]
    rows=c.execute(sql,args).fetchall(); c.close()
    return [dict(x) for x in rows]

def article(id):
    c=connect(); r=c.execute("SELECT * FROM articles WHERE id=?",(id,)).fetchone(); c.close()
    return dict(r) if r else None

def app_state():
    c=connect()
    following=[r["topic"] for r in c.execute("SELECT topic FROM follows ORDER BY topic").fetchall()]
    saved=[r["article_id"] for r in c.execute("SELECT article_id FROM saved").fetchall()]
    c.close()
    return following,saved

def create_app():
    init_db()
    app=Flask(__name__)
    app.config["SECRET_KEY"]=os.getenv("SECRET_KEY","dev-secret-change-me")

    @app.before_request
    def before():
        g.following,g.saved=app_state()

    @app.context_processor
    def ctx():
        return {"topics":TOPICS,"following":g.following,"saved":g.saved,"config_refresh":REFRESH_MINUTES}

    @app.route("/")
    def home():
        return render_template("app.html", screen="home", articles=query_articles(limit=35))

    @app.route("/screen/<screen>")
    def screen(screen):
        if screen=="explore": data=[]
        elif screen=="timeline": data=query_articles(limit=30)
        elif screen.startswith("topic-"):
            topic_name=screen.replace("topic-","").replace("-"," ").title()
            if topic_name=="Pharmacy & Healthcare": topic_name="Pharmacy & Healthcare"
            data=query_articles(topic=topic_name,limit=40)
        elif screen=="following":
            data=[a for a in query_articles(limit=100) if a["topic"] in g.following]
        elif screen=="saved":
            data=[a for a in query_articles(limit=100) if a["id"] in g.saved]
        elif screen=="search": data=[]
        elif screen=="settings": data=[]
        else: data=query_articles(limit=35)
        return render_template("app.html", screen=screen, articles=data)

    @app.get("/health")
    def health():
        c=connect()
        n=c.execute("SELECT COUNT(*) AS n FROM articles").fetchone()["n"]
        c.close()
        return jsonify(ok=True, articles=n, time=now_iso())

    @app.get("/api/sources")
    def api_sources():
        return jsonify({"sources":[{"name":n,"feed":u} for n,u in DEFAULT_FEEDS]})

    @app.get("/api/articles")
    def api_articles():
        q=request.args.get("q","").strip()
        topic=request.args.get("topic","").strip()
        page=max(0,int(request.args.get("page",0)))
        return jsonify({"articles":query_articles(q,topic,40,page*40),"page":page})

    @app.get("/api/article/<int:id>")
    def api_article(id):
        a=article(id)
        return jsonify(a or {}), 200 if a else 404

    @app.post("/api/follow")
    def api_follow():
        topic=request.json.get("topic","").strip()
        if not topic: return jsonify(ok=False),400
        c=connect()
        if c.execute("SELECT 1 FROM follows WHERE topic=?",(topic,)).fetchone():
            c.execute("DELETE FROM follows WHERE topic=?",(topic,))
            state=False
        else:
            c.execute("INSERT INTO follows(topic,created_at) VALUES(?,?)",(topic,now_iso()))
            state=True
        c.commit(); c.close()
        return jsonify(ok=True,following=state,topic=topic)

    @app.post("/api/save")
    def api_save():
        aid=int(request.json.get("id"))
        c=connect()
        if c.execute("SELECT 1 FROM saved WHERE article_id=?",(aid,)).fetchone():
            c.execute("DELETE FROM saved WHERE article_id=?",(aid,)); state=False
        else:
            c.execute("INSERT INTO saved(article_id,created_at) VALUES(?,?)",(aid,now_iso())); state=True
        c.commit(); c.close()
        return jsonify(ok=True,saved=state)

    @app.post("/api/refresh")
    def api_refresh():
        n=ingest(); return jsonify(ok=True,new_articles=n,refreshed_at=now_iso())

    @app.post("/api/ai")
    def api_ai():
        key=os.getenv("OPENAI_API_KEY","").strip()
        data=request.json or {}
        text=data.get("text","")[:12000]
        mode=data.get("mode","summary")
        if not key:
            return jsonify(ok=False, message="AI is not configured. Add OPENAI_API_KEY to .env."), 503
        try:
            from openai import OpenAI
            client=OpenAI(api_key=key)
            prompt=f"""You are Signal, a source-first information intelligence assistant.
Mode: {mode}
Use only the supplied article text. Do not invent facts. Clearly distinguish facts from interpretation.
Article:
{text}
"""
            model=os.getenv("OPENAI_MODEL") or "gpt-4.1-mini"
            r=client.responses.create(model=model,input=prompt)
            return jsonify(ok=True,text=r.output_text)
        except Exception as e:
            return jsonify(ok=False,message=str(e)),500

    scheduler=BackgroundScheduler(daemon=True)
    scheduler.add_job(ingest,"interval",minutes=REFRESH_MINUTES,id="feed_refresh",replace_existing=True)
    scheduler.start()
    threading.Thread(target=ingest,daemon=True).start()
    return app

if __name__=="__main__":
    create_app().run()
