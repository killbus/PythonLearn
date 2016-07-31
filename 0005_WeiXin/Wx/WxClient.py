import requests
import time
import random
import re
import pyqrcode
import Image
import xml.dom.minidom
import json
import traceback

class WxClient():
    def __init__(self):
        self.Session = requests.Session()
        self.Session.headers.update({'User-Agent': 'Mozilla/5.0 (X11; Linux i686; U;) Gecko/20070322 Kazehakase/0.4.5'})
        self.BaseRequest = {
                'DeviceID' : 'e' + repr(random.random())[2:17],
            }
        self.Info_Base = {}
        self.Info_SyncKey = {}
        self.Info_User = {}
        self.IsLogin = False

    def WxLogin(self):
        '''
            web weixin login
        '''
        def WaitForLogin(self):
            '''
                wait for user to scan it,after login,get base info
            '''
            for loop in range(1,10):
                '''
                    #because user param in self.Session.get,the uuid will be urlencode,so we not use params
                    LoginParam = {
                        '_' : int(time.time()),
                        #'loginicon' : 'true',
                        #'r' : -947878708,
                        'tip' : 0,
                        'uuid' : self.Info_Base['UUID'],
                    }
                    #r = self.Session.get('https://login.weixin.qq.com/cgi-bin/mmwebwx-bin/login',params = LoginParam)
                '''
                r = self.Session.get('https://login.weixin.qq.com/cgi-bin/mmwebwx-bin/login?tip=0&uuid=%s&_=%s' % (self.Info_Base['UUID'], int(time.time())))
                r.encoding = 'utf-8'
                code = re.search(r'window.code=(\d+);', r.content)
                reurl = re.search(r'window.redirect_uri="(\S+)"', r.content)
                redirect_url = None
                if code:
                    if '200' == code.group(1):
                        redirect_url = reurl.group(1)
                        break;
                    elif '201' == code.group(1):
                        print 'Wait for Sure...'
                    elif '408' == code.group(1):
                        print 'Wait for Scan...'
                    else:
                        print 'Unknow login return code',code.group(1)
                time.sleep(1)
            if None == redirect_url:
                return False
            r = self.Session.get(redirect_url + '&fun=new')
            r.encoding = 'utf-8'

            #get base info
            doc = xml.dom.minidom.parseString(r.text)
            root = doc.documentElement
            for info in root.childNodes:
                if 'skey' == info.nodeName:
                    self.BaseRequest['Skey'] = info.childNodes[0].data
                elif 'wxsid' == info.nodeName:
                    self.BaseRequest['Sid'] = info.childNodes[0].data
                elif 'wxuin' == info.nodeName:
                    self.BaseRequest['Uin'] = info.childNodes[0].data
                elif 'pass_ticket' == info.nodeName:
                    self.Info_Base['pass_ticket'] = info.childNodes[0].data
                else:
                    pass

            #post to get SyncKey and my user info
            PostParams = {
                'BaseRequest' : self.BaseRequest,
                }
            r = self.Session.post('https://wx.qq.com/cgi-bin/mmwebwx-bin/webwxinit?r=%s&lang=zh_CN&pass_ticket=%s' % (int(time.time()),self.Info_Base['pass_ticket'])
                                  ,json.dumps(PostParams))
            r.encoding = 'utf-8'
            infoDict = json.loads(r.text)
            self.Info_User = infoDict['User']
            self.Info_SyncKey = infoDict['SyncKey']
            self.Info_SyncKeyStr = '|'.join(str(KeyVal['Key']) + '_' + str(KeyVal['Val']) for KeyVal in self.Info_SyncKey['List'])

            if 0 != infoDict['BaseResponse']['Ret']:
                print 'Get SyncKey and MyUserInfo Failure...'
                return False

            #finnaly,post to make sure
            PostParams = {
                'BaseRequest' : self.BaseRequest,
                'ClientMsgId' : int(time.time()),
                'Code' : 3,
                'FromUserName' : self.Info_User['UserName'],
                'ToUserName' : self.Info_User['UserName'],
                }
            r = self.Session.post('https://wx.qq.com/cgi-bin/mmwebwx-bin/webwxstatusnotify?lang=zh_CN&pass_ticket=%s' % self.Info_Base['pass_ticket'],data = json.dumps(PostParams))
            r.encoding = 'utf-8'
            retjson = json.loads(r.text)
            if 0 == retjson['BaseResponse']['Ret']:
                return True
            else:
                print 'Make sure failure',retjson['BaseResponse']['Ret']
                return False

        #First,we get UUID
        TimeTick = int(time.time())
        GetParam = {
            '_': TimeTick,
            'appid': 'wx782c26e4c19acffb',
            'fun' : 'new',
            'lang': 'zh_CN',
            'redirect_uri' : 'https://wx.qq.com/cgi-bin/mmwebwx-bin/webwxnewloginpage',
        }
        try:
            r = self.Session.get('https://login.weixin.qq.com/jslogin',params = GetParam)
            r.encoding = 'utf-8'
            regx = r'window.QRLogin.code = (\d+); window.QRLogin.uuid = "(\S+?)"'
            pm = re.search(regx, r.text)
            if pm:
                code = pm.group(1)
                self.Info_Base['UUID'] = pm.group(2)
                if code != '200':
                    print 'Get UUID Failure,return code',code
                    return False
            else:
                print 'Get UUID with re Failure...'
                return False

            #second,we get QR
            r = self.Session.get('https://login.weixin.qq.com/qrcode/' + self.Info_Base['UUID'])
            with open('QR.jpeg','wb') as f:
                f.write(r.content)
                f.close()
            Image.open("QR.jpeg").show()
            print 'Save QR to QR.jpeg,please scan it by phone...'

            #qr = pyqrcode.create('https://login.weixin.qq.com/qrcode/' + self.Info_Base['UUID'])
            #print qr.terminal(quiet_zone=1)

            if True != WaitForLogin(self):
                return False
            print 'Login Success...'
            self.IsLogin = True
            return True
        except Exception as e:
            print e.message, traceback.format_exc()
            return False

    def SyncCheck(self):
        '''
            return : Exit , MsgDic
        '''
        Exit = 1
        MsgDic = None
        try:
            r = self.Session.get('https://webpush.wx.qq.com/cgi-bin/mmwebwx-bin/synccheck?r=%s&skey=%s&sid=%s&deviceid=%s&synckey=%s&_=%s' % (~int(time.time()),self.BaseRequest['Skey'],self.BaseRequest['Sid'],self.BaseRequest['DeviceID'],self.Info_SyncKeyStr,int(time.time())))
            print r.text
            pm = re.search(r'window.synccheck=\{retcode:"(\d+)",selector:"(\d+)"\}',r.text)
            retcode = pm.group(1)
            selector = pm.group(2)
            if '1100' == retcode:
                print 'login from Wx App,so we logout'
            elif '1101' == retcode:
                print 'xxxxx'
            elif '0' == retcode:
                Exit = 0
                print 'selector',selector

                PostParam = {
                    'BaseRequest' : self.BaseRequest,
                    'SyncKey' : self.Info_SyncKey,
                    'rr' : ~int(time.time())
                    }
                r = self.Session.post('https://wx.qq.com/cgi-bin/mmwebwx-bin/webwxsync?sid=%s&skey=%s&lang=zh_CN&pass_ticket=%s' %
                                      (self.BaseRequest['Sid'],self.BaseRequest['Skey'],self.Info_Base['pass_ticket']),
                                      data = json.dumps(PostParam))
                r.encoding = 'utf-8'
                MsgDic = json.loads(r.text)
                if 0 == MsgDic['BaseResponse']['Ret']:
                    self.Info_SyncKey = MsgDic['SyncKey']
                    self.Info_SyncKeyStr = '|'.join(str(KeyVal['Key']) + '_' + str(KeyVal['Val']) for KeyVal in self.Info_SyncKey['List'])
                else:
                    print 'POST SyncCkeck is not zero',Msg['BaseResponse']['Ret']
            else:
                print 'Unknow code',retcode,selector
                Exit = 1
        except Exception as e:
            print e.message, traceback.format_exc()
        finally:
            return Exit,MsgDic

    def GetAllFriends(self):
        if True == self.IsLogin:
            try:
                r = self.Session.get('https://wx.qq.com/cgi-bin/mmwebwx-bin/webwxgetcontact?lang=zh_CN&pass_ticket=%s&r=%s&seq=0&skey=%s' % (self.Info_Base['pass_ticket'],int(time.time()),self.BaseRequest['Skey']))
                r.encoding = 'utf-8'
                #print r.text
                with open('contacts.json', 'w') as f:
                    f.write(r.text.encode('utf-8'))
                    f.close()
                retjson = json.loads(r.text)
                print 'Total friends number',retjson['MemberCount']
                self.Friends = retjson['MemberList']
            except Exception as e:
                print e.message, traceback.format_exc()
    def Run(self):
        while True:
            Exit,MsgDic = self.SyncCheck()
            if Exit:
                return False
            if None != MsgDic:
                print MsgDic
            time.sleep(1)






