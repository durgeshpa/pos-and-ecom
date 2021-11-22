import codecs
import csv

from products.master_data import UploadMasterData, DownloadMasterData
from products.common_validators import get_csv_file_data


def create_update_master_data(validated_data):
    csv_file = csv.reader(codecs.iterdecode(validated_data['file'], 'utf-8', errors='ignore'))
    excel_file_header_list = next(csv_file)  # headers of the uploaded csv file
    # Converting headers into lowercase
    excel_file_headers = [str(ele).lower() for ele in excel_file_header_list]

    uploaded_data_by_user_list = get_csv_file_data(csv_file, excel_file_headers)
    # update bulk
    if validated_data['upload_type'] == "product_status_update_inactive":
        UploadMasterData.set_inactive_status(uploaded_data_by_user_list, validated_data['updated_by'])
    if validated_data['upload_type'] == "sub_brand_with_brand_mapping":
        UploadMasterData.set_sub_brand_and_brand(uploaded_data_by_user_list, validated_data['updated_by'])
    if validated_data['upload_type'] == "sub_category_with_category_mapping":
        UploadMasterData.set_sub_category_and_category(uploaded_data_by_user_list, validated_data['updated_by'])
    if validated_data['upload_type'] == "child_parent_product_update":
        UploadMasterData.set_child_parent(uploaded_data_by_user_list, validated_data['updated_by'])
    if validated_data['upload_type'] == "product_tax_update":
        UploadMasterData.set_product_tax(uploaded_data_by_user_list, validated_data['updated_by'])

    if validated_data['upload_type'] == "child_product_update":
        UploadMasterData.update_child_data(uploaded_data_by_user_list, validated_data['updated_by'])
    if validated_data['upload_type'] == "parent_product_update":
        UploadMasterData.update_parent_data(uploaded_data_by_user_list, validated_data['updated_by'])
    if validated_data['upload_type'] == "brand_update":
        UploadMasterData.update_brand_data(uploaded_data_by_user_list, validated_data['updated_by'])
    if validated_data['upload_type'] == "category_update":
        UploadMasterData.update_category_data(uploaded_data_by_user_list, validated_data['updated_by'])

    # create bulk
    if validated_data['upload_type'] == "create_child_product":
        UploadMasterData.create_bulk_child_product(uploaded_data_by_user_list, validated_data['updated_by'])
    if validated_data['upload_type'] == "create_parent_product":
        UploadMasterData.create_bulk_parent_product(uploaded_data_by_user_list, validated_data['updated_by'])
    if validated_data['upload_type'] == "create_category":
        UploadMasterData.create_bulk_category(uploaded_data_by_user_list, validated_data['updated_by'])
    if validated_data['upload_type'] == "create_brand":
        UploadMasterData.create_bulk_brand(uploaded_data_by_user_list, validated_data['updated_by'])


def download_sample_file_update_master_data(validated_data):
    # update bulk sample
    if validated_data['upload_type'] == "product_status_update_inactive":
        response = DownloadMasterData.set_inactive_status_sample_file(validated_data)
    if validated_data['upload_type'] == "sub_brand_with_brand_mapping":
        response = DownloadMasterData.set_brand_sub_brand_mapping_sample_file()
    if validated_data['upload_type'] == "sub_category_with_category_mapping":
        response = DownloadMasterData.set_category_sub_category_mapping_sample_file()
    if validated_data['upload_type'] == "product_tax_update":
        response = DownloadMasterData.set_product_tax_sample_file(validated_data)
    if validated_data['upload_type'] == "child_parent_product_update":
        response = DownloadMasterData.update_child_with_parent_sample_file(validated_data)

    # update bulk sample
    if validated_data['upload_type'] == "parent_product_update":
        response = DownloadMasterData.update_parent_product_sample_file(validated_data)
    if validated_data['upload_type'] == "child_product_update":
        response = DownloadMasterData.update_child_product_sample_file(validated_data)
    if validated_data['upload_type'] == "category_update":
        response = DownloadMasterData.update_category_sample_file(validated_data)
    if validated_data['upload_type'] == "brand_update":
        response = DownloadMasterData.update_brand_sample_file(validated_data)

    # create bulk sample
    if validated_data['upload_type'] == "create_child_product":
        response = DownloadMasterData.create_child_product_sample_file(validated_data)
    if validated_data['upload_type'] == "create_parent_product":
        response = DownloadMasterData.create_parent_product_sample_file(validated_data)
    if validated_data['upload_type'] == "create_brand":
        response = DownloadMasterData.create_brand_sample_file(validated_data)
    if validated_data['upload_type'] == "create_category":
        response = DownloadMasterData.create_category_sample_file(validated_data)

    return response

