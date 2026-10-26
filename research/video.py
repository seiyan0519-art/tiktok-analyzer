"""ffprobe/ffmpegでローカル動画のみ処理する。ネットワーク入力は受け付けない。"""
import json
import math
import shutil
import subprocess
from pathlib import Path
from uuid import uuid4

MAX_BYTES = 200 * 1024 * 1024

def inspect_upload(name, payload, root):
    if Path(name).suffix.lower() != '.mp4' or not 0 < len(payload) <= MAX_BYTES:
        raise ValueError('MP4形式・200MB以下・空でない動画を指定してください。')
    if not all(shutil.which(tool) for tool in ('ffmpeg','ffprobe')):
        raise ValueError('ffmpegとffprobeをインストールしてください。')
    folder = Path(root) / uuid4().hex
    folder.mkdir(parents=True)
    path = folder / 'video.mp4'
    try:
        path.write_bytes(payload)
        result = subprocess.run(['ffprobe','-v','error','-protocol_whitelist','file','-show_format','-show_streams','-of','json',str(path)],capture_output=True,timeout=30,check=True)
        metadata = json.loads(result.stdout)
        if not any(s.get('codec_type') == 'video' for s in metadata.get('streams',[])):
            raise ValueError('映像トラックのあるMP4を選択してください。')
        if not ({'mov','mp4'} & set(metadata.get('format',{}).get('format_name','').split(','))):
            raise ValueError('MP4コンテナを確認できませんでした。')
        duration = float(metadata['format']['duration'])
        if not math.isfinite(duration) or duration <= 0:
            raise ValueError('動画の長さを取得できませんでした。')
        frames = []
        for second in (0,1,2):
            if second >= duration:
                continue
            frame = folder / f'frame-{second}.jpg'
            subprocess.run(['ffmpeg','-v','error','-nostdin','-protocol_whitelist','file','-ss',str(second),'-i',str(path),'-map','0:v:0','-frames:v','1','-vf','scale=480:-2','-threads','1',str(frame)],capture_output=True,timeout=30,check=True)
            if not frame.exists() or not frame.stat().st_size:
                raise ValueError('冒頭フレームを抽出できませんでした。')
            frames.append({'second':second,'path':str(frame)})
        return {'video_path':str(path),'duration':duration,'frames':json.dumps(frames)}
    except Exception as exc:
        shutil.rmtree(folder,ignore_errors=True)
        if isinstance(exc, ValueError):
            raise
        raise ValueError('動画を読み込めませんでした。破損していないMP4か確認してください。') from exc
