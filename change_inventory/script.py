import csv


with open('input.csv', 'r') as inputfile:
    with open('output.csv', 'w') as outputfile:
        reader = csv.reader(inputfile)
        writer = csv.writer(outputfile)
        next(reader)
        header_row = ['Warehouse ID','Product Name','SKU','Expiry Date','Bin ID','Inventory Movement Type','Normal Quantity',
                      'Damaged Quantity','Expired Quantity','Missing Quantity']
        writer.writerow(header_row)
        count = 0
        for row in reader:

            print(row)
            if int(row[3])+int(row[4])+int(row[5]) != 0:
                continue
            writer_row = [32154,row[1],row[2],'31/03/21','V2VZ01SR001-0001','In',
                          1,row[4],row[5],0]
            count += 1

            if count < 2000:
                continue
            writer.writerow(writer_row)