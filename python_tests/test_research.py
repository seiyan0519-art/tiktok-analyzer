import json
import subprocess
import csv
import io
import pytest
from research import store
from research.video import inspect_upload
from streamlit.testing.v1 import AppTest

@pytest.fixture
def db(tmp_path):
    connection = store.connect(tmp_path / 'test.sqlite3')
    yield connection
    connection.close()

def test_registration_search_notes_relation_and_csv(db):
    a = store.add_content(db,'YouTube','化粧水レビュー','https://youtu.be/example',body='使用感')
    b = store.add_content(db,'X','紹介への返信','https://x.com/example/status/123')
    store.add_note(db,a,'CTA','推測','購入への誘導かもしれない','動画の2秒')
    store.add_relation(db,b,a,'引用・参照','ユーザー入力','投稿本文の参照URL')
    assert store.contents(db,'誘導')[0]['id'] == a
    assert len(store.contents(db,platform='X')) == 1
    assert store.contents(db,"' OR 1=1 --") == []
    assert store.rows(db,'notes')[0]['status'] == '推測'
    assert store.rows(db,'relations')[0]['target_id'] == a
    output = list(csv.DictReader(io.StringIO(store.export_csv([{'title':'=1+1','body':'美容,商品\nレビュー'}]).decode('utf-8-sig'))))
    assert output[0] == {'title':"'=1+1",'body':'美容,商品\nレビュー'}

def test_validation_and_persistence(tmp_path):
    path = tmp_path / 'persistent.sqlite3'
    db = store.connect(path)
    a = store.add_content(db,'TikTok','動画','https://www.tiktok.com/@example/video/123')
    with pytest.raises(ValueError):
        store.add_content(db,'X','偽URL','https://x.com.evil.invalid/status/1')
    with pytest.raises(ValueError):
        store.add_content(db,'X','認証情報入り','https://user:password@x.com/status/1')
    with pytest.raises(ValueError):
        store.add_note(db,a,'CTA','確認済み','購入リンク','')
    with pytest.raises(ValueError):
        store.add_relation(db,a,a,'リプライ','推測','同一')
    with pytest.raises(ValueError):
        store.add_content(db,'ローカル動画','空')
    db.close()
    db = store.connect(path)
    assert store.contents(db)[0]['title'] == '動画'
    db.close()

@pytest.mark.parametrize('duration,expected',[(4,3),(0.5,1)])
def test_real_video(tmp_path,duration,expected):
    source = tmp_path / 'source.mp4'
    subprocess.run(['ffmpeg','-v','error','-f','lavfi','-i',f'testsrc2=size=120x160:rate=10:duration={duration}','-c:v','libx264',str(source)],check=True)
    result = inspect_upload('動画.mp4',source.read_bytes(),tmp_path / 'uploads')
    assert result['duration'] == pytest.approx(duration,abs=.1)
    frames = json.loads(result['frames'])
    assert len(frames) == expected
    from pathlib import Path
    assert all(Path(frame['path']).stat().st_size > 0 for frame in frames)
    assert len({Path(frame['path']).read_bytes() for frame in frames}) == expected

def test_broken_video_cleanup(tmp_path):
    with pytest.raises(ValueError):
        inspect_upload('bad.mp4',b'not mp4',tmp_path / 'uploads')
    assert list((tmp_path / 'uploads').iterdir()) == []
    with pytest.raises(ValueError):
        inspect_upload('bad.txt',b'bad',tmp_path / 'uploads')

def test_ui_registration_note_comparison(tmp_path,monkeypatch):
    monkeypatch.setenv('RESEARCH_DATA_DIR',str(tmp_path / 'appdata'))
    at = AppTest.from_file('app.py').run()
    assert not at.exception
    at.selectbox[0].select('X')
    next(e for e in at.text_input if e.label=='タイトル（必須）').input('美容投稿')
    next(e for e in at.text_input if e.label=='SNSのURL（ローカル動画以外は必須）').input('https://x.com/example/status/1')
    next(e for e in at.button if e.label=='保存する').click().run()
    assert not at.exception
    assert len(at.expander) == 1
    at.text_area[1].input('冒頭の商品提示が目立つ')
    at.text_area[2].input('手動で動画0秒を確認')
    next(e for e in at.button if e.label=='メモを保存').click().run()
    assert not at.exception
    at.run()
    at.multiselect[0].select(1).run()
    assert len(at.dataframe) == 1
    assert '冒頭の商品提示が目立つ' in at.dataframe[0].value.to_string()
    assert not at.exception
