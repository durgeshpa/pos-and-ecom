class UploadMasterData(object):

    @classmethod
    def set_master_data(cls, header_list, excel_file_data_list):
        print(header_list)
        print(excel_file_data_list)

    @classmethod
    def set_inactive_status(cls, header_list, excel_file_data_list):
        pass
        # required_inactive_data_list = ['sku_id', 'status']
        # required_data = False
        # for ele in required_inactive_data_list:
        #     if ele in header_list:
        #         required_data = True
        #     else:
        #         required_data = False
        #         break
        # if required_data:
        #     count = 0
        #     logger.info("Method Start to set Inactive status from excel file")
        #     for row in excel_file_list:
        #         if row['status'] == 'Deactivated':
        #             count += 1
        #             Product.objects.filter(product_sku=row['sku_id']).update(status='deactivated')
        #         else:
        #             continue
        #     logger.info("Inactive row id count :" + str(count))
        #     logger.info("Method Complete to set the Inactive status from excel file")

    @classmethod
    def set_sub_brand_and_brand(cls, header_list, excel_file_data_list):
        print(header_list)
        print(excel_file_data_list)

    @classmethod
    def set_sub_category_and_category(cls, header_list, excel_file_data_list):
        print(header_list)
        print(excel_file_data_list)

    @classmethod
    def set_parent_data(cls, header_list, excel_file_data_list):
        print(header_list)
        print(excel_file_data_list)

    @classmethod
    def set_child_parent(cls, header_list, excel_file_data_list):
        print(header_list)
        print(excel_file_data_list)

    @classmethod
    def set_child_data(cls, header_list, excel_file_data_list):
        print(header_list)
        print(excel_file_data_list)