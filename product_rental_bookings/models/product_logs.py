# -*- coding: utf-8 -*-

from odoo import models, fields


class RentalProductLogs(models.Model):
    _name = "rental.product.logs"
    _description = "product Products Logs"
    _rec_name = "product_id"

    product_id = fields.Many2one("product.product", string="Product")
    customer_id = fields.Many2one("res.partner", string="Customer")
    from_date = fields.Date(string="From Date")
    to_date = fields.Date(string="To Date")
    company_id = fields.Many2one(
        "res.company", string="Company", default=lambda self: self.env.user.company_id
    )
