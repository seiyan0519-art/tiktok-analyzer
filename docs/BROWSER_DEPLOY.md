# ブラウザで試す（Streamlit Community Cloud）

PCへのPython導入は不要です。GitHubとStreamlit Community Cloudへのログイン・連携は所有者が行ってください。公開操作を行うまではアプリ用URLは作られません。

1. https://share.streamlit.io/ を開き、GitHubでログインします。
2. Create app（アプリ作成）からGitHubリポジトリを指定します。
3. Repository: `seiyan0519-art/tiktok-analyzer`
4. Branch: `feat/cross-platform-research`（PRをマージ済みなら `main`）
5. Main file path: `app.py`
6. Advanced settingsでPython 3.12を選択します。
7. Deployを押します。Python依存はrequirements.txt、ffmpegはpackages.txtから導入されます。
8. アプリ設定のSharing／アクセス範囲を確認します。自分専用で使う場合は、他人がアクセスできない設定であることを確認してからデータを登録してください。プランやリポジトリの公開範囲によって設定の選択肢は変わります。
9. 最初は個人情報を含まないテスト動画で、登録・画像抽出・CSVダウンロードを試します。

## この公開方法の制限

動画・登録内容はStreamlitのホスティング先で処理・保存されます。AIへの送信はありません。TikTok取得ボタンを押した場合、動画ページURLのみTikTokの公式oEmbedへ送信します。アプリ内の利用者別データ分離は未実装なので、アクセスできる人は同じデータを閲覧できます。

Community Cloud上のローカルSQLiteとアップロード動画は永続保存を保証できません。再起動・再デプロイなどで失われる可能性があります。現段階は試用向けです。必要な調査結果はCSVでダウンロードし、元動画は手元に保管してください。本運用には外部DB・ファイル保存先と認証の追加が必要です。その接続や外部送信は事前確認のうえで実装します。

本手順は公開準備です。このリポジトリを更新しただけではデプロイや公開先での動作検証は完了しません。
