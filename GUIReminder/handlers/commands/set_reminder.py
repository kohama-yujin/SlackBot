import os
import datetime
import time
from dotenv import load_dotenv
from slack_sdk.errors import SlackApiError

load_dotenv()
DEVELOPER_SLACK_ID = os.environ.get("DEVELOPER_SLACK_ID")

# 切り上げ間隔（分）
MINUTE_INTERVAL = 5
# リマインド時のヘッダー
REMIND_HEADER = "【 🔔 リマインド 】"


def register(app):


    def generate_minute_options():
        """
        MINUTE_INTERVAL 単位の時刻オプションを生成
        """
        options = []
        for m in range(0, 60, MINUTE_INTERVAL):
            minute_str = f"{m:02d}"  # 0埋め
            options.append({
                "text": {"type": "plain_text", "text": f"{minute_str}分"},
                "value": minute_str
            })
        return options


    def get_next_minute_interval():
        """
        現在時刻を MINUTE_INTERVAL 単位に切り上げた日時を返す
        """
        # タイムゾーンを考慮した現在時刻を取得することが望ましいですが、ここでは一旦ローカルタイム（JST）と仮定
        now = datetime.datetime.now()    
        # 現在の分が MINUTE_INTERVAL 単位の区切りからどれだけ進んでいるか
        minutes_past_interval = now.minute % MINUTE_INTERVAL
        # 次の MINUTE_INTERVAL 単位までの残り時間 
        minutes_to_add = MINUTE_INTERVAL - minutes_past_interval
        # 次の MINUTE_INTERVAL 単位の時刻を計算
        next_time = now + datetime.timedelta(minutes=minutes_to_add)
        # 結果を文字列として返す
        initial_date = next_time.strftime("%Y-%m-%d")
        initial_hour = next_time.strftime("%H")
        initial_minute = next_time.strftime("%M")
        
        return initial_date, initial_hour, initial_minute


    # Slackアプリ設定で登録したスラッシュコマンドに合わせる
    @app.command("/set-reminder")
    def open_reminder_modal(ack, body, client):
        """
        スラッシュコマンド処理：モーダル（GUI）の表示
        """
        
        # コマンドを受け取ったことを即座にSlackに通知
        ack() 
        # コマンドが入力されたチャンネルIDをPrivate Metadataとして保存
        trigger_channel_id = body.get("channel_id")

        # 時刻の初期値設定 
        initial_date, initial_hour, initial_minute = get_next_minute_interval()
        # MINUTE_INTERVAL 分単位の分オプションを生成
        minute_options = generate_minute_options()
        # 1時間単位の時オプションを生成 (00時～23時)
        hour_options = [
            {"text": {"type": "plain_text", "text": f"{h:02d}時"}, "value": f"{h:02d}"}
            for h in range(24)
        ]
        
        # モーダル（GUI画面）の定義
        try:
            # views_openでモーダルを表示します
            client.views_open(
                # モーダルを表示するためのトリガー
                trigger_id=body["trigger_id"],
                view={
                    "type": "modal",
                    "callback_id": "reminder_submission",  # 送信時の識別子,
                    "private_metadata": trigger_channel_id,
                    "title": {"type": "plain_text", "text": "🔔 リマインダー設定"},
                    "submit": {"type": "plain_text", "text": "予約する"},
                    
                    # モーダルのブロック定義
                    "blocks": [
                        # リマインド内容の入力欄
                        {
                            "type": "input",
                            "block_id": "message_block",
                            "label": {"type": "plain_text", "text": "リマインド内容"},
                            "element": {
                                "type": "plain_text_input",
                                "action_id": "message_input",
                                "multiline": True
                            }
                        },
                        # 日付ピッカー
                        {
                            "type": "input",
                            "block_id": "date_block",
                            "label": {"type": "plain_text", "text": "日付 を選択"},
                            "element": {
                                "type": "datepicker",
                                "action_id": "date_input",
                                "initial_date": initial_date,
                                "placeholder": {"type": "plain_text", "text": "日付を選択"}
                            }
                        },
                        # 時刻（時間単位）のプルダウン
                        {
                            "type": "input",
                            "block_id": "hour_block",
                            "label": {"type": "plain_text", "text": "時間 を選択"},
                            "element": {
                                "type": "static_select",
                                "action_id": "hour_select",
                                "options": hour_options,
                                "initial_option": next(opt for opt in hour_options if opt['value'] == initial_hour),
                            }
                        },
                        # 時刻（MINUTE_INTERVAL 分単位）のプルダウン
                        {
                            "type": "input",
                            "block_id": "minute_block",
                            "label": {"type": "plain_text", "text": "分 を選択"},
                            "element": {
                                "type": "static_select",
                                "action_id": "minute_select",
                                "options": minute_options,
                                # 初期値設定は複雑なのでここでは省略
                                "initial_option": next(opt for opt in minute_options if opt['value'] == initial_minute),
                            }
                        },
                        # メンション選択 (ユーザーセレクト)
                        {
                            "type": "input",
                            "block_id": "user_block",
                            "optional": True,
                            "label": {"type": "plain_text", "text": "メンション"},
                            "element": {
                                "type": "multi_users_select",
                                "action_id": "user_select_input",
                                "placeholder": {"type": "plain_text", "text": "メンションするユーザーを選択"}
                            }
                        }
                    ]
                }
            )
        except Exception as e:
            print(f"Error opening view: {e}")


    # モーダルで「リマインド設定」ボタンが押されたときの処理
    @app.view("reminder_submission")
    def handle_reminder_submission(ack, body, client, logger):
        """
        モーダル送信処理：リマインド予約の実行
        """
        
        # モーダルを閉じる応答
        ack()
        # チャンネルIDは private_metadata から取得 (コマンドを入力したチャンネル)
        channel_id = body["view"]["private_metadata"]
        # ユーザー入力を取得
        values = body["view"]["state"]["values"]
        
        # 値の抽出
        message = values["message_block"]["message_input"]["value"]
        # 設定したユーザー
        user_id_setter = body["user"]["id"]
        # メンションするユーザーIDを取得 (選択されていない場合は None)
        user_ids_to_mention = values["user_block"]["user_select_input"].get("selected_users", [])
        if user_ids_to_mention:
            mention_text = " ".join([f"<@{user_id}>" for user_id in user_ids_to_mention])
        else:
            mention_text = ""

        # プルダウンから選択された時間と分を取得
        date_val = values["date_block"]["date_input"]["selected_date"]
        hour_val = values["hour_block"]["hour_select"]["selected_option"]["value"]
        minute_val = values["minute_block"]["minute_select"]["selected_option"]["value"]
        # 日時をSlackが求めるUNIXタイムスタンプに変換
        combined_dt_str = f"{date_val} {hour_val}:{minute_val}"
        dt_obj = datetime.datetime.strptime(combined_dt_str, "%Y-%m-%d %H:%M")
        # UTCタイムスタンプに変換 (Slack APIは通常、UTCタイムスタンプを要求する)
        post_at_timestamp = int(dt_obj.timestamp())

        # タイムスタンプを取得
        current_timestamp = int(time.time())
        # 過去の時間かどうかをチェック
        if post_at_timestamp <= current_timestamp:
            # 過去の時間だった場合、登録を拒否し、エラーメッセージをユーザーに表示
            error_message = {
                "date_block": "過去の日時は設定できません。未来の日時を選択してください。",
                "hour_block": " ",
                "minute_block": " "
            }
            # ack() 関数にエラーメッセージを渡し、モーダルを閉じずにエラー表示させる
            ack(response_action="errors", errors=error_message)
            
            # エラーを返したため、これ以降のメッセージ予約処理は実行しない
            return
        
        try:
            # リマインドメッセージの作成
            reminder_text = (
                f"{mention_text}\n"
                f"{REMIND_HEADER}\n"
                f"{message}"
            )
            
            # Slack API: chat.scheduleMessageでメッセージを予約投稿
            client.chat_scheduleMessage(
                channel=channel_id, 
                post_at=post_at_timestamp,
                text=reminder_text
            )
            
            instant_post_text = (
                f"【 🔔 新規リマインド 】\n"
                f"<@{user_id_setter}> が {combined_dt_str} にリマインダーを予約しました。\n"
                f"{mention_text}\n"
                f"{message}\n"
            )
            
            client.chat_postMessage(
                channel=channel_id,
                text=instant_post_text
            )
        
        except SlackApiError as e:
            logger.error(f"リマインド予約に失敗しました: {e.response['error']}")
            client.chat_postMessage(
                channel=DEVELOPER_SLACK_ID,
                text=f"<@{user_id_setter}>がリマインダーの設定中にSlack APIエラーが発生しました。\n詳細: `{e.response['error']}`"
            )
        except Exception as e:
            logger.error(f"リマインド予約に失敗しました: {e}")
            client.chat_postMessage(
                channel=DEVELOPER_SLACK_ID,
                text=f"<@{user_id_setter}>がリマインダーの設定中に予期せぬエラーが発生しました。\n詳細: `{e}`"
            )