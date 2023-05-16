import random
import re

from gsuid_core.bot import Bot
from gsuid_core.models import Event
from gsuid_core.sv import SV
from .chat import BaseChat, CHATENGINE
from .config import config

chat_sv = SV('聊天', pm=6, priority=10, enabled=True, black_list=[], area='ALL')
at_sv = SV('at聊天', pm=6, priority=2000, enabled=True, black_list=[], area='ALL')

# admin 一键切换所有模式 查看模式和engine
chat_engine = CHATENGINE.build(config.chat)

nickname = config.chat.Normal.nickname
poke__reply: tuple = (
    "lsp你再戳？",
    "连个可爱美少女都要戳的肥宅真恶心啊。",
    "你再戳！",
    "？再戳试试？",
    "别戳了别戳了再戳就坏了555",
    "我爪巴爪巴，球球别再戳了",
    "你戳你🐎呢？！",
    "请不要戳{target_name} >_<",
    "放手啦，不给戳QAQ",
    "喂(#`O′) 戳{target_name}干嘛！",
    "戳坏了，赔钱！",
    "戳坏了",
    "嗯……不可以……啦……不要乱戳",
    "那...那里...那里不能戳...绝对...",
    "(。´・ω・)ん?",
    "有事恁叫我，别天天一个劲戳戳戳！",
    "欸很烦欸！你戳🔨呢",
    "再戳一下试试？",
    "正在关闭对您的所有服务...关闭成功",
    "啊呜，太舒服刚刚竟然睡着了。什么事？",
    "正在定位您的真实地址...定位成功。轰炸机已起飞",
)
hello_reply: tuple = (
    "你好！",
    "哦豁？！",
    "你好！Ov<",
    "库库库，呼唤{target_name}做什么呢",
    "我在呢！",
    "呼呼，叫俺干嘛",
)
nonsense: tuple = (
    "你好啊",
    "你好",
    "在吗",
    "在不在",
    "您好",
    "您好啊",
    "你好",
    "在",
)


async def rand_hello() -> str:
    """随机问候语"""
    return random.choice(hello_reply).format(target_name=nickname)


async def rand_poke() -> str:
    """随机戳一戳"""
    return random.choice(poke__reply).format(target_name=nickname)


@chat_sv.on_prefix(
    ('bing', 'chat', 'openai', 'Bing', 'Chat', 'Openai'),
    block=True,
)
async def chat_handle(bot: Bot, event: Event):
    bot_name = event.command
    new_engine_name = chat_engine.get_engine(bot_name=bot_name)
    await handle_msg(bot, event, new_engine_name)


@at_sv.on_command('', block=True, to_me=True)
async def at_test(bot: Bot, event: Event):
    await handle_msg(bot, event)


@chat_sv.on_prefix(
    ('切换引擎', 'ce'),
    block=True,
)
async def change_engine(bot: Bot, event: Event):
    bot_name = event.text.strip().lower()

    if bot_name not in ['bing', 'chat', 'openai']:
        await bot.send(f"暂时不支持引擎 [{bot_name}] ")

    new_engine_name = chat_engine.get_engine(bot_name=bot_name)
    _, group, _ = chat_engine.get_bot_info(event)
    chat_engine.change_engine(event, new_engine_name)

    await bot.send(f'已切换当前[{"群聊" if group else "私聊"}] 引擎为: [{new_engine_name}]')


@chat_sv.on_fullmatch(
    ('切换模式', 'cm'),
    block=True,
)
async def mode_handle(bot: Bot, event: Event):
    chat_type = event.user_type
    is_private = bool(chat_type == 'direct')

    # 不支持私聊
    if is_private:
        await bot.send(f'私人聊天无法切换模式哦, 在群组中使用该命令。')
        return

    _, _, engine = chat_engine.get_bot_info(event)
    group = chat_engine.change_mode(event.group_id)
    _, _, engine = chat_engine.get_bot_info(event)

    await bot.send(f'切换成功\n当前模式为: [{"群聊" if group else "私人"}模式]\n当前引擎为: [{engine}]')


@chat_sv.on_fullmatch(
    ('重置对话', 'reset'),
    block=True,
)
async def reserve_handle(bot: Bot, event: Event):
    user_id, group, engine_name = chat_engine.get_bot_info(event)
    chatbot: BaseChat = await chat_engine.get_singleton_bot(engine_name)
    if await chatbot.reset(user_id, bot, event):
        await bot.send(f'已重置当前[{"群聊" if group else "私聊"}] 引擎为: [{engine_name}]')


@chat_sv.on_fullmatch('查看引擎', block=True)
async def _(bot: Bot, event: Event):
    _, group, engine_name = chat_engine.get_bot_info(event)
    await bot.send(f'当前[{"群聊" if group else "私聊"}] 引擎为: [{engine_name}]')


async def handle_msg(bot: Bot, event: Event, engine_name: str = None):
    msg = event.text.strip()

    if event.bot_id == 'ntchat':
        if ' ' not in msg and "@" in msg:
            msg = ''
        else:
            msg = re.sub(r"@.*? ", "", msg)

    if (not msg) or msg.isspace():
        await bot.send(await rand_poke(), at_sender=True)
        return
    if msg in nonsense:
        await bot.send(await rand_hello(), at_sender=True)
        return

    user_id, _, engine = chat_engine.get_bot_info(event)

    if not engine_name:
        engine_name = engine

    chat_bot: BaseChat = await chat_engine.get_singleton_bot(engine_name)

    await chat_bot.ask(user_id, bot, event)


@chat_sv.on_fullmatch(
    ('清除人格', '加载人格'),
    block=True,
)
async def handle_person(bot: Bot, event: Event):
    action = event.command.replace('人格', '')
    user_id, _, engine_name = chat_engine.get_bot_info(event)
    chatbot = await chat_engine.get_singleton_bot('Normal')
    res = await chatbot.switch_person(user_id)
    if res:
        await bot.send(f'已经暂时{action}了人格')


@chat_sv.on_prefix(
    '切换风格',
    block=True,
)
async def handle_style(bot: Bot, event: Event):
    style = event.text.strip()[:1].lower()
    if not style or style not in ['c', 'b', 'p']:
        await bot.send('请输入 [切换风格 c/b/p] 来切换风格\n c: creative \n b: balance \n p: precise')

    user_id, _, engine_name = chat_engine.get_bot_info(event)
    style_map = {'c': 'creative', 'b': 'balanced', 'p': 'precise'}
    chatbot = await chat_engine.get_singleton_bot('Bing')
    res = await chatbot.switch_style(user_id, style_map[style])
    if res:
        await bot.send(f'切换成功，已为您创建新的会话\n当前Bing的风格为 [{style_map[style]}]')
