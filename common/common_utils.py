import datetime


def convert_date_format_ddmmmyyyy(scheduled_date):
    #This function converts %Y-%m-%d datetime format to a DD/MMM/YYYY 

    #logging.info("converting date format from %d/%m/%Y to %Y-%m-%d")
    return datetime.datetime.strptime(scheduled_date,'%Y-%m-%d').strftime("%d/%b/%Y").__str__()
