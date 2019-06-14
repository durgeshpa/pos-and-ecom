import datetime


def convert_date_format_ddmmmyyyy(scheduled_date):
    #This function converts %d/%m/%Y datetime format to a DD/MMM/YYYY 
    #format and returns a string for the same.

    #logging.info("converting date format from %d/%m/%Y to %Y-%m-%d")
    return datetime.datetime.strptime(scheduled_date,'%d/%m/%Y').strftime("%d/%b/%Y").__str__()
