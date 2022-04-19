# -*- coding: utf-8 -*-

from odoo import models, fields, api


class ProductDelayLines(models.Model):
    _name = "product.delayed.lines"
    _description = "Product Delayed Lines"

    @api.depends("delayed_hours", "delay_cost_per_hour")
    def _get_subtotal(self):
        for each in self:
            each.sub_total = each.delayed_hours * each.delay_cost_per_hour

    product_delay_id = fields.Many2one("stock.picking", string="Product Move")
    product_id = fields.Many2one("product.product", string="Product Name")
    delay_cost_per_hour = fields.Float(string="Cost/Hour")
    delayed_hours = fields.Float(string="Total Hours")
    sub_total = fields.Float(string="Sub Total", compute="_get_subtotal", store=True)
    products_checked = fields.Boolean(string="Select Products")
