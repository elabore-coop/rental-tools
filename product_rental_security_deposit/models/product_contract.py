# -*- coding: utf-8 -*-

from logging import setLogRecordFactory
from odoo import fields, api, models, _


class RentalProductContract(models.Model):
    _inherit = "rental.product.contract"

    security_deposit = fields.Monetary(string=_("Security Deposit"))

    @api.onchange("security_deposit")
    def add_security_deposit(self):
        if self.security_deposit and self.product_contract_lines_ids:
            line_id = self.product_contract_lines_ids.filtered(
                lambda x: x.description == "Deposit"
            )
            if line_id:
                line_id.price = self.security_deposit
            else:
                self.write(
                    {
                        "product_contract_lines_ids": [
                            (
                                0,
                                0,
                                {
                                    "description": "Deposit",
                                    "enter_days": 1.0,
                                    "price": self.security_deposit,
                                },
                            )
                        ]
                    }
                )

    @api.depends("product_contract_lines_ids", "security_deposit")
    def _compute_amount(self):
        super(RentalProductContract, self)._compute_amount()
