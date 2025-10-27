from odoo import http
from odoo.http import request
from datetime import datetime
import json
from PIL import Image
# import cv2
import numpy as np
import io

# PDF Libraries
from reportlab.lib.pagesizes import landscape, A4
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet
from io import BytesIO


class GuardPortal(http.Controller):

    # 🧭 Main Guard Visitor Page
    @http.route(['/guard/visitors'], type='http', auth='user', website=True)
    def guard_visitors(self, **kwargs):
        Visit = request.env['estate.visit'].sudo()
        Unit = request.env['estate.unit'].sudo()

        # Default to today
        selected_date = kwargs.get('date')
        if selected_date:
            try:
                selected_date = datetime.strptime(selected_date, '%Y-%m-%d').date()
            except ValueError:
                selected_date = datetime.now().date()
        else:
            selected_date = datetime.now().date()

        domain = [
            ('schedule_from', '<=', f'{selected_date} 23:59:59'),
            ('schedule_to', '>=', f'{selected_date} 00:00:00')
        ]

        # Filters
        if kwargs.get('status'):
            domain.append(('state', '=', kwargs['status']))
        if kwargs.get('unit_id'):
            domain.append(('unit_id', '=', int(kwargs['unit_id'])))

        visits = Visit.search(domain, order='schedule_from desc')
        units = Unit.search([])

        return request.render('visitor_mgmt.guard_visitors_page', {
            'visits': visits,
            'units': units,
            'today': selected_date,
            'request': request,
        })

    # ✅ AJAX: Check-in visitor
    @http.route(['/guard/visitors/checkin/<int:visit_id>'], type='http', auth='user', csrf=False)
    def guard_checkin(self, visit_id, **kwargs):
        visit = request.env['estate.visit'].sudo().browse(visit_id)
        if not visit.exists():
            return request.make_response(json.dumps({'success': False, 'message': 'Visit not found'}),
                                         headers=[('Content-Type', 'application/json')])

        if visit.state in ['draft', 'scheduled']:
            visit.write({'state': 'check_in', 'check_in_at': datetime.now()})
            return request.make_response(json.dumps({'success': True}),
                                         headers=[('Content-Type', 'application/json')])
        else:
            return request.make_response(json.dumps({'success': False, 'message': 'Invalid state transition'}),
                                         headers=[('Content-Type', 'application/json')])

    # ✅ AJAX: Check-out visitor
    @http.route(['/guard/visitors/checkout/<int:visit_id>'], type='http', auth='user', csrf=False)
    def guard_checkout(self, visit_id, **kwargs):
        visit = request.env['estate.visit'].sudo().browse(visit_id)
        if not visit.exists():
            return request.make_response(json.dumps({'success': False, 'message': 'Visit not found'}),
                                         headers=[('Content-Type', 'application/json')])

        if visit.state == 'check_in':
            visit.write({'state': 'check_out', 'check_out_at': datetime.now()})
            return request.make_response(json.dumps({'success': True}),
                                         headers=[('Content-Type', 'application/json')])
        else:
            return request.make_response(json.dumps({'success': False, 'message': 'Invalid state transition'}),
                                         headers=[('Content-Type', 'application/json')])

    # 🔍 QR Code Scan Route
    @http.route(['/guard/scan_qr'], type='http', auth='user', methods=['POST'], csrf=False)
    def guard_scan_qr(self, **kwargs):
        file = request.httprequest.files.get('file')
        qr_data = kwargs.get('qr_data')

        try:
            if file:
                # Decode image and extract QR data
                image_bytes = file.read()
                img = Image.open(io.BytesIO(image_bytes))
                img_cv = cv2.cvtColor(np.array(img), cv2.COLOR_RGB2BGR)
                detector = cv2.QRCodeDetector()
                qr_data, _, _ = detector.detectAndDecode(img_cv)

            if not qr_data:
                return json.dumps({'success': False, 'message': 'No QR code detected'})

            visit = request.env['estate.visit'].sudo().search([('qr_token', '=', qr_data)], limit=1)
            if not visit:
                return json.dumps({'success': False, 'message': 'No matching visit found.'})

            # Auto check-in / check-out based on current state
            if visit.state in ['scheduled', 'draft']:
                visit.write({'state': 'check_in', 'check_in_at': datetime.now()})
                msg = f"Visitor {visit.visitor_id.name or 'Unknown'} checked in."
            elif visit.state == 'check_in':
                visit.write({'state': 'check_out', 'check_out_at': datetime.now()})
                msg = f"Visitor {visit.visitor_id.name or 'Unknown'} checked out."
            else:
                msg = f"Visit already {visit.state}."

            return json.dumps({'success': True, 'message': msg})

        except Exception as e:
            return json.dumps({'success': False, 'message': f"Error decoding QR: {str(e)}"})

    # 🧾 Export PDF (Landscape A4)
    @http.route(['/guard/visitors/pdf'], type='http', auth='user', website=True)
    def guard_visitors_pdf(self, **kwargs):
        Visit = request.env['estate.visit'].sudo()

        # Parse filters
        selected_date = kwargs.get('date')
        if selected_date:
            try:
                selected_date = datetime.strptime(selected_date, '%Y-%m-%d').date()
            except ValueError:
                selected_date = datetime.now().date()
        else:
            selected_date = datetime.now().date()

        domain = [
            ('schedule_from', '<=', f'{selected_date} 23:59:59'),
            ('schedule_to', '>=', f'{selected_date} 00:00:00')
        ]

        if kwargs.get('status'):
            domain.append(('state', '=', kwargs['status']))
        if kwargs.get('unit_id'):
            domain.append(('unit_id', '=', int(kwargs['unit_id'])))

        visits = Visit.search(domain, order='schedule_from desc')

        # 🧱 Create PDF
        buffer = BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=landscape(A4))
        elements = []
        styles = getSampleStyleSheet()

        title = Paragraph(f"Guard Visitor List - {selected_date.strftime('%Y-%m-%d')}", styles['Title'])
        elements.append(title)
        elements.append(Spacer(1, 12))

        filter_info = f"Filters → Status: {kwargs.get('status') or 'All'}, Unit: {kwargs.get('unit_id') or 'All'}"
        elements.append(Paragraph(filter_info, styles['Normal']))
        elements.append(Spacer(1, 12))

        data = [['Visitor', 'Host', 'Unit', 'Purpose', 'Schedule', 'Status']]
        for v in visits:
            data.append([
                v.visitor_id.name or '-',
                v.host_id.name or '-',
                v.unit_id.display_name or '-',
                v.purpose or '-',
                f"{v.schedule_from or ''} → {v.schedule_to or ''}",
                dict(v._fields['state'].selection).get(v.state, v.state or '-')
            ])

        table = Table(data, repeatRows=1)
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.lightgrey),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.black),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 10),
            ('GRID', (0, 0), (-1, -1), 0.25, colors.grey),
        ]))

        elements.append(table)
        doc.build(elements)

        pdf = buffer.getvalue()
        buffer.close()

        pdf_name = f"visitor_list_{selected_date.strftime('%Y%m%d')}.pdf"
        return request.make_response(
            pdf,
            headers=[
                ('Content-Type', 'application/pdf'),
                ('Content-Disposition', f'inline; filename={pdf_name}')
            ]
        )
