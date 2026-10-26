import csv
import io
import sqlite3
from pathlib import Path
from urllib.parse import urlparse

PLATFORMS = ('TikTok', 'YouTube', 'X', 'ローカル動画')
STATUSES = ('未取得', 'ユーザー入力', '確認済み', '推測')
CATEGORIES = ('冒頭3秒', 'カット割り', 'テロップ', '音声', '商品紹介', 'CTA', '成功パターン', '企画案', 'その他')
RELATIONS = ('リプライ', '引用・参照', '宣伝リンク', '販売導線', '関連あり（仮説）')

def validate_url(platform, url):
    if not url:
        return ''
    parsed = urlparse(url.strip())
    hosts = {'TikTok': ('tiktok.com',), 'YouTube': ('youtube.com', 'youtu.be'), 'X': ('x.com', 'twitter.com')}
    host = (parsed.hostname or '').lower()
    if parsed.scheme != 'https' or parsed.username or parsed.password or platform not in hosts or not any(host == h or host.endswith('.' + h) for h in hosts[platform]):
        raise ValueError('選択したSNSのHTTPS URLを入力してください。')
    return url.strip()

def connect(path):
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    db = sqlite3.connect(path)
    db.row_factory = sqlite3.Row
    db.execute('PRAGMA foreign_keys=ON')
    db.executescript('''
    CREATE TABLE IF NOT EXISTS contents (
      id INTEGER PRIMARY KEY, platform TEXT NOT NULL, title TEXT NOT NULL,
      url TEXT NOT NULL DEFAULT '', author TEXT NOT NULL DEFAULT '', body TEXT NOT NULL DEFAULT '',
      tags TEXT NOT NULL DEFAULT '', source TEXT NOT NULL, video_path TEXT,
      duration REAL, frames TEXT NOT NULL DEFAULT '[]', created_at TEXT DEFAULT CURRENT_TIMESTAMP
    );
    CREATE TABLE IF NOT EXISTS notes (
      id INTEGER PRIMARY KEY, content_id INTEGER NOT NULL REFERENCES contents(id),
      category TEXT NOT NULL, status TEXT NOT NULL, text TEXT NOT NULL,
      evidence TEXT NOT NULL DEFAULT '', created_at TEXT DEFAULT CURRENT_TIMESTAMP
    );
    CREATE TABLE IF NOT EXISTS relations (
      id INTEGER PRIMARY KEY, source_id INTEGER NOT NULL REFERENCES contents(id),
      target_id INTEGER NOT NULL REFERENCES contents(id), kind TEXT NOT NULL,
      status TEXT NOT NULL, evidence TEXT NOT NULL, created_at TEXT DEFAULT CURRENT_TIMESTAMP,
      CHECK(source_id != target_id)
    );
    ''')
    return db

def add_content(db, platform, title, url='', author='', body='', tags='', video_path=None, duration=None, frames='[]'):
    if platform not in PLATFORMS or not title.strip():
        raise ValueError('プラットフォームとタイトルは必須です。')
    url = validate_url(platform, url)
    if platform != 'ローカル動画' and not url:
        raise ValueError('SNSコンテンツはURLを入力してください。')
    if platform == 'ローカル動画' and not video_path:
        raise ValueError('ローカル動画はMP4を選択してください。')
    with db:
        cur = db.execute('INSERT INTO contents(platform,title,url,author,body,tags,source,video_path,duration,frames) VALUES(?,?,?,?,?,?,?,?,?,?)', (platform,title.strip(),url,author,body,tags,'ユーザー入力',video_path,duration,frames))
    return cur.lastrowid

def add_note(db, content_id, category, status, text, evidence):
    if category not in CATEGORIES or status not in STATUSES or not text.strip():
        raise ValueError('メモの分類・状態・本文を確認してください。')
    if status == '確認済み' and not evidence.strip():
        raise ValueError('確認済みのメモには根拠を記録してください。')
    with db:
        db.execute('INSERT INTO notes(content_id,category,status,text,evidence) VALUES(?,?,?,?,?)',(content_id,category,status,text,evidence))

def add_relation(db, source_id, target_id, kind, status, evidence):
    if source_id == target_id or kind not in RELATIONS or status not in STATUSES or not evidence.strip():
        raise ValueError('異なる2件と、関係の根拠または仮説の理由を指定してください。')
    with db:
        db.execute('INSERT INTO relations(source_id,target_id,kind,status,evidence) VALUES(?,?,?,?,?)',(source_id,target_id,kind,status,evidence))

def contents(db, query='', platform='すべて'):
    return [dict(r) for r in db.execute('''SELECT * FROM contents c WHERE
      (?='すべて' OR platform=?) AND (instr(lower(title || ' ' || url || ' ' || author || ' ' || body || ' ' || tags),lower(?))>0
      OR EXISTS(SELECT 1 FROM notes n WHERE n.content_id=c.id AND instr(lower(n.text || ' ' || n.evidence),lower(?))>0)) ORDER BY id DESC''',(platform,platform,query,query))]

def rows(db, table):
    if table not in ('notes','relations'):
        raise ValueError('不明なテーブル')
    return [dict(r) for r in db.execute(f'SELECT * FROM {table} ORDER BY id DESC')]

def export_csv(records):
    if not records:
        return b''
    output = io.StringIO(newline='')
    writer = csv.DictWriter(output, fieldnames=list(records[0]))
    writer.writeheader()
    for row in records:
        writer.writerow({k: ("'" + v if isinstance(v,str) and v.lstrip().startswith(('=', '+', '-', '@', '\t', '\r')) else v) for k,v in row.items()})
    return output.getvalue().encode('utf-8-sig')
