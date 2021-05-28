from ars.views import initiate_ars, create_po, mail_category_manager_for_po_approval


def run():
    print('create_ars_po|started')
    # initiate_ars()
    print('create_ars_po|initiate_ars done')
    create_po()
    print('create_ars_po|create_po done')
    mail_category_manager_for_po_approval()
    print('create_ars_po|ended')