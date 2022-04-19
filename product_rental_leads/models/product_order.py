# -*- coding: utf-8 -*-

from odoo import models, fields, _


class RentalProductOrder(models.Model):
    _inherit = "rental.product.order"

    opportunity_id = fields.Many2one("crm.lead", string=_("Opportunity"))
