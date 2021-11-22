Select distinct SALESINVOICE_BUSINESSLOCATION.id as bl_id,
    SALESINVOICE_BUSINESSLOCATION.LocationName,
    SalesInvoice.Date,
    SalesInvoice.InvNumber,
    SalesInvoice_InvoiceItem_Item.Name,
    SalesInvoice_InvoiceItem.Quantity,
    SalesInvoice_InvoiceItem.TotalAmount*SalesInvoice_InvoiceItem.ConversionRate as TotalAmount,
    SalesInvoice_InvoiceItem_Item_Category.Name as CategoryName,
    SalesInvoice_InvoiceItem.Barcode,
    ITEM_SKU_LOOKUP.Name as product_sku,
    SalesInvoice_CUSTOMER.Name as CustomerName,
    SalesInvoice_CUSTOMER_ADDRESS_CONTACT.MobileNumber As MobileNumber,
    SalesInvoice.SpotDiscountAmount as Discount
    from tbl_DYN_SalesInvoices SalesInvoice
    Left outer join tbl_DYN_SALESINVOICEs_INVOICEITEMs SalesInvoice_INVOICEITEMs on SalesInvoice_INVOICEITEMs.SALESINVOICEId = SalesInvoice.Id
    Left outer join tbl_DYN_InvoiceItems_ITEMs SALESINVOICE_INVOICEITEM_ITEMs on SALESINVOICE_INVOICEITEM_ITEMs.InvoiceItemId = SalesInvoice_INVOICEITEMs.INVOICEITEMId
    Left outer join tbl_DYN_Items SALESINVOICE_INVOICEITEM_ITEM on SALESINVOICE_INVOICEITEM_ITEM.Id = SALESINVOICE_INVOICEITEM_ITEMs.ITEMId
    Left outer join tbl_DYN_InvoiceItems SALESINVOICE_INVOICEITEM on SALESINVOICE_INVOICEITEM.Id = SalesInvoice_INVOICEITEMs.INVOICEITEMId
    Left outer join tbl_DYN_Items_CATEGORies SALESINVOICE_INVOICEITEM_ITEM_CATEGORies on SALESINVOICE_INVOICEITEM_ITEM_CATEGORies.ItemId = SALESINVOICE_INVOICEITEM_ITEMs.ITEMId
    Left outer join tbl_DYN_Categories SALESINVOICE_INVOICEITEM_ITEM_CATEGORY on SALESINVOICE_INVOICEITEM_ITEM_CATEGORY.Id = SALESINVOICE_INVOICEITEM_ITEM_CATEGORies.CATEGORYId
    Left outer join tbl_DYN_SALESINVOICEs_BUSINESSLOCATIONs SalesInvoice_BUSINESSLOCATIONs on SalesInvoice_BUSINESSLOCATIONs.SALESINVOICEId = SalesInvoice.Id
    Left outer join tbl_DYN_BusinessLocations SALESINVOICE_BUSINESSLOCATION on SALESINVOICE_BUSINESSLOCATION.Id = SalesInvoice_BUSINESSLOCATIONs.BUSINESSLOCATIONId
    Left outer join tbl_DYN_SalesInvoices_Customers SalesInvoices_CUSTOMERs on SalesInvoices_CUSTOMERs.SalesInvoiceId = SalesInvoice.Id
    Left outer join tbl_DYN_Customers SalesInvoice_CUSTOMER on SalesInvoice_CUSTOMER.Id = SalesInvoices_CUSTOMERs.CUSTOMERId
    Left outer join tbl_DYN_Customers_ADDRESSes SalesInvoice_CUSTOMER_ADDRESSes on SalesInvoice_CUSTOMER_ADDRESSes.CustomerId = SalesInvoices_CUSTOMERs.CUSTOMERId
    Left outer join tbl_DYN_Addresses_CONTACTs SalesInvoice_CUSTOMER_ADDRESS_CONTACTs on SalesInvoice_CUSTOMER_ADDRESS_CONTACTs.AddressId = SalesInvoice_CUSTOMER_ADDRESSes.ADDRESSId
    Left outer join tbl_DYN_Contacts SalesInvoice_CUSTOMER_ADDRESS_CONTACT on SalesInvoice_CUSTOMER_ADDRESS_CONTACT.Id = SalesInvoice_CUSTOMER_ADDRESS_CONTACTs.CONTACTId
    Left outer join tbl_DYN_Items_UserFieldDatas ITEM_INFO on SALESINVOICE_INVOICEITEM_ITEM.Id=ITEM_INFO.ItemId
    Left outer join tbl_DYN_UserFieldDatas_ufSellerSKUIDs ITEM_SKU_INFO on ITEM_INFO.UserFieldDataId=ITEM_SKU_INFO.UserFieldDataId
    Left outer join tbl_DYN_LookupValues ITEM_SKU_LOOKUP on ITEM_SKU_INFO.ufSellerSKUIDId = ITEM_SKU_LOOKUP.Id
    where SALESINVOICE.INVNUMBER is not null and SalesInvoice.InvNumber !='' and
    convert(datetime,SalesInvoice.date) >= '{}' and convert(datetime,SalesInvoice.date) < '{}'