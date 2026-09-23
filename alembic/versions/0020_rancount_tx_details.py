"""RanCount transaction details and refund relation.

Revision ID: 0020_rancount_tx_details
Revises: 0019_account_hidden
"""

import sqlalchemy as sa
from alembic import op


revision = "0020_rancount_tx_details"
down_revision = "0019_account_hidden"
branch_labels = None
depends_on = None


def upgrade() -> None:
    for name, type_ in (
        ("merchant", sa.Text()),
        ("item_description", sa.Text()),
        ("payment_channel", sa.Text()),
        ("refund_of_sync_id", sa.String(255)),
    ):
        op.add_column("read_tx_projection", sa.Column(name, type_, nullable=True))
    op.create_index(
        "ix_read_tx_refund_of", "read_tx_projection", ["refund_of_sync_id"]
    )


def downgrade() -> None:
    op.drop_index("ix_read_tx_refund_of", table_name="read_tx_projection")
    for name in ("refund_of_sync_id", "payment_channel", "item_description", "merchant"):
        op.drop_column("read_tx_projection", name)
