#-------------------------------------------------------------------------------
# Name:        module1
# Purpose:
#
# Author:      kingston
#
# Created:     20/04/2018
# Copyright:   (c) kingston 2018
# Licence:     <your licence> datetime.datetime.strptime(row[6], "%m-%d-%Y"),


''' SM -- SUPERVISOR -- TEM HEAD -PM -- SITE MANAGER AUDITOR -ACCOUNT --- AUDITOR TWO  --- '''
#-------------------------------------------------------------------------------
from odoo import fields, models, api, _
from odoo.exceptions import UserError, ValidationError
from odoo.exceptions import except_orm, ValidationError

from datetime import datetime, timedelta
import time

class account_payment(models.Model):
    _inherit = "account.payment"

    direct_labour_idx = fields.Many2one('direct.labourx', string="Payment Ref")

    @api.multi
    def post(self):
        res = super(account_payment,self).post()
        """ Create the journal items for the payment and update the payment's state to 'posted'.
            A journal entry is created containing an item in the source liquidity account (selected journal's default_debit or default_credit)
            and another in the destination reconciliable account (see _compute_destination_account_id).
            If invoice_ids is not empty, there will be one reconciliable move line per invoice to reconcile with.
            If the payment is a transfer, a second journal entry is created in the destination journal to receive money from the transfer account.
        """
        search_direct_labour_id = self.env['direct.labourx'].search([('id','=', self.direct_labour_idx.id)])
        search_direct_labour_id.write({'state':'post'})

        email_from = self.env.user.email
        email_to = search_direct_labour_id.employee_id.work_email
        bodyx = "Dear Sir/Madam, </br>We wish to notify you that an Labour from {} is on payment process</br> </br>Thanks".format(search_direct_labour_id.employee_id.name)

        search_direct_labour_id.mail_sending(email_from,email_to,bodyx)

        return res




class dl_Message(models.Model):
    _name="dl.messagex"
    _inherit = ['mail.thread', 'ir.needaction_mixin']
    #_inherit='res.users'
    reason = fields.Char('Reason')#<tree string="Memo Payments" colors="red:state == 'account';black:state == 'manager';green:state == 'coo';grey:state == 'refused';">

    date = fields.Datetime('Date')
    resp=fields.Many2one('res.users','Responsible')#, default=self.write_uid.id)
    memo_record = fields.Many2one('direct.labourx','Payment ID')


    @api.multi
    def post_refuse(self):
        get_state = self.env['direct.labourx'].search([('id','=', self.memo_record.id)])
        reasons = "%s Refused the labour payment because of the following reason: \n %s." %(self.env.user.name,self.reason)
        get_state.write({'description_two':reasons})
        get_state.message_posts()
        #self._change_state()

        #search_direct_labour_id = self.env['direct.labour'].search([('id','=', self.direct_labour_id.id)])
        get_state.write({'state':'refused'})

        email_from = self.env.user.email
        email_to = get_state.employee_id.work_email
        bodyx = "Dear Sir/Madam, </br>We wish to notify you that an Direct Labour from {} is on payment process</br> </br>Thanks".format(get_state.employee_id.name)
        get_state.mail_sending(email_from,email_to,bodyx)

        return{'type': 'ir.actions.act_window_close'}


class Payment_Request(models.Model):
    _name="direct.labourx"
    _inherit = ['mail.thread', 'ir.needaction_mixin']

    _rec_name ="name"

    def _default_employee(self):
        return self.env.context.get('default_employee_id') or self.env['hr.employee'].search([('user_id', '=', self.env.uid)], limit=1)
    partner_id = fields.Many2one('res.partner',string="Partner",required=True)

    name = fields.Char('Labour Payment', required=True)
    date = fields.Datetime(string='Date',default=fields.Date.context_today, required=True, copy=False)
    employee_id = fields.Many2one('hr.employee', string = 'Project Manager', default =_default_employee)
    dept_ids = fields.Char(string ='Department', related='employee_id.department_id.name',readonly = True, store =True)
    description = fields.Char('Note')
    project_id = fields.Many2one('account.analytic.account', 'Project')
    amountfig = fields.Float('Request Amount', store=True, compute="_compute_amount")
    description_two=fields.Text('Reasons')
    reason_back=fields.Char('Return Reason')
    file_upload = fields.Binary('File Upload')

    product_qty  = fields.Float('Requested Quantity', default=1)


    state = fields.Selection([('sm', 'Draft'),
                                ('sup', 'Supervisor'),
                                ('team', 'Team Head'),
                                ('pm', 'PM'),
                                ('aud', 'Auditor'),
                                ('sm2', 'Site Manager'),

                                ('account', 'Account'),
                                ('audx', 'Audit 2nd Approve'),
                                ('accountx', 'Account'),
                                ('refused', 'Refused'),
                                ('post', 'Posted'),
                              ], string='Status', index=True, readonly=True, track_visibility='onchange', copy=False, default='sm', required=True,
        help='Request Report State')
    ###################
    branch_id = fields.Many2one('res.branch',string="Branch", default=lambda self: self.env.user.branch_id)
    project_name = fields.Many2one('project.project','Project')
    #house_type = fields.Many2one('construction.housetype', string="House Type")
    #plot_id = fields.Many2one('unit.masterx', 'Plot Number')
    #boq_id = fields.Many2one('construction.material', string="Bill of Quantity" )
    #budget_id = fields.Many2one('construction.budget', string="Based on Budget")
    labour = fields.Many2one('labour.schedule', string="Labour Schedule")

    ######################

    users_followers = fields.Many2many('hr.employee', string='Add followers')

    status_progress = fields.Float(string="Status(%)", compute='_taken_states')
    #invoice_ref = fields.Many2one('account.invoice', 'Invoice Ref')
    direct_memo_user = fields.Many2one('hr.employee', 'Direct Memo To:', states={'draft':[('readonly',True)], 'refused':[('readonly',True)]})


    @api.onchange('boq_id')
    def domain_bill_quantity(self):
        domain = {}
        lists = []
        for fec in self.boq_id:
            for rec in fec.labour_schedule_o2m:
                lists.append(rec.id)
        domain = {'labour':[('id','=',lists)]}
        return {'domain':domain }

    @api.depends('labour','product_qty')
    def _compute_amount(self):
        total = 0.0
        for rec in self.labour:
            total = rec.rate * self.product_qty
        self.amountfig = total
    @api.multi
    @api.depends('state')
    #Depending on any field change (ORM or Form), the function is triggered.
    def _taken_states (self):
        for order in self:
            if order.state == "sup":
                order.status_progress = 20
            elif order.state == "pm":
                order.status_progress = 40

            elif order.state == "aud":
                order.status_progress = 60

            elif order.state == "account":
                order.status_progress = 98
            elif order.state == "accountx":
                order.status_progress = 95


            elif order.state == "refused":
                order.status_progress = 0

            elif order.state ==  "sm2":
                order.status_progress = 85
            else:
                order.status_progress = 100 /len(order.state)


    @api.multi
    def button_send_back(self):# Send memo back
        return {
              'name': 'Reason for Return',
              'view_type': 'form',
              "view_mode": 'form',
              'res_model': 'dl.refused.wizardx',
              'type': 'ir.actions.act_window',
              'target': 'new',
              'context': {
                  'default_memo_record': self.id,
                  'default_date': self.date,
                  'default_direct_memo_user':self.employee_id.id,
              },
        }

    @api.multi
    def unlink(self):
        for holiday in self.filtered(lambda holiday: holiday.state not in ['submit', 'refused', 'post','account']):
            raise ValidationError(_('You cannot delete a Payment which is in %s state.') % (holiday.state,))
        return super(Send_Request, self).unlink()


    @api.model
    def _needaction_domain_get(self):

        if self.env.user == "Administrator":
            return False
        return [('state', 'in', ['sup','pm','aud','account','post'])]



    '''@api.onchange('invoice_ref')   SM -- SUPERVISOR -- TEM HEAD -PM -- SITE MANAGER AUDITOR -ACCOUNT --- AUDITOR TWO  ---
    def get_invoice_total(self):

        for order in self:
            invoice_amount = self.env['account.invoice'].search([('id', '=', order.invoice_ref.id)])

            if invoice_amount:
                order.amountfig = invoice_amount.amount_total'''

    def mail_sending(self, email_from, email_to, bodyx):

        from_browse =self.env.user.name

        for order in self:
            partner_mails = order.users_followers
            mail_append=[]
            for partner_emails in partner_mails:

                mail_append.append(partner_emails.work_email)

            subject = "Direct Labour Payment Notification"
            #body = "Dear Sir/Madam, </br>We wish to notify you that a memo from {} is requested on the date of {}</br> </br>Thanks".format(self.employee_id.name,self.date)
            email_froms = str(from_browse) + " <"+str(email_from)+">"

            mail_appends = (', '.join(str(item)for item in mail_append))

            mail_data={
                'email_from': email_froms,
                'subject':subject,
                'email_to':email_to,
                'email_cc':mail_appends,
                'reply_to': email_from,
                'body_html':bodyx
                }
            mail_id =  order.env['mail.mail'].create(mail_data)
            order.env['mail.mail'].send(mail_id)

    @api.constrains('direct_memo_user','users_followers')
    def _check_something(self):

        if self.direct_memo_user and self.users_followers:
            raise ValidationError("You are required to select either Followers or select a Direct User ID")

    def direct_mail_sending(self, email_from, email_to, bodyx):

        subject = "Direct Labour Payment"
        mail_data = {
                    'email_from':email_from,
                    'subject':subject,
                    'email_to':email_to,
                    #'email_cc':mail_appends,
                    'reply_to':email_from,
                    'body_html':bodyx,
                    }
        mail_id = self.env['mail.mail'].create(mail_data)
        self.env['mail.mail'].send(mail_id)

    def message_posts(self):
        body= "RETURN NOTIFICATION;\n %s" %(self.reason_back)
        records = self._get_followers()
        followers = records
        self.message_post(body=body, subtype='mt_comment',message_type='notification',partner_ids=followers)


    def send_Sm_to_Sup(self):

        body = "The Labour Payment has been submitted to Supervisor for Approval on %s" % (datetime.strftime(datetime.today(), '%d-%m-%y'))
        records = self._get_followers()
        followers = records
        self.message_post(body=body, subtype='mt_comment',message_type='notification',partner_ids=followers)


        email_from = self.env.user.email
        email_to = self.direct_memo_user.work_email
        bodyx = "Dear Sir/Madam, </br>I wish to notify you that i sent an Labour Payment from {} department to you. Kindly review and get back to me </br> </br>Thanks </br> Yours Faithfully</br>{}".format(self.employee_id.department_id.name,self.env.user.name)
        self.write({'state':'sup'})
        self.mail_sending(email_from,email_to,bodyx)



    def send_sup_to_teamhead(self):

        body = "The Labour Payment has been submitted to you for Approval on %s" % (datetime.strftime(datetime.today(), '%d-%m-%y'))
        records = self._get_followers()
        followers = records
        self.message_post(body=body, subtype='mt_comment',message_type='notification',partner_ids=followers)


        email_from = self.env.user.email
        email_to = self.direct_memo_user.work_email
        bodyx = "Dear Sir/Madam, </br>I wish to notify you that i sent an Labour Payment from {} department to you. Kindly review and get back to me </br> </br>Thanks </br> Yours Faithfully</br>{}".format(self.employee_id.department_id.name,self.env.user.name)
        self.write({'state':'team'})
        self.mail_sending(email_from,email_to,bodyx)

    def send_team_to_pm(self):

        body = "The Labour Payment has been submitted to you for Approval on %s" % (datetime.strftime(datetime.today(), '%d-%m-%y'))
        records = self._get_followers()
        followers = records
        self.message_post(body=body, subtype='mt_comment',message_type='notification',partner_ids=followers)


        email_from = self.env.user.email
        email_to = self.direct_memo_user.work_email
        bodyx = "Dear Sir/Madam, </br>I wish to notify you that i sent an Labour Payment from {} department to you. Kindly review and get back to me </br> </br>Thanks </br> Yours Faithfully</br>{}".format(self.employee_id.department_id.name,self.env.user.name)
        self.write({'state':'pm'})
        self.mail_sending(email_from,email_to,bodyx)
    def send_pm_to_audit(self):

        body = "The Labour Payment has been submitted to you for Approval on %s" % (datetime.strftime(datetime.today(), '%d-%m-%y'))
        records = self._get_followers()
        followers = records
        self.message_post(body=body, subtype='mt_comment',message_type='notification',partner_ids=followers)


        email_from = self.env.user.email
        email_to = self.direct_memo_user.work_email
        bodyx = "Dear Sir/Madam, </br>I wish to notify you that i sent an Labour Payment from {} department to you. Kindly review and get back to me </br> </br>Thanks </br> Yours Faithfully</br>{}".format(self.employee_id.department_id.name,self.env.user.name)
        self.write({'state':'aud'})
        self.mail_sending(email_from,email_to,bodyx)
    def send_aud_to_site_manager(self):

        body = "The Labour Payment has been submitted to you for Approval on %s" % (datetime.strftime(datetime.today(), '%d-%m-%y'))
        records = self._get_followers()
        followers = records
        self.message_post(body=body, subtype='mt_comment',message_type='notification',partner_ids=followers)


        email_from = self.env.user.email
        email_to = self.direct_memo_user.work_email
        bodyx = "Dear Sir/Madam, </br>I wish to notify you that i sent an Labour Payment from {} department to you. Kindly review and get back to me </br> </br>Thanks </br> Yours Faithfully</br>{}".format(self.employee_id.department_id.name,self.env.user.name)
        self.write({'state':'sm2'})
        self.mail_sending(email_from,email_to,bodyx)

    def send_aud_to_acount(self):
        self.write({'state':'account'})
        body = "The Labour Payment has been submitted to CEO for Approval on %s" % (datetime.strftime(datetime.today(), '%d-%m-%y'))
        records = self._get_followers()
        followers = records
        self.message_post(body=body, subtype='mt_comment',message_type='notification',partner_ids=followers)

        email_from = self.env.user.email
        email_to = self.employee_id.work_email

        bodyx = "Dear Sir/Madam, </br>We wish to notify you that a Labour Payment from {} has been sent to Manager for approval </br> </br>Thanks".format(self.employee_id.name)

        self.mail_sending(email_from,email_to,bodyx)

    def coo_account_to_audit2(self):
        self.write({'state':'audx'})
        body = "The Labour Paymenthas been submitted to Accounts for Payment on %s" % (datetime.strftime(datetime.today(), '%d-%m-%y'))
        records = self._get_followers()
        followers = records
        self.message_post(body=body, subtype='mt_comment',message_type='notification',partner_ids=followers)

        email_from = self.env.user.email
        email_to = self.employee_id.work_email
        bodyx = "Dear Sir/Madam, </br>We wish to notify you that a Labour Payment from {} has been approval </br> </br>Thanks".format(self.employee_id.name)

        self.mail_sending(email_from,email_to,bodyx)




    def coo_audit_to_accountx(self):
        self.write({'state':'accountx'})
        body = "The Labour Paymenthas been submitted to Accounts for Payment on %s" % (datetime.strftime(datetime.today(), '%d-%m-%y'))
        records = self._get_followers()
        followers = records
        self.message_post(body=body, subtype='mt_comment',message_type='notification',partner_ids=followers)

        email_from = self.env.user.email
        email_to = self.employee_id.work_email
        bodyx = "Dear Sir/Madam, </br>We wish to notify you that a Labour Payment from {} has been approval </br> </br>Thanks".format(self.employee_id.name)

        self.mail_sending(email_from,email_to,bodyx)

    '''@api.multi
    def button_send_payments(self):# Send memo back
        return {
              'name': 'Direct Labour Payment',
              'view_type': 'form',
              "view_mode": 'form',
              'res_model': 'account.payment',
              'type': 'ir.actions.act_window',
              'target': 'current',
              'context': {
                  'default_payment_type': "outbound",
                  'default_date': self.date,
                  'default_amount':self.invoice_ref.amount_total,
                  'default_direct_labour_id':self.id,
                  'default_partner_id':self.invoice_ref.partner_id.id,
                  'default_communication':self.invoice_ref.number
              },
        }'''
    @api.multi
    def button_send_payments(self):# Send memo back
        return {
              'name': ' Labour Payment',
              'view_type': 'form',
              "view_mode": 'form',
              'res_model': 'account.payment',
              'type': 'ir.actions.act_window',
              'target': 'current',
              'context': {
                  'default_payment_type': "outbound",
                  'default_date': self.date,
                  'default_amount':self.amountfig,
                  'default_direct_labour_idx':self.id,
                  'default_partner_id':self.partner_id.id,
                  #'default_communication':self.number
              },
        }

        '''body = "The Imprest is on payment process by Accounts on %s" % (datetime.strftime(datetime.today(), '%d-%m-%y'))
        records = self._get_followers()
        followers = records
        self.message_post(body=body, subtype='mt_comment',message_type='notification',partner_ids=followers)

        email_from = self.env.user.email
        email_to = self.employee_id.work_email
        bodyx = "Dear Sir/Madam, </br>We wish to notify you that an Imprest from {} is on payment process</br> </br>Thanks".format(self.employee_id.name)

        self.mail_sending(email_from,email_to,bodyx)   '''

        return ret


    @api.multi
    def auto_create_schedule(self):
        schedule = self.env['payment.schedule']
        for rec in self:
            vals = {}
            vals['pay_amount'] = rec.amountfig
            vals['date_sche'] = fields.Date.today()
            vals['name'] = rec.partner_id.id
            vals['select_mode'] = "lab"
            vals['labour_ref'] = rec.id
            vals['product_qty'] = rec.product_qty

            schedule.create(vals)

    @api.multi
    def auto_create_schedule2(self):
        schedule = self.env['payment.schedule']
        for rec in self:
            vals = {'pay_amount':rec.amountfig,'date_sche':fields.Date.today(),'name':rec.partner_id.id}

            schedule.create(vals)









    @api.multi
    def refuse_gm(self): #vis_account,

        return {
              'name': 'Reason for Refusal',
              'view_type': 'form',
              "view_mode": 'form',
              'res_model': 'dl.messagex',
              'type': 'ir.actions.act_window',
              'target': 'new',
              'context': {
                  'default_memo_record': self.id,
                  'default_date': self.date
              },
        }

    @api.multi
    def refuse_coo(self): #vis_account,

        return {
              'name': 'Reason for Refusal',
              'view_type': 'form',
              "view_mode": 'form',
              'res_model': 'dl.message',
              'type': 'ir.actions.act_window',
              'target': 'new',
              'context': {
                  'default_memo_record': self.id,
                  'default_date': self.date
              },
        }

    @api.multi
    def set_draft(self):
        self.write({'state':'sm'})

    @api.multi
    def submit_Pm_qs(self):
        return self.send_Sm_to_Sup()

    @api.multi
    def submit_qs_gm(self):
        return self.send_sup_to_teamhead()

    def Sendteam_pm(self):
        return self.send_team_to_pm()

    @api.multi
    def Sendpm_sm2(self):
        return self.send_pm_to_audit()



    @api.multi
    def submitAudit_SM(self):
        return self.send_aud_to_site_manager()


    @api.multi
    def submitCooAcc(self):
        self.write({'state':"account"})
        return self.auto_create_schedule()

######
    @api.multi
    def account_payment(self):
        return self.button_send_payments()
    @api.multi


    @api.multi
    def account_account_to_audit2(self):
        return self.coo_account_to_audit2()

    @api.multi
    def audit2_accountx(self):
        return self.coo_audit_to_accountx()
######



class Dl_Message_back(models.Model):
    _name="dl.refused.wizardx"

    resp=fields.Many2one('res.users','Responsible')#, default=self.write_uid.id)
    memo_record = fields.Many2one('direct.labourx','Memo ID',)
    reason = fields.Char('Reason')#<tree string="Memo Payments" colors="red:state == 'account';black:state == 'manager';green:state == 'coo';grey:state == 'refused';">

    date = fields.Datetime('Date')
    direct_memo_user = fields.Many2one('hr.employee', 'Initiator')


    @api.multi
    def post_back(self):
        email_from = self.env.user.email
        email_to = self.direct_memo_user.work_email

        get_state = self.env['direct.labourx'].search([('id','=', self.memo_record.id)])
        reasons = "<b><h4>From %s </br></br>Please refer to the reasons below </br> %s.</h4></b>" %(self.env.user.name,self.reason)
        get_state.write({'reason_back':reasons})
        #get_state.direct_mail_sending(self, email_from, email_to, bodyx)
        #self._change_state()
        get_state.direct_mail_sending(email_from,email_to,reasons)
        get_state.write({'state':'refused'})

        return{'type': 'ir.actions.act_window_close'}

class PurchaseOrder(models.Model):
    _inherit = "purchase.order"
    _order = "id desc"

    note = fields.Text(string = 'Note')

    state = fields.Selection([
        ('officer', 'Officer'),
        ('pm', 'PM'),
        ('draft', 'RFQ'),
        ('sent', 'RFQ Sent'),
        ('to approve', 'To Approve'),
        ('purchase', 'Purchase Order'),
        ('done', 'Locked'),
        ('cancel', 'Cancelled'),
        ], string='Status', readonly=True, index=True, copy=False, default='officer', track_visibility='onchange')

    @api.multi
    def button_request_approval_by_officer(self):# Request for approval by officer   ####state:officer, group:procurement officer
        for rec in self:
            rec.write({'state':'draft'})



    @api.multi
    def button_confirm(self): ####state:draft, group:procurement manager

        res = super(PurchaseOrder, self).button_confirm()

        self.action_rfq_send()
        return res

