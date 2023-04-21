#!/usr/bin/env python3
#ChatGPT,GitHub Copilotを活用して制作されたプログラムです
#systemdで自動起動するように設定しています
import os
import discord
from dotenv import load_dotenv
import GPT as gpt
import configparser
import time
import asyncio

def comma_separated_to_int_list(string):
    return [int(s) for s in string.split(',')]

def remove_first_three_chars(s):
    return s[3:]


async def add_user_input_and_generate_response(prompt, user_input):
    try:
        loop = asyncio.get_running_loop()
        response = await asyncio.wait_for(
            loop.run_in_executor(None, gpt.add_user_input_and_generate_response,prompt, user_input), 
            timeout=60.0
        )
        prompt, response_text = response[0], response[1]
        #prompt.append({"role": "bot", "content": response_text})
        return prompt, response_text
    except asyncio.TimeoutError:
        raise TimeoutError("Function took too long to execute")

class DiscordBot:
    def __init__(self, config):
        self.client = discord.Client(intents=discord.Intents.all())
        self.read_from_dotenv()
        self.read_from_config(config)    
        self.status_by_channel = {}
        #{channel_id: {"prompt": prompt, isCalled: bool, lastCallTime: int}


        # OpenAI APIキーを設定する
        gpt.initialize_openai_api_key(self.api_key)
        #openai.api_key = self.api_key

    def read_from_config(self, config):
        #configから読み取る
        #デフォルト値を設定する
        blacklist_str = config["Discord"]["blacklist"]
        self.blacklist = comma_separated_to_int_list(blacklist_str)
        whitelist_str = config["Discord"]["whitelist"]
        self.whitelist = comma_separated_to_int_list(whitelist_str)
        self.is_whitelist:bool = config["Discord"]["is_whitelist"] == "True"
        self.start_prompt = config["Discord"]["start_prompt"]
        #self.start_words = config["Discord"]["start_words"]
        goodbye_words_list = config["Discord"]["goodbye_words"]
        self.goodbye_words:tuple = tuple(goodbye_words_list.split(',')) 
        self.goodbye_message = config["Discord"]["goodbye_message"]

    def read_from_dotenv(self):
        #.envから読み取る
        load_dotenv()
        self.api_key = os.getenv("OPENAI_API_KEY")
        self.token = os.getenv('DISCORD_BOT_TOKEN')

    def first_prompt(self):
        return [{"role": "user", "content": self.start_prompt}]

    def check_whether_to_respond(self, message):
        if message.author == self.client.user:
            return False
        if self.is_whitelist :
            if message.channel.id not in self.whitelist:
                print(f'{message.channel.id}はホワイトリストにありません。')
                return False   
            else:
                return True
        else:
            if message.channel.id in self.blacklist:
                print(f'{message.channel.id}はブラックリストにあります。')
                return False
            else:
                return True

    def check_whether_called(self, message,context_id):
        #ホワイトリストの場合は省略
        if not self.is_whitelist:
            ##や/で始まるメッセージなら呼ばれていないとみなす
            if message.content.startswith('#') or message.content.startswith('/'):
                return False
            # ###で始まるメッセージならisCalledを反転する
            #if message.content.startswith('###'):
            #    self.status_by_channel[context_id]["isCalled"] = not self.status_by_channel[context_id]["isCalled"]
            #    return
            #GPTで始まるメッセージなら呼ばれているとみなす
            #その場合最初の3文字を消去する
            if message.content.lower().startswith('gpt'):
                message.content = remove_first_three_chars(message.content)
                return True
            #そうでない場合contextのisCalledを確認する
            #comtextが存在しない場合はFalseを返す
            if context_id in self.status_by_channel:
                if not self.status_by_channel[context_id]["isCalled"]:
                    return False
            else:
                return False
        
        return True

    def get_context(self, message):
        #メッセージがどのスレッドにあるのか検知する
        if isinstance(message.channel, discord.Thread):
            return "thread", message.channel.id
        else:
            return "channel", message.channel.id

        

    def start(self):
        lastCallTime = 0

        @self.client.event
        async def on_ready():
            print(f"{self.client.user}がログインしました。")


        @self.client.event
        async def on_message(message):
            # メッセージを受信したときに動作する処理をここに書く
            #!まず状況を確認する
            if not self.check_whether_to_respond(message):
                return
            
            # スレッド内か確認する
            context, context_id = self.get_context(message)

            #呼ばれているか確認する
            if not self.check_whether_called(message,context_id):
                return

            #この時点で呼ばれているとみなす

            #もし履歴がない場合はstart_promptを追加する
            if context_id not in self.status_by_channel:
                self.status_by_channel[context_id] = {"prompt": self.first_prompt(), "isCalled": True, "lastCallTime": time.time()}
            if len(self.status_by_channel[context_id]["prompt"]) == 0:
                self.status_by_channel[context_id]["prompt"] = self.first_prompt()

            #もし(上記の処理も含めて)履歴がある場合はpromptを更新する
            if len(self.status_by_channel[context_id]["prompt"]) > 0:
                self.status_by_channel[context_id]["prompt"].append({"role": "user", "content": message.content})

                
            #終了するかどうか確認する
            #メッセージがgoodbye_wordsの中の1つで始まる場合は終了する
            if message.content.lower().startswith(self.goodbye_words):
                await message.channel.send(self.goodbye_message)
                self.status_by_channel[context_id]["prompt"] = self.first_prompt()
                self.status_by_channel[context_id]["isCalled"] = False

                return
            

            #返信の準備をする
            self.status_by_channel[context_id]["isCalled"] = True

            #返信についての情報を出力する
            if context == "thread":
                print(f"{message.author}のスレッド{message.channel}におけるメッセージに応答します")
            if context == "channel":
                print(f"{message.author}のチャンネル{message.channel}におけるメッセージに応答します")
            
            #初回は挨拶する
            if len(self.status_by_channel[context_id]["prompt"]) == 1:
                #await message.channel.send('Hi.')
                pass

            # 応答する前に、メッセージにリアクションを付ける
            await message.add_reaction("\N{Eyes}")

            # メッセージを受信すると、GPT APIに渡して応答を生成する
            #例外処理をする
            try:
                self.status_by_channel[context_id]["prompt"], response =await add_user_input_and_generate_response(self.status_by_channel[context_id]["prompt"], message.content)
            except Exception as e:
                #例外が発生した場合はエラーを出力する
                print(e)
                await message.channel.send('wah-wah-wah-wah-wah!')
                await message.channel.send(str(e)[:30])
                self.status_by_channel[context_id]["prompt"] = self.first_prompt()
                self.status_by_channel[context_id]["isCalled"] = False
                return
            else:
                # 応答を送信する
                await message.channel.send(response)

        self.client.run(self.token)

if __name__ == "__main__":
    #pythonの作業ディレクトリをカレントディレクトリに変更する
    os.chdir(os.path.dirname(os.path.abspath(__file__)))
    # 設定ファイルを読み込む
    config = configparser.ConfigParser()
    #configはutf-8で保存されているので、encoding="utf-8"を指定する
    config.read("config.ini", encoding="utf-8")

    # DiscordBotクラスのインスタンスを作成して起動する
    bot = DiscordBot(config)
    bot.start()
