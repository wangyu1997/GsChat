from .base import BaseChat
import os
import asyncio
import time
from .build import CHAT
from gsuid_core.bot import Bot
from gsuid_core.models import Event
from gsuid_core.logger import logger
from revChatGPT.V3 import Chatbot as openaiChatbot


@CHAT.register_module()
class OpenaiChat(BaseChat):
  def __init__(self, config=None):
    super(OpenaiChat, self).__init__(config)
    
    
  async def _create(self, user_id):
    current_time = int(time.time())
    api_key = self._get_random_key()
    chat_bot = openaiChatbot(
        api_key=api_key,
        max_tokens=self.max_tokens,
    )
    self.chat_dict[user_id] = {
        "chatbot": chat_bot, "last_time": current_time, "sessions_number": 0, "isRunning": False}


    
  async def _ask(self, user_id, bot: Bot, event: Event):
    msg = event.text.strip()

    chatbot: Chatbot = self.chat_dict[user_id]["chatbot"]
    try:
        loop = asyncio.get_event_loop()    
        data = await loop.run_in_executor(None, chatbot.ask, msg)
        self.chat_dict[user_id]["sessions_number"] += 1
    except Exception as e:
        self.chat_dict[user_id]["isRunning"] = False
        await bot.send(f'askError: {str(e)}多次askError请尝试发送"重置对话"', at_sender=True)
        return
    self.chat_dict[user_id]["isRunning"] = False  # 将当前会话状态设置为未运行
    sessions_number = self.chat_dict[user_id]["sessions_number"]  
    data += f"\n\n当前会话: {sessions_number}   字数异常请发送\"重置对话\""
    try:
        await bot.send(data, at_sender=True)
    except Exception as e:
        try:
            await bot.send(f"文本消息被风控了,错误信息:{str(e)}, 这里咱尝试把文字写在图片上发送了", at_sender=True)
            await bot.send(await txt_to_img(data), at_sender=True)
        except Exception as eeee:
            await bot.send(f"消息全被风控了, 这是捕获的异常: \n{str(eeee)}", at_sender=True)


  async def init_data(self):
      config = self.config
      if config.proxy:
        os.environ["all_proxy"] = config.proxy
        logger.info(f"已设置代理, 值为:{config.proxy}")
      else:
        logger.warning("未检测到代理，国内用户可能无法使用openai功能")
      
      self.max_tokens = config.max_tokens
      self.keys = config.api_keys


  