from django.contrib import admin

class InputFilter(admin.SimpleListFilter):
    template = 'admin/input_filter.html'

    def lookups(self, request, model_admin):
        # Dummy, required to show the filter.
        return ((),)

    def choices(self, changelist):
        # Grab only the "all" option.
        all_choice = next(super().choices(changelist))
        all_choice['query_parts'] = (
            (k, v)
            for k, v in changelist.get_filters_params().items()
            if k != self.parameter_name
        )
        yield all_choice


class SelectInputFilter(admin.SimpleListFilter):
    template = 'admin/select_input_filter.html'

    def lookups(self, request, model_admin):
        # Dummy, required to show the filter.
        return ((),)

    def choices(self, changelist):
        # Grab only the "all" option.
        all_choice = next(super().choices(changelist))
        all_choice['query_parts'] = (
            (k, v)
            for k, v in changelist.get_filters_params().items()
            if k != self.parameter_name
        )
        yield all_choice




class ExportCsvMixin:
    def export_as_csv(self, request, queryset):
        meta = self.model._meta
        exclude_fields = ['created_at', 'modified_at']
        field_names = [field.name for field in meta.fields if field.name not in exclude_fields]
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename={}.csv'.format(meta)
        writer = csv.writer(response)
        if self.model._meta.db_table=='products_product':
            field_names_temp = field_names.copy()
            field_names_temp.append('product_brand')
            field_names_temp.append('product_category')
            field_names_temp.append('image')
            writer.writerow(field_names_temp)
        else:
            writer.writerow(field_names)
        for obj in queryset:
            items= [getattr(obj, field) for field in field_names]
            if self.model._meta.db_table == 'products_product':
                items.append(obj.product_brand)
                items.append(self.product_category(obj))
                if obj.use_parent_image and obj.parent_product.parent_product_pro_image.last():
                    items.append(obj.parent_product.parent_product_pro_image.last().image.url)
                elif obj.product_pro_image.last():
                    items.append(obj.product_pro_image.last().image.url)
                else:
                    items.append('-')
            row = writer.writerow(items)
        return response
    export_as_csv.short_description = "Download CSV of Selected Objects"