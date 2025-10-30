from odoo import models, fields, api
from ftplib import FTP
import io
import pandas as pd
from datetime import date as pydate, timedelta, datetime
import re


class AttendanceFTPImportWizard(models.TransientModel):
    _name = 'attendance.ftp.import.wizard'
    _description = 'Import Attendance from FTP'

    ftp_host = fields.Char(default='192.82.56.74')
    ftp_port = fields.Integer(default=21)
    ftp_user = fields.Char(default='novutal@asolute.com')
    ftp_pass = fields.Char(default='cvudt7zk6PN5QuPgr')
    ftp_folder = fields.Char(default='/')
    file_name = fields.Char(default='')
    import_date = fields.Date(default=lambda self: pydate.today() - timedelta(days=1))
    import_result = fields.Text(readonly=True)

    # -------------------------------------------------------------------------
    # MAIN ACTION - Single Button: "Update"
    # -------------------------------------------------------------------------
    def action_update_attendance(self):
        Attendance = self.env['attendance.hanson']
        imported_count = 0
        skipped = 0

        print(f"🔗 Connecting to FTP: {self.ftp_host}:{self.ftp_port}")
        ftp = FTP()
        ftp.connect(self.ftp_host, self.ftp_port, timeout=15)
        ftp.login(self.ftp_user, self.ftp_pass)
        ftp.cwd(self.ftp_folder)
        print("✅ FTP connection established and folder changed to:", self.ftp_folder)

        files = ftp.nlst()
        excel_files = [f for f in files if f.lower().endswith(('.xls', '.xlsx'))]

        if not excel_files:
            ftp.quit()
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': "⚠ No Excel files found",
                    'message': "There are no attendance Excel files available on the FTP server.",
                    'type': 'warning',
                    'sticky': False,
                },
            }

        # 🕒 Auto-pick latest Excel file
        latest_file = None
        latest_time = None
        try:
            ftp.sendcmd('TYPE I')
            for file in excel_files:
                try:
                    mdtm_resp = ftp.sendcmd(f"MDTM {file}")
                    file_time = mdtm_resp[4:]
                    if not latest_time or file_time > latest_time:
                        latest_time = file_time
                        latest_file = file
                except Exception:
                    continue
        except Exception:
            latest_file = sorted(excel_files)[-1]

        self.file_name = latest_file
        selected_date = pydate.today() - timedelta(days=1)
        print(f"🕒 Auto-selected latest file: {self.file_name}")
        print(f"📅 Importing attendance for: {selected_date}")

        # ---------------------------------------------------------------------
        # DOWNLOAD & PROCESS
        # ---------------------------------------------------------------------
        try:
            filename = self.file_name
            buffer = io.BytesIO()
            ftp.retrbinary(f"RETR {filename}", buffer.write)
            buffer.seek(0)
            print(f"⬇ Downloaded {filename} ({buffer.getbuffer().nbytes} bytes)")

            engine = 'openpyxl' if filename.lower().endswith('.xlsx') else 'xlrd'
            df = pd.read_excel(buffer, engine=engine, skiprows=1, header=1)
            df.columns = [c.strip().lower() for c in df.columns]
            df.rename(columns={
                'first name': 'employee',
                'clock in': 'in_time',
                'clock out': 'out_time',
                'date': 'date',
            }, inplace=True)

            required_cols = {'employee', 'date', 'in_time', 'out_time'}
            if not required_cols.issubset(df.columns):
                ftp.quit()
                return {
                    'type': 'ir.actions.client',
                    'tag': 'display_notification',
                    'params': {
                        'title': "❌ Missing Columns",
                        'message': "Excel file is missing one or more required columns.",
                        'type': 'danger',
                        'sticky': False,
                    },
                }

            # -----------------------------------------------------------------
            # ROW PROCESSING
            # -----------------------------------------------------------------
            for _, row in df.iterrows():
                emp_name = str(row.get('employee', '')).strip()
                date_val = row.get('date')
                in_time = str(row.get('in_time', '')).strip()
                out_time = str(row.get('out_time', '')).strip()

                try:
                    if isinstance(date_val, pd.Timestamp):
                        date_val = date_val.date()
                    elif isinstance(date_val, str):
                        date_val = pd.to_datetime(date_val, errors='coerce').date()
                    elif isinstance(date_val, (float, int)):
                        date_val = (pd.to_datetime('1899-12-30') + pd.to_timedelta(date_val, unit='D')).date()
                except Exception:
                    skipped += 1
                    continue

                if date_val != selected_date:
                    skipped += 1
                    continue
                if not emp_name or not in_time or not out_time:
                    skipped += 1
                    continue

                # Skip duplicate attendance for same date & employee
                existing = Attendance.search([
                    ('employee_id.name', '=', emp_name),
                    ('date', '=', date_val)
                ], limit=1)
                if existing:
                    skipped += 1
                    continue

                # Create/find employee
                employee = self.env['hr.employee'].search([('name', 'ilike', emp_name)], limit=1)
                if not employee:
                    dept_name = str(row.get('department', '')).strip()
                    department = self.env['hr.department'].search([('name', '=', dept_name)], limit=1)
                    if not department and dept_name:
                        department = self.env['hr.department'].create({'name': dept_name})
                    employee = self.env['hr.employee'].create({
                        'name': emp_name,
                        'employee_id_bio': str(row.get('employee id', '')),
                        'nickname': str(row.get('nick name', '')),
                        'department_id': department.id if department else False,
                    })

                Attendance.create({
                    'employee_id': employee.id,
                    'date': date_val,
                    'in_time_char': in_time,
                    'out_time_char': out_time,
                })
                imported_count += 1
                print(f"✅ Imported attendance for {emp_name}")

        except Exception as e:
            skipped += 1
            ftp.quit()
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': "⚠ Error",
                    'message': f"Error processing {self.file_name}: {e}",
                    'type': 'danger',
                    'sticky': False,
                },
            }

        ftp.quit()
        print("🔒 FTP connection closed.")

        # ---------------------------------------------------------------------
        # 🎉 AUTO-CLOSE, REFRESH TREE VIEW & SHOW SUCCESS NOTIFICATION
        # ---------------------------------------------------------------------
        message = (
            f"✅ Imported: {imported_count} • ⚠ Skipped: {skipped}\n"
            f"Attendance successfully updated for {selected_date.strftime('%Y-%m-%d')}"
        )
        print(message)

        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': "Attendance Update Complete",
                'message': f"Imported: {imported_count}, Skipped: {skipped}. "
                           f"Updated for {selected_date.strftime('%Y-%m-%d')}.",
                'type': 'success',
                'sticky': False,
                # 👇 Auto-refresh the list view below the popup
                'next': {
                    'type': 'ir.actions.client',
                    'tag': 'reload',
                },
            },
        }

# -------------------------------------------------------------------------
# CRON HELPER MODEL (for scheduled automation)
# -------------------------------------------------------------------------
class AttendanceFTPImportCron(models.Model):
    _name = 'attendance.ftp.import.cron'
    _description = 'Attendance FTP Import Cron Helper'

    @api.model
    def cron_auto_import_yesterday(self):
        """
        This method is triggered automatically by Odoo's ir.cron scheduler.
        It safely calls the AttendanceFTPImportWizard to perform the import.
        """
        print("⏰ [CRON] Starting automatic attendance FTP import for yesterday...")

        try:
            # Create a wizard record (the wizard holds FTP config)
            wizard = self.env['attendance.ftp.import.wizard'].create({})
            # Call the same update function used by the manual “Update” button
            wizard.action_update_attendance()
            print("✅ [CRON] Attendance import completed successfully.")
        except Exception as e:
            print(f"❌ [CRON] Attendance import failed: {e}")



