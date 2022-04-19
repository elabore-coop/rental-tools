# -*- coding: utf-8 -*-

from datetime import datetime, date, timedelta

from dateutil.relativedelta import relativedelta
from odoo import fields, api, models, _
from odoo.exceptions import UserError, ValidationError


class RentalProductContract(models.Model):
    _name = "rental.product.contract"
    _description = "Product Rental Contract"

    name = fields.Char("Name")
    partner_id = fields.Many2one("res.partner", string="Customer", required=True)
    rental_id = fields.Many2one("rental.product.order", string="Rental Order Id")
    contract_date = fields.Date(
        string="Contract Date",
    )
    contractor_id = fields.Many2one("res.users", string="Contractor Name")
    from_date = fields.Date(string="From Date")
    to_date = fields.Date(string="To Date")
    account_payment_term = fields.Many2one(
        "account.payment.term", string="Payment Term", required=True
    )
    damage_charge = fields.Monetary(string="Damage Charge")
    additional_charges = fields.Monetary(string="Additional Charges")
    subtotal = fields.Monetary(string="Sub Total", readonly=True)
    taxes = fields.Float(string="Taxes", compute="_compute_amount", readonly=True)
    untaxed_amount = fields.Monetary(
        string="Untaxed Amount",
        compute="_compute_amount",
    )
    extra_charges = fields.Monetary(string="Extra Charges")
    invoice_ids = fields.Many2one("account.move", string="Invoice Id")
    signature = fields.Binary(string="Contractor Signature  ")
    signature_contractor = fields.Binary(string="Contractor Signature")
    signature_customer = fields.Binary(string="Customer Signature")
    button_name = fields.Char(string="Button Name")
    terms_condition = fields.Text(string="Terms and Condition")
    product_contract_lines_ids = fields.One2many(
        "product.contract.lines", "product_contract_id", string="Order Line"
    )
    pricelist_id = fields.Many2one("product.pricelist", string="Pricelist")
    total_amount = fields.Monetary(string="Total Amount", compute="_compute_amount")
    total = fields.Monetary(string="Total", compute="_compute_total")
    cost_generated = fields.Monetary(
        string="Recurring Cost",
        help="Costs paid at regular intervals, depending on the cost frequency",
    )
    cost_frequency = fields.Selection(
        [
            ("no", "No"),
            ("daily", "Daily"),
            ("weekly", "Weekly"),
            ("monthly", "Monthly"),
            ("yearly", "Yearly"),
        ],
        string="Recurring Cost Frequency",
        required=True,
    )
    state = fields.Selection(
        [
            ("futur", "Incoming"),
            ("open", "In Progress"),
            ("expired", "Expired"),
            ("diesoon", "Expiring Soon"),
            ("closed", "Closed"),
        ],
        "Status",
        default="open",
        readonly=True,
    )
    cost = fields.Monetary(
        string="Rent Cost",
        help="This fields is to determine the cost of rent",
        required=True,
    )
    account_type = fields.Many2one(
        "account.account",
        "Account",
        default=lambda self: self.env["account.account"].search([("id", "=", 17)]),
    )
    recurring_line = fields.One2many(
        "product.rental.line", "rental_number", readonly=True
    )
    attachment_ids = fields.Many2many(
        "ir.attachment",
        "product_rent_ir_attachments_rel",
        "rental_id",
        "attachment_id",
        string="Attachments",
    )
    sum_cost = fields.Float(
        compute="_compute_sum_cost", string="Indicative Costs Total"
    )
    auto_generated = fields.Boolean("Automatically Generated", readonly=True)
    generated_cost_ids = fields.One2many(
        "product.rental.line", "rental_number", string="Generated Costs"
    )
    invoice_count = fields.Integer(
        compute="_invoice_count", string="# Invoice", copy=False
    )
    first_payment = fields.Float(string="First Payment", compute="_compute_amount")
    first_invoice_created = fields.Boolean(
        string="First Invoice Created", default=False
    )
    origin = fields.Char(string="Order Reference")
    picking_id = fields.Many2one("stock.picking", string="Picking")
    document_ids = fields.One2many(
        "customer.document", "contract_id", string="Contract"
    )
    company_id = fields.Many2one(
        "res.company", string="Company", default=lambda self: self.env.user.company_id
    )
    currency_id = fields.Many2one("res.currency", related="company_id.currency_id")
    cancel_policy_ids = fields.One2many(
        "rental.policy", "contract_id", string="Cancel Policy"
    )
    number_of_slot = fields.Integer(string="Number of Slot")
    is_hours = fields.Boolean(string="Hours")
    is_days = fields.Boolean(string="Days")

    def generate_policy(self):
        if not self.cancel_policy_ids and self.number_of_slot != 0:
            number_of_days = self.from_date - self.contract_date
            cancel_policy_list = []
            if number_of_days.days >= (self.number_of_slot * 2):
                day_per_slot = int(number_of_days.days / self.number_of_slot - 1)
                day = 0
                for i in range(self.number_of_slot - 1):
                    cancel_policy_list.append(
                        (
                            0,
                            0,
                            {
                                "from_date": self.contract_date + timedelta(day),
                                "to_date": self.contract_date
                                + timedelta(day_per_slot + day),
                            },
                        )
                    )
                    day += day_per_slot + 1
                cancel_policy_list.append(
                    (
                        0,
                        0,
                        {
                            "from_date": self.contract_date + timedelta(day),
                            "to_date": self.from_date - timedelta(days=2),
                        },
                    )
                )
                cancel_policy_list.append(
                    (
                        0,
                        0,
                        {
                            "from_date": self.from_date - timedelta(days=1),
                            "policy_charged": 100,
                        },
                    )
                )
                self.cancel_policy_ids = cancel_policy_list
            else:
                raise ValidationError(_("Please enter the sufficient Number of Slot"))

    def write(self, vals):
        if "button_name" in vals.keys():
            if vals["button_name"] == "signature_contractor":
                vals["signature_contractor"] = vals["signature"]
            elif vals["button_name"] == "signature_customer":
                vals["signature_customer"] = vals["signature"]
        return super(RentalProductContract, self).write(vals)

    @api.depends("product_contract_lines_ids")
    def _compute_amount(self):
        """
        Compute the total amounts of the SO.
        """
        for order in self:
            untaxed_amount = 0.0
            taxes = 0.0
            total_amount = 0.0
            for line in order.product_contract_lines_ids:
                untaxed_amount += line.sub_total
                taxes += line.price_tax
                total_amount += line.sub_total + line.price_tax
            order.update(
                {
                    "untaxed_amount": untaxed_amount,
                    "taxes": taxes,
                    "total_amount": untaxed_amount + taxes + order.extra_charges,
                    "first_payment": untaxed_amount + taxes + order.extra_charges,
                }
            )

    @api.depends("recurring_line.recurring_amount")
    def _compute_sum_cost(self):
        for contract in self:
            contract.sum_cost = sum(contract.recurring_line.mapped("recurring_amount"))

    def _invoice_count(self):
        invoice_ids = self.env["account.move"].search(
            [("invoice_origin", "=", self.name)]
        )
        self.invoice_count = len(invoice_ids)

    @api.model
    def create(self, vals):
        sequence_no = self.env["ir.sequence"].next_by_code("product_contract") or _(
            "Product Contract"
        )
        vals.update({"name": sequence_no})
        return super(RentalProductContract, self).create(vals)

    @api.depends("product_contract_lines_ids", "damage_charge")
    def _compute_total(self):
        self.total = self.total_amount + self.damage_charge

    def contract_close(self):
        invoice_ids = self.env["account.move"].search(
            [("invoice_origin", "=", self.name)]
        )
        order_ids = self.env["rental.product.order"].search(
            [("res_number", "=", self.origin)]
        )
        is_paid = 0
        for each in invoice_ids:
            if each.state != "posted":
                is_paid = 1
                break

        if is_paid == 0:
            self.state = "closed"
            order_ids.state = "close"
        else:
            raise UserError("Please Check invoices There are Some Invoices are pending")

    def contract_open(self):
        for record in self:
            order_ids = self.env["rental.product.order"].search(
                [("res_number", "=", record.origin)]
            )
            record.state = "open"
            order_ids.state = "draft"

    def act_renew_contract(self):
        product_list = []
        for product_line in self.product_contract_lines_ids:
            product_list.append(
                (
                    0,
                    0,
                    {
                        "product_id": product_line.product_id.id,
                        "price_based": product_line.price_based,
                        "enter_days": product_line.enter_days,
                        "price": product_line.price,
                        "enter_hour": product_line.enter_hour,
                    },
                )
            )
        assert (
            len(self.ids) == 1
        ), "This operation should only be done for 1 single contract at a time, as it it suppose to open a window as result"
        for element in self:
            # compute end date
            startdate = fields.Date.from_string(element.from_date)
            enddate = fields.Date.from_string(element.to_date)
            diffdate = enddate - startdate
            default = {
                "contract_date": fields.Date.context_today(self),
                "from_date": fields.Date.to_string(
                    fields.Date.from_string(element.to_date) + relativedelta(days=1)
                ),
                "to_date": fields.Date.to_string(enddate + diffdate),
                "cost_generated": self.cost_generated,
                "product_contract_lines_ids": product_list,
            }
            newid = element.copy(default).id
        return {
            "name": _("Renew Contract"),
            "view_mode": "form",
            "view_id": self.env.ref(
                "product_rental_bookings.rental_product_contract_form"
            ).id,
            "view_type": "tree,form",
            "res_model": "rental.product.contract",
            "type": "ir.actions.act_window",
            "res_id": newid,
        }

    def send_product_contract(self):
        """
        This is Email for send contract Detail
        """
        self.ensure_one()
        ir_model_data = self.env["ir.model.data"]
        try:
            template_id = ir_model_data.get_object_reference(
                "product_rental_bookings", "email_template_product_contract"
            )[1]
        except ValueError:
            template_id = False
        try:
            compose_form_id = ir_model_data.get_object_reference(
                "mail", "email_compose_message_wizard_form"
            )[1]
        except ValueError:
            compose_form_id = False
        ctx = {
            "default_model": "rental.product.contract",
            "default_res_id": self.ids[0],
            "default_use_template": bool(template_id),
            "default_template_id": template_id,
            "mark_so_as_sent": True,
        }
        return {
            "type": "ir.actions.act_window",
            "view_type": "form",
            "view_mode": "form",
            "res_model": "mail.compose.message",
            "views": [(compose_form_id, "form")],
            "view_id": compose_form_id,
            "target": "new",
            "context": ctx,
        }

    def send_email_for_firstpayment(self, inv_id, contracts):
        """
        Send email for payment.
        """
        mail_content = _(
            "<h3>First Payment!</h3><br/>Hi %s, <br/> This is to notify that You have to pay amount as per mention below.<br/><br/>"
            "Please find the details below:<br/><br/>"
            "<table><tr><td>Reference Number<td/><td> %s<td/><tr/>"
            "<tr><td>Date<td/><td> %s <td/><tr/><tr><td>Amount <td/><td> %s<td/><tr/><table/>"
        ) % (
            contracts.partner_id.name,
            inv_id.invoice_origin,
            date.today(),
            inv_id.amount_total,
        )
        main_content = {
            "subject": _("You First Payment For: %s") % inv_id.invoice_origin,
            "author_id": contracts.env.user.partner_id.id,
            "body_html": mail_content,
            "email_to": contracts.partner_id.email,
        }
        self.env["mail.mail"].create(main_content).send()

    def notification_email_for_expire_contract(self, contracts):
        mail_content = _(
            "<h3>Expiration Of Rental Contract</h3>"
            "<br/>Dear %s, <br/>"
            "Our record indicate that your rental contract <b>%s,</b> expire soon,<br/>"
            "If you want to renew this contract Then contact to our agency before last date of contract."
            "<br/>"
            "<br/>"
            "<br/>"
            "<br/>"
            "<table>"
            "<tr>"
            "<td>Contract Ref<td/>"
            "<td>%s<td/>"
            "<tr/>"
            "<tr>"
            "<td>Responsible Person <td/>"
            "<td> %s - %s<td/>"
            "<tr/>"
            "<table/>"
        ) % (
            contracts.partner_id.name,
            contracts.name,
            contracts.name,
            contracts.contractor_id.name,
            contracts.contractor_id.mobile,
        )
        main_content = {
            "subject": "Expiration Of Rental Contract!",
            "author_id": contracts.env.user.partner_id.id,
            "body_html": mail_content,
            "email_to": contracts.partner_id.email,
        }
        self.env["mail.mail"].create(main_content).send()

    def send_email_for_recurring_invoice(self, inv_id, contracts):
        mail_content = _(
            "<h3>Reminder Recurrent Payment!</h3>"
            "<br/>Hi %s, <br/> This is to remind you that the "
            "recurrent payment for the "
            "rental contract has to be done."
            "Please make the payment at the earliest."
            "<br/>"
            "<br/>"
            "Please find the details below:"
            "<br/>"
            "<br/>"
            "<table>"
            "<tr>"
            "<td>Amount <td/>"
            "<td> %s<td/>"
            "<tr/>"
            "<tr>"
            "<td>Due Date <td/>"
            "<td> %s<td/>"
            "<tr/>"
            "<tr>"
            "<td>Responsible Person <td/>"
            "<td> %s, %s<td/>"
            "<tr/>"
            "<table/>"
        ) % (
            contracts.partner_id.name,
            inv_id.amount_total,
            date.today(),
            inv_id.user_id.name,
            inv_id.user_id.mobile,
        )
        main_content = {
            "subject": "Reminder Recurrent Payment!",
            "author_id": contracts.env.user.partner_id.id,
            "body_html": mail_content,
            "email_to": contracts.partner_id.email,
        }
        self.env["mail.mail"].create(main_content).send()

    def create_invoice(self):
        inv_obj = self.env["account.move"]
        recurring_obj = self.env["product.rental.line"]
        inv_line = []
        today = date.today()
        journal_id = (
            self.env["account.journal"]
            .sudo()
            .search(
                [("type", "=", "sale"), ("company_id", "=", self.company_id.id)],
                limit=1,
            )
        )
        for contracts in self.search([]):
            if not contracts.first_invoice_created:
                contracts.first_invoice_created = True
                supplier = contracts.partner_id
                account_id = self.env["account.account"].search(
                    [
                        ("code", "like", "708000"),
                        ("company_id", "=", self.company_id.id),
                    ]
                )
                if not account_id:
                    user_type_id = self.env.ref("account.data_account_type_revenue")
                    account_id = self.env["account.account"].create(
                        {
                            "code": "708000",
                            "name": "Location",
                            "company_id": self.company_id.id,
                            "user_type_id": user_type_id.id,
                        }
                    )
                for each_product in contracts.product_contract_lines_ids:
                    if each_product.price_based == "per_hour":
                        total_qty = each_product.enter_hour
                    else:
                        total_qty = each_product.enter_days
                    inv_line_data = (
                        0,
                        0,
                        {
                            "name": each_product.product_id.name or "Deposit",
                            "product_id": each_product.product_id.id or False,
                            "product_id": each_product.product_id.id or False,
                            "account_id": account_id.id,
                            "price_unit": each_product.price * total_qty or 0.0,
                            "quantity": each_product.qty_needed,
                            "enter_hour": each_product.enter_hour,
                            "enter_days": each_product.enter_days,
                            "tax_ids": [(6, 0, each_product.tax_id.ids)],
                        },
                    )
                    inv_line.append(inv_line_data)
                if self.extra_charges:
                    extra_charge_p_id = self.env.ref(
                        "product_rental_bookings.extra_charge_product_id"
                    )
                    extra_charge_inv_line = (
                        0,
                        0,
                        {
                            "name": extra_charge_p_id.name,
                            "product_id": extra_charge_p_id.id or False,
                            "price_unit": self.extra_charges,
                            "account_id": account_id.id,
                            "quantity": 1.0,
                        },
                    )
                    inv_line.append(extra_charge_inv_line)
                inv_data = {
                    "move_type": "out_invoice",
                    "amount_residual": self.total_amount,
                    "currency_id": self.env.company.currency_id.id,
                    "journal_id": journal_id.id,
                    "company_id": self.env.company.id,
                    "partner_id": supplier.id,
                    "invoice_date_due": self.to_date,
                    "invoice_origin": contracts.name,
                    "contract_id": self.id,
                    "is_hours": self.is_hours,
                    "is_days": self.is_days,
                    "rental_order_id": self.rental_id.id,
                    "invoice_line_ids": inv_line,
                }
                bokeh = self.env["ir.module.module"].search(
                    [("name", "in", ["l10n_in", "l10n_in_purchase", "l10n_in_sale"])],
                    limit=1,
                )
                if bokeh and bokeh.state == "installed":
                    inv_data.update(
                        {
                            "l10n_in_gst_treatment": supplier.l10n_in_gst_treatment
                            or "unregistered",
                        }
                    )
                inv_id = inv_obj.create(inv_data)
                inv_id.action_post()

                recurring_data = {
                    "name": "demo",
                    "date_today": today,
                    "rental_number": contracts.id,
                    "recurring_amount": contracts.first_payment,
                    "invoice_number": inv_id.id,
                    "invoice_ref": inv_id.id,
                }
                recurring_obj.create(recurring_data)
                # self.send_email_for_firstpayment(inv_id, contracts)
                if inv_id:
                    return {
                        "name": _("Account Move"),
                        "view_mode": "form",
                        "view_id": self.env.ref("account.view_move_form").id,
                        "view_type": "tree,form",
                        "res_model": "account.move",
                        "type": "ir.actions.act_window",
                        "res_id": inv_id.id,
                    }

    @api.model
    def scheduler_manage_invoice(self):
        journal_id = self.env["account.move"].default_get(["journal_id"])["journal_id"]
        inv_obj = self.env["account.move"]
        recurring_obj = self.env["product.rental.line"]
        _inv_line_data = {}
        today = date.today()
        for contracts in self.search([]):
            account_id = self.env["account.account"].search(
                [
                    ("code", "like", "708000"),
                    ("company_id", "=", contracts.company_id.id),
                ]
            )
            if not account_id:
                user_type_id = self.env.ref("account.data_account_type_revenue")
                account_id = self.env["account.account"].create(
                    {
                        "code": "708000",
                        "name": "Location",
                        "company_id": contracts.company_id.id,
                        "user_type_id": user_type_id.id,
                    }
                )
            start_date = datetime.strptime(str(contracts.from_date), "%Y-%m-%d").date()
            end_date = datetime.strptime(str(contracts.to_date), "%Y-%m-%d").date()
            if end_date >= date.today():
                is_recurring = 0
                if contracts.cost_frequency == "daily":
                    is_recurring = 1
                elif contracts.cost_frequency == "weekly":
                    week_days = (date.today() - start_date).days
                    if week_days % 7 == 0 and week_days != 0:
                        is_recurring = 1
                elif contracts.cost_frequency == "monthly":
                    if (
                        start_date.day == date.today().day
                        and start_date != date.today()
                    ):
                        is_recurring = 1
                elif contracts.cost_frequency == "yearly":
                    if (
                        start_date.day == date.today().day
                        and start_date.month == date.today().month
                        and start_date != date.today()
                    ):
                        is_recurring = 1
                if (
                    is_recurring == 1
                    and contracts.cost_frequency != "no"
                    and contracts.state != "expire"
                    and contracts.state != "close"
                    and contracts.state != "futur"
                    and contracts.first_invoice_created == True
                ):
                    inv_line = []
                    supplier = contracts.partner_id
                    line_len = len(contracts.product_contract_lines_ids)
                    for each_product in contracts.product_contract_lines_ids:
                        unit_price = contracts.cost_generated / line_len
                        inv_line_data = (
                            0,
                            0,
                            {
                                "product_id": each_product.product_id.id,
                                "name": each_product.product_id.name,
                                "product_id": each_product.product_id.id,
                                "account_id": account_id.id,
                                "price_unit": float(unit_price),
                                "quantity": 1,
                                "exclude_from_invoice_tab": False,
                            },
                        )
                        inv_line.append(inv_line_data)
                    inv_data = {
                        "type": "out_invoice",
                        "currency_id": contracts.account_type.company_id.currency_id.id,
                        "journal_id": journal_id,
                        "company_id": contracts.account_type.company_id.id,
                        "name": supplier.name,
                        "partner_id": supplier.id,
                        "invoice_date_due": contracts.to_date,
                        "invoice_origin": contracts.name,
                        "contract_id": contracts.id,
                        "invoice_line_ids": inv_line,
                        "is_hours": contracts.is_hours,
                        "is_days": contracts.is_days,
                    }

                    inv_id = inv_obj.create(inv_data)
                    payment_id = self.env["account.payment"].create(
                        {
                            "payment_type": "inbound",
                            "partner_type": "supplier",
                            "partner_id": supplier.id,
                            "amount": inv_id.amount_total,
                            "journal_id": journal_id,
                            "payment_date": date.today(),
                            "payment_method_id": "1",
                            "communication": inv_id.name,
                        }
                    )
                    recurring_data = {
                        "name": "demo",
                        "date_today": today,
                        "rental_number": contracts.id,
                        "recurring_amount": contracts.cost_generated,
                        "invoice_number": inv_id.id,
                        "invoice_ref": inv_id.id,
                    }
                    recurring_obj.create(recurring_data)
                    # self.send_email_for_recurring_invoice(inv_id, contracts)
                else:
                    inv_line = []
                    if (
                        not contracts.first_invoice_created
                        and contracts.state != "futur"
                        and contracts.state != "expired"
                    ):
                        contracts.first_invoice_created = True
                        supplier = contracts.partner_id
                        for each_product in contracts.product_contract_lines_ids:
                            if each_product.price_based == "per_day":
                                total_qty = each_product.enter_days
                            else:
                                total_qty = each_product.enter_hour
                            inv_line_data = (
                                0,
                                0,
                                {
                                    "product_id": each_product.product_id.id,
                                    "name": each_product.product_id.name,
                                    "product_id": each_product.product_id.id,
                                    "account_id": supplier.property_account_payable_id.id,
                                    "price_unit": each_product.price,
                                    "quantity": total_qty,
                                    "tax_ids": [(6, 0, each_product.tax_id.ids)],
                                    "exclude_from_invoice_tab": False,
                                },
                            )
                            inv_line.append(inv_line_data)
                        inv_data = {
                            "name": supplier.name,
                            "partner_id": supplier.id,
                            "currency_id": contracts.account_type.company_id.currency_id.id,
                            "journal_id": journal_id,
                            "invoice_origin": contracts.name,
                            "company_id": contracts.account_type.company_id.id,
                            "invoice_date_due": self.to_date,
                            "invoice_line_ids": inv_line,
                        }
                        inv_id = inv_obj.create(inv_data)
                        recurring_data = {
                            "name": "demo",
                            "date_today": today,
                            "rental_number": contracts.id,
                            "recurring_amount": contracts.first_payment,
                            "invoice_number": inv_id.id,
                            "invoice_ref": inv_id.id,
                        }
                        recurring_obj.create(recurring_data)
                        # self.send_email_for_firstpayment(inv_id, contracts)

    @api.model
    def shedule_manage_contract(self):
        date_today = fields.Date.from_string(fields.Date.today())
        in_fifteen_days = fields.Date.to_string(date_today + relativedelta(days=+15))
        nearly_expired_contracts = self.search(
            [("state", "=", "open"), ("to_date", "<", in_fifteen_days)]
        )
        res = {}
        for contract in nearly_expired_contracts:
            if contract.partner_id.id in res:
                res[contract.partner_id.id] += 1
            else:
                res[contract.partner_id.id] = 1
            # contract.notification_email_for_expire_contract(contract)

        nearly_expired_contracts.write({"state": "diesoon"})

        expired_contracts = self.search(
            [("state", "!=", "expired"), ("to_date", "<", fields.Date.today())]
        )
        expired_contracts.write({"state": "expired"})

        futur_contracts = self.search(
            [
                ("state", "not in", ["futur", "closed"]),
                ("from_date", ">", fields.Date.today()),
            ]
        )
        futur_contracts.write({"state": "futur"})

        now_running_contracts = self.search(
            [("state", "=", "futur"), ("from_date", "<=", fields.Date.today())]
        )
        now_running_contracts.write({"state": "open"})

    @api.model
    def run_scheduler(self):
        self.shedule_manage_contract()
        self.scheduler_manage_invoice()


class productConLines(models.Model):
    _name = "product.contract.lines"
    _description = "Product Rental Contract Lines"

    product_id = fields.Many2one("product.product", string="product Name")
    price_based = fields.Selection(
        [("per_day", "Day"), ("per_hour", "Hour"), ("per_session", "Session")],
        default="per_day",
        string="Based On",
    )
    enter_hour = fields.Float(string="Hour")
    enter_days = fields.Float(string="Days")
    price = fields.Monetary(string="Price")
    total = fields.Monetary(string="Total")
    product_contract_id = fields.Many2one("rental.product.contract", string="Contract")
    tax_id = fields.Many2many("account.tax", "product_contract_tax_rel", string="Tax")
    sub_total = fields.Monetary(string="Sub Total", compute="_get_subtotal", store=True)
    price_tax = fields.Float(
        compute="_get_subtotal", string="Taxes", readonly=True, store=True
    )
    price_total = fields.Monetary(
        compute="_get_subtotal", string="Total ", readonly=True, store=True
    )
    description = fields.Char(string="Description")
    currency_id = fields.Many2one(
        "res.currency",
        related="product_contract_id.currency_id",
        store=True,
        readonly=True,
    )
    qty_needed = fields.Integer(string="Quantity", default=1)

    @api.depends("product_id", "enter_hour", "enter_days", "price", "tax_id")
    def _get_subtotal(self):
        for line in self:
            if line.price_based == "per_day":
                qty = line.enter_days * line.qty_needed
            elif line.price_based == "per_session":
                qty = line.qty_needed
            else:
                qty = line.enter_hour * line.qty_needed
            print("\n\n\n\n\n\n------>", qty)
            taxes = line.tax_id.compute_all(
                qty, line.product_contract_id.currency_id, line.price
            )
            line.update(
                {
                    "price_tax": sum(
                        t.get("amount", 0.0) for t in taxes.get("taxes", [])
                    ),
                    "price_total": taxes["total_included"],
                    "sub_total": taxes["total_excluded"],
                }
            )


class ProductRentalLine(models.Model):
    _name = "product.rental.line"
    _description = "Rental Lines"

    name = fields.Char(string="Name")
    date_today = fields.Date("Date")
    recurring_amount = fields.Float("Amount")
    rental_number = fields.Many2one("rental.product.contract", string="Rental Number")
    payment_info = fields.Char(
        compute="paid_info", string="Payment Stage", default="draft"
    )
    auto_generated = fields.Boolean("Automatically Generated", readonly=True)
    invoice_number = fields.Integer(string="Invoice ID")
    invoice_ref = fields.Many2one("account.move", string="Invoice Ref")

    @api.depends("payment_info")
    def paid_info(self):
        for record in self:
            if self.env["account.move"].browse(record.invoice_number):
                record.payment_info = (
                    self.env["account.move"].browse(record.invoice_number).state
                )
            else:
                record.payment_info = "Record Deleted"


class CustomerDocument(models.Model):
    _name = "customer.document"
    _description = "Customer Document"

    name = fields.Binary(string="Document")
    id_number = fields.Char(string="ID Number")
    contract_id = fields.Many2one("rental.product.contract", string="Conrtract")


class RentalPolicy(models.Model):
    _name = "rental.policy"
    _description = "Rental Policy"

    contract_id = fields.Many2one("rental.product.contract", string="Contract")
    from_date = fields.Date(string="From Date")
    to_date = fields.Date(string="To Date")
    policy_charged = fields.Float(string="Charge(In Percentage)")
