"""TikTok公式oEmbedから公開メタデータのみ取得。動画本体は取得しない。"""
import re
from datetime import datetime, timezone
from urllib.parse import urlsplit
import requests

class TikTokError(ValueError):
    pass

def canonical_url(value):
    parts = urlsplit(value.strip())
    if parts.scheme != 'https' or parts.hostname not in ('www.tiktok.com','tiktok.com') or parts.username or parts.password or parts.port:
        raise TikTokError('https://www.tiktok.com/@投稿者/video/数字 の形式で入力してください。')
    if not re.fullmatch(r'/@[A-Za-z0-9_.]+/video/[0-9]+/?', parts.path):
        raise TikTokError('短縮URLではなく、TikTokの動画ページURLを貼り付けてください。')
    return 'https://www.tiktok.com' + parts.path.rstrip('/')

def fetch_public_metadata(value):
    url = canonical_url(value)
    try:
        response = requests.get('https://www.tiktok.com/oembed', params={'url':url}, timeout=20, allow_redirects=False)
        if response.status_code != 200:
            raise TikTokError(f'TikTokの公開情報を取得できませんでした（HTTP {response.status_code}）。公開範囲・アクセス制限・サービス状況などが考えられます。取得済みとしては保存しません。')
        payload = response.json()
        if not isinstance(payload,dict) or not isinstance(payload.get('title'),str) or not isinstance(payload.get('author_name'),str):
            raise TikTokError('TikTokの応答に必要な公開情報がありません。')
        return {'url':url,'caption':payload['title'],'author':payload['author_name'],
                'provider':'TikTok公式oEmbed','retrieved_at':datetime.now(timezone.utc).isoformat(),
                'unavailable':['動画本体','冒頭フレーム','動画の長さ','音声','テロップ','再生数','商品・CTAの映像分析']}
    except requests.RequestException as exc:
        raise TikTokError('TikTokへ接続できませんでした。ネットワーク設定や一時的な制限が考えられます。動画の削除を意味するものではありません。') from exc
    except (TypeError, ValueError) as exc:
        if isinstance(exc,TikTokError):
            raise
        raise TikTokError('TikTokの応答を読み取れませんでした。') from exc
