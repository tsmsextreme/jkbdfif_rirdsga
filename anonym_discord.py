#!/usr/bin/env python
import datetime, sqlite3
import discord, discord.app_commands
from dotenv import load_dotenv
import MySQLdb
from concurrent.futures import ThreadPoolExecutor
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

###
###環境変数の取得
###
load_dotenv()
import os
TOKEN = os.getenv("TOKEN")
SERVERID = int(os.getenv("SERVERID"))
CHANNELID = int(os.getenv("CHANNELID"))

# pingが来たらサーバーの状態を返すようにする
port = int(os.getenv("PORT", "8080"))
address = os.getenv("RENDER_EXTERNAL_URL", "127.0.0.2")
class MyHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header('Content-type', 'text/html')
        self.end_headers()
        message = "Hello, world!"
        self.wfile.write(bytes(message, "utf8"))
        print("a")
        return
print(port)
print(address)
httpd = ThreadingHTTPServer(("", port), MyHandler)

client = discord.Client(intents=discord.Intents.all(),
                        activity=discord.Game("@silent忘れずに‼"))
tree = discord.app_commands.CommandTree(client)

@discord.app_commands.guilds(SERVERID)




###
###ユーザー定義
###
def insert_db(message_id:int, author:str, content:str, created_at:datetime, moderator:str):
    conn = MySQLdb.connect(
        host= os.getenv("HOST"),
        user=os.getenv("USERNAME"),
        passwd= os.getenv("PASSWORD"),
        db= os.getenv("DATABASE"),
        autocommit = True,
        ssl_mode = "VERIFY_IDENTITY",
        ssl      = {
            "ca": os.getenv("SSL_CERT")
        }
    )
    cur = conn.cursor()

    if moderator:
        sql_query = "UPDATE logs SET moderator = %s WHERE message_id = %s;"
        cur.execute(sql_query, [moderator, message_id]);
    else:
        created_at_JST = (created_at + datetime.timedelta(hours=9)).strftime('%Y/%m/%d %H:%M:%S') #もっと書き方あるはず
        sql_query = "INSERT INTO logs values(%s, %s, %s, %s, NULL)"
        cur.execute(sql_query, [message_id, str(author), content, created_at_JST])

    conn.commit()
    cur.close()
    conn.close()


def extract_db(created_at): #return: レコードのtuple
    conn = MySQLdb.connect(
        host= os.getenv("HOST"),
        user=os.getenv("USERNAME"),
        passwd= os.getenv("PASSWORD"),
        db= os.getenv("DATABASE"),
        autocommit = True,
        ssl_mode = "VERIFY_IDENTITY",
        ssl      = {
            "ca": os.getenv("SSL_CERT")
        }
    )
    cur = conn.cursor()

    created_at_JST = (created_at + datetime.timedelta(hours=9)).strftime('%Y/%m/%d %H:%M:%S')

    sql_query = "SELECT * FROM logs WHERE time <= '%s' ORDER BY time DESC LIMIT 1;"
    cur.execute(sql_query % created_at_JST)
    extract = cur.fetchone()
    cur.close()
    conn.close()

    return extract


def moderator_list(created_at):
    moderator:int = extract_db(created_at)[4]

    if moderator is None:
        moderator = ""

    moderator_list_:list = moderator.split(",")
    try:
        moderator_list_.remove("")
    except ValueError:
        pass
    return moderator_list_


def create_Embed(title:str, frame_color:int, description:str, f1:str, v1:str, f2:str, v2:str, f3:str, v3:str): #(*args, **kwargs)めんどくさくて…
    embed = discord.Embed(title = title,
                          color = frame_color,
                          description = description)
    embed.set_author(name = client.user,
                     url = "https://twitter.com/UirouMachineVRC",
                     icon_url = client.user.display_avatar)

    embed.add_field(name = f1,
                    value = v1,
                    inline = False)
    embed.add_field(name = f2,
                    value = v2,
                    inline = False)
    embed.add_field(name = f3,
                    value = v3,
                    inline = False)

    embed.set_footer(text = "made by willoh",
                     icon_url = "https://pbs.twimg.com/profile_images/1665235452755050496/FUkvyf1-_400x400.jpg")

    return embed




###
###イベント
###
@client.event
async def on_ready():
    await tree.sync()
    print("起動")


@client.event
async def on_message(message):
    if not message.author.bot and message.channel.id == CHANNELID:
        channel = client.get_channel(CHANNELID)
        message_content = message.content
        attach_file = []
        if message.attachments:
            for _ in message.attachments:
                attach_file.append(_.url)

        if message_content and attach_file:
            message_content = message_content + " ".join(attach_file)
        elif not message_content and attach_file:
            message_content = " ".join(attach_file)

        await message.delete()

        if message.reference:
            message_ = await channel.fetch_message(message.reference.message_id)
            await message_.reply(">>> " + message_content)
        else:
            await channel.send(">>> " + message_content)

        try:
            insert_db(message.id, message.author.name, message_content, message.created_at, None)
        except:
            pass #握り潰し、よくないらしい




###
###コマンド
###
@tree.command(name="あぼーん", description="メッセージIDを入れると消せます")
async def delete_command(ctx: discord.Interaction, message_id: str):
    channel = client.get_channel(CHANNELID)
    message = await channel.fetch_message(int(message_id))
    await ctx.response.send_message("あぼーんしたので", ephemeral=True)
    await message.delete()


@tree.command(name="特定しますた", description="4ポイント貯まる (4人から実行される) とそのメッセージの投稿者が晒し上げられます")
async def tokutei(ctx: discord.Interaction, message_id: str):
    flag = False
    channel = client.get_channel(CHANNELID)
    message = await ctx.channel.fetch_message(message_id)

    now_moderator = str(ctx.user)
    db_return:tuple = extract_db(message.created_at)
    moderator_list_:list = moderator_list(message.created_at)
    modr_len = len(moderator_list_)
    if now_moderator not in moderator_list_:
        req_num = 4 #################################################開示人数閾値
        if modr_len >= req_num - 1:
            flag = True

        moderator_list_.append(now_moderator)
        insert_db(db_return[0], None, None, None, ",".join(moderator_list_))
        await ctx.response.send_message(embed=create_Embed("/特定しますた　⬆追加", 0x00bfff, "__特定ポイントを追加しました__",
                                                           "送信日時", db_return[3], "内容", db_return[2], "累計特定Pt", modr_len+1), ephemeral=True)

        if flag:
            await channel.send(embed=create_Embed("/特定しますた　🧨発動", 0x00bfff, "__特定ポイントがたまりました！🎉__",
                                                  "送信日時", db_return[3], "内容", db_return[2], "送信者", f"||{db_return[1]}||"))
    else:
        await ctx.response.send_message(embed=create_Embed("/特定しますた　⚠️警告", 0x00bfff, "__あなたはすでに特定ポイントを追加しています__",
                                                           "送信日時", db_return[3], "内容", db_return[2], "累計特定Pt", modr_len), ephemeral=True)


@tree.command(name="silent", description="@silentしなくてもいいし入力中も出ないしどのチャンネルからでも🥷匿名🥷に書き込めるかわりにファイル添付はできないコマンド")
async def silent(ctx: discord.Interaction, text :str):
    channel = client.get_channel(CHANNELID)
    insert_db(ctx.id, ctx.user, text, ctx.created_at, None)

    await channel.send(">>> " + text)
    await ctx.response.send_message(f"送信済 0.2秒後にこのメッセージは消えます", ephemeral=True, delete_after=0.2)





if __name__ == '__main__':
    print('開始')
    with ThreadPoolExecutor() as executor:
        executor.submit(httpd.serve_forever)
        executor.submit(client.run, TOKEN)
