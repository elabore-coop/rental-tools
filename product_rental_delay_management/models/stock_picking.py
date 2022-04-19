# -*- coding: utf-8 -*-

from datetime import datetime

from odoo import models, fields, api, _
from odoo.exceptions import UserError
from odoo.tests import Form


class StockPicking(models.Model):
    _inherit = "stock.picking"

    product_delay_line_ids = fields.One2many(
        "product.delayed.lines", "product_delay_id", string="Delayed Hours "
    )
    is_delayed = fields.Boolean(string="Is Delayed")
    total_amount = fields.Float(
        string="Total Amount", compute="_compute_total", store=True
    )

    @api.depends("product_delay_line_ids")
    def _compute_total(self):
        for record in self:
            for line in record.product_delay_line_ids:
                record.total_amount += line.sub_total

    def delivery(self):
        product_delay_line_ids = []
        if any([each.products_checked for each in self.move_ids_without_package]):
            deliver_move_id = super(StockPicking, self).delivery()
            deliver_move_id.write(
                {
                    "product_delay_line_ids": product_delay_line_ids,
                }
            )
