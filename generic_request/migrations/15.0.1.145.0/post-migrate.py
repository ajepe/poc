def migrate(cr, installed_version):
    cr.execute("""
        UPDATE res_company
        SET request_mail_create_author_contact_from_email = TRUE,
            request_mail_create_cc_contact_from_email = TRUE,
            request_mail_auto_subscribe_cc_contacts = TRUE
        WHERE request_mail_create_partner_from_email = TRUE;
        """)
