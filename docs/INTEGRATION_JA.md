# 既存AIアプリへの組み込み手順

## 1. 元の発言と送信前の候補を用意する

履歴はアプリが保存している原文・発言者・日時・発言IDを渡します。モデルが説明した会話履歴を、実記録として扱わないでください。現在時刻は端末やサーバーが提供するタイムゾーン付き日時、`turn_id` は今回の要求を識別するIDです。

```python
from turn_grounding_guard import build_turn_evidence

evidence = build_turn_evidence(
    recorded_recent_messages,
    user_message=current_user_text,
    reference=current_time_with_timezone,
    turn_id=current_turn_id,
)
```

`recorded_recent_messages` の各行は、`role`（`user` または `assistant`）、`time`、`content`、任意の `message_id` を持つ辞書です。`reference` と `time` は `2026-01-15T07:45:00+09:00` のような形式にします。

次に、既存のモデルで返答案 `draft` を生成します。この段階では画面・音声・外部サービスへ送信せず、候補として保持します。

## 2. 実行器がreceiptを作る

実際の永続記憶保存が成功したあとで、実行器からreceiptを作ります。

```python
from turn_grounding_guard import ExecutionReceipt

receipts = []
operation = your_memory_store.save(record_to_save)
if operation.succeeded:
    receipts.append(ExecutionReceipt(
        turn_id=current_turn_id,
        action="memory.write",
        ok=True,
        receipt_id=operation.id,
    ))
```

この例の `your_memory_store` は、アプリが既に持っている保存機構です。このパッケージには保存機能はありません。保存が要求されていない会話で、receiptを得るために保存処理を追加する必要もありません。その場合は空の配列を渡します。

`memory.update` も対応します。検索・読取りの成功を保存の証拠にしたり、前のターンのreceiptを今回のものへ付け替えたりしないでください。receiptは暗号署名ではなく、信頼できる実行層から渡される構造です。

## 3. 操作を行わない修正コールバックを接続する

```python
from turn_grounding_guard import correction_messages, guard_reply

def correct_text(request):
    messages = correction_messages(request)
    # 下の関数名は、あなたのアプリが持つ既存の生成APIの例です。
    # ツール選択・記憶保存・予定登録などは無効にします。
    return your_text_only_model(
        messages=messages,
        timeout_seconds=30,
        max_output_tokens=500,
    )

result = guard_reply(
    draft, evidence,
    receipts=receipts,
    regenerate=correct_text,
)
```

モデルへは、検出した項目、原文、現在の時刻、候補回答を渡します。モデルは今回の返答だけを修正します。修正指示が書かれた過去発言も、過去のデータとして扱うように明示しています。

コールバックは最大1回です。通信失敗・空文字・非文字列・修正後も残る不整合は `blocked` になります。ライブラリは任意のPythonコールバックを強制終了できないため、通信や生成の上限はアプリ側で設定してください。

## 4. 検証後の返答だけを送る

```python
if result.reply is not None:
    send_to_chat_ui(result.reply)
else:
    show_generation_status("回答の整合性を確認できませんでした。")
```

`show_generation_status` はアプリ側の状態表示です。候補回答の内容を一部送ったり、「保存が完了した」などの代替の事実を作ったりしないでください。音声合成も検証後の `result.reply` だけを読み上げます。

元の候補をストリーミングすると、最終文が修正されても不整合な文が先に表示されます。このAPIで送出を保留する場合は、候補全体を内部で保持してから判定します。

## 5. 検出後の修正例

以下はすべて合成例です。一般化したモデル評価ではありません。

| 記録・状況 | 候補 | 修正例・結果 |
|---|---|---|
| 7:10「おはよう、仕事してくるね」、7:45の会話 | 「またあとで。おやすみなさい。」 | 「またあとでね。気をつけて。」を再検出し、問題が残らなければ送る |
| 朝の挨拶の直後は実際に「行ってらっしゃい」 | 「朝の挨拶の直後におやすみなさいと返した」 | 「朝の挨拶の直後には、行ってらっしゃいと返していました。」を再検出する。後の出来事や経過分数は捏造しない |
| 今回の記憶保存成功receiptなし | 「永続メモリを更新しました。」 | 「この会話では、その点を訂正して答えます。」など、保存を主張しない返答を再検出する |
| 修正後も「おやすみなさい」が残る | 再生成しても未解決 | `blocked`、`reply=None`。候補を送らない |
| 夜勤から帰り「今から寝る」 | 「おやすみなさい。」 | 明示された休息希望と整合するため、朝という時刻だけで止めない |

## 6. アプリ側の受入確認

`examples/agent_integration.py` は、`pass` と `corrected` の文だけがUI送信口へ届き、`blocked` は届かないことをオフラインで確認します。

実アプリでは、候補が先行表示・先行読み上げされないこと、同一ターンのreceiptを使っていること、修正コールバックから操作が実行されないことを、各アプリの送信経路で確かめてください。一般的な質問応答の正確さは別途評価が必要です。
