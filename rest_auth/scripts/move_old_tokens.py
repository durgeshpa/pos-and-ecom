def run():
    from django.db import connection
    with connection.cursor() as cursor:
        cursor.execute("insert into rest_auth_token (key, user_id, created, name, phone) \
            select key, user_id, created, substring(au.first_name,1,64), au.phone_number  from authtoken_token at \
                left join accounts_user au on au.id = user_id;")