Select ITEM_SKU_LOOKUP.Name as product_sku
from tbl_DYN_Items Item
Left outer join tbl_DYN_Items_UserFieldDatas ITEM_INFO on Item.Id=ITEM_INFO.ItemId
Left outer join tbl_DYN_UserFieldDatas_ufSellerSKUIDs ITEM_SKU_INFO on ITEM_INFO.UserFieldDataId=ITEM_SKU_INFO.UserFieldDataId
Left outer join tbl_DYN_LookupValues ITEM_SKU_LOOKUP on ITEM_SKU_INFO.ufSellerSKUIDId = ITEM_SKU_LOOKUP.Id
where Item.Barcode=
