# -*- coding: utf-8 -*-
"""
■【librtrt】デフォルトの動作
・自分のツイートを公式RTした人のRT直後の発言を取得(最大5RT・各5名まで)
"""
import os
import sys

sys.path.append('..')
from librtrt import Rtrt # librtrtのRtrt classをインポート

def logerr(str):
  sys.stderr.write((u'Error: %s\n' % (str)).encode('utf-8','replace'))
  
def log(str):
  print str.encode('utf-8','replace')

if not os.path.exists('config.yaml'):
  logerr(u'カレントディレクトリに設定ファイル(config.yaml)が必要')
  sys.exit(1)

log(u'■Rtrtオブジェクト作成')
rtrt = Rtrt()

log(u'■自分のツイートを公式RTした人のRT直後の発言を取得中...')
rtrt_info_list = rtrt.get_rtrt()

log(u'■結果をファイル "rtrt.json" に出力')
rtrt.json_write('rtrt')
