# -*- coding: utf-8 -*-
# © 2013-2015 Camptocamp SA - Nicolas Bessi, Leonardo Pistone
# © 2016 Eficent Business and IT Consulting Services S.L.
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).

from datetime import timedelta, date
from openerp import fields
import openerp.tests.common as test_common
from .common import BaseAgreementTestMixin


class TestAvailableQty(test_common.TransactionCase, BaseAgreementTestMixin):

    """Test the function fields available_quantity"""

    def setUp(self):
        """ Create a default agreement"""
        super(TestAvailableQty, self).setUp()
        self.commonsetUp()
        start_date = date.today() + timedelta(days=10)
        end_date = date.today() + timedelta(days=20)

        self.agreement = self.agreement_model.create({
            'portfolio_id': self.portfolio.id,
            'product_id': self.product.id,
            'start_date': fields.Date.to_string(start_date),
            'end_date': fields.Date.to_string(end_date),
            'delay': 5,
            'quantity': 200,
        })
        pl = self.agreement_pl_model.create(
            {'framework_agreement_id': self.agreement.id,
             'currency_id': self.ref('base.EUR')}
        )

        self.agreement_line_model.create(
            {'framework_agreement_pricelist_id': pl.id,
             'quantity': 0,
             'price': 77.0}
        )
        self.agreement.open_agreement(strict=False)

    def test_00_noting_consumed(self):
        """Test non consumption"""
        self.assertEqual(self.agreement.available_quantity, 200)

    def test_01_150_consumed(self):
        """ test consumption of 150 units"""
        po = self.env['purchase.order'].create(
            self._map_agreement_to_po(self.agreement, delta_days=5))
        self.env['purchase.order.line'].create(
            self._map_agreement_to_po_line(self.agreement, qty=150, po=po))

        po.button_confirm()
        self.assertIn(po.state, 'purchase')
        self.assertEqual(self.agreement.available_quantity, 50)

    def _map_agreement_to_po(self, agreement, delta_days):
        """Map agreement to dict to be used by PO create"""
        supplier = agreement.supplier_id
        address = self.env.ref('base.res_partner_3')
        start_date = fields.Date.from_string(agreement.start_date)
        date_order = start_date + timedelta(days=delta_days)

        return {
            'partner_id': supplier.id,
            'dest_address_id': address.id,
            'payment_term_id': supplier.property_supplier_payment_term_id.id,
            'origin': agreement.name,
            'date_order': fields.Date.to_string(date_order),
            'name': agreement.name,
            'currency_id': self.ref('base.EUR')
        }

    def _map_agreement_to_po_line(self, agreement, qty, po):
        """Map agreement to dict to be used by PO line create"""
        currency = po.currency_id
        return {
            'product_qty': qty,
            'product_id': agreement.product_id.product_variant_ids[0].id,
            'product_uom': agreement.product_id.uom_id.id,
            'price_unit': agreement.get_price(qty, currency=currency),
            'name': agreement.product_id.name,
            'order_id': po.id,
            'date_planned': fields.Date.today(),
            'framework_agreement_id': agreement.id,
        }
