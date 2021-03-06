#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# @Time    : 2019/7/15 3:52 PM
# @Author  : w8ay
# @File    : xss.py
# referer: https://www.anquanke.com/post/id/148357
import copy
import os
import random
import re

import requests

from W13SCAN.lib.common import random_str
from W13SCAN.lib.const import acceptedExt, ignoreParams, Level
from W13SCAN.lib.output import out
from W13SCAN.lib.plugins import PluginBase


class W13SCAN(PluginBase):
    name = 'XSS多种方式探测'
    desc = '''暂只支持Get请求方式'''
    level = Level.MIDDLE

    def audit(self):
        method = self.requests.command  # 请求方式 GET or POST
        headers = self.requests.get_headers()  # 请求头 dict类型
        url = self.build_url()  # 请求完整URL

        resp_data = self.response.get_body_data()  # 返回数据 byte类型
        resp_str = self.response.get_body_str()  # 返回数据 str类型 自动解码
        resp_headers = self.response.get_headers()  # 返回头 dict类型

        p = self.requests.urlparse
        params = self.requests.params
        netloc = self.requests.netloc

        if method == 'GET':
            if p.query == '':
                return
            exi = os.path.splitext(p.path)[1]
            if exi not in acceptedExt:
                return

            rndStr = 9000 + random.randint(1, 999)
            tag = random_str(4)
            html_payload = "<{tag}>{randint}</{tag}>".format(tag=tag, randint=rndStr)  # html xss
            attr_payload = [
                '" oNsOmeEvent="console.log(233)',  # 双引号payload
                "' oNsOmeEvent='console.log(2333)",  # 单引号payload
            ]
            url_payload = "javascript&colon;{randint}".format(randint=rndStr)
            javascript_payload = "{randint}".format(randint=rndStr)

            for k, v in params.items():
                if k.lower() in ignoreParams:
                    continue
                # check v is in content
                if v.lower() not in resp_str.lower():
                    continue
                data = copy.deepcopy(params)
                ranstr = random_str(5)
                data[k] = v + ranstr
                r = requests.get(url, headers=headers, params=data)
                html1 = r.text
                if ranstr not in html1:
                    continue

                in_script = False
                script_group = re.findall('<script.*?>(.*?)</script>', html1, re.I | re.S | re.M)
                if script_group:
                    for i in script_group:
                        if ranstr in i:
                            in_script = True
                            break

                if in_script:
                    if ('"' + ranstr) in html1:
                        data[k] = v + javascript_payload + '"'
                        r = requests.get(url, headers=headers, params=data)
                        if (javascript_payload + '"') in r.text:
                            out.success(url, self.name, payload="{}:{}".format(k, data[k]), raw=r.raw,
                                        descript="探测字符在<script>脚本内被解析,且双引号未被转义",
                                        type="javascript xss")
                    if ("'" + ranstr) in html1:
                        data[k] = v + javascript_payload + "'"
                        r = requests.get(url, headers=headers, params=data)
                        if (javascript_payload + "'") in r.text:
                            out.success(url, self.name, payload="{}:{}".format(k, data[k]), raw=r.raw,
                                        descript="探测字符在<script>脚本内被解析,且单引号未被转义",
                                        type="javascript xss")

                else:
                    # check html xss
                    data[k] = v + html_payload
                    r = requests.get(url, headers=headers, params=data)
                    html1 = r.text
                    if html_payload in html1:
                        out.success(url, self.name, payload="{}:{}".format(k, data[k]), raw=r.raw, descript="探测tag被解析",
                                    type="html xss")
                        break

                    # check attr xss
                    for payload in attr_payload:
                        data[k] = v + payload
                        r = requests.get(url, headers=headers, params=data)
                        html1 = r.text
                        if payload[0] == '"':
                            if payload + '"' in html1:
                                out.success(url, self.name, payload="{}:{}".format(k, data[k]), raw=r.raw,
                                            type="标签属性xss")
                                break
                        elif payload[0] == "'":
                            if payload + "'" in html1:
                                out.success(url, self.name, payload="{}:{}".format(k, data[k]), raw=r.raw,
                                            type="标签属性xss")
                                break

                    # check url payload
                    re_parren = r'''[src|href|action]=['"]'''
                    data[k] = v + url_payload
                    r = requests.get(url, headers=headers, params=data)
                    html1 = r.text
                    if re.search(re_parren + url_payload, html1):
                        out.success(url, self.name, payload="{}:{}".format(k, data[k]), raw=r.raw,
                                    type="url xss")
                        break
