librtrt
=======
Twitterで公式RT直後の発言を取得するためのPythonモジュール  
　License: The MIT license  
　Copyright (c) 2014 風柳(furyu)  
　記事：[【librtrt】Twitterで公式RT直後の発言を取得するためのPythonモジュールを試作](http://d.hatena.ne.jp/furyu-tei/20140403/1396534292)  

使い方
------
### 準備
1. PyYAML と tweepy を easy_install や pip 等でインストール
2. librtrtディレクトリを、実行するスクリプトと同一ディレクトリ、もしくは $PYTHONPATH 下に設置
3. config.yaml.sample を参考に、自分のTwitter認証情報を含む config.yaml を作成し、実行するスクリプトと同一ディレクトリに設置

### 使用例
```python
from librtrt import Rtrt # librtrtのRtrt classをインポート
rtrt = Rtrt() # オブジェクト作成
rtrt_info_list = rtrt.get_rtrt() # 自分のツイートを公式RTした人のRT直後の発言を取得
rtrt.json_write('rtrt') # JSON 形式でファイルに出力
```
※ オプション等については、librtrt.py 内もしくは help(Rtrt) で。


参考
----
- [RtRTはAPI廃止でダメになった→すまん、ありゃウソだった - esuji5's diary](http://esuji5.hateblo.jp/entry/2014/04/01/233633)
- [tweepyでApplication-only authenticationしてみた - Shogo’s Blog](http://shogo82148.github.io/blog/2013/05/09/application-only-authentication-with-tweepy/)
