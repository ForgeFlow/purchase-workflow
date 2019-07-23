# Copyright 2018-2019 Eficent Business and IT Consulting Services S.L.
# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl-3.0).

import logging
logger = logging.getLogger(__name__)


def store_field_qty_in_progress(cr):
    cr.execute("""SELECT column_name
    FROM information_schema.columns
    WHERE table_name='purchase_request' AND
    column_name='qty_in_progress'""")
    if not cr.fetchone():
        cr.execute(
            """
            ALTER TABLE purchase_request ADD COLUMN qty_in_progress float;
            """)

    logger.info('Computing field qty_in_progress on purchase.request.line')

    cr.execute(
        """
        UPDATE purchase_request_line to_update
        SET qty_in_progress = 0.0
        WHERE qty_in_progress is null
        """
    )


def store_field_qty_done(cr):
    cr.execute("""SELECT column_name
    FROM information_schema.columns
    WHERE table_name='purchase_request' AND
    column_name='qty_done'""")
    if not cr.fetchone():
        cr.execute(
            """
            ALTER TABLE purchase_request ADD COLUMN qty_done float;
            """)

    logger.info('Computing field qty_done on purchase.request.line')

    cr.execute(
        """
        UPDATE purchase_request_line to_update
        SET qty_cancelled = to_update.product_qty
        FROM purchase_request_line prl
        INNER JOIN purchase_request pr ON prl.request_id = pr.id        
        WHERE pr.state = 'done'
        AND to_update.id = prl.id
        """
    )
    cr.execute(
        """
        UPDATE purchase_request_line to_update
        SET qty_done = 0.0
        WHERE qty_done is null
        """
    )


def store_field_qty_cancelled(cr):
    cr.execute("""SELECT column_name
    FROM information_schema.columns
    WHERE table_name='purchase_request' AND
    column_name='qty_cancelled'""")
    if not cr.fetchone():
        cr.execute(
            """
            ALTER TABLE purchase_request ADD COLUMN qty_cancelled float;
            """)

    logger.info('Computing field qty_cancelled on purchase.request.line')

    cr.execute(
        """
        UPDATE purchase_request_line to_update
        SET qty_cancelled = to_update.product_qty
        FROM purchase_request_line prl
        INNER JOIN purchase_request pr ON prl.request_id = pr.id        
        WHERE pr.state = 'cancel'
        AND to_update.id = prl.id
        """
    )
    cr.execute(
        """
        UPDATE purchase_request_line to_update
        SET qty_cancelled = 0.0
        WHERE qty_cancelled is null
        """
    )


def migrate(cr, version):
    if not version:
        return
    store_field_qty_cancelled(cr)
    store_field_qty_done(cr)
    store_field_qty_in_progress(cr)
