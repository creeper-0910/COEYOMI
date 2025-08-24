# COEIROINK 読み上げbot v25
![COEYOMI](https://raw.githubusercontent.com/creeper-0910/COEYOMI/main/COEYOMI.png)
## 環境
* Python 3.12
* Poetry 2.1.3
* ffpmeg 2025-08-22
* COEIROINK v2.12.1
## インストール
`config.toml.template`を`config.toml`にリネームしてください。  
DiscordのBOTトークンを取得し、`config.toml`内に書き込み、保存してください。  

COEIROINKフォルダ内に  
* engine (フォルダ)
* speaker_info (フォルダ)
* COEIROINKv2.exe (ファイル)  

をコピーしてください。  

ffmpegフォルダ内に  
* ffmpeg.exe (ファイル)
* ffplay.exe (ファイル)
* ffprobe.exe (ファイル)  

をコピーしてください  

python 3.12をインストールし、[Poetryのインストール手順](https://python-poetry.org/docs/#installation)を参考にPoetryをインストールしてください。  
その後、以下のコマンドを実行して、実行してください。
```bash
poetry install
poetry run py coeyomi.py
```
### 参考文献・必須ファイル
[Pycord ドキュメント](https://docs.pycord.dev/ja/master)  
[ffpmeg](https://github.com/btbn/ffmpeg-builds/releases)
[COEIROINK](https://coeiroink.com/download)
ありがとうございます！  