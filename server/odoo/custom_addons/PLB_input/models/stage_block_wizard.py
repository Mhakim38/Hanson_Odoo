from odoo import api, fields, models


class PLBStageBlockWizard(models.TransientModel):
    _name = 'plb.stage.block.wizard'
    _description = 'PLB Stage Block Wizard'

    message = fields.Text(string='Message', readonly=True)

    def action_ok(self):
        return {'type': 'ir.actions.act_window_close'}

