import psycopg2
import psycopg2.extras

conn = psycopg2.connect(
    host="localhost",
    database="prod_copy",
    user="gramfac18",
    password="12345")
cur = conn.cursor(cursor_factory=psycopg2.extras.NamedTupleCursor)

query = "select ps.id as slab_id, ps.product_price_id, pp.selling_price, ps.selling_price as slab_selling_price, ppo.inner_case_size from products_productprice pp"\
        " inner join products_priceslab ps on pp.id=ps.product_price_id" \
	" inner join products_product p on p.id=pp.product_id" \
	" inner join products_parentproduct ppo on ppo.id=p.parent_product_id"

print(query)
cur.execute(query)
rows = cur.fetchall()
selling_prices_to_update={}
for row in rows:
    if row.selling_price is None and row.inner_case_size is not None:
        selling_prices_to_update[row.slab_id] = round(row.slab_selling_price/row.inner_case_size, 2)
    else:        
        selling_prices_to_update[row.slab_id] = row.selling_price
for key,value in selling_prices_to_update.items():
    query = "update products_priceslab set selling_price = "+ str(value) +" where id = "+ str(key)
    print(query)
    cur.execute(query)
    conn.commit()
    count = cur.rowcount
    print(count, "Record Updated successfully ")

if (conn):
    cur.close()
    print("PostgreSQL connection is closed")
