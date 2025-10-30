from odoo import models, fields, api
from odoo.exceptions import ValidationError
from datetime import datetime, time
import re


class AttendanceHanson(models.Model):
    _name = 'attendance.hanson'
    _description = 'Attendance Hanson'
    _order = 'date desc, employee_id'

    # --------------------------------------------------------
    # BASIC FIELDS
    # --------------------------------------------------------
    name = fields.Char(string='Name')
    date = fields.Date(string='Date', required=True)
    day = fields.Char(string='Day', compute='_compute_day', store=True)
    office = fields.Char(string='Office')

    # --------------------------------------------------------
    # DEPARTMENT / EMPLOYEE
    # --------------------------------------------------------
    department_id = fields.Many2one('hr.department', string='Department')
    department_employee = fields.Char(string='Department Name')

    employee_id = fields.Many2one('hr.employee', string='Employee', required=True)
    employee_id_bio = fields.Char(string='Employee ID (Bio)')
    nickname = fields.Char(string='Nickname')

    # --------------------------------------------------------
    # TIME FIELDS (user-facing)
    # --------------------------------------------------------
    in_time_char = fields.Char(string='Clock In', help='Format: HH:MM or HH:MM:SS')
    out_time_char = fields.Char(string='Clock Out', help='Format: HH:MM or HH:MM:SS')

    # Internal datetimes computed from *_char
    in_time = fields.Datetime(string='Clock In (Internal)', compute='_compute_datetime_fields', store=True)
    out_time = fields.Datetime(string='Clock Out (Internal)', compute='_compute_datetime_fields', store=True)

    late = fields.Char(string='Late In', compute='_compute_late_early', store=True)
    early = fields.Char(string='Early Out', compute='_compute_late_early', store=True)
    total_hours = fields.Char(string='Total Hours', compute='_compute_total_hours', store=True)

    remarks = fields.Text(string='Remarks')

    # --------------------------------------------------------
    # COMPUTE METHODS
    # --------------------------------------------------------
    @api.depends('date')
    def _compute_day(self):
        for rec in self:
            rec.day = rec.date.strftime('%A') if rec.date else False

    def _parse_time_string(self, time_str):
        """
        Convert a variety of Excel/CSV/user inputs to minutes since midnight.
        Returns:
            float minutes or int minutes, or None if invalid/missing.
        """
        if time_str in (None, "", "NaT", "nan"):
            return None

        # Excel float like 0.5 = 12:00
        if isinstance(time_str, (float, int)):
            try:
                return float(time_str) * 24 * 60
            except Exception:
                return None

        s = str(time_str).strip().upper().replace('.', ':').replace(' ', '')
        if not s:
            return None

        # Numeric-only inputs: "9", "09", "900", "0930"
        if s.isdigit():
            if len(s) in (1, 2):
                return int(s) * 60
            if len(s) == 3:
                hours = int(s[0])
                minutes = int(s[1:])
                return hours * 60 + minutes
            if len(s) == 4:
                hours = int(s[:2])
                minutes = int(s[2:])
                return hours * 60 + minutes

        # 9:00, 09:00:00, 9:00PM
        m = re.match(r'(\d{1,2}):(\d{1,2})(?::(\d{1,2}))?(AM|PM)?', s)
        if m:
            hours = int(m.group(1))
            minutes = int(m.group(2))
            seconds = int(m.group(3)) if m.group(3) else 0
            period = m.group(4)

            if period == 'PM' and hours != 12:
                hours += 12
            elif period == 'AM' and hours == 12:
                hours = 0

            if 0 <= hours < 24 and 0 <= minutes < 60:
                return hours * 60 + minutes + seconds / 60.0

        # Invalid
        print(f"⚠ Invalid time format detected: {time_str}, setting as None")
        return None

    def _format_minutes_to_display(self, minutes):
        if minutes is None or minutes <= 0:
            return "0 min"
        hours = int(minutes // 60)
        mins = int(minutes % 60)
        return f"{hours}h {mins}min" if hours > 0 else f"{mins} min"

    @api.depends('in_time_char', 'out_time_char')
    def _compute_total_hours(self):
        for rec in self:
            in_minutes = rec._parse_time_string(rec.in_time_char)
            out_minutes = rec._parse_time_string(rec.out_time_char)

            if in_minutes is None or out_minutes is None or out_minutes <= in_minutes:
                rec.total_hours = "0 min"
            else:
                rec.total_hours = self._format_minutes_to_display(out_minutes - in_minutes)

    @api.depends('in_time_char', 'out_time_char')
    def _compute_late_early(self):
        WORK_START_MINUTES = 9 * 60  # 9:00
        WORK_END_MINUTES = 18 * 60  # 18:00

        for rec in self:
            rec.late = "0 min"
            rec.early = "0 min"

            in_minutes = rec._parse_time_string(rec.in_time_char)
            out_minutes = rec._parse_time_string(rec.out_time_char)

            if in_minutes is not None and in_minutes > WORK_START_MINUTES:
                rec.late = self._format_minutes_to_display(in_minutes - WORK_START_MINUTES)
            if out_minutes is not None and out_minutes < WORK_END_MINUTES:
                rec.early = self._format_minutes_to_display(WORK_END_MINUTES - out_minutes)

    @api.depends('date', 'in_time_char', 'out_time_char')
    def _compute_datetime_fields(self):
        for rec in self:
            rec.in_time = False
            rec.out_time = False
            if not rec.date:
                continue

            in_minutes = rec._parse_time_string(rec.in_time_char)
            if in_minutes is not None:
                rec.in_time = datetime.combine(rec.date, time(int(in_minutes // 60), int(in_minutes % 60), 0))

            out_minutes = rec._parse_time_string(rec.out_time_char)
            if out_minutes is not None:
                rec.out_time = datetime.combine(rec.date, time(int(out_minutes // 60), int(out_minutes % 60), 0))

    # --------------------------------------------------------
    # VALIDATION (no writes here to avoid recursion)
    # --------------------------------------------------------
    @api.constrains('in_time_char', 'out_time_char')
    def _check_times(self):
        for rec in self:
            in_minutes = rec._parse_time_string(rec.in_time_char) if rec.in_time_char else None
            out_minutes = rec._parse_time_string(rec.out_time_char) if rec.out_time_char else None

            # Only the logical check here to avoid recursion
            if in_minutes is not None and out_minutes is not None and out_minutes < in_minutes:
                raise ValidationError('Clock Out time cannot be earlier than Clock In time.')

    # --------------------------------------------------------
    # HELPERS TO SANITIZE INPUT & SET REMARKS (used by create/write)
    # --------------------------------------------------------
    def _sanitize_times_and_remarks(self, vals):
        """
        Normalize *char* times and set remarks accordingly.
        We do it in create/write (NOT in constrains) to avoid recursion.
        """
        # Work on a copy so we don't mutate the original dict
        out = dict(vals)

        # Parse proposed values (fall back to current values if not in vals)
        in_char = out.get('in_time_char', self.in_time_char if self else False)
        out_char = out.get('out_time_char', self.out_time_char if self else False)

        in_minutes = self._parse_time_string(in_char) if in_char else None
        out_minutes = self._parse_time_string(out_char) if out_char else None

        # Blank invalid ones
        if in_char and in_minutes is None:
            out['in_time_char'] = False
        if out_char and out_minutes is None:
            out['out_time_char'] = False

        # Remarks priority
        if (in_minutes is None and bool(in_char)) and (out_minutes is None and bool(out_char)):
            out['remarks'] = "⚠ Absence / Not Clock In or Out"
        elif in_char and in_minutes is None and out_minutes is not None:
            out['remarks'] = "⚠ Not Clock In"
        elif out_char and out_minutes is None and in_minutes is not None:
            out['remarks'] = "⚠ Not Clock Out"
        elif (not in_char and not out_char) or (in_minutes is None and out_minutes is None):
            out['remarks'] = "⚠ Absence / Not Clock In or Out"

        return out

    # --------------------------------------------------------
    # CREATE / WRITE
    # --------------------------------------------------------
    @api.model
    def create(self, vals):
        # Fill dependent fields from employee
        if vals.get('employee_id'):
            emp = self.env['hr.employee'].browse(vals['employee_id'])
            vals.update({
                'department_id': emp.department_id.id or False,
                'department_employee': emp.department_id.name or '',
                'office': getattr(emp, 'office', '') or '',
                'employee_id_bio': getattr(emp, 'employee_id_bio', '') or '',
                'nickname': getattr(emp, 'nickname', '') or '',
            })

        # Sanitize times & remarks
        vals = self._sanitize_times_and_remarks(vals)

        # Default remarks if both times missing
        if not vals.get('in_time_char') and not vals.get('out_time_char') and not vals.get('remarks'):
            vals['remarks'] = "⚠ Absence / Not Clock In or Out"

        # Build default name
        if not vals.get('name'):
            emp_name = ''
            if vals.get('employee_id'):
                emp_name = self.env['hr.employee'].browse(vals['employee_id']).name or ''
            date_str = str(vals.get('date')) if vals.get('date') else ''
            vals['name'] = f"{emp_name} - {date_str}" if (emp_name or date_str) else 'Attendance'

        return super().create(vals)

    def write(self, vals):
        # If employee changed, refresh the related info
        if vals.get('employee_id'):
            emp = self.env['hr.employee'].browse(vals['employee_id'])
            vals.update({
                'department_id': emp.department_id.id or False,
                'department_employee': emp.department_id.name or '',
                'office': getattr(emp, 'office', '') or '',
                'employee_id_bio': getattr(emp, 'employee_id_bio', '') or '',
                'nickname': getattr(emp, 'nickname', '') or '',
            })

        # Sanitize times & remarks if times are part of the write
        if 'in_time_char' in vals or 'out_time_char' in vals:
            vals = self._sanitize_times_and_remarks(vals)

        return super().write(vals)

    # --------------------------------------------------------
    # NAME GET
    # --------------------------------------------------------
    def name_get(self):
        result = []
        for rec in self:
            display = rec.name or rec.employee_id.name or 'Attendance'
            if rec.date:
                display = f"{display} - {rec.date}"
            result.append((rec.id, display))
        return result
