"""RanCount transaction details survive partial push and full recovery."""

from sqlalchemy import select

from src.main import app
from src.models import Ledger, ReadTxProjection
from src.snapshot_builder import build

from test_tx_multi_currency import _make_client, _two_tokens, _push, _iso


def test_details_refund_relation_survive_merge_and_full_snapshot():
    client, TS = _make_client()
    try:
        app_token, web_token = _two_tokens(client, "rancount-details@test.local")
        app_hdr = {"Authorization": f"Bearer {app_token}"}
        web_hdr = {"Authorization": f"Bearer {web_token}"}

        _push(client, app_hdr, "lg-ran", "ledger", "lg-ran", {
            "syncId": "lg-ran", "ledgerName": "账本", "currency": "CNY",
        })
        _push(client, app_hdr, "lg-ran", "transaction", "tx-original", {
            "syncId": "tx-original", "type": "expense", "amount": 100,
            "happenedAt": _iso(), "merchant": "书店",
            "itemDescription": "图书", "paymentChannel": "微信支付",
        })
        _push(client, app_hdr, "lg-ran", "transaction", "tx-refund", {
            "syncId": "tx-refund", "type": "expense", "amount": -30,
            "happenedAt": _iso(), "refundOfSyncId": "tx-original",
        })
        _push(client, app_hdr, "lg-ran", "transaction", "tx-original", {
            "syncId": "tx-original", "type": "expense", "amount": 100,
            "happenedAt": _iso(), "note": "edited by an old client",
        })

        with TS() as db:
            ledger = db.scalar(select(Ledger).where(Ledger.external_id == "lg-ran"))
            original = db.scalar(select(ReadTxProjection).where(
                ReadTxProjection.ledger_id == ledger.id,
                ReadTxProjection.sync_id == "tx-original",
            ))
            refund = db.scalar(select(ReadTxProjection).where(
                ReadTxProjection.ledger_id == ledger.id,
                ReadTxProjection.sync_id == "tx-refund",
            ))
            assert original.merchant == "书店"
            assert original.item_description == "图书"
            assert original.payment_channel == "微信支付"
            assert refund.refund_of_sync_id == "tx-original"
            items = {item["syncId"]: item for item in build(db, ledger)["items"]}
            assert items["tx-original"]["merchant"] == "书店"
            assert items["tx-original"]["itemDescription"] == "图书"
            assert items["tx-original"]["paymentChannel"] == "微信支付"
            assert items["tx-refund"]["refundOfSyncId"] == "tx-original"

        response = client.get(
            "/api/v1/read/ledgers/lg-ran/transactions", headers=web_hdr
        )
        assert response.status_code == 200, response.text
        by_id = {item["id"]: item for item in response.json()}
        assert by_id["tx-original"]["merchant"] == "书店"
        assert by_id["tx-refund"]["refund_of_sync_id"] == "tx-original"
    finally:
        app.dependency_overrides.clear()
