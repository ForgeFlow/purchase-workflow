# Copyright 2018-2019 Eficent Business and IT Consulting Services S.L.
# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl-3.0).

from openupgradelib import openupgrade
import logging
logger = logging.getLogger(__name__)


def create_allocation(env, po_line, pr_line, stock_move_id, qty):
    vals = {'requested_product_uom_qty': qty,
            'purchase_request_line_id': pr_line,
            'purchase_line_id': po_line,
            'stock_move_id': stock_move_id,
            'allocated_product_qty': 0.0,  # this forces recalculate
            }
    alloc = env['purchase.request.allocation'].create(vals)
    return alloc


def create_service_allocation(env, po_line, pr_line, qty):
    vals = {'requested_product_uom_qty': qty,
            'purchase_request_line_id': pr_line,
            'purchase_line_id': po_line,
            }
    alloc = env['purchase.request.allocation'].create(vals)
    return alloc


def allocate_stockable(ml, a_done=None):
    #  done here because open_product_qty is zero so cannot call method in
    #  stock_move_line
    if a_done is None:
        a_done = []
    ml.product_uom_id._compute_quantity(
        ml.qty_done, ml.product_id.uom_id)
    to_allocate_qty = ml.qty_done
    for allocation in \
            ml.move_id.purchase_request_allocation_ids.filtered(
                lambda a: a.id not in a_done).sudo():
        if to_allocate_qty > 0.0 and \
                allocation.allocated_product_qty < \
                allocation.requested_product_uom_qty:
            allocated_qty = min(
                allocation.requested_product_uom_qty, to_allocate_qty)
            allocation.allocated_product_qty += allocated_qty
            to_allocate_qty -= allocated_qty
        a_done.append(allocation.id)
    return a_done


def create_allocations(env):
    env['purchase.request'].search([('state', '=', 'purchase')])
    cr = env.cr
    #  First allocate stockable and consumables
    logger.info('Allocating purchase request for stockables '
                'and consumables')
    cr.execute(
        """
        SELECT purchase_request_line_id, purchase_order_line_id, sm.id,
         sm.product_qty, sm.product_uom_qty, sm.product_qty, prl.product_qty
        FROM purchase_request_purchase_order_line_rel rel
        INNER JOIN purchase_request_line prl ON prl.id = 
        rel.purchase_request_line_id
        INNER JOIN purchase_order_line pol ON pol.id = 
        rel.purchase_order_line_id    
        INNER JOIN product_product pp ON prl.product_id = pp.id
        INNER JOIN product_template pt ON pp.product_tmpl_id = pt.id
        LEFT JOIN stock_move sm ON sm.purchase_line_id = pol.id
        WHERE pt.type != 'service'
        ORDER BY sm.create_date ASC
        """
    )
    res = cr.fetchall()
    move_ids = []
    for (purchase_request_line_id, purchase_order_line_id, sm_id, product_qty,
         product_uom_qty, move_product_qty, req_qty) in res:

        move_ids.append(sm_id)
        if sm_id:
            # we allocated what is in the stock move
            create_allocation(
                env, purchase_order_line_id, purchase_request_line_id,
                sm_id, move_product_qty)
        else:
            # we allocated what is in the PR line
            create_allocation(
                env, purchase_order_line_id, purchase_request_line_id,
                False, req_qty)
    #  cannot call super, open_qty is zero
    a_done = []
    for move_id in move_ids:
        sm = env['stock.move'].browse(move_id)
        if sm.state == 'done':
            a_done = allocate_stockable(sm.move_line_ids, a_done)
    env['purchase.request.allocation']._compute_open_product_qty()
    env['purchase.request.line']._compute_qty()


def create_service_allocations(env):
    env['purchase.request'].search([('state', '=', 'purchase')])
    cr = env.cr
    #  Allocate services
    logger.info('Allocating purchase request for services')
    cr.execute(
        """
        SELECT purchase_request_line_id, purchase_order_line_id,
         pol.product_qty, pol.product_uom_qty
        FROM purchase_request_purchase_order_line_rel rel
        INNER JOIN purchase_request_line prl ON prl.id = 
        rel.purchase_request_line_id
        INNER JOIN purchase_order_line pol ON pol.id = 
        rel.purchase_order_line_id    
        INNER JOIN product_product pp ON prl.product_id = pp.id
        INNER JOIN product_template pt ON pp.product_tmpl_id = pt.id
        WHERE pt.type = 'service'
        """
    )
    res = cr.fetchall()
    for (purchase_request_line_id, purchase_order_line_id, product_qty,
         product_uom_qty) in res:
        alloc = create_service_allocation(
            env, purchase_order_line_id, purchase_request_line_id,
            product_qty)
        pol = env['purchase.order.line'].browse(purchase_order_line_id)
        pol.with_context(no_notify=True).update_service_allocations()
        alloc._compute_open_product_qty()


@openupgrade.migrate(use_env=True)
def migrate(env, version):
    if not version:
        return
    create_allocations(env)
    create_service_allocations(env)
