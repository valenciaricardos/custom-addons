# -*- coding: utf-8 -*-
# (c) 2016 Alfredo de la Fuente - AvanzOSC
# License AGPL-3 - See http://www.gnu.org/licenses/agpl-3.0.html
from openerp import models, fields, api, exceptions, _


class EventEvent(models.Model):
    _inherit = 'event.event'

    sale_order_payer = fields.Selection(
        related='sale_order.payer', string='Event payer',
        store=True)

    def _validate_registrations_email(self):
        for event in self:
            registrations = event.mapped(
                'no_employee_registration_ids').filtered(
                lambda x: not x.partner_id.parent_id.email)
            for registration in registrations:
                raise exceptions.Warning(_("Partner %s without email.") %
                                         registration.partner_id.name)

    def _send_email_to_registrations(self, body):
        template = self.env.ref(
            'event_registration_mass_mailing.email_template_event_'
            'registration', False)
        if not template:
            raise exceptions.Warning(
                _("Email template not found for event registration"))
        for event in self:
            for registration in event.no_employee_registration_ids:
                wizard = self.env['mail.compose.message'].with_context(
                    default_composition_mode='mass_mail',
                    default_template_id=template.id,
                    default_use_template=True,
                    active_id=registration.id,
                    active_ids=registration.ids,
                    active_model='event.registration',
                    default_model='event.registration',
                    default_res_id=registration.id,
                    force_send=True
                ).create({'body': body})
                wizard.send_mail()

    @api.onchange('group_description')
    def onchange_group_description(self):
        for event in self:
            if event.group_description:
                event.name = event.group_description

    @api.multi
    def write(self, values):
        translation_obj = self.env['ir.translation']
        res = super(EventEvent, self).write(values)
        if values.get('name', False):
            for event in self:
                cond = [('lang', '=', self.env.context.get('lang')),
                        ('name', '=', 'event.event,name'),
                        ('res_id', '=', event.id),
                        ('type', '=', 'model')]
                translation = translation_obj.search(cond, limit=1)
                if translation:
                    translation._set_src('source', values.get('name'), None)
        return res


class EventTrack(models.Model):
    _inherit = 'event.track'

    address_id = fields.Many2one(
        comodel_name='res.partner', string='Location',
        related='event_id.address_id', store=True, readonly=True)


class EventRegistration(models.Model):
    _inherit = 'event.registration'

    address_id = fields.Many2one(
        comodel_name='res.partner', string='Address',
        related='event_id.address_id', store=True)
    organizer_id = fields.Many2one(
        string='Organizer', comodel_name='res.partner',
        related='event_id.organizer_id', store=True)
    parent_id = fields.Many2one(string='Parent', comodel_name='res.partner',
                                related='partner_id.parent_id', store=True)
    parent_name = fields.Char(related='parent_id.name')
    parent_mobile = fields.Char(related='parent_id.mobile')
    parent_email = fields.Char(related='parent_id.email')
    submitted_evaluation = fields.Selection(
        [('yes', _('Yes')),
         ('no', 'No')], string='Submitted evaluation', default='no')
    submitted_evaluation_error = fields.Char(
        string='Submitted evaluation error')

    def _send_email_to_registrations_with_evaluation(self, body):
        attachment_obj = self.env['ir.attachment']
        template = self.env.ref(
            'rockbotic_custom.email_template_event_registration_evaluation',
            False)
        if not template:
            raise exceptions.Warning(
                _("Email template not found to send evaluations to event"
                  " registration"))
        for registration in self:
            vals = {'submitted_evaluation': 'no'}
            cond = [('res_model', '=', 'event.registration'),
                    ('res_id', '=', registration.id)]
            attachments = attachment_obj.search(cond)
            if len(attachments) == 0:
                vals['submitted_evaluation_error'] = _('Attachment not found')
            elif len(attachments) > 1:
                vals['submitted_evaluation_error'] = _('Found more than one '
                                                       'attachment')
            elif not registration.partner_id.parent_id:
                vals['submitted_evaluation_error'] = _('Student without '
                                                       'parent')
            elif not registration.partner_id.parent_id.email:
                vals['submitted_evaluation_error'] = _('Parent without email')
            else:
                wizard = self.env['mail.compose.message'].with_context(
                    default_composition_mode='mass_mail',
                    default_template_id=template.id,
                    default_use_template=True,
                    default_attachment_ids=[(6, 0, attachments.ids)],
                    active_id=registration.id,
                    active_ids=registration.ids,
                    active_model='event.registration',
                    default_model='event.registration',
                    default_res_id=registration.id,
                    force_send=True
                ).create({'body': body})
                wizard.send_mail()
                vals = {'submitted_evaluation': 'yes',
                        'submitted_evaluation_error': ''}
            registration.write(vals)
