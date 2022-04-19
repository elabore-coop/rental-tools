# -*- coding: utf-8 -*-

from odoo import models, fields, api


class CrmLead(models.Model):
    _inherit = "crm.lead"

    product_model = fields.Many2one("product.product", string="Product Model")
    from_date = fields.Datetime("From Date")
    to_date = fields.Datetime("To Date")
    sale_number = fields.Integer(
        compute="_compute_sale_amount_total", string="Number of Quotations", default="5"
    )
    order_ids = fields.One2many(
        "rental.product.order", "opportunity_id", string="Orders"
    )
    company_id = fields.Many2one(
        "res.company", string="Company", default=lambda self: self.env.user.company_id
    )

    @api.depends("order_ids")
    def _compute_sale_amount_total(self):
        for lead in self:
            total = 0.0
            nbr = 0
            company_currency = (
                lead.company_currency or self.env.user.company_id.currency_id
            )
            for order in lead.order_ids:
                if order.state in (
                    "draft",
                    "confirm",
                ):
                    nbr += 1
                if order.state not in ("draft", "sent", "cancel"):
                    total += order.currency_id.compute(
                        order.untaxed_amount, company_currency
                    )
            lead.sale_amount_total = total
            lead.sale_number = nbr
        return True
