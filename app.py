from flask import Flask, request, abort
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import os
import pandas as pd

from linebot import (
    LineBotApi, WebhookHandler
)
from linebot.exceptions import (
    InvalidSignatureError
)
from linebot.models import (
    MessageEvent, TextMessage, ImageMessage, TextSendMessage, FollowEvent, SourceGroup, SourceRoom
)
from dotenv import load_dotenv

app = Flask(__name__)

# LINE MessagingAPIの情報
load_dotenv()
line_bot_api = LineBotApi(os.getenv('YOUR_CHANNEL_ACCESS_TOKEN'))
handler = WebhookHandler(os.getenv('YOUR_CHANNEL_SECRET'))

# google シートの情報
SP_SHEET_KEY = os.getenv('SP_SHEET_KEY')
SP_SHEET = os.getenv('SP_SHEET')

def auth():
    # Google Sheets APIの設定
    scope = ['https://spreadsheets.google.com/feeds',
            'https://www.googleapis.com/auth/drive']
    credentials = ServiceAccountCredentials.from_json_keyfile_name('json/gcp-credentials.json', scope)
    gc = gspread.authorize(credentials)
    worksheet = gc.open_by_key(SP_SHEET_KEY).worksheet(SP_SHEET)
    return worksheet

# スプレッドシートへのアップロード関数
def upload_url(url):
    worksheet = auth()
    df = pd.DataFrame(worksheet.get_all_records())
    # 新しいURLをDataFrameに追加
    new_row = pd.DataFrame([[url]], columns=['URL'])
    df = pd.concat([df, new_row], ignore_index=True)
    worksheet.append_row(new_row.values.flatten().tolist())
    return worksheet

@app.route('/')
def hello_world():
    return 'Hello, World!'

# ここはLINE MessagingAPIのWebhookの設定
@app.route("/callback", methods=['POST'])
def callback():
    signature = request.headers['X-Line-Signature']

    body = request.get_data(as_text=True)
    app.logger.info("Request body: " + body)
    try:
        handler.handle(body, signature)
    except InvalidSignatureError:
        abort(400)
    return 'OK'

@handler.add(MessageEvent, message=TextMessage)
def handle_message(event):
    text = event.message.text
    parts = text.split(',', 1)
    if len(parts) == 2 and parts[1].strip().startswith("http"):
        category = parts[0].strip()
        url = parts[1].strip()
        try:
            upload_url(url)
            line_bot_api.reply_message(
                event.reply_token,
                TextSendMessage(text="カテゴリーとURLを保存しました。")
            )
        except Exception as e:
            line_bot_api.reply_message(
                event.reply_token,
                TextSendMessage(text="カテゴリーとURLの保存中にエラーが発生しました。もう一度お試しください。")
            )
    elif text.startswith("http"):
        try:
            upload_url(text)
            line_bot_api.reply_message(
                event.reply_token,
                TextSendMessage(text="URLを保存しました。")
            )
        except Exception as e:
            line_bot_api.reply_message(
                event.reply_token,
                TextSendMessage(text="URLの保存中にエラーが発生しました。もう一度お試しください。")
            )
    else:
        line_bot_api.reply_message(
            event.reply_token,
            TextSendMessage(text=f"URLを送信してください。\nそれ以外はおうむ返しします。\n{event.message.text}")
        )


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)