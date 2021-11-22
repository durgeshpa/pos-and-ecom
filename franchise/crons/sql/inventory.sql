Select inv.*,sales.Net_Quantity as Last90daysaleqty
FROM

(Select Final.warehouse_name as Shop_name,final.warehouse_id,final.Barcode,
Final.item_id,
 Final.product_sku,final.product_name,final.category,final.HSNSAC as hsn,
 final.Tax_structure,
case
when final.tax_structure ='In State GST 0 %' then 'GST-0'
when final.tax_structure ='In State GST 5 %' then 'GST-5'
when final.tax_structure ='In State GST 12 %' then 'GST-12'
when final.tax_structure ='In State GST 18 %' then 'GST-18'
when final.tax_structure ='In State GST 28 %' then 'GST-28'
when final.tax_structure ='In State GST 28 % + Cess 12%' then 'GST-40'
when final.tax_structure ='In State GST 40 %' then 'GST-40'
else null end as GST_flag,
 final.MRP,

 case when  final.PTC=0 then Final.MRP else Final.PTC end as PTC,
final.quantity as Realtime_available_qty



from

(
Select realtime.*,latest.mrp,latest.PTC,ITEM_SKU_LOOKUP.Name as product_sku,items.HSNSAC,tax_stru.name as Tax_structure,cat.Name as category

--,pri.MRP
from
(Select a.* from
(SELECT warehouse.Id as warehouse_id,warehouse.Name as warehouse_name,items.id as item_id,items.Barcode,items.Name as product_name,sum(quickstocks.Quantity) as quantity


FROM [HDERPData].[dbo].[tbl_DYN_QuickStocks] quickstocks
LEFT JOIN [HDERPData].[dbo].[tbl_DYN_Warehouses] warehouse on quickstocks.WarehouseNumber=warehouse.Id
LEFT join [HDERPData].[dbo].[tbl_DYN_Items] items on quickstocks.ItemNumber=items.id

where warehouse.name not like '%Correction%' and warehouse.name not like '%Temp%'
group by warehouse.Id,warehouse.Name,items.id,items.Barcode,items.Name)a
where quantity>0

)realtime
left join

(Select b.warehouse_id,b.warehouse_name,b.ItemId,b.mrp,sum(case when flag='PTF' then SalesPrice else  0 end)  as PTF,
sum(case when flag='PTC' then SalesPrice else  0 end)  as PTC
from
(Select a.warehouse_id,a.warehouse_name,a.ItemId,a.flag,a.mrp,a.salesprice,
ROW_NUMBER()OVER(partition by a.itemid,a.warehouse_id,a.flag order by a.date desc) as rank
from

(SELECT distinct(i1.creationdate) as date,warehouse.id as warehouse_id,warehouse.name as warehouse_name,i1.ItemId ,i6.SalesPrice,i6.MRP,
case when pl.CustomerGroupId is null then 'PTC' else 'PTF' end as flag
  FROM [HDERPData].[dbo].[tbl_DYN_ItemPrices_Items] i1
left join [HDERPData].[dbo].tbl_dyn_items i2 on i1.ItemId= i2.id
left join [HDERPData].[dbo].[tbl_DYN_PriceLists_ItemPrices] i3 on i1.ItemPriceId=i3.ItemPriceId
left join [HDERPData].[dbo].[tbl_DYN_PriceLists_BusinessLocations] i4 on i3.PriceListId=i4.PriceListId
Left join [HDERPData].[dbo].[tbl_DYN_PriceLists_CustomerGroups] pl on i3.PriceListId= pl.PriceListId
left join [HDERPData].[dbo].[tbl_DYN_BusinessLocations] BL on i4.BusinessLocationId=bl.id
LEFT JOIN [HDERPData].[dbo].[tbl_DYN_Warehouses_BusinessLocations] wbl on bl.id=wbl.BusinessLocationId
left join [HDERPData].[dbo].[tbl_DYN_Warehouses] warehouse on wbl.WarehouseId= warehouse.Id
left join [HDERPData].[dbo].[tbl_DYN_ItemPrices] i6 on i1.ItemPriceId=i6.Id
where warehouse.name  not like '%GFDN%' and warehouse.name not like '%Stock Correction%')a
)b
where B.rank=1
group by  b.warehouse_id,b.warehouse_name,b.ItemId,b.mrp
)latest
on realtime.warehouse_id= latest.warehouse_id and realtime.item_id=latest.ItemId

Left outer join tbl_DYN_Items_UserFieldDatas ITEM_INFO on realtime.item_id=ITEM_INFO.ItemId
Left outer join tbl_DYN_UserFieldDatas_ufSellerSKUIDs ITEM_SKU_INFO on ITEM_INFO.UserFieldDataId=ITEM_SKU_INFO.UserFieldDataId
Left outer join tbl_DYN_LookupValues ITEM_SKU_LOOKUP on ITEM_SKU_INFO.ufSellerSKUIDId = ITEM_SKU_LOOKUP.Id

LEFT JOIN [HDERPData].[dbo].tbl_dyn_items items on realtime.item_id= items.Id
  LEFT JOIN  [HDERPData].[dbo].[tbl_DYN_Items_SalesTaxStructures] salestax on items.id=salestax.ItemId
    LEFT JOIN  [HDERPData].[dbo].[tbl_DYN_TaxStructures] tax_stru on salestax.SalesTaxStructureId= tax_stru.Id
    LEFT JOIN [HDERPData].[dbo].[tbl_dyn_items_Categories] itcat on items.id= itcat.ItemId
LEFT JOIN [HDERPData].[dbo].[tbl_DYN_Categories] cat on itcat.CategoryId=cat.Id
)Final
) Inv

/*LAST 3 Months Sale */
LEFT JOIN

(Select
--convert(date,a.date) as DATE,
id as itemid,
warehouseid,
a.LocationName,
a.name,a.barcode,round(round(sum(A.Quantity)-SUM(A.ReturnQuantity),0),0) as Net_Quantity,
round(sum(A.TotalAmount)-SUM(A.ReturnAmount),0) as Net_Sales_Amount




from


(Select distinct SALESINVOICE_BUSINESSLOCATION.id as bl_id,SALESINVOICE_BUSINESSLOCATION.LocationName,SALESINVOICE_INVOICEITEM_ITEM.Id,SalesInvoice.Date,wbl.WarehouseId, SalesInvoice.InvNumber, SalesInvoice_InvoiceItem_Item.Name, SalesInvoice_InvoiceItem.Quantity,SalesInvoice_InvoiceItem.ReturnQuantity,
 SalesInvoice_InvoiceItem.TotalAmount*SalesInvoice_InvoiceItem.ConversionRate as TotalAmount,
 SalesInvoice_InvoiceItem.ReturnItemTotalPrice*SalesInvoice_InvoiceItem.ConversionRate as ReturnAmount,


     SalesInvoice_InvoiceItem_Item_Category.Name as CategoryName, SalesInvoice_InvoiceItem.Barcode, SalesInvoice_Customer.Name as CustomerName
    from tbl_DYN_SalesInvoices SalesInvoice
    Left outer join tbl_DYN_SALESINVOICEs_INVOICEITEMs SalesInvoice_INVOICEITEMs on SalesInvoice_INVOICEITEMs.SALESINVOICEId = SalesInvoice.Id
    Left outer join tbl_DYN_InvoiceItems_ITEMs SALESINVOICE_INVOICEITEM_ITEMs on SALESINVOICE_INVOICEITEM_ITEMs.InvoiceItemId = SalesInvoice_INVOICEITEMs.INVOICEITEMId
    Left outer join tbl_DYN_Items SALESINVOICE_INVOICEITEM_ITEM on SALESINVOICE_INVOICEITEM_ITEM.Id = SALESINVOICE_INVOICEITEM_ITEMs.ITEMId
    Left outer join tbl_DYN_InvoiceItems SALESINVOICE_INVOICEITEM on SALESINVOICE_INVOICEITEM.Id = SalesInvoice_INVOICEITEMs.INVOICEITEMId
    Left outer join tbl_DYN_Items_CATEGORies SALESINVOICE_INVOICEITEM_ITEM_CATEGORies on SALESINVOICE_INVOICEITEM_ITEM_CATEGORies.ItemId = SALESINVOICE_INVOICEITEM_ITEMs.ITEMId
    Left outer join tbl_DYN_Categories SALESINVOICE_INVOICEITEM_ITEM_CATEGORY on SALESINVOICE_INVOICEITEM_ITEM_CATEGORY.Id = SALESINVOICE_INVOICEITEM_ITEM_CATEGORies.CATEGORYId
    Left outer join tbl_DYN_SALESINVOICEs_CUSTOMERs SalesInvoice_CUSTOMERs on SalesInvoice_CUSTOMERs.SALESINVOICEId = SalesInvoice.Id
    Left outer join tbl_DYN_Customers SALESINVOICE_CUSTOMER on SALESINVOICE_CUSTOMER.Id = SalesInvoice_CUSTOMERs.CUSTOMERId
    Left outer join tbl_DYN_SALESINVOICEs_BUSINESSLOCATIONs SalesInvoice_BUSINESSLOCATIONs on SalesInvoice_BUSINESSLOCATIONs.SALESINVOICEId = SalesInvoice.Id
    Left outer join tbl_DYN_BusinessLocations SALESINVOICE_BUSINESSLOCATION on SALESINVOICE_BUSINESSLOCATION.Id = SalesInvoice_BUSINESSLOCATIONs.BUSINESSLOCATIONId
    LEFT outer join     [HDERPData].[dbo].[tbl_DYN_Warehouses_BusinessLocations] wbl on SALESINVOICE_BUSINESSLOCATION.Id=wbl.BusinessLocationId
    where SALESINVOICE.INVNUMBER is not null and SalesInvoice.InvNumber !='' and
    convert(date,SalesInvoice.date) BETWEEN  convert(date,GETDATE()-90) and convert(date,GETDATE())
    --and SalesInvoice_InvoiceItem.returnQuantity>0
    and SalesInvoice_Customer.Name not like '%GFDN%'


    --and SALESINVOICE_BUSINESSLOCATION.id='hd-20200204-1224-53135-093-00000-000'
)A
group by
--convert(date,a.date),
a.LocationName,
a.name,a.barcode,warehouseid,id) sales
on inv.item_id= sales.itemid and inv.warehouse_id= sales.WarehouseId
