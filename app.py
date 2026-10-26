import json
import os
import shutil
from pathlib import Path
import pandas as pd
import streamlit as st
from research import store
from research.video import inspect_upload
from providers.tiktok import fetch_public_metadata, TikTokError

st.set_page_config(page_title='Beauty Research | 横断リサーチ', page_icon='🔎', layout='wide')
DATA = Path(os.environ.get('RESEARCH_DATA_DIR', str(Path(__file__).parent / 'data'))).resolve()
db = store.connect(DATA / 'research.sqlite3')
st.title('🔎 Beauty Research')
st.caption('TikTok・YouTube・Xを横断する、美容コンテンツのリサーチノート')
st.info('TikTokのURLから公式公開情報を取得できます。動画本体・音声の取得とAI解析は未実装です。取得ボタンを押した場合だけ、追跡パラメーターを除いた動画URLをTikTokへ送信します。')
with st.sidebar:
    st.header('リサーチの範囲')
    query = st.text_input('キーワード検索', placeholder='タイトル・投稿本文・タグ・メモ')
    platform_filter = st.selectbox('SNSで絞り込み', ['すべて', *store.PLATFORMS])
    st.caption('URL登録は取得完了を意味しません。再生数・投稿日時・字幕などは未取得です。推測は確認済みの情報と分けて記録してください。')
    st.caption('公開投稿の関係だけで、不正行為や組織的宣伝を断定しないでください。')
all_contents = store.contents(db)
selected_contents = store.contents(db, query, platform_filter)
labels = {c['id']:f"#{c['id']} {c['platform']}｜{c['title']}" for c in all_contents}
register, library, notes_tab, relations_tab, comparison = st.tabs(['登録', '検索・閲覧', '分析メモ', '投稿の関係', '比較・CSV出力'])
with register:
    st.subheader('TikTokのURLから公開情報を取得')
    st.caption('公式oEmbedから説明文・投稿者名を取得します。料金・APIキーは不要です。動画を視聴した分析や、冒頭画像・音声の抽出は行いません。')
    with st.form('tiktok_url'):
        tiktok_url = st.text_input('TikTok動画のURL', placeholder='https://www.tiktok.com/@投稿者/video/数字')
        fetch_clicked = st.form_submit_button('TikTokの公開情報を取得')
    if fetch_clicked:
        st.session_state.pop('tiktok_preview', None)
        try:
            with st.spinner('TikTok公式の公開情報を確認中…'):
                st.session_state['tiktok_preview'] = fetch_public_metadata(tiktok_url)
        except TikTokError as exc:
            st.error(str(exc))
    if 'tiktok_preview' in st.session_state:
        preview = st.session_state['tiktok_preview']
        st.write('取得元：' + preview['provider'])
        st.write('投稿者：' + preview['author'])
        st.text(preview['caption'] or '説明文は空です。')
        st.caption('取得時刻（UTC）：' + preview['retrieved_at'])
        st.warning('未取得：' + '・'.join(preview['unavailable']) + '。説明文の記載内容が事実かどうかも未確認です。')
        if st.button('取得した公開情報を保存'):
            store.save_public_metadata(db, preview)
            st.session_state.pop('tiktok_preview', None)
            db.close()
            st.rerun()
    st.divider()
    st.subheader('コンテンツを手動登録')
    st.caption('権利を持つ動画・利用許諾のある動画だけをアップロードしてください。登録情報と動画はこの環境のdataフォルダーに保存されます。')
    with st.form('register',clear_on_submit=True):
        platform = st.selectbox('プラットフォーム',store.PLATFORMS)
        title = st.text_input('タイトル（必須）',max_chars=300)
        url = st.text_input('SNSのURL（ローカル動画以外は必須）')
        author = st.text_input('投稿者（必要な場合のみ）')
        body = st.text_area('投稿本文・説明（手動入力）')
        tags = st.text_input('タグ・商品名（自由入力）')
        upload = st.file_uploader('MP4動画（任意／ローカル動画の場合は必須・最大200MB）',type=['mp4'])
        submitted = st.form_submit_button('保存する',type='primary')
    if submitted:
        video_info = {}
        try:
            if not title.strip():
                raise ValueError('タイトルを入力してください。')
            store.validate_url(platform,url)
            if platform != 'ローカル動画' and not url.strip():
                raise ValueError('SNSのURLを入力してください。')
            if platform == 'ローカル動画' and upload is None:
                raise ValueError('MP4を選択してください。')
            if upload:
                with st.spinner('動画の長さと冒頭フレームを抽出中…'):
                    video_info = inspect_upload(upload.name,upload.getvalue(),DATA / 'videos')
            content_id = store.add_content(db,platform,title,url,author,body,tags,**video_info)
            st.session_state['saved_message'] = f'コンテンツ #{content_id} を保存しました。検索・閲覧タブで確認できます。'
            st.rerun()
        except ValueError as exc:
            if video_info:
                shutil.rmtree(Path(video_info['video_path']).parent,ignore_errors=True)
            st.error(str(exc))
    if 'saved_message' in st.session_state:
        st.success(st.session_state.pop('saved_message'))
with library:
    st.subheader(f'検索結果：{len(selected_contents)}件')
    if not selected_contents:
        st.write('登録データがありません。登録タブから追加してください。')
    for c in selected_contents:
        with st.expander(labels[c['id']]):
            st.write('登録情報の出所：' + c['source'])
            st.write({'URL':c['url'],'投稿者':c['author'],'投稿本文':c['body'],'タグ':c['tags'],'登録日時（UTC）':c['created_at']})
            metadata = store.public_metadata(db,c['id'])
            if metadata:
                st.caption('説明文・投稿者名：TikTok公式oEmbedから取得 ／ AI解析：未実施')
                st.caption('取得時刻（UTC）：' + metadata['retrieved_at'])
                st.caption('未取得：' + '・'.join(metadata['unavailable']))
            else:
                st.caption('SNSメタデータ：未取得 ／ AI解析：未実施')
            if c['duration'] is not None:
                st.metric('動画の長さ（ローカル抽出）',f"{c['duration']:.2f} 秒")
                if Path(c['video_path']).is_file():
                    st.video(c['video_path'])
                else:
                    st.warning('保存動画が見つかりません。バックアップからの復元を確認してください。')
                frames = json.loads(c['frames'])
                columns = st.columns(max(1,len(frames)))
                for column, frame in zip(columns,frames):
                    if Path(frame['path']).is_file():
                        column.image(frame['path'],caption=f"冒頭 {frame['second']} 秒（抽出画像）")
                if c['duration'] < 3:
                    st.caption('3秒未満の動画は、存在する秒数の画像だけを表示します。')
            for n in store.rows(db,'notes'):
                if n['content_id'] == c['id']:
                    st.write(f"【{n['status']}】{n['category']}：{n['text']}")
                    st.caption(f"根拠・理由：{n['evidence'] or '未記録'}")
with notes_tab:
    st.subheader('動画・投稿の分析メモ')
    if not labels:
        st.write('先にコンテンツを登録してください。')
    else:
        with st.form('note',clear_on_submit=True):
            content_id = st.selectbox('対象コンテンツ',list(labels),format_func=labels.get)
            category = st.selectbox('分析項目',store.CATEGORIES)
            status = st.selectbox('情報の状態',store.STATUSES,index=3)
            text = st.text_area('メモ本文')
            evidence = st.text_area('根拠・出典URL・動画の秒数／推測の理由')
            if st.form_submit_button('メモを保存'):
                try:
                    store.add_note(db,content_id,category,status,text,evidence)
                    st.success('メモを保存しました。')
                except ValueError as exc:
                    st.error(str(exc))
        st.caption('確認済みには根拠が必須です。この状態はユーザーの判断であり、システムが事実を保証するものではありません。')
with relations_tab:
    st.subheader('投稿間の関係・販売導線')
    st.caption('矢印は「関係元 → 関係先」。リプライや宣伝の根拠URLを記録してください。協調や不正を自動判定する機能はありません。')
    if len(labels) < 2:
        st.write('関係を記録するにはコンテンツを2件以上登録してください。')
    else:
        with st.form('relation',clear_on_submit=True):
            source = st.selectbox('関係元',list(labels),format_func=labels.get)
            target = st.selectbox('関係先',list(labels),index=1,format_func=labels.get)
            kind = st.selectbox('関係の種類',store.RELATIONS)
            state = st.selectbox('関係の状態',store.STATUSES,index=3)
            reason = st.text_area('根拠・理由（必須）')
            if st.form_submit_button('関係を保存'):
                try:
                    store.add_relation(db,source,target,kind,state,reason)
                    st.success('関係を保存しました。')
                except ValueError as exc:
                    st.error(str(exc))
    for r in store.rows(db,'relations'):
        st.write(f"{labels[r['source_id']]} → {labels[r['target_id']]}")
        st.caption(f"{r['kind']}／{r['status']}：{r['evidence']}")
with comparison:
    st.subheader('コンテンツを横並びで比較')
    ids = [c['id'] for c in selected_contents]
    choices = st.multiselect('比較するコンテンツ（最大4件）',ids,format_func=labels.get,max_selections=4)
    all_notes = store.rows(db,'notes')
    if choices:
        table = {}
        for c in selected_contents:
            if c['id'] in choices:
                entry = {'SNS':c['platform'],'URL':c['url'],'タグ':c['tags'],'長さ（秒）':str(c['duration']) if c['duration'] is not None else '未取得','SNSメタデータ':'説明文・投稿者名を取得（他は未取得）' if c['source']=='TikTok公式oEmbed' else '未取得','AI解析':'未実施'}
                for category in store.CATEGORIES:
                    entry[category] = '\n'.join(f"【{n['status']}】{n['text']}（根拠：{n['evidence'] or '未記録'}）" for n in all_notes if n['content_id']==c['id'] and n['category']==category) or '未記録'
                table[labels[c['id']]] = entry
        st.dataframe(pd.DataFrame(table),width='stretch')
    st.caption('比較は手動メモの一覧です。成功の因果関係や販売実績は自動判定しません。')
    export_contents = [{**c,'sns_metadata_status':'説明文・投稿者名を取得（他は未取得）' if c['source']=='TikTok公式oEmbed' else '未取得', 'metadata_provenance':json.dumps(store.public_metadata(db,c['id']),ensure_ascii=False),'ai_analysis_status':'未実施'} for c in selected_contents]
    export_notes = [n for n in all_notes if n['content_id'] in ids]
    export_relations = [r for r in store.rows(db,'relations') if r['source_id'] in ids and r['target_id'] in ids]
    for label,records,filename in [('コンテンツ',export_contents,'contents.csv'),('メモ',export_notes,'notes.csv'),('関係',export_relations,'relations.csv')]:
        st.download_button(f'{label}CSVをダウンロード',store.export_csv(records),file_name=filename,mime='text/csv',disabled=not records)
    st.caption('検索・SNS絞り込みがCSVにも適用されます。関係は両端のコンテンツが検索範囲にある場合に出力します。CSVはUTF-8 BOM付き、数式として解釈される入力を無害化しています。')
db.close()
