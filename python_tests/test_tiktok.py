from unittest.mock import Mock
import requests
import pytest
from providers.tiktok import canonical_url, fetch_public_metadata, TikTokError
from research import store
from streamlit.testing.v1 import AppTest

URL = 'https://www.tiktok.com/@mote_fox/video/7663801543338200341'

def test_canonical_url_removes_tracking():
    assert canonical_url(URL+'?web_id=private&sender_device=pc') == URL
    for url in ['https://www.tiktok.com.evil.test/@a/video/1','https://user:pw@www.tiktok.com/@a/video/1','http://www.tiktok.com/@a/video/1','https://vm.tiktok.com/abc','https://www.tiktok.com:444/@a/video/1']:
        with pytest.raises(TikTokError): canonical_url(url)

def test_fetch_and_persist(monkeypatch,tmp_path):
    get = Mock(return_value=Mock(status_code=200,json=lambda:{'title':'美容レビュー #美容','author_name':'テスト投稿者'}))
    monkeypatch.setattr('providers.tiktok.requests.get',get)
    result = fetch_public_metadata(URL+'?web_id=private')
    assert get.call_args.kwargs['params'] == {'url':URL}
    assert get.call_args.kwargs['allow_redirects'] is False
    assert '動画本体' in result['unavailable']
    db = store.connect(tmp_path/'test.db')
    content_id = store.save_public_metadata(db,result)
    assert store.contents(db)[0]['source'] == 'TikTok公式oEmbed'
    assert store.public_metadata(db,content_id) == result
    assert store.contents(db)[0]['duration'] is None
    db.close()

@pytest.mark.parametrize('response',[Mock(status_code=403),Mock(status_code=404),Mock(status_code=200,json=lambda:{}),Mock(status_code=200,json=lambda:[])])
def test_failed_or_missing_response(monkeypatch,response):
    monkeypatch.setattr('providers.tiktok.requests.get',Mock(return_value=response))
    with pytest.raises(TikTokError): fetch_public_metadata(URL)

def test_network_error(monkeypatch):
    monkeypatch.setattr('providers.tiktok.requests.get',Mock(side_effect=requests.Timeout()))
    with pytest.raises(TikTokError,match='接続できません'): fetch_public_metadata(URL)

def test_ui_preview_save_and_error(monkeypatch,tmp_path):
    monkeypatch.setenv('RESEARCH_DATA_DIR',str(tmp_path))
    get = Mock(return_value=Mock(status_code=200,json=lambda:{'title':'公開説明文','author_name':'投稿者'}))
    monkeypatch.setattr('providers.tiktok.requests.get',get)
    at = AppTest.from_file('app.py').run()
    next(e for e in at.text_input if e.label=='TikTok動画のURL').input(URL)
    next(e for e in at.button if e.label=='TikTokの公開情報を取得').click().run()
    assert not at.exception
    assert any(e.value=='公開説明文' for e in at.text)
    next(e for e in at.button if e.label=='取得した公開情報を保存').click().run()
    assert not at.exception
    assert len(at.expander)==1
    get.side_effect=requests.Timeout()
    next(e for e in at.text_input if e.label=='TikTok動画のURL').input(URL)
    next(e for e in at.button if e.label=='TikTokの公開情報を取得').click().run()
    assert len(at.error)==1
    assert 'tiktok_preview' not in at.session_state
