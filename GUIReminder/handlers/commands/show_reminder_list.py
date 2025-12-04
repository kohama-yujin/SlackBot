import os
import datetime
from dotenv import load_dotenv
from slack_sdk.errors import SlackApiError


load_dotenv()
DEVELOPER_SLACK_ID = os.environ.get("DEVELOPER_SLACK_ID")


def register(app):
    
    
    def build_list_modal_blocks(messages):
        """
        予約メッセージのリストからモーダル用の Block Kit リストを生成する
        """
        
        if not messages:
            return [
                {
                    "type": "section",
                    "text": {"type": "mrkdwn", "text": "現在、このチャンネルに予約されているリマインダーはありません。"}
                }
            ]
            
        blocks = []
        
        for msg in messages:
            schedule_time_ts = msg.get("post_at")
            schedule_id = msg.get("id")
            
            # UNIXタイムスタンプを人が読める形式に変換
            schedule_time = datetime.datetime.fromtimestamp(
                schedule_time_ts, 
                tz=datetime.timezone.utc
            ).astimezone(None)

            # 予約メッセージの本文（text）から、リマインド内容を取得
            full_text = msg.get("text", "（内容不明）")
            
            # REMIND_HEADER 以外を抽出
            parts = full_text.split('\n', 2)
            mentions = parts[0]
            disp_mentions = f"【メンション】{mentions}" if mentions else ""
            preview_text = parts[2]
            ellipsis = "..." if len(preview_text) >= 50 else ""
            
            # リマインダー情報の Section Block
            blocks.append({
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": (
                        f"{disp_mentions}\n"
                        f"【予約日時】{schedule_time.strftime('%Y/%m/%d %H:%M')}\n"
                        f"【内容】\n{preview_text[:50]}" + ellipsis
                    )
                }
            })
            
            # blocks.append({
            #     "type": "actions",
            #     "elements": [
            #         # 編集ボタン
            #         {
            #             "type": "button",
            #             "text": {"type": "plain_text", "text": "編集"},
            #             "style": "primary",
            #             "value": schedule_id, 
            #             "action_id": "open_edit_modal"
            #         },
            #         # 削除ボタン
            #         {
            #             "type": "button",
            #             "text": {"type": "plain_text", "text": "削除"},
            #             "style": "danger", # 削除操作は赤色（danger）が推奨
            #             "value": schedule_id, 
            #             "action_id": "open_delete_modal"
            #         }
            #     ]
            # })
            
            # 区切り線の Divider Block
            blocks.append({"type": "divider"})
        
        return blocks
    

    @app.command("/show-reminder-list")
    def open_reminder_list_modal(ack, body, client, logger):
        ack()
        
        channel_id = body["channel_id"]
        
        try:
            result = client.chat_scheduledMessages_list(
                channel=channel_id
            )
            
            messages = result.get("scheduled_messages", [])
            
            # ソート
            sorted_messages = sorted(messages, key=lambda msg: msg.get('post_at', 0))
            # 予約メッセージのリストをBlock Kitの要素に変換
            modal_blocks = build_list_modal_blocks(sorted_messages)
            
            # モーダルを開く
            client.views_open(
                trigger_id=body["trigger_id"],
                view={
                    "type": "modal",
                    "callback_id": "reminder_list_modal", 
                    "private_metadata": body["channel_id"],
                    "title": {"type": "plain_text", "text": "📝 予約中のリマインダー"},
                    "blocks": modal_blocks
                }
            )

        except SlackApiError as e:
            logger.error(f"予約メッセージの取得に失敗しました: {e.response['error']}")
            # エラー時はチャンネルにメッセージを投稿してユーザーに通知
            client.chat_postMessage(
                channel=channel_id,
                text=f"リマインダー一覧の取得中にエラーが発生しました。\n詳細: `{e.response['error']}`"
            )


    # def open_confirmation_modal(client, logger, schedule_id, trigger_id, channel_id):
    #     try:
    #         # ※ chat.scheduledMessages.list は全件リストであり、特定IDの詳細は取得できないため、
    #         #    リスト全体を取得して該当IDを検索する必要があります。
    #         result = client.chat_scheduledMessages_list(channel=channel_id)
            
    #         # IDが一致するメッセージを検索
    #         message_data = next((m for m in result.get("scheduled_messages", []) if m["id"] == schedule_id), None)
            
    #         if not message_data:
    #             # メッセージが見つからない場合のエラー処理
    #             client.chat_postMessage(channel=channel_id, text="⚠ 編集対象のリマインダーが見つかりませんでした。")
    #             return

    #         # リマインド内容と日時を抽出
    #         raw_text = message_data.get("text", "（内容不明）")
            
    #         # プレビューテキストの取得 (以前の抽出ロジックを使用)
    #         # 最終行の内容のみを取得（実際の構造に合わせて調整してください）
    #         preview_text = raw_text.split('\n\n')[-1].strip()
            
    #         # UNIXタイムスタンプから日時を取得
    #         schedule_time_ts = message_data.get("post_at")
    #         schedule_time = datetime.datetime.fromtimestamp(schedule_time_ts).strftime('%Y/%m/%d %H:%M:%S')

    #         # 最終確認モーダルを開く
    #         client.views_open(
    #             trigger_id=trigger_id,
    #             view={
    #                 "type": "modal",
    #                 "callback_id": "edit_delete_confirmation",
    #                 "private_metadata": schedule_id, # 削除・編集時に必要
    #                 "title": {"type": "plain_text", "text": "リマインダーの確認"},
    #                 "blocks": [
    #                     {
    #                         "type": "section",
    #                         "text": {"type": "mrkdwn", "text": f"**設定日時**: {schedule_time}\n**内容**: {preview_text}"}
    #                     },
    #                     {"type": "divider"},
    #                     # 編集ボタンと削除ボタンを Actions Block で配置
    #                     {
    #                         "type": "actions",
    #                         "elements": [
    #                             {
    #                                 "type": "button",
    #                                 "text": {"type": "plain_text", "text": "✏️ 編集する"},
    #                                 "style": "primary",
    #                                 "value": schedule_id,
    #                                 "action_id": "final_edit_button" # 編集フローへ
    #                             },
    #                             {
    #                                 "type": "button",
    #                                 "text": {"type": "plain_text", "text": "🗑️ 削除する"},
    #                                 "style": "danger",
    #                                 "value": schedule_id,
    #                                 "action_id": "final_delete_button" # 削除フローへ
    #                             }
    #                         ]
    #                     }
    #                 ]
    #             }
    #         )
    #     except SlackApiError as e:
    #         logger.error(f"リマインダー詳細の取得に失敗: {e.response['error']}")


    # @app.action("open_edit_modal")
    # def handle_edit_click(ack, body, client, logger):
    #     ack()
        
    #     # ユーザーがクリックしたボタンの value (schedule_id) を取得
    #     schedule_id = body["actions"][0]["value"]
    #     trigger_id = body["trigger_id"]
    #     channel_id = body["channel"]["id"]
        
    #     # 編集用モーダルを開く関数を呼び出す
    #     open_confirmation_modal(client, logger, schedule_id, trigger_id, channel_id)


    # @app.action("open_delete_modal")
    # def handle_delete_scheduled_reminder(ack, body, client, logger):
    #     ack()
        
    #     # 削除対象IDの取得
    #     schedule_id = str(body["actions"][0]["value"])
        
    #     # チャンネルIDの安全な取得 (モーダルからのアクションと仮定)
    #     view_metadata = body.get("view", {}).get("private_metadata")
        
    #     # private_metadata が存在しなければ、アクションペイロード内の channel ID を試す
    #     if view_metadata:
    #         channel_id = view_metadata
    #     else:
    #         # fallback: メッセージ上のボタンなど、他の形式のペイロードを想定
    #         channel_id = body.get("channel", {}).get("id")
            
    #     if not channel_id:
    #         logger.error("Channel ID not found for scheduled message deletion.")
    #         # チャンネルIDが取得できない場合は処理を中断
    #         return 

    #     try:
    #         # chat.deleteScheduledMessage APIを使って予約メッセージを削除
    #         client.chat_deleteScheduledMessage(
    #             channel=channel_id,
    #             scheduled_message_id=schedule_id
    #         )
            
    #         # 削除成功の確認メッセージを投稿 (Ephemeral Messageでユーザーに通知)
    #         client.chat_postEphemeral(
    #             channel=channel_id,
    #             user=body["user"]["id"],
    #             text=f"✅ 予約ID `{schedule_id}` のリマインダーを削除しました。",
    #             # モーダル内のメッセージを更新したい場合は view_update を使うが、今回はシンプルにephemeralで通知
    #         )

    #     except SlackApiError as e:
    #         logger.error(f"予約メッセージの削除に失敗: {e.response['error']}")
    #         client.chat_postEphemeral(
    #             channel=channel_id,
    #             user=body["user"]["id"],
    #             text=f"❌ リマインダーの削除に失敗しました: `{e.response['error']}`"
    #         )