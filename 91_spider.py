# 首页列表爬取
import asyncio
from email import header
import re
import requests
from urllib import parse
from bs4 import BeautifulSoup
from faker import Faker
from pyppeteer import launch
from pyppeteer.errors import ElementHandleError
import util
import shutil


fake = Faker('zh_CN')
hea = {'Accept-Language':'zh-CN,zh;q=0.9','User-Agent':'Mozilla/5.0 (Windows NT 6.3; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/41.0.2272.118 Safari/537.36'}

class VideoInfo(object):
    pass

# 去除文件名中 非法的字符
def clean_file_name(filename: str):
    invalid_chars = '[\\\/:*?"<>|]'
    replace_char = '-'
    return re.sub(invalid_chars, replace_char, filename)


async def getVideoInfo91(url):
    print('得到的url:',url)
    try:
        browser, page = await ini_browser()
        await asyncio.wait_for(page.goto(url, {'waitUntil': 'domcontentloaded'}), timeout=10.0)
        await page._client.send("Page.stopLoading")

        await page.waitForSelector('.video-border')
        # 执行JS代码
        # evaluate页面跳转后 已经注入的JS代码会失效
        # evaluateOnNewDocument每次打开新页面注入
        strencode = await page.evaluate('''() => {
               return $(".video-border").html().match(/document.write([\s\S]*?);/)[1];
            }''')

        realM3u8 = await page.evaluate(" () => {return " + strencode + ".match(/src='([\s\S]*?)'/)[1];}")

        imgUrl = await page.evaluate('''() => {
               return $(".video-border").html().match(/poster="([\s\S]*?)"/)[1]
            }''')
        scCount = await page.Jeval('#useraction > div:nth-child(1) > span:nth-child(4) > span', 'el => el.innerText')
        title = await page.Jeval('#videodetails > h4', 'el => el.innerText')
        try:
            author = await page.Jeval(
                '#videodetails-content > div:nth-child(2) > span.title-yakov > a:nth-child(1) > span',
                'el => el.innerText')
        except ElementHandleError:
            author = '匿名'

        # 判断是否高清
        length = await page.evaluate('''() => {
               return $("#videodetails-content > a:nth-child(2)").length
            }''')
        if int(length) > 0:
            if '.mp4' in realM3u8:
                # realM3u8 = realM3u8.replace('/mp43', '/mp4hd')
                pass
            else:
                realM3u8 = realM3u8.replace('/m3u8', '/m3u8hd')

    finally:
        # 关闭浏览器
        await page.close()
        await browser.close()

    videoinfo = VideoInfo()
    videoinfo.title = title
    videoinfo.author = author
    videoinfo.scCount = scCount
    videoinfo.realM3u8 = realM3u8
    videoinfo.imgUrl = imgUrl
    print(title)
    print(realM3u8)
    return videoinfo



async def ini_browser():
    browser = await launch(headless=True, dumpio=True, devtools=False,
                           # userDataDir=r'F:\temporary',
                           args=[
                               # 关闭受控制提示：比如，Chrome正在受到自动测试软件的控制...
                               '--disable-infobars',
                               # 取消沙盒模式，沙盒模式下权限太小
                               '--no-sandbox',
                               '--ignore-certificate-errors',
                               '--disable-setuid-sandbox',
                               '--disable-features=TranslateUI',
                               '-–disable-gpu',
                               '--disable-software-rasterizer',
                               '--disable-dev-shm-usage',
                               # log 等级设置，如果出现一大堆warning，可以不使用默认的日志等级
                               '--log-level=3',
                           ])
    page = await browser.newPage()
    await page.setUserAgent(fake.user_agent())
    await page.setExtraHTTPHeaders(
        headers={'X-Forwarded-For': await util.genIpaddr(), 'Accept-Language': 'zh-cn,zh;q=0.5'})
    await page.evaluateOnNewDocument('() =>{ Object.defineProperties(navigator,'
                                     '{ webdriver:{ get: () => false } }) }')
    return browser, page


async def main():
    # 页数1-8
    bet = int(input('下载多少页:'))
    for i in range(1, bet):
        url = 'http://91porn.com/v.php?category=rf&viewtype=basic&page=' + str(i)
        print(url)
        html = requests.get(url,headers=hea)
                # print(html)
        soup = BeautifulSoup(html.content, 'lxml')
        divs = soup.select('#wrapper > div.container.container-minheight > div.row > div > div > div > div')
        for div in divs:
            # print(repr(div))
            title = div.select('a > span')[0].text
            #author = div.select('span:nth-child(5)')[0].next_sibling.replace("\n", "").strip()
            href = div.select('a')[0].get('href')
            params = parse.parse_qs(parse.urlparse(href).query)
            viewkey = params['viewkey'][0]
            #print(title, href,viewkey)
            # 开始爬取视频
            try:
                videoinfo=await getVideoInfo91(href)
                await util.download91(videoinfo.realM3u8, videoinfo.title, viewkey)
                shutil.rmtree(viewkey, ignore_errors=True)
                # tspath = viewkey + '/'
                # files = os.listdir(tspath)
                # for file in files:
                #     if file.endswith('.ts','.txt'):
                #         os.remove(os.path.join(tspath, file))
            except:
                print('转码失败')
                shutil.rmtree(viewkey, ignore_errors=True)
                continue
            

asyncio.get_event_loop().run_until_complete(main())
