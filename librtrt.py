# -*- coding: utf-8 -*-
"""
Twitter公式RT直後の発言を取得するライブラリ

■ オリジナル
  http://esuji5.hateblo.jp/entry/2014/04/01/233633
  「RtRTはAPI廃止でダメになった→すまん、ありゃウソだった - esuji5's diary」
  を元に、class 化。

■ 準備
  ・PyYAML と tweepy を easy_install や pip 等で予めインストールしておくこと。
  ・同一ディレクトリ下に AppAuthHandler.py を置いておくこと。
  ・必要に応じて、認証情報ファイル(config.yaml)を用意すること。
    ※認証情報ファイルが無い場合、Rtrt() の引数で指定すること。

■ 使い方
  >>> from librtrt import Rtrt # librtrtのRtrt classをインポート
  >>> rtrt = Rtrt() # オブジェクト作成
  >>> rtrt_info_list = rtrt.get_rtrt() # 自分のツイートを公式RTした人のRT直後の発言を取得
  >>> rtrt.json_write('rtrt') # JSON 形式でファイルに出力
"""

import os
import sys
import re
import json
import codecs
import traceback
import datetime
import urllib
import urllib2
import lxml.html as lxml_html

import yaml   # pip install PyYAML
import tweepy # pip install tweepy
import AppAuthHandler # 別ファイル(AppAuthHandler.py)で提供


__author__    = 'furyu (furyutei@gmail.com)'
__version__   = '0.0.2'


class Rtrt(object): #{
  #{ //***** static paratemters
  DEFAULT_DEBUG = False
  
  DEFAULT_CONFIG = 'config.yaml'
  DEFAULT_USE_AAUTH = False
  
  DEFAULT_LIMIT_RTS_OF_ME = 5
  DEFAULT_LIMIT_RTERS = 5
  DEFAULT_LIMIT_STATUSES = 3200
  DEFAULT_RTRT_WAIT = 5 # RTへの言及は5分以内に行われる場合がほとんど(@esujiさんの情報(経験則)より)
  
  DEFAULT_USE_TIMELINE = True
  DEFAULT_USE_SEARCH = False
  DEFAULT_USE_SEARCH_API = False
  DEFAULT_INCLUDE_RT = False
  
  DEFAULT_JSON_FILENAME = 'rtrt'
  DEFAULT_JSON_EXT = 'json'
  DEFAULT_JSON_INDENT = 4
  
  MAX_RTS_OF_ME = 100
  MAX_RTERS = 100
  MAX_STATUSES = 3200
  
  MAX_STATUSES_PER_CALL_TIMELINE = 200
  MAX_STATUSES_PER_CALL_SEARCH = 100
  
  RATE_STATUS_PER_SEC = 0x0FA000000 # 2010.11.4 22:00(UTC)頃にstatusのidが約30,000,000,000→約300,000,000,000,000になり、その後はほぼ一定速度で増加
  #} // end of static paratemters
  
  #{ //***** functions
  def __init__(self, *argv, **kargv): #{
    """
    Options:
      consumer_key       : CONSUMER_KEY for ?Auth        (default: None => read from config)
      consumer_secret    : CONSUMER_SECRET for ?Auth     (default: None => read from config)
      access_token       : ACCESS_TOKEN for OAuth        (default: None => read from config)
      access_token_secret: ACCESS_TOKEN_SECRET for OAuth (default: None => read from config)
      config             : <YAML filename>               (default: DEFAULT_CONFIG)
      use_aauth          : True/False                    (default: DEFAULT_USE_AAUTH)
      debug              : True/False                    (default: DEFAULT_DEBUG)
      (*) ?Auth = OAuth or AAuth(Application-only authentication)
    """
    self.flg_debug = kargv.get('debug', self.DEFAULT_DEBUG)
    (logdebug, log, logerr) = (self.logdebug, self.log, self.logerr)
    
    consumer_key = kargv.get('consumer_key')
    consumer_secret = kargv.get('consumer_secret')
    access_token = kargv.get('access_token')
    access_token_secret = kargv.get('access_token_secret')
    config = kargv.get('config', self.DEFAULT_CONFIG)
    conf = {}
    try:
      if os.path.exists(config): conf = yaml.load(open(config,'rb').read().decode('utf-8','ignore'))
    except Exception, s:
      logerr(traceback.format_exc())
      pass
    if not consumer_key: consumer_key = conf.get('CONSUMER_KEY')
    if not consumer_secret: consumer_secret = conf.get('CONSUMER_SECRET')
    if not access_token: access_token = conf.get('ACCESS_TOKEN')
    if not access_token_secret: access_token_secret = conf.get('ACCESS_TOKEN_SECRET')
    
    self.oapi = None
    self.aapi = None
    if consumer_key and consumer_secret:
      if access_token and access_token_secret:
        try:
          oauth = tweepy.OAuthHandler(consumer_key, consumer_secret)
          oauth.set_access_token(access_token, access_token_secret)
          self.oapi = tweepy.API(oauth)
          self.oapi.rate_limit_status()
        except Exception, s:
          self.oapi = None
          logerr(traceback.format_exc())
          logerr('Error: failed to initialize OAuth API')
      
      self.aapi = None
      if kargv.get('use_aauth', self.DEFAULT_USE_AAUTH):
        try:
          aauth = AppAuthHandler.AppAuthHandler(consumer_key, consumer_secret)
          self.aapi = tweepy.API(aauth)
          self.aapi.rate_limit_status()
        except Exception, s:
          self.aapi = None
          logerr(traceback.format_exc())
          logerr('Error: failed to initialize Application-only Auth API')
    else:
      logerr('Error: consumer key or secret not found')
    self.api = self.aapi if self.aapi else self.oapi
    self.rtrt_info_list = []
  #} // end of def __init__()
  
  
  def get_rtrt(self, *argv, **kargv): #{
    """
    Options:
      retweeted_ids     : [id0,id1,...]     (default: [] => get retweeted statuses with 'statuses/retweets_of_me')
      retweet_user_ids  : [id0,id1,...]     (default: [])
      retweet_user_names: [name1,name2,...] (default: [])
      limit_rts_of_me   : 1~MAX_RTS_OF_ME   (default: DEFAULT_LIMIT_RTS_OF_ME)
      limit_rters       : 1~MAX_RTERS       (default: DEFAULT_LIMIT_RTERS)
      limit_statuses    : 1~MAX_STATUSES    (default: DEFAULT_LIMIT_STATUSES)
      limit_rtrt_wait   : 0, or 1~          (default: DEFAULT_RTRT_WAIT(minutes), 0: ignore) 
      use_timeline      : True/False        (default: DEFAULT_USE_TIMELINE)
      use_search        : True/False        (default: DEFAULT_USE_SEARCH)
      use_search_api    : True/False        (default: DEFAULT_USE_SEARCH_API)
      include_rt        : True/False        (default: DEFAULT_INCLUDE_RT)
      debug             : True/False        (default: DEFAULT_DEBUG)
    """
    _debug = kargv.get('debug')
    if _debug is not None: self.flg_debug = _debug
    (logdebug, log, logerr) = (self.logdebug, self.log, self.logerr)
    try:
      retweeted_id_list = [int(v) for v in kargv.get('retweeted_ids', [])]
    except:
      logerr(traceback.format_exc())
      retweeted_id_list = []
    
    try:
      retweet_user_id_list = [int(v) for v in kargv.get('retweet_user_ids', [])]
    except:
      logerr(traceback.format_exc())
      retweet_user_id_list = []
    
    try:
      retweet_user_name_list = [v.strip() for v in kargv.get('retweet_user_names', [])]
    except:
      logerr(traceback.format_exc())
      retweet_user_name_list = []
    
    flg_check_user = True if 0 < len(retweet_user_id_list) or 0 < len(retweet_user_name_list) else False
    retweet_user_id_dict = dict(zip(retweet_user_id_list, [1 for v in retweet_user_id_list]))
    retweet_user_name_dict = dict(zip(retweet_user_name_list, [1 for v in retweet_user_name_list]))
    
    try:
      limit_rts_of_me = int(kargv.get('limit_rts_of_me', self.DEFAULT_LIMIT_RTS_OF_ME))
      if limit_rts_of_me < 1 or self.MAX_RTS_OF_ME < limit_rts_of_me: limit_rts_of_me = self.DEFAULT_LIMIT_RTS_OF_ME
    except Exception, s:
      logerr(traceback.format_exc())
      limit_rts_of_me = self.DEFAULT_LIMIT_RTS_OF_ME
    
    try:
      limit_rters = int(kargv.get('limit_rters', self.DEFAULT_LIMIT_RTERS))
      if limit_rters < 1 or self.MAX_RTERS < limit_rters: limit_rters = self.DEFAULT_LIMIT_RTERS
    except Exception, s:
      logerr(traceback.format_exc())
      limit_rters = self.DEFAULT_LIMIT_RTERS
    
    try:
      limit_statuses = int(kargv.get('limit_statuses', self.DEFAULT_LIMIT_STATUSES))
      if limit_statuses < 1 or self.MAX_STATUSES < limit_statuses: limit_statuses = self.DEFAULT_LIMIT_STATUSES
    except Exception, s:
      logerr(traceback.format_exc())
      limit_statuses = self.DEFAULT_LIMIT_STATUSES
    
    try:
      limit_rtrt_wait = int(kargv.get('limit_rtrt_wait', self.DEFAULT_RTRT_WAIT))
      if limit_rtrt_wait < 0: limit_rtrt_wait = self.DEFAULT_RTRT_WAIT
    except Exception, s:
      limit_rtrt_wait = self.DEFAULT_RTRT_WAIT
    
    limit_rtrt_count = self.RATE_STATUS_PER_SEC * limit_rtrt_wait * 60
    
    use_timeline = kargv.get('use_timeline', self.DEFAULT_USE_TIMELINE)
    use_search = kargv.get('use_search', self.DEFAULT_USE_SEARCH)
    use_search_api = kargv.get('use_search_api', self.DEFAULT_USE_SEARCH_API)
    include_rt = kargv.get('include_rt', self.DEFAULT_INCLUDE_RT)
    
    (oapi, aapi, api) = (self.oapi, self.aapi, self.api)
    
    retweeted_list = []
    if 0 < len(retweeted_id_list):
      for rtid in retweeted_id_list:
        try:
          retweeted_list.append(api.get_status(id=rtid))
        except:
          logerr(traceback.format_exc())
    else:
      try:
        retweeted_list = oapi.retweets_of_me(count=limit_rts_of_me)
      except Exception, s:
        logerr(traceback.format_exc())
    
    rtrt_info_list = []
    
    for retweeted in retweeted_list:
      logdebug('retweeted_id: %s' % (retweeted.id))
      
      rtrt_info = dict(
        rted_status = self._get_rtrt_status(retweeted),
        rtrts = [],
      )
      rtrts = rtrt_info['rtrts']
      while True:
        try:
          #retweets = api.retweets(id=retweeted.id, count=limit_rters)
          retweets = api.retweets(id=retweeted.id, count=self.MAX_RTERS)
        except Exception, s:
          logerr(traceback.format_exc())
          break
        
        for retweet in retweets:
          rt_user_id = retweet.user.id
          rt_user_name = retweet.user.screen_name
          search_id = retweet.id
          logdebug('retweeted by "%s" (search_id=%s)' % (rt_user_name, search_id))
          if flg_check_user:
            if not retweet_user_id_dict.get(rt_user_id) and not retweet_user_name_dict.get(rt_user_name):
              logdebug('=> skipped')
              continue
          
          (tgt_status, status_list) = (None, [])
          created_at = retweet.created_at
          #since = (created_at-datetime.timedelta(hours=24*1)).strftime('%Y-%m-%d')
          since = created_at.strftime('%Y-%m-%d')
          until = (created_at+datetime.timedelta(hours=24*2)).strftime('%Y-%m-%d')
          query = 'from:%s since:%s until:%s' % (rt_user_name, since, until)
          
          (since_id, max_id) = (search_id, None)
          if 0 < limit_rtrt_count:
            max_id = since_id + limit_rtrt_count
          else:
            for status in self._iter_search(query=query, limit=1):
              if since_id < status.id:
                max_id = status.id
          
          logdebug('initial max_id=%s' % (max_id))
          if max_id:
            query = 'from:%s since_id:%s max_id:%s' % (rt_user_name, since_id, max_id)
          
          if use_timeline and not tgt_status:
            try:
              logdebug('  retweet.user.id: %s' % (retweet.user.id))
              cursor = tweepy.Cursor(api.user_timeline, id=retweet.user.id, count=self.MAX_STATUSES_PER_CALL_TIMELINE, include_rts=True)
              """■メモ
               - tweepy.Cursor() の引数として max_id を渡すとイテレート中に例外が発生(不具合？)
               - cursor.iterator.max_id・cursor.iterator.since_id 共に自然数で初期化しておかないと正常動作しない。
               - cursor.iterator.since_id に初期値を渡すと、最初のAPIコール時の max_id に cursor.iterator.since_id - 1 が渡される
              """
              cursor.iterator.max_id = max_id + 1 if max_id else None
              cursor.iterator.since_id = max_id
              tl_iter = cursor.items(limit=limit_statuses)
              (tgt_status, status_list) = self._check_timeline(search_id, tl_iter, limit_statuses, include_rt)
            except Exception, s:
              logerr(traceback.format_exc())
          
          if use_search and not tgt_status:
            try:
              logdebug('  query: %s' % (query))
              if use_search_api:
                tl_iter = tweepy.Cursor(api.search, q=query, count=self.MAX_STATUSES_PER_CALL_SEARCH).items(limit=limit_statuses)
              else:
                tl_iter = self._iter_search(query=query, limit=limit_statuses)
              (tgt_status, status_list) = self._check_timeline(search_id, tl_iter, limit_statuses, include_rt)
            except Exception, s:
              logerr(traceback.format_exc())
          
          if tgt_status:
            rtrt_status = self._get_rtrt_status(tgt_status)
            logdebug('=> found (%s)' % (tgt_status.id))
          else:
            rtrt_status = self._get_rtrt_status(retweet)
            rtrt_status.update(
              id = '',
              text = '<<< NOT FOUND >>>',
              created_at = '',
              retweet_count = 0,
            )
            logdebug('=> not found')
          rtrts.append(rtrt_status)
          if limit_rters <= len(rtrts):
            break
        break
      
      rtrt_info_list.append(rtrt_info)
      
      logdebug('='*80)
    
    self.rtrt_info_list = rtrt_info_list
    
    return rtrt_info_list
  #} // end of get_rtrt()
  
  
  def json_write(self, filename=None, *argv, **kargv): #{
    """
    Options:
      filename      : <JSON file's name>       (default: DEFAULT_JSON_FILENAME)
      rtrt_info_list: <results of get_rtrt()>  (default: None => most recent results of get_rtrt())
      ext           : <JSON file's extension>  (default: DEFAULT_JSON_EXT)
      indent        : <indent of JSON>         (default: DEFAULT_JSON_INDENT)
    """
    (logdebug, log, logerr) = (self.logdebug, self.log, self.logerr)
    
    if not filename: filename = self.DEFAULT_JSON_FILENAME
    rtrt_info_list = kargv.get('rtrt_info_list', self.rtrt_info_list)
    ext = kargv.get('ext', self.DEFAULT_JSON_EXT)
    indent = kargv.get('indent', self.DEFAULT_JSON_INDENT)
    
    encoding = sys.getfilesystemencoding()
    if isinstance(filename, unicode): filename = filename.encode(encoding,'ignore')
    if isinstance(ext, unicode): ext = ext.encode(encoding,'ignore')
    fn = [filename]
    if ext: fn.append(ext)
    
    fp = codecs.open('.'.join(fn), 'wb', encoding)
    json.dump(rtrt_info_list, fp, ensure_ascii=False, indent=indent)
    fp.close()
  #} // end of json_write()
  
  
  def _check_timeline(self, search_id, tl_iter, limit_statuses, include_rt): #{
    (logdebug, log, logerr) = (self.logdebug, self.log, self.logerr)
    
    (flg_found, status_list, status_list_wo_rt) = (False, [], [])
    
    flg_break = False
    for status in tl_iter:
      logdebug('%s: %s' % (status.id, str(status.created_at)))
      if status.id <= search_id:
        flg_break = True
        break
      status_list.append(status)
      if not getattr(status, 'retweeted_status', None):
        status_list_wo_rt.append(status)
    
    target_list = status_list if include_rt else status_list_wo_rt
    
    logdebug('  status count: %d  (without RT: %d)' % (len(status_list), len(status_list_wo_rt)))
    
    if flg_break:
      if 0 < len(target_list):
        flg_found = True
    else:
      if len(status_list) < limit_statuses and 0 < len(target_list):
        flg_found = True
    
    tgt_status = None
    if flg_found:
      tgt_status = target_list[-1]
      if tgt_status and not hasattr(tgt_status, 'text'):
        try:
          tgt_status = target_list[-1] = self.api.get_status(id=tgt_status.id)
        except Exception, s:
          tgt_status = None
          flg_found = False
          logerr(traceback.format_exc())
    
    return (tgt_status, target_list)
  #} // end of _check_timeline()
  
  
  def _iter_search(self, query, limit=0): #{
    (logdebug, log, logerr) = (self.logdebug, self.log, self.logerr)
    class Status(object):
      def __init__(self, *argv, **kargv):
        for (key, val) in kargv.items():
          setattr(self, key, val)
    
    url_ep = 'https://twitter.com/i/search/timeline'
    if isinstance(query, unicode): query = query.encode('utf-8','ignore')
    param_dict = dict(
      q = query,
      f='realtime',
      include_available_features = 1,
      include_entities = 1,
      last_note_ts = 0,
    )
    
    cnt_status = 0
    scroll_cursor = None
    while True:
      if scroll_cursor: param_dict['scroll_cursor'] = scroll_cursor
      url = '%s?%s' % (url_ep, urllib.urlencode(param_dict))
      logdebug(url)
      req = urllib2.Request(url, None, {'User-Agent':'Mozilla/5.0 (Windows NT 6.3; WOW64; Trident/7.0; Touch; rv:11.0) like Gecko'})
      try:
        rsp = urllib2.urlopen(url)
      except URLError, s:
        logerr(traceback.format_exc())
        if hasattr(s, 'reason'):
          logerr('URLError: reason="%s"' % (s.reason))
        elif hasattr(s, 'code'):
          logerr('URLError: code=%s' % (s.code))
        break
      
      rsp_json = rsp.read()
      rsp_dict = json.loads(rsp_json)
      inner = rsp_dict.get('inner')
      if inner: rsp_dict = inner
      
      html = re.sub('(?:\A\s+|\s+\z)', '', rsp_dict.get('items_html',''))
      if html:
        doc = lxml_html.fromstring(html, base_url='https://twitter.com/')
        tweet_list = doc.xpath('.//li[@data-item-type="tweet"]/div[@data-tweet-id]')
        for tweet in tweet_list:
          id = int(tweet.attrib.get('data-tweet-id'))
          timestamp = int(tweet.xpath('.//a[contains(concat(" ",@class," ")," tweet-timestamp ")]//*[@data-time][1]')[0].attrib.get('data-time'))
          created_at = datetime.datetime.utcfromtimestamp(timestamp)
          status = Status(
            id = id,
            created_at = created_at,
          )
          yield status
          cnt_status += 1
          if limit and limit <= cnt_status: break
        
        if limit and limit <= cnt_status:
          logdebug('*** limit (count=%d) ***' % (cnt_status))
          break
      
      tmp_scroll_cursor = rsp_dict.get('scroll_cursor')
      if not html or not tmp_scroll_cursor or (tmp_scroll_cursor == scroll_cursor) or (scroll_cursor and not rsp_dict.get('has_more_items')):
        logdebug('*** data end ***')
        break
      
      scroll_cursor = tmp_scroll_cursor
    
  #} // end of _iter_search()
  
  
  def _get_rtrt_status(self, status): #{
    (logdebug, log, logerr) = (self.logdebug, self.log, self.logerr)
    
    rtrt_status = dict(
      user = dict(
        id = status.user.id_str,
        screen_name = status.user.screen_name,
        protected = status.user.protected,
        profile_image_url = status.user.profile_image_url,
      ),
      id = status.id_str,
      text = status.text,
      created_at = str(status.created_at),
      retweet_count = status.retweet_count,
    )
    return rtrt_status
  #} // end of _get_rtrt_status()
  
  
  def logdebug(self, *argv): #{
    if not self.flg_debug: return
    self.log(*argv)
  #} // end of logdebug()
  
  
  def log(self, *argv): #{
    for val in argv:
      print val
  #} // end of log()
  
  
  def logerr(self, *argv): #{
    for val in argv:
      sys.stderr.write(val+'\n')
  #} // end of log()
  
  #} // end of functions
  
#} // end of class Rtrt()


# ■ end of file
