Select Distinct SalesReturn.Date as SR_Date,
    SalesReturn.Number as SR_Number,
    SalesReturn_SalesReturnItem_Item.Name,
    -(SalesReturn_SalesReturnItem.Quantity) as ItemtotalQty,
    (SalesReturn_SalesReturnItem.TotalAmount) as TotalAmount,
    SalesReturn_SalesReturnItem_Item_Category.Name as CategoryName,
    SalesReturn_SalesReturnItem_Item.Barcode,
    SalesReturn_BusinessLocation.Id as bl_id,
    SalesReturn_BusinessLocation.LocationName as BS_Location_Name,
    SalesReturn_SalesInvoice.Date,
    SalesReturn_SalesInvoice.InvNumber,
    ITEM_SKU_LOOKUP.Name as product_sku,
    SalesReturn_Customer.Name as CustomerName,
    SalesReturn_Customer_Address_Contact.MobileNumber As MobileNumber
    from tbl_DYN_SalesReturns SalesReturn
    Left outer join tbl_DYN_SALESRETURNs_SALESRETURNITEMs SalesReturn_SALESRETURNITEMs on SalesReturn_SALESRETURNITEMs.SALESRETURNId = SalesReturn.Id
    Left outer join tbl_DYN_InvoiceItems_ITEMs SALESRETURN_SALESRETURNITEM_ITEMs on SALESRETURN_SALESRETURNITEM_ITEMs.InvoiceItemId = SalesReturn_SALESRETURNITEMs.SALESRETURNITEMId
    Left outer join tbl_DYN_Items SALESRETURN_SALESRETURNITEM_ITEM on SALESRETURN_SALESRETURNITEM_ITEM.Id = SALESRETURN_SALESRETURNITEM_ITEMs.ITEMId
    Left outer join tbl_DYN_InvoiceItems SALESRETURN_SALESRETURNITEM on SALESRETURN_SALESRETURNITEM.Id = SalesReturn_SALESRETURNITEMs.SALESRETURNITEMId
    Left outer join tbl_DYN_Items_CATEGORies SALESRETURN_SALESRETURNITEM_ITEM_CATEGORies on SALESRETURN_SALESRETURNITEM_ITEM_CATEGORies.ItemId = SALESRETURN_SALESRETURNITEM_ITEMs.ITEMId
    Left outer join tbl_DYN_Categories SALESRETURN_SALESRETURNITEM_ITEM_CATEGORY on SALESRETURN_SALESRETURNITEM_ITEM_CATEGORY.Id = SALESRETURN_SALESRETURNITEM_ITEM_CATEGORies.CATEGORYId
    Left outer join tbl_DYN_SALESRETURNs_BUSINESSLOCATIONs SalesReturn_BUSINESSLOCATIONs on SalesReturn_BUSINESSLOCATIONs.SALESRETURNId = SalesReturn.Id
    Left outer join tbl_DYN_BusinessLocations SALESRETURN_BUSINESSLOCATION on SALESRETURN_BUSINESSLOCATION.Id = SalesReturn_BUSINESSLOCATIONs.BUSINESSLOCATIONId
    Left outer join tbl_DYN_SALESRETURNs_SALESINVOICEs SalesReturn_SALESINVOICEs on SalesReturn_SALESINVOICEs.SALESRETURNId = SalesReturn.Id
    Left outer join tbl_DYN_SalesInvoices SALESRETURN_SALESINVOICE on SALESRETURN_SALESINVOICE.Id = SalesReturn_SALESINVOICEs.SALESINVOICEId
    Left outer join tbl_DYN_SALESRETURNs_CUSTOMERs SalesReturn_CUSTOMERs on SalesReturn_CUSTOMERs.SALESRETURNId = SalesReturn.Id
    Left outer join tbl_DYN_Customers SALESRETURN_CUSTOMER on SALESRETURN_CUSTOMER.Id = SalesReturn_CUSTOMERs.CUSTOMERId
    Left outer join tbl_DYN_Customers_ADDRESSes SALESRETURN_CUSTOMER_ADDRESSes on SALESRETURN_CUSTOMER_ADDRESSes.CustomerId = SalesReturn_CUSTOMERs.CUSTOMERId
    Left outer join tbl_DYN_Addresses_CONTACTs SALESRETURN_CUSTOMER_ADDRESS_CONTACTs on SALESRETURN_CUSTOMER_ADDRESS_CONTACTs.AddressId = SALESRETURN_CUSTOMER_ADDRESSes.ADDRESSId
    Left outer join tbl_DYN_Contacts SALESRETURN_CUSTOMER_ADDRESS_CONTACT on SALESRETURN_CUSTOMER_ADDRESS_CONTACT.Id = SALESRETURN_CUSTOMER_ADDRESS_CONTACTs.CONTACTId
    Left outer join tbl_DYN_Items_UserFieldDatas ITEM_INFO on SALESRETURN_SALESRETURNITEM_ITEM.Id=ITEM_INFO.ItemId
    Left outer join tbl_DYN_UserFieldDatas_ufSellerSKUIDs ITEM_SKU_INFO on ITEM_INFO.UserFieldDataId=ITEM_SKU_INFO.UserFieldDataId
    Left outer join tbl_DYN_LookupValues ITEM_SKU_LOOKUP on ITEM_SKU_INFO.ufSellerSKUIDId = ITEM_SKU_LOOKUP.Id
    where convert(datetime,SalesReturn.date) >= '{}' and convert(datetime,SalesReturn.date) < '{}'