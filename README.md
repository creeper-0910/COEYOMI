# COEIROINK 読み上げbot v2 API
## 環境
* Python 3.10
* ffpmeg 2024-2-26
* COEIROINK v2.3.3
## インストール
DiscordのBOTトークンを取得し、sample.env内に書き込み、.envに名前を変更して保存してください。  

COEIROINKフォルダ内に  
* engine (フォルダ)
* speaker_info (フォルダ)
* COEIROINKv2.exe (ファイル)  

をコピーしてください。  

binフォルダ内に  
* ffmpeg.exe (ファイル)
* ffplay.exe (ファイル)
* ffprobe.exe (ファイル)  

をコピーしてください  

python 3.10をインストールし、  
```shell
pip install -r requirements.txt
python3 main.py
```  
を実行してください。
### 参考文献
[Discord.py ドキュメント](https://discordpy.readthedocs.io/ja/latest)  
[aka7004さんのnote(無料範囲)](https://note.com/aka7004/n/n235d251f9da3)  
ありがとうございます！  

一部コードの簡略化にChat GPTを使用している場合があります。