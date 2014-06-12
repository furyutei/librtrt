# -*- coding: utf-8 -*-
"""
AppAuthHandler for Tweepy

■ オリジナル
  http://shogo82148.github.io/blog/2013/05/09/application-only-authentication-with-tweepy/
  「tweepyでApplication-only authenticationしてみた - Shogo's Blog」
  より。

■ 準備
  ・tweepy を easy_install や pip 等で予めインストールしておくこと。

■ 使い方
  >>> import tweepy
  >>> import AppAuthHandler
  >>> auth = AppAuthHandler.AppAuthHandler(CONSUMER_KEY, CONSUMER_SECRET)
  >>> api = tweepy.API(auth)
"""

import tweepy
import urllib
import urllib2
import base64
import json

class AppAuthHandler(tweepy.auth.AuthHandler): #{
    TOKEN_URL = 'https://api.twitter.com/oauth2/token'

    def __init__(self, consumer_key, consumer_secret): #{
        token_credential = urllib.quote(consumer_key) + ':' + urllib.quote(consumer_secret)
        credential = base64.b64encode(token_credential)

        value = {'grant_type': 'client_credentials'}
        data = urllib.urlencode(value)
        req = urllib2.Request(self.TOKEN_URL)
        req.add_header('Authorization', 'Basic ' + credential)
        req.add_header('Content-Type', 'application/x-www-form-urlencoded;charset=UTF-8')

        response = urllib2.urlopen(req, data)
        json_response = json.loads(response.read())
        self._access_token = json_response['access_token']
    #} // end of def __init__()

    def apply_auth(self, url, method, headers, parameters): #{
        headers['Authorization'] = 'Bearer ' + self._access_token
    #} // end of def apply_auth()

#} // end of class AppAuthHandler()

# ■ end of file
