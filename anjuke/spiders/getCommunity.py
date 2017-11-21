#coding: utf-8

import re
import random
import logging
import redis
import json
import scrapy
import requests
from ..useragents import agents
from scrapy.http import Request
from scrapy.utils.log import configure_logging
from scrapy.spiders import CrawlSpider, Rule
from scrapy.linkextractors import LinkExtractor
from requests.exceptions import ConnectTimeout, ReadTimeout

configure_logging(install_root_handler=False)
#定义了logging的些属性
logging.basicConfig(
    filename='scrapy.log',
    format='%(levelname)s: %(message)s',
    level=logging.INFO
)
#运行时追加模式
log = logging.getLogger('SimilarFace')

def processValue(value):
    log.info("当前下一页链接为:" + value)
    return value

def getResult(url):
    header = {'user-agent': agents[0]}
    r = requests.get(url, headers=header)
    try:
        if r.ok:
            result = json.loads(r.text)
            return result
        return None
    except:
        return None

class CommunitySpider(CrawlSpider):
    name = "community"
    start_urls = ["https://beijing.anjuke.com/community/zizhuqiao/"]

    def parse_start_url(self, response):
        return self.getRecord(response)   

    rules = (
        Rule(LinkExtractor(restrict_xpaths = ("//div[@class='multi-page']/a[@class='aNxt']"), process_value=processValue),\
            callback = "getRecord", follow=True),
    )

    def getRecord(self, response):
        items = response.xpath("//div[@class='li-itemmod']")
        for i in range(len(items)):
            url = ""
            price = "--"
            trend = "--"
            try:
                url = items[i].xpath("./div[@class='li-info']/h3/a/@href").extract_first()
                trend = items[i].xpath("./div[@class='li-side']/p/text()").extract()[2]
                price = items[i].xpath("./div[@class='li-side']/p/strong/text()").extract_first()
            except:
                log.error("error occured, url is " + url)
            log.info(url)
            log.info(price)
            log.info(trend)
            wholeUrl = "https://beijing.anjuke.com" + url.decode('utf-8')
            #log.info("request for " + wholeUrl[:-1])
            yield Request(url=wholeUrl[:-1], callback=self.parseItem, meta={"price": price, "trend": trend.encode('utf-8')})

    def parseItem(self, response):
        resultStr = ""
        id = response.url.split('/')[-1]
        name  = response.xpath("//div[@class='comm-title']/h1/text()").extract_first().strip().encode('utf-8')
        addr  = response.xpath("//div[@class='comm-title']/h1/span[@class='sub-hd']/text()").extract_first().strip().encode('utf-8')
        resultStr = name + ',' + addr + ','
        #获取经纬度
        lng = re.findall("lng=(.*?)&", response.text)
        lat = re.findall("lat=(.*?)&", response.text)
        if lng:
            #log.info(lng[0])
            resultStr += str(lng[0]) + ','
        if lat:
            #log.info(lat[0])
            resultStr += str(lat[0]) + ','
        #价格和剩余房源是ajax请求
        #priceUrl = "https://beijing.anjuke.com/community_ajax/152/price/?cis=" + str(id) + "&ib=0"
        #priceResult = getResult(priceUrl)
        #if priceResult:
        #    price = priceResult["data"][str(id)]["mid_price"]
        #    change = priceResult["data"][str(id)]["mid_change"]
        #    #log.info(price)
        #    #log.info(change)
        #    resultStr += str(price) + ',' + str(change) + ','
        resultStr += str(response.meta["price"]) + ',' + str(response.meta["trend"]) + ','
        resourceUrl = "https://beijing.anjuke.com/v3/ajax/communityext/?commid=" +str(id) + "&useflg=onlyForAjax"
        resourceResult = getResult(resourceUrl)
        if resourceResult:
            saleNum = resourceResult["comm_propnum"]["saleNum"]
            rentNum = resourceResult["comm_propnum"]["rentNum"]
            #log.info(saleNum)
            #log.info(rentNum)
            resultStr += str(saleNum) + ',' + str(rentNum) + ','
        #获取基础数据,可能为10或11个数据
        basicParams = response.xpath("//dl[@class='basic-parms-mod']//dd/text()").extract() 
        for param in basicParams:
            #log.info(param)
            resultStr += param.encode('utf-8') + ','

        log.warn(resultStr)
