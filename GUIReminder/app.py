import os
from dotenv import load_dotenv
from slack_bolt import App
from slack_bolt.adapter.socket_mode import SocketModeHandler

from handlers.commands import (
    set_reminder,
    set_schedule,
    show_reminder_list
)


# 環境設定の読み込み
load_dotenv()
SLACK_BOT_TOKEN = os.environ.get("SLACK_BOT_TOKEN")
SLACK_SIGNING_SECRET = os.environ.get("SLACK_SIGNING_SECRET")
SLACK_APP_TOKEN = os.environ.get("SLACK_APP_TOKEN")


# ソケットモード / HTTPモード
IS_SOCKET_MODE = True

# Bolt Appの初期化
app = App(
    token=SLACK_BOT_TOKEN,
    signing_secret=SLACK_SIGNING_SECRET
)

command_modules = [
    set_reminder, 
    set_schedule,
    show_reminder_list
]

for module in command_modules:
    module.register(app)


if __name__ == "__main__":
    if IS_SOCKET_MODE:
    # 開発環境で最も簡単な Socket Mode で実行
    # 本番環境では Web サーバー（Flask/Djangoなど）と連携して実行するのが一般的
        print("Bot is running via Socket Mode...")
        SocketModeHandler(app, SLACK_APP_TOKEN).start()
    else:
        # ポート3000でHTTPサーバーとして起動
        PORT = 3000
        print(f"Bot is running on port {PORT}...")
        # Boltの組み込みアダプターはFlask/Djangoを使用していないため、
        # 実行には適切なWSGIサーバーが必要です。ここではシンプルな起動を想定。
        # 通常、BotをHTTPサーバーとして実行するには別の起動スクリプトが必要です。
        # ここでは便宜上、Boltが内部的にHTTPサーバーとして動作すると仮定します。
        from slack_bolt.adapter.flask import SlackRequestHandler
        from flask import Flask, request
        
        flask_app = Flask(__name__)
        handler = SlackRequestHandler(app)

        @flask_app.route("/slack/events", methods=["POST"])
        def slack_events():
            return handler.handle(request)

        flask_app.run(port=PORT)