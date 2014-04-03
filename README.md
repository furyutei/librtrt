librtrt
=======

Twitterで公式RT直後の発言を取得するためのPythonモジュール

使い方
------
### 準備
1. PyYAML と tweepy を easy_install や pip 等でインストール
2. librtrt.py・AppAuthHandler.py を同一ディレクトリに設置
3. config.yaml.sample を参照に、自分のTwitter認証情報を含む config.yaml を作成し、同一ディレクトリに設置

### 使用例
```python
from librtrt import Rtrt # librtrtのRtrt classをインポート
rtrt = Rtrt() # オブジェクト作成
rtrt_info_list = rtrt.get_rtrt() # 自分のツイートを公式RTした人のRT直後の発言を取得
rtrt.json_write('rtrt') # JSON 形式でファイルに出力
```
※ オプション等については、librtrt.py 内もしくは help(Rtrt) で。

