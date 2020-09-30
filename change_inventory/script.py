import csv

with open('input.csv', 'r') as inputfile:
    reader = csv.reader(inputfile)
    next(reader)

    count = 0


    for row in reader:

        if count % 1000 == 0:
            output_file = 'output_' + str(int(count / 1000))+'.csv'
            print(count)
            print(output_file)
            with open(output_file, 'w') as outputfile:
                writer = csv.writer(outputfile)
                header_row = ['Warehouse ID', 'Product Name', 'SKU', 'Expiry Date', 'Bin ID', 'Inventory Movement Type',
                               'Normal Quantity',
                               'Damaged Quantity', 'Expired Quantity', 'Missing Quantity']
                writer.writerow(header_row)
                temp_count=0
                reader1 = reader
                print(reader1)
                break;
                # for row1 in reader1:
                #     if temp_count < count:
                #         temp_count+=1
                #         continue
                #     if temp_count > count+1000:
                #         break
                #     writer_row = [32154, row1[1], row1[2], '31/03/21', 'V2VZ01SR001-0001', 'In',
                #                       row1[3], row1[4], row1[5], 0]
                #     writer.writerow(writer_row)
                #     temp_count += 1
        count += 1
