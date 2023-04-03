import re
from contextlib import asynccontextmanager
from contextlib import suppress
from typing import Optional, Literal, Tuple, Union, List, AsyncGenerator, AsyncIterator

from playwright.async_api import Page, Browser, Playwright, async_playwright, Error

from gsuid_core.logger import logger
from gsuid_core.bot import Bot
from gsuid_core.sv import SV
from gsuid_core.models import Event

_playwright: Optional[Playwright] = None
_browser: Optional[Browser] = None


async def init(**kwargs) -> Browser:
    global _browser
    global _playwright
    try:
        _playwright = await async_playwright().start()
        _browser = await launch_browser(**kwargs)
    except NotImplementedError:
        logger.warning('Playwright', '初始化失败，请关闭FASTAPI_RELOAD')
    except Error:
        await install_browser()
        _browser = await launch_browser(**kwargs)
    return _browser


async def launch_browser(**kwargs) -> Browser:
    assert _playwright is not None, "Playwright is not initialized"
    return await _playwright.chromium.launch(**kwargs)


async def get_browser(**kwargs) -> Browser:
    return _browser or await init(**kwargs)


async def install_browser():
    import os
    import sys

    from playwright.__main__ import main

    logger.info('Playwright', '正在安装 chromium')
    sys.argv = ["", "install", "chromium"]
    with suppress(SystemExit):
        logger.info('Playwright', '正在安装依赖')
        os.system("playwright install-deps")
        main()


@asynccontextmanager
async def get_new_page(**kwargs) -> AsyncGenerator[Page, None]:
    assert _browser, "playwright尚未初始化"
    page = await _browser.new_page(**kwargs)
    try:
        yield page
    finally:
        await page.close()


async def screenshot(url: str,
                     *,
                     elements: Optional[Union[List[str]]] = None,
                     timeout: Optional[float] = 100000,
                     wait_until: Literal["domcontentloaded", "load", "networkidle", "load", "commit"] = "networkidle",
                     viewport_size: Tuple[int, int] = (1920, 1080),
                     full_page=True,
                     **kwargs):
    if not url.startswith(('https://', 'http://')):
        url = f'https://{url}'
    viewport_size = {'width': viewport_size[0], 'height': viewport_size[1]}
    brower = await get_browser()
    page = await brower.new_page(
        viewport=viewport_size,
        **kwargs)
    try:
        await page.goto(url, wait_until=wait_until, timeout=timeout)
        assert page
        if not elements:
            return await page.screenshot(timeout=timeout, full_page=full_page)
        for e in elements:
            card = await page.wait_for_selector(e, timeout=timeout, state='visible')
            assert card
            clip = await card.bounding_box()
        return await page.screenshot(clip=clip, timeout=timeout, full_page=full_page, path='test.png')

    except Exception as e:
        raise e
    finally:
        if page:
            await page.close()


@asynccontextmanager
async def get_new_page(**kwargs) -> AsyncIterator[Page]:
    browser = await get_browser()
    page = await browser.new_page(**kwargs)
    try:
        yield page
    finally:
        await page.close()
        
        
web_sv = SV(
    '网页截图',
    pm=6,  
    priority=1400,
    enabled=True,
    black_list=[],
    area='ALL'
)


@web_sv.on_prefix('网页截图', block=True,)
async def reserve_openai(bot:Bot, event:Event):
    text = event.text
    pattern = r"(?i)\b((?:https?://|www\d{0,3}[.]|[a-z0-9.\-]+[.][a-z]{2,4}/)(?:[^\s()<>]+|\(([^\s()<>]+|(\([^\s()<>]+\)))*\))+(?:\(([^\s()<>]+|(\([^\s()<>]+\)))*\)|[^\s`!()\[\]{};:'\".,<>?«»“”‘’]))"
    matches = re.findall(pattern, text)
    if matches:
      await bot.send(await screenshot(matches[0][0]))
    else:
      await bot.send('抱歉，我没有提取到合法的url，请确认后重新发送命令[网页截图 url]')