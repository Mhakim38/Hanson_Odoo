from odoo import models, fields, api

class Container(models.Model):
    _name = "res.container"
    _description = "Container"
    _order = "container_number"
    _rec_name = "container_number"

    # ========== IDENTIFICATION ==========
    container_number = fields.Char(
        string="Container Number",
        required=True,
        help="Globally unique identifier (4 letters + 7 digits) as per ISO 6346."
    )
    owner_code = fields.Char(
        string="Owner Code",
        help="First 3 letters of container number; identifies the owning company."
    )
    equipment_category = fields.Selection([
        ('U', 'Freight Container'),
        ('J', 'Detachable Equipment'),
        ('Z', 'Chassis'),
    ], string="Equipment Category Identifier",
       help="U for freight container, J for equipment, Z for chassis.")
    serial_number = fields.Char(string="Serial Number")
    check_digit = fields.Char(string="Check Digit")

    # ========== CLASSIFICATION ==========
    iso_size_type_code = fields.Char(string="ISO Size & Type Code")
    container_type = fields.Selection([
        ('dry', 'Dry Van'),
        ('reefer', 'Reefer (Refrigerated)'),
        ('open_top', 'Open Top'),
        ('flat_rack', 'Flat Rack'),
        ('tank', 'Tank'),
        ('other', 'Other'),
    ], string="Container Type")
    size = fields.Selection([
        ('20ft', '20FT'),
        ('40ft', '40FT'),
        ('45ft', '45FT'),
        ('40hc', '40HC (High Cube)'),
        ('20hc', '20HC (High Cube)'),
    ], string="Size")

    # ========== WEIGHT & CAPACITY ==========
    max_gross_weight = fields.Float(string="Max Gross Weight (kg)")
    tare_weight = fields.Float(string="Tare Weight (kg)")
    payload_capacity = fields.Float(
        string="Payload Capacity (kg)",
        compute="_compute_payload_capacity",
        store=True
    )

    @api.depends('max_gross_weight', 'tare_weight')
    def _compute_payload_capacity(self):
        for rec in self:
            rec.payload_capacity = (rec.max_gross_weight or 0.0) - (rec.tare_weight or 0.0)

    # ========== SECURITY & STATUS ==========
    #seal_number = fields.Char(string="Seal Number")

    stage_id = fields.Many2one(
        'res.container.stage',
        string="Stage",
        compute="_compute_stage_from_maintenance",
        store=True,
        readonly=False,
        help="Automatically reflects the container's current maintenance status."
    )

    # ========== OWNERSHIP & LOCATION ==========
    container_owner = fields.Many2one("res.partner", string="Owner")
    #current_loc = fields.Char(string="Current Location")
    last_inspection_date = fields.Date(string="Last Inspection Date")

    # ========== TECHNICAL ==========
    remarks = fields.Text(string="Remarks")

    # Child Relations
    maintenance_ids = fields.One2many(
        "res.container.maintenance",
        "container_id",
        string="Maintenance Records"
    )
    journey_ids = fields.One2many(
        "res.container.journey",
        "container_id",
        string="Journey Records"
    )
    depot_id = fields.Many2one("res.depot", string="Depot")
    yard_id = fields.Many2one("res.yard", string="Yard")
    block = fields.Many2one("res.yard", string="Block")

    # ========== COMPUTE STAGE ==========
    @api.depends('maintenance_ids.status')
    def _compute_stage_from_maintenance(self):
        for container in self:
            latest_maintenance = container.maintenance_ids.sorted('create_date', reverse=True)[:1]
            if latest_maintenance:
                # Match maintenance.status to stage
                stage = self.env['res.container.stage'].search([('name', '=', latest_maintenance.status)], limit=1)
                container.stage_id = stage.id if stage else False
            else:
                # No maintenance records: default to the 'Available' stage if it exists
                stage = self.env['res.container.stage'].search([('name', '=', 'Available')], limit=1)
                container.stage_id = stage.id if stage else False
