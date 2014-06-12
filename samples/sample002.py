# -*- coding: utf-8 -*-
"""
■【librtrt】ホームやユーザタイムラインからRTを抜き出してRtRTする例
・記事：http://d.hatena.ne.jp/furyu-tei/20140404/1396628020
"""
import os
import sys
import tweepy

sys.path.append('..')
from librtrt import Rtrt # librtrtのRtrt classをインポート

DEBUG = False
USER_NAME = 'TwitterJP' # ユーザタイムラインを取得する screen_name

LIMIT_RT = 5           # タイムラインから取得するRT件数の制限(最新からLIMIT_RT件目まで)
LIMIT_RTERS = 20       # RT人数制限(最新からLIMIT_RTERS人まで)


def logerr(str):
  sys.stderr.write((u'Error: %s\n' % (str)).encode('utf-8','replace'))
  
def log(str):
  sys.stdout.write((u'%s\n' % str).encode('utf-8','replace'))

def get_rtid_list(tl_iter): #{
  rtid_list = []
  for status in tl_iter:
    rt = getattr(status, 'retweeted_status', None)
    if rt:
      if DEBUG: log(rt.id)
      rtid_list.append(rt.id)
      if LIMIT_RT and LIMIT_RT <= len(rtid_list): break
  return rtid_list
#} // end of get_rtid_list()


rtrt = Rtrt(
  use_aauth=True # Application-only authentication を有効化
)

log(u'■ ユーザタイムラインのRTよりRtRT検索中…')
api = rtrt.api
tl_iter = tweepy.Cursor(api.user_timeline, screen_name=USER_NAME, count=rtrt.MAX_STATUSES_PER_CALL_TIMELINE).items()
rtid_list = get_rtid_list(tl_iter)
rtrt.get_rtrt(retweeted_ids=rtid_list, limit_rters=LIMIT_RTERS, debug=DEBUG)
rtrt.json_write('user_rt_rtrt')


log(u'■ ホームタイムラインのRTよりRtRT検索中…')
api = rtrt.oapi # OAuth用API使用時は明示的に Rtrt#oapi を使用
tl_iter = tweepy.Cursor(api.home_timeline, count=rtrt.MAX_STATUSES_PER_CALL_TIMELINE).items()
rtid_list = get_rtid_list(tl_iter)
rtrt.get_rtrt(retweeted_ids=rtid_list, limit_rters=LIMIT_RTERS, debug=DEBUG)
rtrt.json_write('home_rt_rtrt')
