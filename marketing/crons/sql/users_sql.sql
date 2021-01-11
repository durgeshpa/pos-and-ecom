Select contacts.MobileNumber, contacts.Email, customers.FirstName, customers.LastName
from tbl_DYN_Customers customers
Left outer join tbl_DYN_Customers_ADDRESSes addresses on addresses.CustomerId = customers.Id
Left outer join tbl_DYN_Addresses_CONTACTs address_contact on address_contact.AddressId = addresses.ADDRESSId
Left outer join tbl_DYN_Contacts contacts on contacts.Id = address_contact.CONTACTId