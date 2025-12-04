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
    @app.command("/set-schedule")
    def open_schedule_modal(ack, body, client):
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
                    "callback_id": "schedule_submission",  # 送信時の識別子,
                    "private_metadata": trigger_channel_id,
                    "title": {"type": "plain_text", "text": "🗓️ スケジュール登録"},
                    "submit": {"type": "plain_text", "text": "登録する"},
                    
                    # モーダルのブロック定義
                    "blocks": [
                        # タイトル入力欄
                        {
                            "type": "input",
                            "block_id": "title_block",
                            "label": {"type": "plain_text", "text": "タイトル"},
                            "element": {
                                "type": "plain_text_input",
                                "action_id": "title_input"
                            }
                        },
                        # 開始日付
                        {
                            "type": "input",
                            "block_id": "start_date_block",
                            "label": {"type": "plain_text", "text": "開始日 を選択"},
                            "element": {
                                "type": "datepicker",
                                "action_id": "start_date_input",
                                "initial_date": initial_date,
                                "placeholder": {"type": "plain_text", "text": "日付を選択"}
                            }
                        },
                        # 開始時刻（時間単位）のプルダウン
                        {
                            "type": "input",
                            "block_id": "start_hour_block",
                            "label": {"type": "plain_text", "text": "開始時刻（時間） を選択"},
                            "element": {
                                "type": "static_select",
                                "action_id": "start_hour_select",
                                "options": hour_options,
                                "initial_option": next(opt for opt in hour_options if opt['value'] == initial_hour),
                            }
                        },
                        # 開始時刻（MINUTE_INTERVAL 分単位）のプルダウン
                        {
                            "type": "input",
                            "block_id": "start_minute_block",
                            "label": {"type": "plain_text", "text": "開始時刻（分） を選択"},
                            "element": {
                                "type": "static_select",
                                "action_id": "start_minute_select",
                                "options": minute_options,
                                "initial_option": next(opt for opt in minute_options if opt['value'] == initial_minute),
                            }
                        },
                        # 詳細入力欄
                        {
                            "type": "input",
                            "block_id": "message_block",
                            "optional": True,
                            "label": {"type": "plain_text", "text": "詳細"},
                            "element": {
                                "type": "plain_text_input",
                                "action_id": "message_input",
                                "multiline": True
                            }
                        },
                        # リマインドオフセット（時間前・分前）の選択
                        {
                            "type": "input",
                            "block_id": "offset_block",
                            "label": {"type": "plain_text", "text": "リマインド通知"},
                            "element": {
                                "type": "static_select",
                                "action_id": "offset_select",
                                "placeholder": {"type": "plain_text", "text": "通知時刻を選択"},
                                "options": [
                                    {"text": {"type": "plain_text", "text": "設定時刻にのみ通知"}, "value": "0"},
                                    {"text": {"type": "plain_text", "text": "15分前にも通知"}, "value": "-15m"},
                                    {"text": {"type": "plain_text", "text": "30分前にも通知"}, "value": "-30m"},
                                    {"text": {"type": "plain_text", "text": "1時間前にも通知"}, "value": "-1h"},
                                    {"text": {"type": "plain_text", "text": "3時間前にも通知"}, "value": "-3h"},
                                    {"text": {"type": "plain_text", "text": "1日前にも通知"}, "value": "-1d"},
                                    {"text": {"type": "plain_text", "text": "3日前にも通知"}, "value": "-3d"},
                                ],
                                "initial_option": {"text": {"type": "plain_text", "text": "設定時刻にのみ通知"}, "value": "0"},
                            }
                        },
                    ]
                }
            )
        except Exception as e:
            print(f"Error opening view: {e}")


    # モーダルで「登録」ボタンが押されたときの処理
    @app.view("schedule_submission")
    def handle_schedule_submission(ack, body, client, logger):
        """
        モーダル送信処理：スケジュール登録の実行
        """
        
        # モーダルを閉じる応答
        ack()
        # チャンネルIDは private_metadata から取得 (コマンドを入力したチャンネル)
        channel_id = body["view"]["private_metadata"]
        # ユーザー入力を取得
        values = body["view"]["state"]["values"]
        
        # 値の抽出
        title = values["title_block"]["title_input"]["value"]
        message = values["message_block"]["message_input"]["value"]
        disp_message = f"【詳細】\n{message}" if message else ""
        # 設定したユーザー
        user_id_setter = body["user"]["id"]

        # プルダウンから選択された時間と分を取得
        date_val = values["start_date_block"]["start_date_input"]["selected_date"]
        hour_val = values["start_hour_block"]["start_hour_select"]["selected_option"]["value"]
        minute_val = values["start_minute_block"]["start_minute_select"]["selected_option"]["value"]
        # 日時をSlackが求めるUNIXタイムスタンプに変換
        combined_dt_str = f"{date_val} {hour_val}:{minute_val}"
        dt_obj = datetime.datetime.strptime(combined_dt_str, "%Y-%m-%d %H:%M")
        # UTCタイムスタンプに変換 (Slack APIは通常、UTCタイムスタンプを要求する)
        dt_timestamp = int(dt_obj.timestamp())

        # オフセット値を取得
        offset_val = values["offset_block"]["offset_select"]["selected_option"]["value"]
        # オフセットを処理するための timedelta を初期化
        offset_delta = datetime.timedelta(seconds=0) 
        if offset_val != "0":
            # オフセット値（例: "-1h", "-30m", "-1d"）を解析
            magnitude = int(offset_val[:-1]) # 数値部分（負の値）
            unit = offset_val[-1]            # 単位部分（'m', 'h', 'd'）
            if unit == 'm':
                # 分単位のオフセット
                offset_delta = datetime.timedelta(minutes=magnitude)
            elif unit == 'h':
                # 時間単位のオフセット
                offset_delta = datetime.timedelta(hours=magnitude)
            elif unit == 'd':
                # 日単位のオフセット
                offset_delta = datetime.timedelta(days=magnitude)
                
        schedule_dt_obj = dt_obj + offset_delta
        # UTCタイムスタンプに変換
        offset_timestamp = int(schedule_dt_obj.timestamp())

        # タイムスタンプを取得
        current_timestamp = int(time.time())
        # 過去の時間かどうかをチェック
        if dt_timestamp <= current_timestamp:
            # 過去の時間だった場合、登録を拒否し、エラーメッセージをユーザーに表示
            error_message = {
                "start_date_block": "過去の日時は設定できません。未来の日時を選択してください。",
                "start_hour_block": " ",
                "start_minute_block": " "
            }
            # ack() 関数にエラーメッセージを渡し、モーダルを閉じずにエラー表示させる
            ack(response_action="errors", errors=error_message)
            return
        
        if offset_timestamp <= current_timestamp:
            # リマインド通知が過去だった場合、登録を拒否し、エラーメッセージをユーザーに表示
            error_message = {
                "offset_block": "リマインド設定が過去になっています。選択し直してください。",
            }
            # ack() 関数にエラーメッセージを渡し、モーダルを閉じずにエラー表示させる
            ack(response_action="errors", errors=error_message)
            return
        
        try:
            # リマインドメッセージの作成
            reminder_text = (
                f"\n"
                f"{REMIND_HEADER}\n"
                f"{combined_dt_str} から {title}\n"
                f"{disp_message}"
            )
            
            # Slack API: chat.scheduleMessageでメッセージを予約投稿
            client.chat_scheduleMessage(
                channel=channel_id, 
                post_at=dt_timestamp,
                text=reminder_text
            )
            if offset_val != "0":
                client.chat_scheduleMessage(
                    channel=channel_id, 
                    post_at=offset_timestamp,
                    text=reminder_text
                )
            
            instant_post_text = (
                f"【 🗓️ 新規スケジュール 】\n"
                f"<@{user_id_setter}> がスケジュールを登録しました。\n"
                f"{combined_dt_str} から {title}\n"
                f"{disp_message}"
            )
            
            client.chat_postMessage(
                channel=channel_id,
                text=instant_post_text
            )
        
        except SlackApiError as e:
            logger.error(f"スケジュール登録に失敗しました: {e.response['error']}")
            client.chat_postMessage(
                channel=DEVELOPER_SLACK_ID,
                text=f"<@{user_id_setter}>がリマインダーの設定中にSlack APIエラーが発生しました。\n詳細: `{e.response['error']}`"
            )
        except Exception as e:
            logger.error(f"スケジュール登録に失敗しました: {e}")
            client.chat_postMessage(
                channel=DEVELOPER_SLACK_ID,
                text=f"<@{user_id_setter}>がリマインダーの設定中に予期せぬエラーが発生しました。\n詳細: `{e}`"
            )