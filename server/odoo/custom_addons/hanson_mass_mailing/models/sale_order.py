from odoo import models, fields, api, _
import re
from lxml import html, etree


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    mail_body = fields.Html(
        string="Mail Body",
        sanitize=False,
        help="Body of the email for this sale order."
    )

    mailing_id = fields.Many2one(
        'mailing.mailing',
        string="Mailing Template",
        help="Select or create an email template for this sale order."
    )

    cleaned_mail_body = fields.Html(
        string="Mail Body (Cleaned)",
        compute="_compute_cleaned_mail_body",
        sanitize=False,
        store=False,
        help="Mail body with all background colors removed for clean PDF rendering."
    )

    @api.depends('mail_body')
    def _compute_cleaned_mail_body(self):
        """Fully clean mail body for PDF: remove background, borders, and wrappers."""
        from lxml import html, etree
        for order in self:
            html_source = order.mail_body or ''
            cleaned_html = html_source

            if html_source:
                try:
                    doc = html.fragment_fromstring(html_source, create_parent=True)

                    for el in doc.iter():
                        # --- 1. Clean inline styles ---
                        style = el.attrib.get("style", "")
                        if style:
                            style = re.sub(
                                r"(background|border|box-shadow)[^:]*:[^;]*;?",
                                "",
                                style,
                                flags=re.IGNORECASE
                            )
                            el.attrib["style"] = style.strip()

                        # --- 2. Remove border-related HTML attributes ---
                        for attr in ["border", "bgcolor", "cellpadding", "cellspacing"]:
                            if attr in el.attrib:
                                del el.attrib[attr]

                        # --- 3. Clean suspicious classes ---
                        if "class" in el.attrib:
                            el.attrib["class"] = " ".join(
                                c for c in el.attrib["class"].split()
                                if not re.search(r"(border|bg|shadow|wrapper)", c, re.I)
                            )

                        # --- 4. Remove table-level borders entirely ---
                        if el.tag.lower() == "table":
                            # force no border and no padding
                            el.attrib["border"] = "0"
                            el.attrib["cellpadding"] = "0"
                            el.attrib["cellspacing"] = "0"
                            el.attrib["style"] = "border:none; background:none; box-shadow:none; padding:0; margin:0;"

                    # --- 5. Optional flattening: unwrap top-level table if it’s a single-cell wrapper ---
                    if doc.tag == "table" and len(doc) == 1:
                        first = doc[0]
                        if first.tag == "tr" and len(first) == 1 and first[0].tag == "td":
                            doc = first[0]  # replace with its contents

                    cleaned_html = etree.tostring(doc, encoding="unicode", method="html")

                except Exception:
                    cleaned_html = re.sub(
                        r"(background|border|box-shadow)[^:]*:[^;\"']+;?",
                        "",
                        html_source,
                        flags=re.IGNORECASE,
                    )
                    cleaned_html = re.sub(
                        r'\s*(border|bgcolor|cellpadding|cellspacing)="[^"]+"',
                        "",
                        cleaned_html,
                        flags=re.IGNORECASE,
                    )

            order.cleaned_mail_body = cleaned_html

    @api.onchange('mailing_id')
    def _onchange_mailing_id(self):
        """When a mailing template is selected, update mail_body preview."""
        self.mail_body = self.mailing_id.body_html or ''

    @api.model
    def _get_default_email_template(self):
        return self.env.ref('sale.email_template_edi_sale', raise_if_not_found=False)

    def action_quotation_send(self):
        """Override 'Send by Email' to include custom mail body."""
        self.ensure_one()
        template = self._get_default_email_template()

        ctx = {
            'default_model': 'sale.order',
            'default_res_ids': [self.id],
            'default_use_template': bool(template),
            'default_template_id': template.id if template else False,
            'default_composition_mode': 'comment',
            'custom_layout': "mail.mail_notification_paynow",
        }

        if self.mail_body:
            ctx['default_body'] = self.mail_body
            ctx['default_body_html'] = self.mail_body

        return {
            'type': 'ir.actions.act_window',
            'view_mode': 'form',
            'res_model': 'mail.compose.message',
            'target': 'new',
            'context': ctx,
        }
